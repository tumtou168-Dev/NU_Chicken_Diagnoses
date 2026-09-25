# app/models/stored_file.py
from utils.timezone import now_kh
from extensions import db


class StoredFile(db.Model):
    """An uploaded file (profile picture, chat photo, voice message) kept in the database.
    Hosts such as Render's free plan wipe the local disk on every restart, so uploads
    written under static/ would disappear; the database is the one place that persists."""
    __tablename__ = "tbl_files"

    key = db.Column(db.String(300), primary_key=True)   # "<folder>/<filename>", e.g. "avatars/ab12….jpg"
    content_type = db.Column(db.String(100), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    def __repr__(self) -> str:
        return f"<StoredFile {self.key}>"
