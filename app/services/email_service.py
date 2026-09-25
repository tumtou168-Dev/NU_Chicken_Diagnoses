# app/services/email_service.py
import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

import requests
from flask import current_app

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    @staticmethod
    def send_password_reset_code_email(to_email: str, code: str, user_name: str = "", minutes: int = 10) -> bool:
        """Email a 6-digit password reset code via Brevo (when BREVO_API_KEY is set) or SMTP.
        If neither is configured, or sending fails, the code is logged instead (for dev use)."""
        mail_server = current_app.config.get("MAIL_SERVER")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        mail_use_tls = current_app.config.get("MAIL_USE_TLS", True)
        mail_use_ssl = current_app.config.get("MAIL_USE_SSL", False)
        mail_sender = current_app.config.get("MAIL_DEFAULT_SENDER") or mail_username or "noreply@chickendiagnoses.com"

        subject = f"Chicken Diagnosis - លេខកូដកំណត់ពាក្យសម្ងាត់ / Password reset code: {code}"

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
                    <h2 style="color: #0a7f5f; margin: 0; font-size: 22px; font-weight: 700;">Chicken Diagnosis</h2>
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

        text_content = f"""Chicken Diagnosis - Password reset code

Hello {display_name},

Your password reset code is: {code}

It expires in {minutes} minutes. Never share it with anyone.
If you did not request a password reset, please ignore this email.
"""

        brevo_key = current_app.config.get("BREVO_API_KEY")
        if brevo_key:
            if EmailService._send_brevo(brevo_key, mail_sender, to_email, display_name, subject, html_content, text_content):
                return True
            print(f"[FALLBACK CODE] {to_email}: {code}")
            return False

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

    @staticmethod
    def _send_brevo(api_key: str, sender: str, to_email: str, to_name: str,
                    subject: str, html_content: str, text_content: str) -> bool:
        """Send through Brevo's HTTPS API. The sender ("Name <email>" or just an email) must be
        verified in Brevo, or Brevo rejects the message."""
        sender_name, sender_email = parseaddr(sender)
        payload = {
            "sender": {"name": sender_name or "Chicken Diagnosis", "email": sender_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content,
        }
        try:
            resp = requests.post(BREVO_SEND_URL, json=payload, timeout=10,
                                 headers={"api-key": api_key, "accept": "application/json"})
        except requests.RequestException as e:
            logger.error(f"Brevo request failed for {to_email}: {e}")
            print(f"[EMAIL ERROR] Brevo request failed: {e}")
            return False
        if resp.status_code >= 300:
            # Brevo explains the problem in the body, e.g. an unverified sender or a wrong key.
            logger.error(f"Brevo rejected email to {to_email}: {resp.status_code} {resp.text[:300]}")
            print(f"[EMAIL ERROR] Brevo rejected the email: {resp.status_code} {resp.text[:300]}")
            return False
        return True
