"""Per-user expense category classifier.

Trains a fresh TF-IDF + Naive Bayes pipeline per request from that user's own
labeled history. Retraining is cheap at this data scale and avoids persisting
a model file to Render's ephemeral disk.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score

from expense_tracker import storage

MIN_EXAMPLES = 8
MIN_CATEGORIES = 2


def _labeled_rows(user_id: str | None = None) -> list[dict]:
    expenses = storage.load_expenses()
    return [e for e in expenses if e.get("description") and e.get("category")]


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)),
        ("clf", MultinomialNB()),
    ])


def train_status() -> dict:
    """Reports whether this user has enough labeled data to use the classifier."""
    rows = _labeled_rows()
    categories = {r["category"] for r in rows}
    ready = len(rows) >= MIN_EXAMPLES and len(categories) >= MIN_CATEGORIES
    return {
        "ready": ready,
        "labeled_examples": len(rows),
        "distinct_categories": len(categories),
        "min_examples_required": MIN_EXAMPLES,
        "min_categories_required": MIN_CATEGORIES,
    }


def predict_category(description: str) -> dict:
    """Predicts a category for a new expense description using this user's history."""
    status = train_status()
    if not status["ready"]:
        return {
            "predicted_category": None,
            "confidence": None,
            "reason": "Not enough labeled history yet.",
            **status,
        }

    rows = _labeled_rows()
    X = [r["description"] for r in rows]
    y = [r["category"] for r in rows]

    pipeline = _build_pipeline()
    pipeline.fit(X, y)

    probs = pipeline.predict_proba([description])[0]
    classes = pipeline.classes_
    best_idx = probs.argmax()

    return {
        "predicted_category": classes[best_idx],
        "confidence": round(float(probs[best_idx]), 3),
        "alternatives": sorted(
            [{"category": c, "confidence": round(float(p), 3)} for c, p in zip(classes, probs)],
            key=lambda x: -x["confidence"],
        )[:3],
    }


def evaluate_model() -> dict:
    """Cross-validated accuracy for this user's classifier — for reporting/documentation."""
    status = train_status()
    if not status["ready"]:
        return {"evaluated": False, **status}

    rows = _labeled_rows()
    X = [r["description"] for r in rows]
    y = [r["category"] for r in rows]

    pipeline = _build_pipeline()
    n_splits = min(5, min(status["labeled_examples"], 5))
    try:
        scores = cross_val_score(pipeline, X, y, cv=n_splits)
        return {
            "evaluated": True,
            "cv_folds": n_splits,
            "mean_accuracy": round(float(scores.mean()), 3),
            "fold_scores": [round(float(s), 3) for s in scores],
        }
    except ValueError as e:
        return {"evaluated": False, "reason": str(e), **status}
