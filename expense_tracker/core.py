import csv
import html
import io
import uuid
from datetime import datetime

from . import storage


def filter_by_month(records, year_month):
    return [r for r in records if r.get("date", "").startswith(year_month)]


def norm_cat(category):
    return category.strip().lower()


def find_budget_for_category(cat_budgets, category):
    target = norm_cat(category)
    for key, limit in cat_budgets.items():
        if norm_cat(key) == target:
            return key, limit
    return None, None


def category_summary(expenses):
    summary = {}
    for e in expenses:
        summary[e["category"]] = summary.get(e["category"], 0) + e["amount"]
    return summary


def calculate_statistics(expenses):
    if not expenses:
        return None
    amounts = [e["amount"] for e in expenses]
    total = sum(amounts)
    average = total / len(amounts)
    highest = max(expenses, key=lambda e: e["amount"])
    lowest = min(expenses, key=lambda e: e["amount"])
    summary = category_summary(expenses)
    top_category = max(summary, key=summary.get)
    return {
        "count": len(expenses),
        "total": total,
        "average": average,
        "highest": highest,
        "lowest": lowest,
        "top_category": top_category,
        "top_category_amount": summary[top_category],
    }


def check_budget_warnings(expense, expenses=None, budgets=None):
    """Return list of warning strings after adding/updating an expense."""
    if expenses is None:
        expenses = storage.load_expenses()
    if budgets is None:
        budgets = storage.load_budgets()

    warnings = []
    current_month = expense["date"][:7]
    month_expenses = filter_by_month(expenses, current_month)

    overall_total = sum(e["amount"] for e in month_expenses)
    if budgets.get("overall") is not None:
        limit = budgets["overall"]
        if overall_total > limit:
            warnings.append(
                f"OVER overall budget! Spent ₹{overall_total:.2f} of ₹{limit:.2f} this month."
            )
        elif overall_total > 0.9 * limit:
            warnings.append(
                f"Warning: ₹{overall_total:.2f} of ₹{limit:.2f} overall budget used this month."
            )

    cat = expense["category"]
    cat_budgets = budgets.get("categories", {})
    matched_key, cat_limit = find_budget_for_category(cat_budgets, cat)
    if matched_key is not None:
        cat_total = sum(
            e["amount"]
            for e in month_expenses
            if norm_cat(e["category"]) == norm_cat(cat)
        )
        if cat_total > cat_limit:
            warnings.append(
                f"OVER '{matched_key}' budget! Spent ₹{cat_total:.2f} of ₹{cat_limit:.2f} this month."
            )
        elif cat_total > 0.9 * cat_limit:
            warnings.append(
                f"Warning: ₹{cat_total:.2f} of ₹{cat_limit:.2f} '{matched_key}' budget used this month."
            )
    return warnings


def add_expense(date, category, amount):
    expenses = storage.load_expenses()
    expense = {
        "id": str(uuid.uuid4())[:8],
        "date": date,
        "category": category.strip(),
        "amount": float(amount),
    }
    expenses.append(expense)
    storage.save_expenses(expenses)
    warnings = check_budget_warnings(expense, expenses)
    return expense, warnings


def update_expense(expense_id, date, category, amount):
    expenses = storage.load_expenses()
    expense = None
    for e in expenses:
        if e["id"] == expense_id:
            e["date"] = date
            e["category"] = category.strip()
            e["amount"] = float(amount)
            expense = e
            break
    if expense is None:
        raise ValueError(f"Expense {expense_id} not found")
    storage.save_expenses(expenses)
    warnings = check_budget_warnings(expense, expenses)
    return expense, warnings


def delete_expense(expense_id):
    expenses = storage.load_expenses()
    before = len(expenses)
    expenses = [e for e in expenses if e["id"] != expense_id]
    if len(expenses) == before:
        raise ValueError(f"Expense {expense_id} not found")
    storage.save_expenses(expenses)


def search_expenses(query):
    expenses = storage.load_expenses()
    q = query.strip().lower()
    return [e for e in expenses if q in e.get("category", "").lower()]


def add_income(date, source, amount):
    income = storage.load_income()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "date": date,
        "source": source.strip() or "Other",
        "amount": float(amount),
    }
    income.append(entry)
    storage.save_income(income)
    return entry


def delete_income(income_id):
    income = storage.load_income()
    before = len(income)
    income = [i for i in income if i["id"] != income_id]
    if len(income) == before:
        raise ValueError(f"Income {income_id} not found")
    storage.save_income(income)


def set_overall_budget(amount):
    budgets = storage.load_budgets()
    budgets["overall"] = float(amount)
    storage.save_budgets(budgets)
    return budgets


def set_category_budget(category, amount):
    budgets = storage.load_budgets()
    budgets.setdefault("categories", {})[category.strip()] = float(amount)
    storage.save_budgets(budgets)
    return budgets


def add_recurring(category, amount, day):
    recurring = storage.load_recurring()
    template = {
        "id": str(uuid.uuid4())[:8],
        "category": category.strip(),
        "amount": float(amount),
        "day": int(day),
    }
    recurring.append(template)
    storage.save_recurring(recurring)
    return template


def delete_recurring(recurring_id):
    recurring = storage.load_recurring()
    before = len(recurring)
    recurring = [r for r in recurring if r["id"] != recurring_id]
    if len(recurring) == before:
        raise ValueError(f"Recurring expense {recurring_id} not found")
    storage.save_recurring(recurring)


def process_recurring_for_month(year_month):
    recurring = storage.load_recurring()
    if not recurring:
        return []

    expenses = storage.load_expenses()
    existing_month_expenses = filter_by_month(expenses, year_month)
    added = []

    for template in recurring:
        already_added = any(
            e.get("recurring")
            and (
                e.get("recurring_id") == template["id"]
                or (
                    e.get("recurring_id") is None
                    and e["category"] == template["category"]
                    and e["amount"] == template["amount"]
                )
            )
            for e in existing_month_expenses
        )
        if not already_added:
            day = str(template["day"]).zfill(2)
            date = f"{year_month}-{day}"
            new_expense = {
                "id": str(uuid.uuid4())[:8],
                "date": date,
                "category": template["category"],
                "amount": template["amount"],
                "recurring": True,
                "recurring_id": template["id"],
            }
            expenses.append(new_expense)
            added.append(new_expense)

    if added:
        storage.save_expenses(expenses)
    return added


def get_all_months_with_data():
    expenses = storage.load_expenses()
    income = storage.load_income()
    months = set()
    for e in expenses:
        d = e.get("date", "")
        if len(d) >= 7:
            months.add(d[:7])
    for i in income:
        d = i.get("date", "")
        if len(d) >= 7:
            months.add(d[:7])
    return sorted(months)


def get_dashboard_stats(year_month=None):
    expenses = storage.load_expenses()
    income = storage.load_income()
    budgets = storage.load_budgets()

    if year_month:
        expenses = filter_by_month(expenses, year_month)
        income = filter_by_month(income, year_month)

    stats = calculate_statistics(expenses)
    total_income = sum(i["amount"] for i in income)
    total_spent = stats["total"] if stats else 0
    summary = category_summary(expenses)

    budget_status = []
    if year_month:
        if budgets.get("overall") is not None:
            limit = budgets["overall"]
            budget_status.append({
                "name": "Overall",
                "spent": total_spent,
                "limit": limit,
                "over": total_spent > limit,
            })
        for cat, limit in budgets.get("categories", {}).items():
            spent = sum(
                amt for scat, amt in summary.items() if norm_cat(scat) == norm_cat(cat)
            )
            budget_status.append({
                "name": cat,
                "spent": spent,
                "limit": limit,
                "over": spent > limit,
            })

    return {
        "stats": stats,
        "total_income": total_income,
        "total_spent": total_spent,
        "net_savings": total_income - total_spent,
        "category_summary": summary,
        "budget_status": budget_status,
    }


def get_comparison_data(n_months):
    all_months = get_all_months_with_data()
    if not all_months:
        return []

    months_to_show = all_months[-n_months:]
    expenses = storage.load_expenses()
    income = storage.load_income()

    month_data = []
    for ym in months_to_show:
        month_expenses = filter_by_month(expenses, ym)
        month_income = filter_by_month(income, ym)
        spent = sum(e["amount"] for e in month_expenses)
        earned = sum(i["amount"] for i in month_income)
        month_data.append({
            "month": ym,
            "spent": spent,
            "earned": earned,
            "net": earned - spent,
        })
    return month_data


def export_expenses_csv():
    expenses = storage.load_expenses()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "category", "amount"])
    for e in expenses:
        writer.writerow([
            e.get("date", "unknown"),
            e.get("category", "uncategorized"),
            e.get("amount", 0),
        ])
    return output.getvalue()


def generate_report_html(year_month=None):
    if year_month:
        process_recurring_for_month(year_month)

    expenses = storage.load_expenses()
    income = storage.load_income()

    if year_month:
        filtered = filter_by_month(expenses, year_month)
        filtered_income = filter_by_month(income, year_month)
        title_suffix = f" — {year_month}"
    else:
        filtered = expenses
        filtered_income = income
        title_suffix = " — All Time"

    total = sum(e["amount"] for e in filtered)
    total_income = sum(i["amount"] for i in filtered_income)
    net = total_income - total
    summary = category_summary(filtered)
    stats = calculate_statistics(filtered)
    budgets = storage.load_budgets()

    rows = "".join(
        f"<tr><td>{html.escape(str(e.get('date', 'unknown')))}</td>"
        f"<td>{html.escape(str(e['category']))}</td><td>₹{e['amount']:.2f}</td></tr>"
        for e in filtered
    )

    income_rows = "".join(
        f"<tr><td>{html.escape(str(i.get('date', 'unknown')))}</td>"
        f"<td>{html.escape(str(i.get('source', 'unknown')))}</td>"
        f"<td>₹{i.get('amount', 0):.2f}</td></tr>"
        for i in filtered_income
    )

    summary_rows = "".join(
        f"<tr><td>{html.escape(str(cat))}</td><td>₹{amt:.2f}</td></tr>"
        for cat, amt in sorted(summary.items(), key=lambda x: -x[1])
    )

    stats_html = ""
    if stats:
        stats_html = f"""
    <h2>Statistics</h2>
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><td>Average expense</td><td>₹{stats['average']:.2f}</td></tr>
        <tr><td>Highest expense</td><td>₹{stats['highest']['amount']:.2f} ({html.escape(str(stats['highest']['category']))})</td></tr>
        <tr><td>Lowest expense</td><td>₹{stats['lowest']['amount']:.2f} ({html.escape(str(stats['lowest']['category']))})</td></tr>
        <tr><td>Top category</td><td>{html.escape(str(stats['top_category']))} (₹{stats['top_category_amount']:.2f})</td></tr>
    </table>
        """

    budget_html = ""
    overall_limit = budgets.get("overall")
    cat_limits = budgets.get("categories", {})
    if year_month and (overall_limit is not None or cat_limits):
        budget_rows = ""
        if overall_limit is not None:
            status = "OVER" if total > overall_limit else "OK"
            budget_rows += f"<tr><td>Overall</td><td>₹{total:.2f} / ₹{overall_limit:.2f}</td><td>{status}</td></tr>"
        for cat, limit in cat_limits.items():
            spent = sum(
                amt for scat, amt in summary.items() if norm_cat(scat) == norm_cat(cat)
            )
            status = "OVER" if spent > limit else "OK"
            budget_rows += f"<tr><td>{html.escape(cat)}</td><td>₹{spent:.2f} / ₹{limit:.2f}</td><td>{status}</td></tr>"
        budget_html = f"""
    <h2>Budget Status ({year_month})</h2>
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><th>Budget</th><th>Spent / Limit</th><th>Status</th></tr>
        {budget_rows}
    </table>
        """

    net_color = "green" if net >= 0 else "red"

    return f"""<!DOCTYPE html>
<html>
<head><title>Expense Tracker</title></head>
<body style="font-family: Arial; max-width: 600px; margin: 40px auto;">
    <h1>Expense Tracker{title_suffix}</h1>
    <h2>Expenses</h2>
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><th>Date</th><th>Category</th><th>Amount</th></tr>
        {rows}
    </table>
    <h3>Total Spent: ₹{total:.2f}</h3>
    <h2>Income</h2>
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><th>Date</th><th>Source</th><th>Amount</th></tr>
        {income_rows}
    </table>
    <h3>Total Income: ₹{total_income:.2f}</h3>
    <h2 style="color: {net_color};">Net Savings: ₹{net:.2f}</h2>
    <h2>By Category</h2>
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><th>Category</th><th>Amount</th></tr>
        {summary_rows}
    </table>
    {stats_html}
    {budget_html}
</body>
</html>"""
