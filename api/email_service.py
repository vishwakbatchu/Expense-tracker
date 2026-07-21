import os
import smtplib
from email.mime.text import MIMEText

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")


def send_password_reset_email(to_email: str, token: str) -> None:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("Email service is not configured (missing GMAIL_ADDRESS/GMAIL_APP_PASSWORD)")

    reset_link = f"{APP_BASE_URL}/reset-password.html?token={token}"

    body = (
        "You asked to reset your Expense Tracker password.\n\n"
        f"Click this link to set a new password (expires in 30 minutes):\n{reset_link}\n\n"
        "If you didn't request this, you can ignore this email."
    )

    message = MIMEText(body)
    message["Subject"] = "Reset your Expense Tracker password"
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [to_email], message.as_string())
