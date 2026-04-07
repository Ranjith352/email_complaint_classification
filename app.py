from flask import Flask, render_template, redirect, request
from firebase_config import db
from gmail_service import fetch_complaint_emails
from collections import Counter
import os

app = Flask(__name__)

# ---------------- OPTIONAL SYNC ROUTE (SAFE) ----------------
@app.route("/sync")
def sync():
    try:
        fetch_complaint_emails()
        return "Gmail sync successful ✅"
    except Exception as e:
        return f"Sync failed ❌: {e}"

# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    docs = db.collection("complaints").stream()
    complaints = [doc.to_dict() for doc in docs]

    total = len(complaints)
    high = len([c for c in complaints if c.get("urgency") == "High"])
    resolved = len([c for c in complaints if c.get("status") == "Resolved"])

    high_percentage = (high / total * 100) if total else 0
    resolution_rate = (resolved / total * 100) if total else 0

    # Risk Level
    if high_percentage > 40:
        risk = "Critical"
    elif high_percentage > 20:
        risk = "Warning"
    else:
        risk = "Stable"

    # Top Category
    categories = Counter()
    for c in complaints:
        categories[c.get("category", "Unknown")] += 1

    top_category = categories.most_common(1)[0][0] if categories else "None"

    return render_template(
        "dashboard.html",
        total=total,
        high=high,
        high_percentage=round(high_percentage, 1),
        resolution_rate=round(resolution_rate, 1),
        risk_level=risk,
        top_category=top_category
    )

# ---------------- COMPLAINTS ----------------
@app.route("/complaints")
def complaints():
    search = request.args.get("search", "").lower()
    urgency_filter = request.args.get("urgency", "")
    category_filter = request.args.get("category", "")

    docs = db.collection("complaints").stream()
    complaints = []

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        title = str(data.get("title", "")).lower()
        sender = str(data.get("sender", "")).lower()

        if search and search not in title and search not in sender:
            continue

        if urgency_filter and data.get("urgency") != urgency_filter:
            continue

        if category_filter and category_filter not in str(data.get("category")):
            continue

        complaints.append(data)

    return render_template("complaints.html", complaints=complaints, search=search)

# ---------------- RESOLVE ----------------
@app.route("/resolve/<id>")
def resolve(id):
    db.collection("complaints").document(id).update({
        "status": "Resolved"
    })
    return redirect("/complaints")

# ---------------- DEPARTMENT ----------------
@app.route("/department/<dept>")
def department(dept):
    docs = db.collection("complaints").stream()
    filtered = []

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        if dept.lower() in str(data.get("department", "")).lower():
            filtered.append(data)

    return render_template(
        "department.html",
        complaints=filtered,
        department=dept.upper()
    )

# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():
    docs = db.collection("complaints").stream()
    complaints = [doc.to_dict() for doc in docs]

    total = len(complaints)

    open_cases = len([c for c in complaints if c.get("status") == "Open"])
    resolved = len([c for c in complaints if c.get("status") == "Resolved"])

    open_rate = (open_cases / total * 100) if total else 0
    resolution_rate = (resolved / total * 100) if total else 0

    # CATEGORY
    technical = len([c for c in complaints if "technical" in str(c.get("category", "")).lower()])
    security = len([c for c in complaints if "security" in str(c.get("category", "")).lower()])
    billing = len([c for c in complaints if "billing" in str(c.get("category", "")).lower()])
    academic = len([c for c in complaints if "academic" in str(c.get("category", "")).lower()])
    general = len([c for c in complaints if "general" in str(c.get("category", "")).lower()])

    # DEPARTMENT
    it = len([c for c in complaints if "it" in str(c.get("department", "")).lower()])
    finance = len([c for c in complaints if "finance" in str(c.get("department", "")).lower()])
    security_team = len([c for c in complaints if "security" in str(c.get("department", "")).lower()])
    admin = len([c for c in complaints if "admin" in str(c.get("department", "")).lower()])
    support = len([c for c in complaints if "support" in str(c.get("department", "")).lower()])

    # TREND
    trend_counter = Counter()
    for c in complaints:
        date = c.get("date")
        if date:
            trend_counter[date] += 1

    trend_dates = list(trend_counter.keys())
    trend_values = list(trend_counter.values())

    data = {
        "total": total,
        "open_rate": round(open_rate, 1),
        "resolution_rate": round(resolution_rate, 1),

        "technical": technical,
        "security": security,
        "billing": billing,
        "academic": academic,
        "general": general,

        "it": it,
        "finance": finance,
        "security_team": security_team,
        "admin": admin,
        "support": support,

        "trend_dates": trend_dates,
        "trend_values": trend_values
    }

    return render_template("analytics.html", data=data)

# ---------------- RUN (RENDER FIX) ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)