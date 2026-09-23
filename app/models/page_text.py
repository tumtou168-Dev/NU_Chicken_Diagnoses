# app/models/page_text.py
from utils.timezone import now_kh
from extensions import db
from app.models.bilingual import BilingualMixin


class PageText(BilingualMixin, db.Model):
    """Editable UI text (headings, labels, hints) shown on a page, in Khmer and English."""
    __tablename__ = "tbl_page_texts"

    id = db.Column(db.Integer, db.Sequence('seq_page_texts_id'), primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False)
    page = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.String(255))
    description_km = db.Column(db.String(255))
    text_km = db.Column(db.Text, nullable=False)
    text_en = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_kh, onupdate=now_kh, nullable=False)

    def __repr__(self) -> str:
        return f"<PageText {self.key}>"
