import json
import os
import shutil
import tempfile
from contextvars import ContextVar

DATA_DIR = os.environ.get("DATA_DIR", ".")
_active_user = ContextVar("active_user", default=None)


def _path(name):
    user = _active_user.get()
    if user and user != "__owner__":
        return os.path.join(DATA_DIR, "users", user, name)
    return os.path.join(DATA_DIR, name)


def set_active_user(username):
    """Scope subsequent data access to one signed-in user's private files."""
    return _active_user.set(username)


def reset_active_user(token):
    _active_user.reset(token)


def current_data_file(name):
    return _path(name)


FILENAME = _path("expenses.json")
BUDGET_FILENAME = _path("budgets.json")
RECURRING_FILENAME = _path("recurring.json")
INCOME_FILENAME = _path("income.json")

if DATA_DIR != ".":
    os.makedirs(DATA_DIR, exist_ok=True)


def backup_file(filename):
    if os.path.exists(filename):
        backup_name = filename.replace(".json", "_backup.json")
        shutil.copy(filename, backup_name)


def atomic_write_json(filename, data):
    dir_name = os.path.dirname(os.path.abspath(filename)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, filename)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return default


def save_json(filename, data):
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    backup_file(filename)
    atomic_write_json(filename, data)


def load_expenses():
    return load_json(_path("expenses.json"), [])


def save_expenses(expenses):
    save_json(_path("expenses.json"), expenses)


def load_budgets():
    return load_json(_path("budgets.json"), {"overall": None, "categories": {}})


def save_budgets(budgets):
    save_json(_path("budgets.json"), budgets)


def load_recurring():
    return load_json(_path("recurring.json"), [])


def save_recurring(recurring):
    save_json(_path("recurring.json"), recurring)


def load_income():
    return load_json(_path("income.json"), [])


def save_income(income):
    save_json(_path("income.json"), income)


def restore_from_backup(filename):
    backup_name = filename.replace(".json", "_backup.json")
    if not os.path.exists(backup_name):
        raise FileNotFoundError(f"No backup found for {filename}")
    shutil.copy(backup_name, filename)
