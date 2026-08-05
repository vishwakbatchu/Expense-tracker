"""Per-user anomaly detection over expense history.

Uses IsolationForest once there's enough history to make it meaningful;
falls back to a simple z-score baseline for sparse data. Both are reported
so the two can be compared as part of documentation.
"""

import datetime
import numpy as np
from sklearn.ensemble import IsolationForest

from expense_tracker import storage

MIN_ROWS_FOR_ISOLATION_FOREST = 15


def _features(expenses: list[dict]) -> tuple[np.ndarray, list[str], list[dict]]:
    categories = sorted({e["category"] for e in expenses})
    cat_index = {c: i for i, c in enumerate(categories)}

    rows = []
    valid_expenses = []
    for e in expenses:
        try:
            d = datetime.datetime.strptime(e["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        rows.append([e["amount"], cat_index[e["category"]], d.weekday(), d.day])
        valid_expenses.append(e)

    return np.array(rows), categories, valid_expenses


def _zscore_flags(expenses: list[dict], threshold: float = 2.5) -> list[dict]:
    by_category: dict[str, list[dict]] = {}
    for e in expenses:
        by_category.setdefault(e["category"], []).append(e)

    flagged = []
    for cat, items in by_category.items():
        amounts = np.array([i["amount"] for i in items])
        if len(amounts) < 3:
            continue
        mean, std = amounts.mean(), amounts.std()
        if std == 0:
            continue
        for i, amt in zip(items, amounts):
            z = (amt - mean) / std
            if abs(z) >= threshold:
                flagged.append({**i, "method": "zscore", "score": round(float(z), 2)})
    return flagged


def detect_anomalies() -> dict:
    expenses = storage.load_expenses()
    if len(expenses) < 5:
        return {"method": "none", "flagged": [], "reason": "Not enough history yet."}

    if len(expenses) >= MIN_ROWS_FOR_ISOLATION_FOREST:
        X, _, valid_expenses = _features(expenses)
        if len(X) < MIN_ROWS_FOR_ISOLATION_FOREST:
            flagged = _zscore_flags(expenses)
            return {"method": "zscore", "flagged": flagged}

        model = IsolationForest(contamination="auto", random_state=42)
        preds = model.fit_predict(X)
        scores = model.decision_function(X)

        flagged = [
            {**valid_expenses[i], "method": "isolation_forest", "score": round(float(scores[i]), 3)}
            for i in range(len(preds)) if preds[i] == -1
        ]
        return {"method": "isolation_forest", "flagged": flagged}

    flagged = _zscore_flags(expenses)
    return {"method": "zscore", "flagged": flagged}


def check_single_expense(date: str, category: str, amount: float) -> dict:
    """Real-time check: is this new expense unusual given this user's history in that category?"""
    expenses = storage.load_expenses()
    same_cat = [e for e in expenses if e["category"] == category]
    if len(same_cat) < 3:
        return {"is_anomaly": False, "reason": "Not enough history in this category yet."}

    amounts = np.array([e["amount"] for e in same_cat])
    mean, std = amounts.mean(), amounts.std()
    if std == 0:
        return {"is_anomaly": False, "reason": "No variance in this category's spending."}

    z = (amount - mean) / std
    return {
        "is_anomaly": bool(abs(z) >= 2.5),
        "z_score": round(float(z), 2),
        "category_average": round(float(mean), 2),
    }
