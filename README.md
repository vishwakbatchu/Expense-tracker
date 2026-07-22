# Expense Tracker

Track spending and income, set budgets, manage recurring expenses, and view reports — from the **terminal**, **web browser**, or as an **installable app** on your phone or desktop.

## Features

- **Add / Edit / Delete expenses** — each expense gets a unique ID, with category search
- **Income tracking** — log income separately and see net savings (income − expenses)
- **Budgets** — overall monthly and per-category budgets, with live warnings when you're close to or over limit
- **Recurring expenses** — rent, subscriptions, etc. auto-added when you view a month
- **Dashboard** — spent, income, net savings, category breakdown, budget bars
- **Monthly comparison** — side-by-side spent vs income across recent months
- **HTML reports & CSV export**
- **Automatic backups** — the previous version of each record type is retained in SQLite and can be restored from the app or CLI

## Web app (website + installable PWA)

### Setup

```bash
python3 -m pip install -r requirements.txt
```

### Run

From the project folder:

```bash
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

### Install as an app

- **Phone (Chrome / Safari):** open the site → browser menu → **Add to Home Screen** / **Install app**
- **Desktop (Chrome / Edge):** click the install icon in the address bar, or use the ⬇ button in the app header

The app works offline for the UI shell; data syncs when the server is running.

### API

REST endpoints live under `/api/` (e.g. `/api/expenses`, `/api/stats`). The web UI and any future mobile client can share the same backend.

## Deploy online (public website)

Put the app on the internet so **anyone** can open it with a link. [Render](https://render.com) free tier is the easiest option.

### Step 1 — Push code to GitHub

In your project folder:

```bash
git add api/ expense_tracker/ web/ requirements.txt render.yaml Procfile README.md
git commit -m "Add web app and deployment config"
git push origin main
```

If GitHub asks you to sign in, use your GitHub account (not a token pasted into the URL).

### Step 2 — Create a Render account

1. Go to [render.com](https://render.com) and sign up (free).
2. Connect your **GitHub** account when asked.

### Step 3 — Create the web service

1. Click **New +** → **Web Service**.
2. Select your **Expense-tracker** repository.
3. Render should detect `render.yaml` automatically. If not, set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python3 -m uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Choose the **Free** plan.
5. Click **Create Web Service**.

Wait 2–5 minutes for the first deploy. When it says **Live**, Render gives you a URL like:

```text
https://expense-tracker-xxxx.onrender.com
```

Share that link — anyone in the world can open it.

### Step 4 — Accounts and login

In Render → your service → **Environment**:

| Variable | Value |
|----------|--------|
| `APP_SECRET_KEY` | A long random secret used to secure sign-in sessions |

Save changes — Render redeploys automatically. Visitors must create an account and sign in before seeing or editing data. Each account has its own private expenses, income, budgets, and recurring items.

To keep access to your original shared data as the site owner, also set these optional variables:

| Variable | Value |
|----------|--------|
| `APP_USERNAME` | Your owner username |
| `APP_PASSWORD` | A strong owner password |

### Password-reset email setup

Password reset emails are sent through [Resend](https://resend.com). Create a Resend API key, then set these environment variables in your deployment (Render → Environment):

| Variable | Value |
|----------|-------|
| `RESEND_API_KEY` | Your Resend API key |
| `EMAIL_FROM` | A sender address allowed by Resend (the default is only suitable for testing) |
| `APP_BASE_URL` | The public URL of this app, such as `https://your-app.onrender.com` |

For local testing, export the same variables before starting Uvicorn. Never commit the API key to the repository.

**Local dev:** login is always enabled. Start the app normally, then create an account from the sign-in screen. To enable an owner account for existing data:

```bash
APP_USERNAME=admin APP_PASSWORD=secret APP_SECRET_KEY=dev-key \
  python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5 — Keep in mind

- **Every visitor signs in** — accounts are created from the sign-in screen and each person's tracker data is private.
- **Free tier sleeps** after ~15 minutes of no visits. The first load after that may take 30–60 seconds.
- **Data** is stored on the server while it runs. On redeploys, data may reset (fine for a demo; add a database later for production).

### Quick temporary link (optional)

To share **right now** without deploying (link works only while your Mac is on):

1. Install [ngrok](https://ngrok.com/download).
2. With your local server running on port 8000:
   ```bash
   ngrok http 8000
   ```
3. Copy the `https://….ngrok-free.app` URL and share it. It stops when you close ngrok or your computer sleeps.

## Command-line (original)

Still works with no extra dependencies beyond Python 3:

```bash
python3 start.py
```

Menu options 1–12 match the web features (add expense, reports, CSV, budgets, etc.).

## Data storage

The application uses SQLAlchemy. Locally, it defaults to SQLite in
`expense_tracker.db`. On Render, `render.yaml` provisions Render Postgres and
supplies its private connection string as `DATABASE_URL`. On first launch,
existing JSON files are imported automatically, so current accounts and
financial data are preserved.

## Project layout

```
start.py              # CLI entry point
database.py            # SQLAlchemy connection configuration
models.py              # SQLite data models
expense_tracker/       # Shared business logic & database storage
api/main.py           # FastAPI server
web/                  # Web UI + PWA (HTML, CSS, JS)
requirements.txt      # fastapi, uvicorn
```

## Tech

- **CLI:** Python + SQLAlchemy
- **Web:** FastAPI + vanilla HTML/CSS/JS (PWA)
- **Data:** SQLite (SQLAlchemy)

---

Built as a learning project while studying Python and AI/ML .
