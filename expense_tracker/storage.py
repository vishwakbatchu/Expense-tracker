"""Database-backed persistence helpers used by the existing application code.

The public functions deliberately retain the JSON storage module's interface so
the API responses and frontend contracts do not change during the migration.
"""

import json
import os
from contextvars import ContextVar
from pathlib import Path

from sqlalchemy import select

from database import Base, SessionLocal, engine
from models import BackupSnapshot, Budget, CategoryBudget, Expense, Income, LegacyImport, RecurringExpense, User


DATA_DIR = os.environ.get("DATA_DIR", ".")
_active_user = ContextVar("active_user", default=None)


def set_active_user(username):
    return _active_user.set(username)


def reset_active_user(token):
    _active_user.reset(token)


def _current_user() -> str:
    user = _active_user.get()
    if not user:
        raise RuntimeError("Database access requires an authenticated user")
    return user


def _ensure_user(session, username: str) -> None:
    # APP_USERNAME remains a supported deployment option. Its data is owned by
    # this internal account, never shared with registered users.
    if username == "__owner__" and session.get(User, username) is None:
        session.add(User(username=username, password_hash="external-auth", email="owner@local"))
        session.flush()


def _expense_dict(row: Expense) -> dict:
    result = {"id": row.id, "date": row.date, "category": row.category, "amount": row.amount}
    if row.recurring:
        result["recurring"] = True
        result["recurring_id"] = row.recurring_id
    return result


def _income_dict(row: Income) -> dict:
    return {"id": row.id, "date": row.date, "source": row.source, "amount": row.amount}


def _recurring_dict(row: RecurringExpense) -> dict:
    return {"id": row.id, "category": row.category, "amount": row.amount, "day": row.day}


def _snapshot(session, user_id: str, name: str, data: object) -> None:
    existing = session.get(BackupSnapshot, {"user_id": user_id, "name": name})
    if existing is None:
        existing = BackupSnapshot(user_id=user_id, name=name, data=json.dumps(data))
        session.add(existing)
    else:
        existing.data = json.dumps(data)


def current_data_file(name):
    """Compatibility label for the backup endpoint; no JSON file is used."""
    return name.replace(".json", "")


def load_expenses():
    user_id = _current_user()
    with SessionLocal() as session:
        _ensure_user(session, user_id)
        rows = session.scalars(select(Expense).where(Expense.user_id == user_id).order_by(Expense.date, Expense.id)).all()
        session.commit()
        return [_expense_dict(row) for row in rows]


def save_expenses(expenses):
    user_id = _current_user()
    with SessionLocal.begin() as session:
        _ensure_user(session, user_id)
        previous = [_expense_dict(row) for row in session.scalars(select(Expense).where(Expense.user_id == user_id)).all()]
        _snapshot(session, user_id, "expenses", previous)
        for row in session.scalars(select(Expense).where(Expense.user_id == user_id)).all():
            session.delete(row)
        for item in expenses:
            session.add(Expense(
                id=item["id"], user_id=user_id, date=item["date"], category=item["category"],
                amount=float(item["amount"]), recurring=bool(item.get("recurring", False)),
                recurring_id=item.get("recurring_id"),
            ))


def load_income():
    user_id = _current_user()
    with SessionLocal() as session:
        _ensure_user(session, user_id)
        rows = session.scalars(select(Income).where(Income.user_id == user_id).order_by(Income.date, Income.id)).all()
        session.commit()
        return [_income_dict(row) for row in rows]


def save_income(income):
    user_id = _current_user()
    with SessionLocal.begin() as session:
        _ensure_user(session, user_id)
        previous = [_income_dict(row) for row in session.scalars(select(Income).where(Income.user_id == user_id)).all()]
        _snapshot(session, user_id, "income", previous)
        for row in session.scalars(select(Income).where(Income.user_id == user_id)).all():
            session.delete(row)
        for item in income:
            session.add(Income(id=item["id"], user_id=user_id, date=item["date"], source=item["source"], amount=float(item["amount"])))


def load_budgets():
    user_id = _current_user()
    with SessionLocal() as session:
        _ensure_user(session, user_id)
        budget = session.get(Budget, user_id)
        categories = session.scalars(select(CategoryBudget).where(CategoryBudget.user_id == user_id)).all()
        session.commit()
        return {"overall": budget.overall if budget else None, "categories": {row.category: row.amount for row in categories}}


def save_budgets(budgets):
    user_id = _current_user()
    with SessionLocal.begin() as session:
        _ensure_user(session, user_id)
        previous = {"overall": (session.get(Budget, user_id).overall if session.get(Budget, user_id) else None), "categories": {row.category: row.amount for row in session.scalars(select(CategoryBudget).where(CategoryBudget.user_id == user_id)).all()}}
        _snapshot(session, user_id, "budgets", previous)
        budget = session.get(Budget, user_id)
        if budget is None:
            session.add(Budget(user_id=user_id, overall=budgets.get("overall")))
        else:
            budget.overall = budgets.get("overall")
        for row in session.scalars(select(CategoryBudget).where(CategoryBudget.user_id == user_id)).all():
            session.delete(row)
        for category, amount in budgets.get("categories", {}).items():
            session.add(CategoryBudget(user_id=user_id, category=category, amount=float(amount)))


def load_recurring():
    user_id = _current_user()
    with SessionLocal() as session:
        _ensure_user(session, user_id)
        rows = session.scalars(select(RecurringExpense).where(RecurringExpense.user_id == user_id).order_by(RecurringExpense.id)).all()
        session.commit()
        return [_recurring_dict(row) for row in rows]


def save_recurring(recurring):
    user_id = _current_user()
    with SessionLocal.begin() as session:
        _ensure_user(session, user_id)
        previous = [_recurring_dict(row) for row in session.scalars(select(RecurringExpense).where(RecurringExpense.user_id == user_id)).all()]
        _snapshot(session, user_id, "recurring", previous)
        for row in session.scalars(select(RecurringExpense).where(RecurringExpense.user_id == user_id)).all():
            session.delete(row)
        for item in recurring:
            session.add(RecurringExpense(id=item["id"], user_id=user_id, category=item["category"], amount=float(item["amount"]), day=int(item["day"])))


def restore_from_backup(name):
    key = name.replace(".json", "")
    user_id = _current_user()
    with SessionLocal() as session:
        snapshot = session.get(BackupSnapshot, {"user_id": user_id, "name": key})
        if snapshot is None:
            raise FileNotFoundError(f"No backup found for {key}")
        data = json.loads(snapshot.data)
    {"expenses": save_expenses, "income": save_income, "budgets": save_budgets, "recurring": save_recurring}[key](data)


def migrate_legacy_json() -> None:
    """One-time, idempotent import of the app's old JSON data files."""
    legacy_root = Path(DATA_DIR)
    users_file = legacy_root / "users.json"
    with SessionLocal.begin() as session:
        if users_file.exists():
            for username, account in json.loads(users_file.read_text()).items():
                if session.get(User, username) is None:
                    session.add(User(username=username, password_hash=account["password"], email=account["email"]))
        user_directories = (
            [path for path in (legacy_root / "users").glob("*") if path.is_dir()]
            if (legacy_root / "users").exists()
            else []
        )
        for directory in [legacy_root, *user_directories]:
            user_id = "__owner__" if directory == legacy_root else directory.name
            _ensure_user(session, user_id)
            if session.get(LegacyImport, user_id) is not None:
                continue
            files = {name: directory / f"{name}.json" for name in ("expenses", "income", "budgets", "recurring")}
            if files["expenses"].exists():
                for item in json.loads(files["expenses"].read_text()):
                    session.add(Expense(id=item["id"], user_id=user_id, date=item["date"], category=item["category"], amount=float(item["amount"]), recurring=bool(item.get("recurring", False)), recurring_id=item.get("recurring_id")))
            if files["income"].exists():
                for item in json.loads(files["income"].read_text()):
                    session.add(Income(id=item["id"], user_id=user_id, date=item["date"], source=item.get("source", "Other"), amount=float(item["amount"])))
            if files["budgets"].exists():
                item = json.loads(files["budgets"].read_text())
                session.add(Budget(user_id=user_id, overall=item.get("overall")))
                for category, amount in item.get("categories", {}).items():
                    session.add(CategoryBudget(user_id=user_id, category=category, amount=float(amount)))
            if files["recurring"].exists():
                for item in json.loads(files["recurring"].read_text()):
                    session.add(RecurringExpense(id=item["id"], user_id=user_id, category=item["category"], amount=float(item["amount"]), day=int(item["day"])))
            session.add(LegacyImport(user_id=user_id))


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_legacy_json()
