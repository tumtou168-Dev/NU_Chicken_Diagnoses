# app/services/email_service.py
import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_password_reset_code_email(to_email: str, code: str, user_name: str = "", minutes: int = 10) -> bool:
        """Email a 6-digit password reset code via SMTP. If unconfigured, logs the code for dev use."""
        mail_server = current_app.config.get("MAIL_SERVER")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        mail_use_tls = current_app.config.get("MAIL_USE_TLS", True)
        mail_use_ssl = current_app.config.get("MAIL_USE_SSL", False)
        mail_sender = current_app.config.get("MAIL_DEFAULT_SENDER") or mail_username or "noreply@chickendiagnoses.com"

        subject = f"IDNS - លេខកូដកំណត់ពាក្យសម្ងាត់ / Password reset code: {code}"

        display_name = user_name or to_email
        safe_name = html.escape(display_name)
        spaced_code = " ".join(code)

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
                    <p>សួស្តី <strong>{safe_name}</strong>,</p>
                    <p>នេះជាលេខកូដសម្រាប់កំណត់ពាក្យសម្ងាត់ឡើងវិញ។ សូមបញ្ចូលវានៅលើគេហទំព័រ។<br>
                    <span style="color: #65756e; font-size: 13px;">Here is your password reset code. Enter it on the website.</span></p>
                    <div style="text-align: center; margin: 28px 0;">
                        <div style="display: inline-block; background-color: #ecfdf5; border: 1px solid #a7f3d0; color: #086b50; border-radius: 10px; padding: 14px 26px; font-size: 32px; font-weight: 700; letter-spacing: 6px; font-family: 'SFMono-Regular', Menlo, Consolas, monospace;">{spaced_code}</div>
                    </div>
                    <p style="font-size: 13px; color: #65756e; margin-bottom: 20px;">លេខកូដនេះមានសុពលភាព <strong>{minutes} នាទី</strong>។ កុំចែករំលែកលេខកូដនេះជាមួយនរណាម្នាក់។ ប្រសិនបើអ្នកមិនបានស្នើសុំទេ សូមរំលងអ៊ីមែលនេះ។<br>
                    This code expires in <strong>{minutes} minutes</strong>. Never share it with anyone. If you didn't request it, ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""IDNS - Password reset code

Hello {display_name},

Your password reset code is: {code}

It expires in {minutes} minutes. Never share it with anyone.
If you did not request a password reset, please ignore this email.
"""

        if not mail_server or not mail_username or not mail_password:
            # SMTP is not configured - log the code for easy local testing
            print(f"\n=======================================================")
            print(f"[PASSWORD RESET CODE] (SMTP not configured, logging code)")
            print(f"To: {to_email}")
            print(f"Code: {code}")
            print(f"=======================================================\n")
            logger.info(f"Password reset code for {to_email}: {code}")
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
            print(f"[FALLBACK CODE] {to_email}: {code}")
            return False
