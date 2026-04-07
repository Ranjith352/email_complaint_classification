from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# =====================================================
# LOAD MODELS
# =====================================================

# Zero-shot classification
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

# Sentiment
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

# Use text-generation instead of summarization
generator = pipeline(
    "text-generation",
    model="facebook/bart-large-cnn"
)

# =====================================================
# LABELS
# =====================================================

URGENCY_LABELS = ["High urgency", "Medium urgency", "Low urgency"]

CATEGORY_LABELS = [
    "Security issue",
    "Technical problem",
    "Billing issue",
    "Academic issue",
    "General inquiry"
]

# =====================================================
# FUNCTIONS
# =====================================================

def predict_urgency(text):
    result = classifier(text[:1024], URGENCY_LABELS)

    label = result["labels"][0]
    score = float(result["scores"][0])

    if "High" in label:
        urgency = "High"
    elif "Medium" in label:
        urgency = "Medium"
    else:
        urgency = "Low"

    return urgency, score


def predict_category(text):
    result = classifier(text[:1024], CATEGORY_LABELS)

    category = result["labels"][0]
    score = float(result["scores"][0])

    return category, score


def predict_sentiment(text):
    result = sentiment_analyzer(text[:512])[0]
    return result["label"], float(result["score"])


def generate_summary(text):
    if len(text.split()) < 30:
        return text

    prompt = f"Summarize the following complaint briefly:\n{text[:800]}"

    summary = generator(
        prompt,
        max_length=120,
        do_sample=False
    )

    return summary[0]["generated_text"]


def check_duplicate(new_text, existing_texts):
    if not existing_texts:
        return 0.0

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([new_text] + existing_texts)

    similarity_matrix = cosine_similarity(vectors[0:1], vectors[1:])
    max_similarity = similarity_matrix.max()

    return float(max_similarity)