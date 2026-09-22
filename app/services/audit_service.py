from flask import request
from flask_login import current_user
from app.models.audit_log import AuditLog
from app.models.user import UserTable
from extensions import db
import json

class AuditService:
    @staticmethod
    def log(action, target_type, target_id=None, details=None):
        """
        Logs an action to the audit log.
        """
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        ip_address = request.remote_addr if request else None
        
        if isinstance(details, (dict, list)):
            details = json.dumps(details)

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            details=details,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()

    @staticmethod
    def get_all_logs():
        return AuditLog.query.order_by(AuditLog.created_at.desc()).all()

    @staticmethod
    def get_logs_by_user(user_id):
        return AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc()).all()

    @staticmethod
    def search_logs(username_query):
        """
        Search logs by username.
        """
        if not username_query:
            return AuditService.get_all_logs()

        return AuditLog.query.join(UserTable).filter(
            UserTable.username.ilike(f"%{username_query}%")
        ).order_by(AuditLog.created_at.desc()).all()

    @staticmethod
    def get_page(page: int, username_query: str = "", per_page: int = 25):
        query = AuditLog.query
        if username_query:
            query = query.join(UserTable).filter(UserTable.username.ilike(f"%{username_query}%"))
        return query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_user_logs_page(user_id: int, page: int, per_page: int = 25):
        return AuditLog.query.filter_by(user_id=user_id).order_by(
            AuditLog.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
