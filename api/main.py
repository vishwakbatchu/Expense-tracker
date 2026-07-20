from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
import os

from expense_tracker import storage
from expense_tracker import core

app = FastAPI(title="Expense Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExpenseCreate(BaseModel):
    date: str
    category: str
    amount: float = Field(gt=0)


class ExpenseUpdate(BaseModel):
    date: str
    category: str
    amount: float = Field(gt=0)


class IncomeCreate(BaseModel):
    date: str
    source: str = "Other"
    amount: float = Field(gt=0)


class BudgetOverall(BaseModel):
    amount: float = Field(gt=0)


class BudgetCategory(BaseModel):
    category: str
    amount: float = Field(gt=0)


class RecurringCreate(BaseModel):
    category: str
    amount: float = Field(gt=0)
    day: int = Field(ge=1, le=28)


class RestoreRequest(BaseModel):
    file: str  # expenses, budgets, recurring, income


@app.get("/api/expenses")
def list_expenses(month: Optional[str] = None, search: Optional[str] = None):
    expenses = storage.load_expenses()
    if search:
        expenses = core.search_expenses(search)
    if month:
        expenses = core.filter_by_month(expenses, month)
    return expenses


@app.post("/api/expenses")
def create_expense(data: ExpenseCreate):
    try:
        expense, warnings = core.add_expense(data.date, data.category, data.amount)
        return {"expense": expense, "warnings": warnings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: str, data: ExpenseUpdate):
    try:
        expense, warnings = core.update_expense(
            expense_id, data.date, data.category, data.amount
        )
        return {"expense": expense, "warnings": warnings}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/expenses/{expense_id}")
def remove_expense(expense_id: str):
    try:
        core.delete_expense(expense_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/income")
def list_income(month: Optional[str] = None):
    income = storage.load_income()
    if month:
        income = core.filter_by_month(income, month)
    return income


@app.post("/api/income")
def create_income(data: IncomeCreate):
    entry = core.add_income(data.date, data.source, data.amount)
    return entry


@app.delete("/api/income/{income_id}")
def remove_income(income_id: str):
    try:
        core.delete_income(income_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/budgets")
def get_budgets():
    return storage.load_budgets()


@app.put("/api/budgets/overall")
def update_overall_budget(data: BudgetOverall):
    return core.set_overall_budget(data.amount)


@app.put("/api/budgets/category")
def update_category_budget(data: BudgetCategory):
    return core.set_category_budget(data.category, data.amount)


@app.get("/api/recurring")
def list_recurring():
    return storage.load_recurring()


@app.post("/api/recurring")
def create_recurring(data: RecurringCreate):
    return core.add_recurring(data.category, data.amount, data.day)


@app.delete("/api/recurring/{recurring_id}")
def remove_recurring(recurring_id: str):
    try:
        core.delete_recurring(recurring_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/recurring/process")
def process_recurring(month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    added = core.process_recurring_for_month(month)
    return {"added": added}


@app.get("/api/stats")
def get_stats(month: Optional[str] = None):
    return core.get_dashboard_stats(month)


@app.get("/api/comparison")
def get_comparison(n: int = Query(3, ge=1, le=24)):
    return core.get_comparison_data(n)


@app.get("/api/months")
def get_months():
    return core.get_all_months_with_data()


@app.get("/api/report", response_class=HTMLResponse)
def get_report(month: Optional[str] = None):
    return core.generate_report_html(month)


@app.get("/api/export/csv", response_class=PlainTextResponse)
def export_csv():
    return PlainTextResponse(
        core.export_expenses_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses_export.csv"},
    )


@app.post("/api/backup/restore")
def restore_backup(data: RestoreRequest):
    mapping = {
        "expenses": storage.FILENAME,
        "budgets": storage.BUDGET_FILENAME,
        "recurring": storage.RECURRING_FILENAME,
        "income": storage.INCOME_FILENAME,
    }
    if data.file not in mapping:
        raise HTTPException(status_code=400, detail="Invalid file type")
    try:
        storage.restore_from_backup(mapping[data.file])
        return {"ok": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


static_dir = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
