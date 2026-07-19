# Expense Tracker

A command-line expense tracker built in Python. Tracks spending and income, generates HTML reports, and helps you stay on budget — all through a simple terminal menu.

## Features

- **Add / Edit / Delete expenses** — each expense gets a unique ID, with category search to quickly find entries in a long list
- **Input validation** — dates, amounts, and categories are all validated before being saved
- **Income tracking** — log income separately and see net savings (income − expenses)
- **Budgets** — set an overall monthly budget and/or per-category budgets, with live warnings when you're close to or over your limit
- **Recurring expenses** — set up things like rent or subscriptions once, and they're automatically added each month when you generate a report
- **HTML reports** — a full report with expense/income tables, category breakdown, statistics, and budget status, generated locally and opened in your browser
- **Multi-month comparison** — a bar-chart style report comparing spending and income across your last N months
- **Statistics** — average, highest, and lowest expense, plus your top spending category
- **CSV export** — export all expenses to a `.csv` file for use in Excel, Sheets, or Numbers
- **Automatic backups** — every save is backed up automatically, with a menu option to restore from the last backup if something goes wrong

## How to run

Requires Python 3.

```bash
python3 start.py
```

You'll see a menu like this:

```
1. Add expense
2. Edit expense
3. Delete expense
4. Generate report
5. Export to CSV
6. View statistics
7. Manage budgets
8. Manage recurring expenses
9. Manage income
10. Compare months
11. Restore from backup
12. Exit
```

Just enter the number for whatever you want to do, and follow the prompts.

## Data storage

All data is stored locally in JSON files created automatically the first time you use each feature:

- `expenses.json` — your expenses
- `income.json` — your income entries
- `budgets.json` — your overall and category budgets
- `recurring.json` — your recurring expense templates

Each of these gets a `_backup.json` copy created automatically before every save.

## Reports

Running "Generate report" or "Compare months" creates an HTML file (`report.html` or `comparison.html`) in the project folder and opens it directly in your default browser.

## Tech

Built with core Python only — no external dependencies. Uses the standard library (`json`, `csv`, `datetime`, `uuid`, `shutil`, `webbrowser`) to keep it lightweight and easy to run anywhere.

---

Built as a learning project while studying Python and AI/ML fundamentals.
