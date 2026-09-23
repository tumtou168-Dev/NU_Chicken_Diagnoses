# app/services/page_feature_service.py
from datetime import timedelta
from typing import Optional

from extensions import db
from app.models.page_feature import PageFeature
from utils.timezone import now_kh


class PageFeatureService:
    """Lets an admin take a page/menu item offline (indefinitely, or for a set
    amount of time) and show a maintenance message instead. A page with no row
    is enabled, so nothing needs seeding for existing pages."""

    @staticmethod
    def _get(page: str) -> Optional[PageFeature]:
        return db.session.scalar(db.select(PageFeature).filter_by(page=page))

    @classmethod
    def is_enabled(cls, page: str) -> bool:
        feature = cls._get(page)
        if feature is None or feature.enabled:
            return True
        if feature.disabled_until and now_kh() >= feature.disabled_until:
            # The timer ran out - flip it back on now, no scheduler needed.
            feature.enabled = True
            feature.disabled_until = None
            db.session.commit()
            return True
        return False

    @classmethod
    def status(cls, page: str) -> dict:
        """{"enabled": bool, "disabled_until": datetime|None} after resolving any expired timer."""
        enabled = cls.is_enabled(page)
        feature = cls._get(page)
        return {"enabled": enabled, "disabled_until": None if enabled or feature is None else feature.disabled_until}

    @classmethod
    def set_enabled(cls, page: str, enabled: bool) -> PageFeature:
        feature = cls._get(page)
        if feature is None:
            feature = PageFeature(page=page, enabled=enabled)
            db.session.add(feature)
        else:
            feature.enabled = enabled
            feature.disabled_until = None
        db.session.commit()
        return feature

    @classmethod
    def disable_for(cls, page: str, minutes: int) -> PageFeature:
        feature = cls._get(page)
        until = now_kh() + timedelta(minutes=minutes)
        if feature is None:
            feature = PageFeature(page=page, enabled=False, disabled_until=until)
            db.session.add(feature)
        else:
            feature.enabled = False
            feature.disabled_until = until
        db.session.commit()
        return feature
