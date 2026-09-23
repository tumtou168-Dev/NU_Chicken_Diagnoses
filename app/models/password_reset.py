# app/models/password_reset.py
from datetime import timedelta

from utils.timezone import now_kh
from extensions import db


class PasswordResetCode(db.Model):
    """A 6-digit code emailed for "forgot password". Only a keyed hash of the code is stored."""
    __tablename__ = "tbl_password_reset_codes"

    LIFETIME = timedelta(minutes=10)          # code must be entered within this time
    MAX_ATTEMPTS = 5                          # wrong guesses before the code is burned
    RESEND_COOLDOWN = timedelta(seconds=60)   # minimum gap between emails to one user
    SET_PASSWORD_WINDOW = timedelta(minutes=15)  # after verifying, time allowed to pick a new password

    id = db.Column(db.Integer, db.Sequence('seq_password_reset_codes_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("UserTable")

    @property
    def is_open(self) -> bool:
        """Still accepting guesses: not expired, not used, not locked out."""
        return self.used_at is None and self.attempts < self.MAX_ATTEMPTS and now_kh() < self.expires_at

    @property
    def can_set_password(self) -> bool:
        return (self.verified_at is not None and self.used_at is None
                and now_kh() < self.verified_at + self.SET_PASSWORD_WINDOW)
