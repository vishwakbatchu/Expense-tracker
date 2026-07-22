import os
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")


def send_password_reset_email(to_email: str, token: str) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("Email service is not configured (missing RESEND_API_KEY)")

    resend.api_key = RESEND_API_KEY
    reset_link = f"{APP_BASE_URL}/reset-password.html?token={token}"

    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": "Reset your Expense Tracker password",
        "html": (
            f"<p>You asked to reset your Expense Tracker password.</p>"
            f"<p><a href=\"{reset_link}\">Click here to set a new password</a> "
            f"(expires in 30 minutes).</p>"
            f"<p>If you didn't request this, you can ignore this email.</p>"
        ),
    })
