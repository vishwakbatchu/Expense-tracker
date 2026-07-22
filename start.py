import webbrowser
import uuid
import csv
import html
from datetime import datetime

from expense_tracker import storage

storage.initialize_database()
storage.set_active_user("__owner__")

# ---------- Backup ----------

def restore_from_backup():
    print("\nWhich file do you want to restore?")
    print("1. Expenses\n2. Budgets\n3. Recurring\n4. Income\n5. Back")
    choice = input("Choose: ").strip()
    mapping = {"1": "expenses", "2": "budgets", "3": "recurring", "4": "income"}
    if choice == "5":
        return
    if choice not in mapping:
        print("Invalid choice.")
        return

    data_type = mapping[choice]
    confirm = input(f"This will overwrite {data_type} with the last backup. Continue? (y/n): ").strip().lower()
    if confirm == "y":
        try:
            storage.restore_from_backup(data_type)
            print(f"Restored {data_type} from backup.")
        except FileNotFoundError:
            print(f"No backup found for {data_type}.")
    else:
        print("Cancelled.")


# ---------- Load / Save ----------

def load_expenses():
    return storage.load_expenses()


def save_expenses(expenses):
    storage.save_expenses(expenses)


def load_budgets():
    return storage.load_budgets()


def save_budgets(budgets):
    storage.save_budgets(budgets)


def load_recurring():
    return storage.load_recurring()


def save_recurring(recurring):
    storage.save_recurring(recurring)


def load_income():
    return storage.load_income()


def save_income(income):
    storage.save_income(income)


# ---------- Validated Input Helpers ----------

def get_valid_date():
    while True:
        date = input("Date (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(date, "%Y-%m-%d")
            return date
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")


def get_valid_amount():
    while True:
        amount = input("Amount: ").strip()
        try:
            value = float(amount)
            if value <= 0:
                print("Amount must be positive.")
                continue
            return value
        except ValueError:
            print("Invalid amount. Enter a number.")


def get_valid_category():
    while True:
        category = input("Category: ").strip()
        if category:
            return category
        print("Category cannot be empty.")


def get_valid_day():
    while True:
        day = input("Day of month it recurs (1-28): ").strip()
        if day.isdigit() and 1 <= int(day) <= 28:
            return int(day)
        print("Enter a number between 1 and 28 (kept safe for all months).")


def get_valid_month():
    while True:
        ym = input("Enter month (YYYY-MM), or leave blank for all: ").strip()
        if ym == "":
            return None
        try:
            datetime.strptime(ym, "%Y-%m")
            return ym
        except ValueError:
            print("Invalid format. Use YYYY-MM.")


def get_valid_n_months():
    while True:
        n = input("How many recent months to compare? (e.g. 3, 6): ").strip()
        if n.isdigit() and int(n) > 0:
            return int(n)
        print("Enter a positive number.")


def filter_by_month(records, year_month):
    return [r for r in records if r.get("date", "").startswith(year_month)]


def norm_cat(category):
    """Normalized key for case/whitespace-insensitive category matching."""
    return category.strip().lower()


def find_budget_for_category(cat_budgets, category):
    """Look up a category's budget limit ignoring case/whitespace, returning
    (matched_key, limit) or (None, None) if no match."""
    target = norm_cat(category)
    for key, limit in cat_budgets.items():
        if norm_cat(key) == target:
            return key, limit
    return None, None


# ---------- Budget Warnings ----------

def check_budget_after_add(new_expense):
    budgets = load_budgets()
    expenses = load_expenses()
    current_month = new_expense["date"][:7]
    month_expenses = filter_by_month(expenses, current_month)

    overall_total = sum(e["amount"] for e in month_expenses)
    if budgets.get("overall") is not None:
        limit = budgets["overall"]
        if overall_total > limit:
            print(f"⚠️  OVER overall budget! Spent ₹{overall_total:.2f} of ₹{limit:.2f} this month.")
        elif overall_total > 0.9 * limit:
            print(f"⚠️  Warning: ₹{overall_total:.2f} of ₹{limit:.2f} overall budget used this month.")

    cat = new_expense["category"]
    cat_budgets = budgets.get("categories", {})
    matched_key, cat_limit = find_budget_for_category(cat_budgets, cat)
    if matched_key is not None:
        cat_total = sum(
            e["amount"] for e in month_expenses
            if norm_cat(e["category"]) == norm_cat(cat)
        )
        if cat_total > cat_limit:
            print(f"⚠️  OVER '{matched_key}' budget! Spent ₹{cat_total:.2f} of ₹{cat_limit:.2f} this month.")
        elif cat_total > 0.9 * cat_limit:
            print(f"⚠️  Warning: ₹{cat_total:.2f} of ₹{cat_limit:.2f} '{matched_key}' budget used this month.")


# ---------- Expenses ----------

def add_expense():
    expenses = load_expenses()
    date = get_valid_date()
    category = get_valid_category()
    amount = get_valid_amount()
    expense = {
        "id": str(uuid.uuid4())[:8],
        "date": date,
        "category": category,
        "amount": amount
    }
    expenses.append(expense)
    save_expenses(expenses)
    print(f"Added [{expense['id']}]: {date} | {category} | ₹{amount}")
    check_budget_after_add(expense)


def list_expenses(expenses):
    if not expenses:
        print("No expenses recorded.")
        return False
    for e in expenses:
        eid = e.get("id", "no-id")
        date = e.get("date", "unknown")
        category = e.get("category", "uncategorized")
        amount = e.get("amount", 0)
        tag = " (recurring)" if e.get("recurring") else ""
        print(f"{eid} | {date} | {category} | ₹{amount}{tag}")
    return True


def find_expense_by_id(expenses, expense_id):
    for e in expenses:
        if e["id"] == expense_id:
            return e
    return None


def search_by_category(expenses):
    query = input("Search category (partial match ok): ").strip().lower()
    results = [e for e in expenses if query in e.get("category", "").lower()]
    if not results:
        print("No matches found.")
    return results


def pick_expenses_to_act_on(expenses):
    choice = input("Search by category first? (y/n): ").strip().lower()
    if choice == "y":
        results = search_by_category(expenses)
        if not results:
            return None
        list_expenses(results)
        return get_valid_id(results)
    else:
        if not list_expenses(expenses):
            return None
        return get_valid_id(expenses)


def get_valid_id(expenses):
    while True:
        eid = input("Enter ID: ").strip()
        if find_expense_by_id(expenses, eid):
            return eid
        print("No expense with that ID. Try again.")


def delete_expense():
    expenses = load_expenses()
    eid = pick_expenses_to_act_on(expenses)
    if eid is None:
        return
    expenses = [e for e in expenses if e["id"] != eid]
    save_expenses(expenses)
    print(f"Deleted expense {eid}")


def edit_expense():
    expenses = load_expenses()
    eid = pick_expenses_to_act_on(expenses)
    if eid is None:
        return
    print("Enter new values:")
    date = get_valid_date()
    category = get_valid_category()
    amount = get_valid_amount()
    for e in expenses:
        if e["id"] == eid:
            e["date"] = date
            e["category"] = category
            e["amount"] = amount
            break
    save_expenses(expenses)
    print(f"Updated {eid}: {date} | {category} | ₹{amount}")
    check_budget_after_add({"date": date, "category": category, "amount": amount})


def category_summary(expenses):
    summary = {}
    for e in expenses:
        summary[e["category"]] = summary.get(e["category"], 0) + e["amount"]
    return summary


# ---------- Income ----------

def add_income():
    income = load_income()
    date = get_valid_date()
    source = input("Source (e.g. Salary, Allowance, Freelance): ").strip() or "Other"
    amount = get_valid_amount()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "date": date,
        "source": source,
        "amount": amount
    }
    income.append(entry)
    save_income(income)
    print(f"Added income [{entry['id']}]: {date} | {source} | ₹{amount}")


def list_income(income):
    if not income:
        print("No income recorded.")
        return False
    for i in income:
        print(f"{i.get('id','no-id')} | {i.get('date','unknown')} | {i.get('source','unknown')} | ₹{i.get('amount',0)}")
    return True


def delete_income():
    income = load_income()
    if not list_income(income):
        return
    iid = input("Enter ID to delete: ").strip()
    income = [i for i in income if i["id"] != iid]
    save_income(income)
    print("Deleted (if it existed).")


def manage_income():
    while True:
        print("\n1. Add income\n2. View income\n3. Delete income\n4. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            add_income()
        elif choice == "2":
            income = load_income()
            list_income(income)
        elif choice == "3":
            delete_income()
        elif choice == "4":
            return
        else:
            print("Invalid choice.")


# ---------- Statistics ----------

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
        "top_category_amount": summary[top_category]
    }


def show_statistics():
    expenses = load_expenses()
    income = load_income()
    stats = calculate_statistics(expenses)
    total_income = sum(i["amount"] for i in income)

    if stats is None and not income:
        print("No data recorded.")
        return

    print("\n--- Expense Statistics ---")
    if stats:
        print(f"Total expenses recorded: {stats['count']}")
        print(f"Total spent: ₹{stats['total']:.2f}")
        print(f"Average expense: ₹{stats['average']:.2f}")
        print(f"Highest expense: ₹{stats['highest']['amount']} ({stats['highest']['category']} on {stats['highest'].get('date','unknown')})")
        print(f"Lowest expense: ₹{stats['lowest']['amount']} ({stats['lowest']['category']} on {stats['lowest'].get('date','unknown')})")
        print(f"Top spending category: {stats['top_category']} (₹{stats['top_category_amount']:.2f})")
    else:
        print("No expenses recorded.")

    print(f"\nTotal income: ₹{total_income:.2f}")
    if stats:
        net = total_income - stats['total']
        print(f"Net savings: ₹{net:.2f}")


# ---------- Budgets ----------

def set_budgets():
    budgets = load_budgets()
    print("\n1. Set overall monthly budget\n2. Set category budget\n3. View current budgets\n4. Back")
    choice = input("Choose: ").strip()
    if choice == "1":
        amount = get_valid_amount()
        budgets["overall"] = amount
        save_budgets(budgets)
        print(f"Overall monthly budget set to ₹{amount:.2f}")
    elif choice == "2":
        category = get_valid_category()
        amount = get_valid_amount()
        budgets.setdefault("categories", {})[category] = amount
        save_budgets(budgets)
        print(f"Budget for '{category}' set to ₹{amount:.2f}")
    elif choice == "3":
        overall = budgets.get("overall")
        print(f"\nOverall monthly budget: ₹{overall:.2f}" if overall is not None else "\nOverall monthly budget: not set")
        cats = budgets.get("categories", {})
        if cats:
            print("Category budgets:")
            for cat, amt in cats.items():
                print(f"  {cat}: ₹{amt:.2f}")
        else:
            print("No category budgets set.")
    elif choice == "4":
        return
    else:
        print("Invalid choice.")


# ---------- Recurring Expenses ----------

def manage_recurring():
    while True:
        print("\n1. Add recurring expense\n2. View recurring expenses\n3. Delete recurring expense\n4. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            category = get_valid_category()
            amount = get_valid_amount()
            day = get_valid_day()
            recurring = load_recurring()
            template = {
                "id": str(uuid.uuid4())[:8],
                "category": category,
                "amount": amount,
                "day": day
            }
            recurring.append(template)
            save_recurring(recurring)
            print(f"Recurring expense added: {category} | ₹{amount} | on day {day} of each month")
        elif choice == "2":
            recurring = load_recurring()
            if not recurring:
                print("No recurring expenses set.")
            else:
                for r in recurring:
                    print(f"{r['id']} | {r['category']} | ₹{r['amount']} | day {r['day']}")
        elif choice == "3":
            recurring = load_recurring()
            if not recurring:
                print("No recurring expenses to delete.")
                continue
            for r in recurring:
                print(f"{r['id']} | {r['category']} | ₹{r['amount']} | day {r['day']}")
            rid = input("Enter ID to delete: ").strip()
            recurring = [r for r in recurring if r["id"] != rid]
            save_recurring(recurring)
            print("Deleted (if it existed).")
        elif choice == "4":
            return
        else:
            print("Invalid choice.")


def process_recurring_for_month(year_month):
    """Auto-adds recurring expenses for the given month if not already added."""
    recurring = load_recurring()
    if not recurring:
        return

    expenses = load_expenses()
    existing_month_expenses = filter_by_month(expenses, year_month)
    added_any = False

    for template in recurring:
        already_added = any(
            e.get("recurring") and (
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
                "recurring_id": template["id"]
            }
            expenses.append(new_expense)
            added_any = True
            print(f"Auto-added recurring: {date} | {template['category']} | ₹{template['amount']}")

    if added_any:
        save_expenses(expenses)


# ---------- HTML Report ----------

def generate_html():
    year_month = get_valid_month()

    if year_month:
        process_recurring_for_month(year_month)

    expenses = load_expenses()
    income = load_income()

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
    budgets = load_budgets()

    rows = "".join(
        f"<tr><td>{html.escape(str(e.get('date','unknown')))}</td>"
        f"<td>{html.escape(str(e['category']))}</td><td>₹{e['amount']:.2f}</td></tr>"
        for e in filtered
    )

    income_rows = "".join(
        f"<tr><td>{html.escape(str(i.get('date','unknown')))}</td>"
        f"<td>{html.escape(str(i.get('source','unknown')))}</td><td>₹{i.get('amount',0):.2f}</td></tr>"
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
                amt for scat, amt in summary.items()
                if norm_cat(scat) == norm_cat(cat)
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
    elif not year_month and (overall_limit is not None or cat_limits):
        budget_html = """
    <h2>Budget Status</h2>
    <p><em>Filter by a specific month above to see budget status — budgets are tracked monthly.</em></p>
        """

    net_color = "green" if net >= 0 else "red"

    page_html = f"""<html>
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

    with open("report.html", "w") as f:
        f.write(page_html)

    webbrowser.open("file://" + os.path.abspath("report.html"))
    print("Report generated and opened.")


# ---------- Multi-Month Comparison ----------

def get_all_months_with_data():
    expenses = load_expenses()
    income = load_income()
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


def generate_comparison_report():
    all_months = get_all_months_with_data()
    if not all_months:
        print("No dated expenses or income found to compare.")
        return

    n = get_valid_n_months()
    months_to_show = all_months[-n:]

    expenses = load_expenses()
    income = load_income()

    month_data = []
    max_value = 0
    for ym in months_to_show:
        month_expenses = filter_by_month(expenses, ym)
        month_income = filter_by_month(income, ym)
        spent = sum(e["amount"] for e in month_expenses)
        earned = sum(i["amount"] for i in month_income)
        max_value = max(max_value, spent, earned)
        month_data.append({"month": ym, "spent": spent, "earned": earned, "net": earned - spent})

    max_value = max_value if max_value > 0 else 1

    bar_rows = ""
    for m in month_data:
        spent_width = int((m["spent"] / max_value) * 100)
        earned_width = int((m["earned"] / max_value) * 100)
        net_color = "green" if m["net"] >= 0 else "red"
        bar_rows += f"""
        <tr>
            <td>{m['month']}</td>
            <td>
                <div style="background:#e74c3c; width:{spent_width}%; height:18px; border-radius:3px;"></div>
                ₹{m['spent']:.2f}
            </td>
            <td>
                <div style="background:#2ecc71; width:{earned_width}%; height:18px; border-radius:3px;"></div>
                ₹{m['earned']:.2f}
            </td>
            <td style="color:{net_color};">₹{m['net']:.2f}</td>
        </tr>
        """

    page_html = f"""<html>
<head><title>Monthly Comparison</title></head>
<body style="font-family: Arial; max-width: 700px; margin: 40px auto;">
    <h1>Monthly Comparison — Last {n} Month(s)</h1>
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><th>Month</th><th>Spent</th><th>Income</th><th>Net</th></tr>
        {bar_rows}
    </table>
    <p><em>Bar length is relative to the highest single spent/income value shown.</em></p>
</body>
</html>"""

    with open("comparison.html", "w") as f:
        f.write(page_html)

    webbrowser.open("file://" + os.path.abspath("comparison.html"))
    print("Comparison report generated and opened.")


# ---------- CSV Export ----------

def export_to_csv():
    expenses = load_expenses()
    if not expenses:
        print("No expenses to export.")
        return
    filename = "expenses_export.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "category", "amount"])
        for e in expenses:
            writer.writerow([
                e.get("date", "unknown"),
                e.get("category", "uncategorized"),
                e.get("amount", 0)
            ])
    print(f"Exported to {os.path.abspath(filename)}")


# ---------- Menu ----------

def menu():
    while True:
        print(
            "\n1. Add expense"
            "\n2. Edit expense"
            "\n3. Delete expense"
            "\n4. Generate report"
            "\n5. Export to CSV"
            "\n6. View statistics"
            "\n7. Manage budgets"
            "\n8. Manage recurring expenses"
            "\n9. Manage income"
            "\n10. Compare months"
            "\n11. Restore from backup"
            "\n12. Exit"
        )
        choice = input("Choose: ").strip()
        if choice == "1":
            add_expense()
        elif choice == "2":
            edit_expense()
        elif choice == "3":
            delete_expense()
        elif choice == "4":
            generate_html()
        elif choice == "5":
            export_to_csv()
        elif choice == "6":
            show_statistics()
        elif choice == "7":
            set_budgets()
        elif choice == "8":
            manage_recurring()
        elif choice == "9":
            manage_income()
        elif choice == "10":
            generate_comparison_report()
        elif choice == "11":
            restore_from_backup()
        elif choice == "12":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    menu()
