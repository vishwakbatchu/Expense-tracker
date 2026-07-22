
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
import os
from datetime import datetime

from expense_tracker import storage
from expense_tracker import core
from api import auth

storage.initialize_database()


class UserStorageMiddleware:
    """Make a signed-in user's private data folder available to each request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        user = scope.get("session", {}).get("user")
        token = storage.set_active_user(user)
        try:
            await self.app(scope, receive, send)
        finally:
            storage.reset_active_user(token)


app = FastAPI(title="Expense Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(UserStorageMiddleware)
app.add_middleware(SessionMiddleware, secret_key=auth.SECRET_KEY, https_only=False)


@app.middleware("http")
async def no_cache_app_shell(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in ("/", "/index.html") or path.startswith("/js/") or path == "/sw.js":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

require_login = Depends(auth.require_auth)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(LoginRequest):
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    username: str
    code: str
    password: str


class ExpenseData(BaseModel):
    date: str
    category: str
    amount: float = Field(gt=0)


    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must use YYYY-MM-DD format")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Category cannot be empty")
        return value


class ExpenseCreate(ExpenseData):
    pass


class ExpenseUpdate(ExpenseData):
    pass


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


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/auth/status")
def auth_status(request: Request):
    return {
        "auth_required": True,
        "authenticated": bool(request.session.get("user")),
        "registration_enabled": True,
    }


@app.post("/api/auth/login")
def login(data: LoginRequest, request: Request):
    user = auth.authenticate(data.username, data.password)
    if user:
        request.session.clear()
        request.session["user"] = user
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/api/auth/register")
def register(data: RegisterRequest, request: Request):
    try:
        user = auth.create_account(data.username, data.password, data.email)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    request.session.clear()
    request.session["user"] = user
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.post("/api/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    result = auth.create_reset_code(data.email)
    if not result:
        raise HTTPException(status_code=404, detail="No account found with that email")
    username, code = result
    # No email is sent — the code is returned directly so the frontend can show it.
    return {"ok": True, "username": username, "code": code}


@app.post("/api/auth/reset-password")
def reset_password(data: ResetPasswordRequest):
    try:
        success = auth.consume_reset_code(data.username, data.code, data.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if not success:
        raise HTTPException(status_code=400, detail="That code is invalid or has expired")
    return {"ok": True}


@app.get("/api/expenses", dependencies=[require_login])
def list_expenses(month: Optional[str] = None, search: Optional[str] = None):
    expenses = storage.load_expenses()
    if search:
        expenses = core.search_expenses(search)
    if month:
        expenses = core.filter_by_month(expenses, month)
    return expenses


@app.post("/api/expenses", dependencies=[require_login])
def create_expense(data: ExpenseCreate):
    try:
        expense, warnings = core.add_expense(data.date, data.category, data.amount)
        return {"expense": expense, "warnings": warnings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/expenses/{expense_id}", dependencies=[require_login])
def update_expense(expense_id: str, data: ExpenseUpdate):
    try:
        expense, warnings = core.update_expense(
            expense_id, data.date, data.category, data.amount
        )
        return {"expense": expense, "warnings": warnings}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/expenses/{expense_id}", dependencies=[require_login])
def remove_expense(expense_id: str):
    try:
        core.delete_expense(expense_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/income", dependencies=[require_login])
def list_income(month: Optional[str] = None):
    income = storage.load_income()
    if month:
        income = core.filter_by_month(income, month)
    return income


@app.post("/api/income", dependencies=[require_login])
def create_income(data: IncomeCreate):
    entry = core.add_income(data.date, data.source, data.amount)
    return entry


@app.delete("/api/income/{income_id}", dependencies=[require_login])
def remove_income(income_id: str):
    try:
        core.delete_income(income_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/budgets", dependencies=[require_login])
def get_budgets():
    return storage.load_budgets()


@app.put("/api/budgets/overall", dependencies=[require_login])
def update_overall_budget(data: BudgetOverall):
    return core.set_overall_budget(data.amount)


@app.put("/api/budgets/category", dependencies=[require_login])
def update_category_budget(data: BudgetCategory):
    return core.set_category_budget(data.category, data.amount)


@app.get("/api/recurring", dependencies=[require_login])
def list_recurring():
    return storage.load_recurring()


@app.post("/api/recurring", dependencies=[require_login])
def create_recurring(data: RecurringCreate):
    return core.add_recurring(data.category, data.amount, data.day)


@app.delete("/api/recurring/{recurring_id}", dependencies=[require_login])
def remove_recurring(recurring_id: str):
    try:
        core.delete_recurring(recurring_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/recurring/process", dependencies=[require_login])
def process_recurring(month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    added = core.process_recurring_for_month(month)
    return {"added": added}


@app.get("/api/stats", dependencies=[require_login])
def get_stats(month: Optional[str] = None):
    return core.get_dashboard_stats(month)


@app.get("/api/comparison", dependencies=[require_login])
def get_comparison(n: int = Query(3, ge=1, le=24)):
    return core.get_comparison_data(n)


@app.get("/api/months", dependencies=[require_login])
def get_months():
    return core.get_all_months_with_data()


@app.get("/api/report", response_class=HTMLResponse, dependencies=[require_login])
def get_report(month: Optional[str] = None):
    return core.generate_report_html(month)


@app.get("/api/export/csv", response_class=PlainTextResponse, dependencies=[require_login])
def export_csv():
    return PlainTextResponse(
        core.export_expenses_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses_export.csv"},
    )


@app.post("/api/backup/restore", dependencies=[require_login])
def restore_backup(data: RestoreRequest):
    mapping = {"expenses", "budgets", "recurring", "income"}
    if data.file not in mapping:
        raise HTTPException(status_code=400, detail="Invalid file type")
    try:
        storage.restore_from_backup(data.file)
        return {"ok": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


static_dir = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
