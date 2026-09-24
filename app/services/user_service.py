# app/services/user_service.py
from typing import List, Optional
from app.models.user import UserTable
from app.models.role import RoleTable
from extensions import db
from app.services.avatar_service import AvatarService

class UserService:
    @staticmethod
    def get_user_all() -> List[UserTable]:
        return UserTable.query.order_by(UserTable.id.desc()).all()

    @staticmethod
    def get_page(page: int, per_page: int = 20):
        return UserTable.query.order_by(UserTable.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def counts() -> dict:
        """Total / active / inactive counts via SQL COUNT, without loading every row."""
        total = db.session.scalar(db.select(db.func.count(UserTable.id)))
        active = db.session.scalar(db.select(db.func.count(UserTable.id)).filter_by(is_active=True))
        return {"total": total, "active": active, "inactive": total - active}

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[UserTable]:
        return UserTable.query.get(user_id)
    
    @staticmethod
    def create_user(
        data: dict,
        password: str,
        role_id: Optional[int] = None,
    ) -> UserTable:
        user = UserTable(
            username=data["username"],
            email=data["email"],
            full_name=data["full_name"],
            is_active=data.get("is_active", True),
        )
        user.set_password(password)
        
        if role_id:
            role = db.session.get(RoleTable, role_id)
            if role:
                user.roles = [role]
                
        db.session.add(user)
        db.session.commit()
        return user
        
    @staticmethod
    def update_user(
        user: UserTable,
        data: dict,
        password: Optional[str] = None,
        role_id: Optional[int] = None,
    ) -> UserTable:
        user.username = data["username"]
        user.email = data["email"]
        user.full_name = data["full_name"]
        user.is_active = data.get("is_active", True)
        
        if password:
            user.set_password(password)
        
        if role_id:
            role = db.session.get(RoleTable, role_id)
            if role:
                user.roles = [role]
                
        db.session.commit()
        return user
    
    @staticmethod
    def set_avatar(user: UserTable, file=None, remove: bool = False) -> None:
        """Replace (file) or clear (remove) a user's profile picture, deleting the old file."""
        old = user.avatar
        if file is not None and getattr(file, "filename", ""):
            user.avatar = AvatarService.save(file)
        elif remove:
            user.avatar = None
        else:
            return
        db.session.commit()
        AvatarService.delete(old)

    @staticmethod
    def delete_user(user: UserTable) -> None:
        """Delete a user. Rows that point at them via a foreign key would otherwise make PostgreSQL
        reject the delete: history keeps its rows with the user cleared, chat messages go with them."""
        from app.models.audit_log import AuditLog
        from app.models.chat_message import ChatMessage, ChatMessageHidden
        from app.models.expert_system import Case, Disease, Rule

        uid = user.id
        avatar = user.avatar
        AuditLog.query.filter_by(user_id=uid).update({"user_id": None}, synchronize_session=False)
        Case.query.filter_by(user_id=uid).update({"user_id": None}, synchronize_session=False)
        Disease.query.filter_by(doctor_id=uid).update({"doctor_id": None}, synchronize_session=False)
        Rule.query.filter_by(approved_by_id=uid).update({"approved_by_id": None}, synchronize_session=False)

        messages = db.select(ChatMessage.id).where(db.or_(
            ChatMessage.thread_user_id == uid,
            ChatMessage.sender_id == uid,
            ChatMessage.recipient_id == uid,
        ))
        ChatMessageHidden.query.filter(db.or_(
            ChatMessageHidden.user_id == uid,
            ChatMessageHidden.message_id.in_(messages),
        )).delete(synchronize_session=False)
        ChatMessage.query.filter(ChatMessage.id.in_(messages)).delete(synchronize_session=False)

        db.session.delete(user)
        db.session.commit()
        AvatarService.delete(avatar)