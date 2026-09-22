# app/models/page_feature.py
from datetime import datetime
from extensions import db


class PageFeature(db.Model):
    """Per-page/menu-item enable/disable switch. Absence of a row means enabled;
    when disabled, visitors see a maintenance message (or the menu link disappears).
    disabled_until: optional - lets an admin disable something for a short time and
    have it turn back on by itself, with no scheduler needed (checked at request time)."""
    __tablename__ = "tbl_page_features"

    id = db.Column(db.Integer, db.Sequence('seq_page_features_id'), primary_key=True)
    page = db.Column(db.String(60), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    disabled_until = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<PageFeature {self.page} enabled={self.enabled}>"
