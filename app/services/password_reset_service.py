# app/services/password_reset_service.py
import hashlib
import hmac
import secrets

from flask import current_app

from extensions import db
from utils.timezone import now_kh
from app.models.password_reset import PasswordResetCode
from app.models.user import UserTable
from app.services.email_service import EmailService


class PasswordResetService:

    @staticmethod
    def _hash(code: str) -> str:
        # Keyed with SECRET_KEY so a leaked table can't be brute-forced offline (only 1M possible codes).
        key = current_app.config["SECRET_KEY"].encode()
        return hmac.new(key, code.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def latest(user: UserTable) -> PasswordResetCode | None:
        return (PasswordResetCode.query.filter_by(user_id=user.id)
                .order_by(PasswordResetCode.id.desc()).first())

    @staticmethod
    def send_code(user: UserTable) -> bool:
        """Create a fresh code (voiding older ones) and email it. Returns False if still in the resend cooldown."""
        now = now_kh()
        last = PasswordResetService.latest(user)
        if last and now < last.created_at + PasswordResetCode.RESEND_COOLDOWN:
            return False

        PasswordResetCode.query.filter_by(user_id=user.id, used_at=None).update({"used_at": now})

        code = f"{secrets.randbelow(1_000_000):06d}"
        db.session.add(PasswordResetCode(
            user_id=user.id,
            code_hash=PasswordResetService._hash(code),
            created_at=now,
            expires_at=now + PasswordResetCode.LIFETIME,
        ))
        db.session.commit()

        minutes = int(PasswordResetCode.LIFETIME.total_seconds() // 60)
        EmailService.send_password_reset_code_email(user.email, code, user.full_name, minutes)
        return True

    @staticmethod
    def verify(user: UserTable, code: str) -> PasswordResetCode | None:
        """Check a guess against the user's latest code. Each wrong guess counts toward MAX_ATTEMPTS."""
        record = PasswordResetService.latest(user)
        if not record or not record.is_open:
            return None

        if hmac.compare_digest(record.code_hash, PasswordResetService._hash(code)):
            record.verified_at = now_kh()
            db.session.commit()
            return record

        record.attempts += 1
        db.session.commit()
        return None

    @staticmethod
    def consume(record: PasswordResetCode, new_password: str) -> None:
        record.user.set_password(new_password)
        record.used_at = now_kh()
        db.session.commit()
