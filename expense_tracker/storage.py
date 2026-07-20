import json
import os
import shutil
import tempfile

DATA_DIR = os.environ.get("DATA_DIR", ".")


def _path(name):
    return os.path.join(DATA_DIR, name)


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
    backup_file(filename)
    atomic_write_json(filename, data)


def load_expenses():
    return load_json(FILENAME, [])


def save_expenses(expenses):
    save_json(FILENAME, expenses)


def load_budgets():
    return load_json(BUDGET_FILENAME, {"overall": None, "categories": {}})


def save_budgets(budgets):
    save_json(BUDGET_FILENAME, budgets)


def load_recurring():
    return load_json(RECURRING_FILENAME, [])


def save_recurring(recurring):
    save_json(RECURRING_FILENAME, recurring)


def load_income():
    return load_json(INCOME_FILENAME, [])


def save_income(income):
    save_json(INCOME_FILENAME, income)


def restore_from_backup(filename):
    backup_name = filename.replace(".json", "_backup.json")
    if not os.path.exists(backup_name):
        raise FileNotFoundError(f"No backup found for {filename}")
    shutil.copy(backup_name, filename)
