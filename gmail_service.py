import os
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from firebase_config import db
from ai_engine import predict_urgency, predict_category, predict_sentiment

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


# ---------------- GMAIL CONNECTION ----------------
def get_gmail_service():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    return service


# ---------------- DEPARTMENT ROUTING ----------------
def assign_department(category):

    if "Technical" in category:
        return "IT Department"

    elif "Billing" in category:
        return "Finance Department"

    elif "Security" in category:
        return "Security Team"

    elif "Academic" in category:
        return "Administration"

    else:
        return "Customer Support"


# ---------------- FETCH EMAILS ----------------
def fetch_complaint_emails():

    service = get_gmail_service()

    labels = service.users().labels().list(userId='me').execute()
    label_list = labels.get('labels', [])

    complaints_label_id = None

    for label in label_list:
        if label['name'] == "Complaints":
            complaints_label_id = label['id']
            break

    if not complaints_label_id:
        raise Exception("Complaints label not found")

    results = service.users().messages().list(
        userId='me',
        labelIds=[complaints_label_id]
    ).execute()

    messages = results.get('messages', [])

    for message in messages:

        message_id = message['id']

        doc_ref = db.collection("complaints").document(message_id)

        # Prevent duplicates
        if doc_ref.get().exists:
            continue

        msg = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = msg['payload']['headers']

        subject = ""
        sender = ""

        for h in headers:

            if h['name'] == "Subject":
                subject = h['value']

            if h['name'] == "From":
                sender = h['value']

        body = ""

        if 'parts' in msg['payload']:

            for part in msg['payload']['parts']:

                if part['mimeType'] == "text/plain":

                    data = part['body'].get('data')

                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')

        else:

            data = msg['payload']['body'].get('data')

            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        text = subject + " " + body

        urgency, confidence = predict_urgency(text)
        category, _ = predict_category(text)
        sentiment, _ = predict_sentiment(text)

        department = assign_department(category)

        complaint = {
            "title": subject,
            "description": body[:1000],
            "sender": sender,
            "urgency": urgency,
            "category": category,
            "sentiment": sentiment,
            "department": department,
            "confidence": confidence,
            "status": "Open",
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        doc_ref.set(complaint)