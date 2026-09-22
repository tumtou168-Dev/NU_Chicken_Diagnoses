# app/services/email_service.py
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

logger = logging.getLogger(__name__)

RESET_SALT = "password-reset-salt"


def generate_reset_token(email: str, secret_key: str) -> str:
    """Generate a time-stamped cryptographically signed password reset token."""
    s = URLSafeTimedSerializer(secret_key)
    return s.dumps(email, salt=RESET_SALT)


def verify_reset_token(token: str, secret_key: str, max_age: int = 3600) -> str | None:
    """Verify the token and return the email if valid and not expired (default 1 hour)."""
    s = URLSafeTimedSerializer(secret_key)
    try:
        email = s.loads(token, salt=RESET_SALT, max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None


class EmailService:
    @staticmethod
    def send_password_reset_email(to_email: str, reset_url: str, user_name: str = "") -> bool:
        """Send a password reset email via SMTP. If unconfigured, logs the reset URL for dev use."""
        mail_server = current_app.config.get("MAIL_SERVER")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        mail_use_tls = current_app.config.get("MAIL_USE_TLS", True)
        mail_use_ssl = current_app.config.get("MAIL_USE_SSL", False)
        mail_sender = current_app.config.get("MAIL_DEFAULT_SENDER") or mail_username or "noreply@chickendiagnoses.com"

        subject = "IDNS - កំណត់ពាក្យសម្ងាត់ឡើងវិញ / Password Reset Request"

        display_name = user_name or to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6f8f7; margin: 0; padding: 30px 15px;">
            <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e6ebe8; border-radius: 12px; padding: 32px 28px; box-shadow: 0 4px 16px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h2 style="color: #0a7f5f; margin: 0; font-size: 22px; font-weight: 700;">IDNS</h2>
                    <p style="color: #65756e; font-size: 13px; margin: 4px 0 0;">ប្រព័ន្ធជំនាញសម្រាប់រោគវិនិច្ឆ័យមាន់ · Chicken Disease Diagnosis</p>
                </div>
                <div style="color: #26332e; font-size: 15px; line-height: 1.6;">
                    <p>សួស្តី <strong>{display_name}</strong>,</p>
                    <p>យើងបានទទួលសំណើសុំកំណត់ពាក្យសម្ងាត់ឡើងវិញសម្រាប់គណនីរបស់អ្នក។ សូមចុចប៊ូតុងខាងក្រោមដើម្បីបង្កើតពាក្យសម្ងាត់ថ្មី៖</p>
                    <div style="text-align: center; margin: 28px 0;">
                        <a href="{reset_url}" style="background-color: #0a7f5f; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block;">កំណត់ពាក្យសម្ងាត់ឡើងវិញ / Reset Password</a>
                    </div>
                    <p style="font-size: 13px; color: #65756e; margin-bottom: 20px;">តំណភ្ជាប់នេះមានសុពលភាពរយៈពេល <strong>៦០ នាទី (1 ម៉ោង)</strong>។ ប្រសិនបើអ្នកមិនបានស្នើសុំទេ សូមរំលងអ៊ីមែលនេះ។</p>
                    <hr style="border: none; border-top: 1px solid #f1f5f3; margin: 20px 0;">
                    <p style="font-size: 12px; color: #9aa8a2; word-break: break-all; margin: 0;">ប្រសិនបើប៊ូតុងខាងលើមិនដំណើរការ សូមចម្លងតំណភ្ជាប់នេះទៅកាន់ Browser របស់អ្នក៖<br><a href="{reset_url}" style="color: #0a7f5f;">{reset_url}</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""IDNS - Password Reset Request

Hello {display_name},

We received a request to reset your password. Click the link below to set a new password:
{reset_url}

This link is valid for 60 minutes. If you did not request a password reset, please ignore this email.
"""

        if not mail_server or not mail_username or not mail_password:
            # SMTP is not configured - log the link for easy local testing
            print(f"\n=======================================================")
            print(f"[PASSWORD RESET LINK] (SMTP not configured, logging link)")
            print(f"To: {to_email}")
            print(f"URL: {reset_url}")
            print(f"=======================================================\n")
            logger.info(f"Password reset link for {to_email}: {reset_url}")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = mail_sender
            msg["To"] = to_email

            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if mail_use_ssl:
                server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=10)
            else:
                server = smtplib.SMTP(mail_server, mail_port, timeout=10)
                if mail_use_tls:
                    server.starttls()

            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, [to_email], msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            print(f"[EMAIL ERROR] Failed to send via SMTP: {e}")
            print(f"[FALLBACK LINK] {reset_url}")
            return False
