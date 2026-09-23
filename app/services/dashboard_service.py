# app/services/dashboard_service.py
from collections import Counter
from datetime import datetime, time, timedelta
from typing import Any, Dict, List

from sqlalchemy import desc, func

from extensions import db
from app.i18n import ordered, pair_text
from app.models.audit_log import AuditLog
from utils.timezone import now_kh
from app.models.expert_system import Case, Disease, Rule, Symptom
from app.models.user import UserTable

TREND_DAYS = 14


def _axis(max_value: int) -> Dict[str, Any]:
    """Round the y-axis up to a clean top value with at most four steps."""
    if max_value <= 0:
        return {"top": 4, "ticks": [0, 1, 2, 3, 4]}
    magnitude = 1
    while True:
        for base in (1, 2, 5):
            step = base * magnitude
            if -(-max_value // step) <= 4:
                top = step * (-(-max_value // step))
                return {"top": top, "ticks": list(range(0, top + 1, step))}
        magnitude *= 10


class DashboardService:
    @staticmethod
    def build(user: UserTable) -> Dict[str, Any]:
        is_admin = user.has_role("Admin")
        is_staff = is_admin or user.has_role("Doctor")
        data: Dict[str, Any] = {"is_admin": is_admin, "is_staff": is_staff, "can_view_cases": False}

        if user.has_permission("view_cases"):
            data["can_view_cases"] = True
            data.update(DashboardService._case_data(user, is_staff))

        if is_staff:
            data["knowledge"] = {
                "diseases": db.session.query(func.count(Disease.id)).scalar() or 0,
                "symptoms": db.session.query(func.count(Symptom.id)).scalar() or 0,
                "rules": db.session.query(func.count(Rule.id)).scalar() or 0,
            }

        if is_admin:
            data["users_total"] = db.session.query(func.count(UserTable.id)).scalar() or 0
            data["users_active"] = (
                db.session.query(func.count(UserTable.id)).filter(UserTable.is_active.is_(True)).scalar() or 0
            )
            data["recent_logs"] = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(6).all()
        return data

    @staticmethod
    def _case_data(user: UserTable, is_staff: bool) -> Dict[str, Any]:
        # Admins/Doctors see every case (same rule as the Cases page); users only their own.
        scope = [] if is_staff else [Case.user_id == user.id]

        today = now_kh().date()
        first_day = today - timedelta(days=TREND_DAYS - 1)
        created = db.session.query(Case.created_at).filter(
            *scope, Case.created_at >= datetime.combine(first_day, time.min)
        )
        per_day = Counter(row[0].date() for row in created)
        trend: List[Dict[str, Any]] = []
        for i in range(TREND_DAYS):
            day = first_day + timedelta(days=i)
            trend.append({"date": day.isoformat(), "short": day.strftime("%d/%m"), "count": per_day.get(day, 0),
                          "label_visible": (TREND_DAYS - 1 - i) % 2 == 0})
        axis = _axis(max(p["count"] for p in trend))
        for p in trend:
            p["pct"] = round(p["count"] / axis["top"] * 100, 2)

        this_week = sum(p["count"] for p in trend[-7:])
        last_week = sum(p["count"] for p in trend[:7])
        avg_conf = db.session.query(func.avg(Case.confidence)).filter(*scope).scalar()

        top_rows = (
            db.session.query(Disease.name, Disease.name_km, func.count(Case.id).label("n"))
            .join(Case, Case.disease_id == Disease.id)
            .filter(*scope)
            .group_by(Disease.id, Disease.name, Disease.name_km)
            .order_by(desc("n"), Disease.name)
            .limit(5)
            .all()
        )
        top_max = max((n for _, _, n in top_rows), default=0)
        top_diseases = []
        for name, name_km, n in top_rows:
            first, second = ordered(name_km or "", name or "")
            top_diseases.append({
                "name": pair_text(first, second), "first": first, "second": second, "count": n,
                "pct": round(n / top_max * 100, 2) if top_max else 0,
            })

        return {
            "cases_total": Case.query.filter(*scope).count(),
            "cases_today": per_day.get(today, 0),
            "cases_week": this_week,
            "cases_week_delta": this_week - last_week,
            "avg_confidence": round(avg_conf, 1) if avg_conf is not None else None,
            "trend": trend,
            "trend_axis": axis,
            "trend_total": sum(p["count"] for p in trend),
            "top_diseases": top_diseases,
            "recent_cases": Case.query.filter(*scope).order_by(Case.created_at.desc()).limit(6).all(),
        }
