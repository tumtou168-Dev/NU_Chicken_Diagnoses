# app/models/user.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db
from app.models.associations import tbl_user_roles


class UserTable(UserMixin, db.Model):
    __tablename__ = "tbl_users"
    
    id = db.Column(db.Integer, db.Sequence('seq_users_id'), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), nullable=True)  # filename under static/uploads/avatars
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # NOTE: matches RoleTable.users
    roles = db.relationship("RoleTable", secondary=tbl_user_roles, back_populates="users")
    
    def set_password(self, password:str) -> None:
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password:str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)
    
    def get_permission_codes(self) -> set[str]:
        return {perm.code for role in self.roles for perm in role.permissions}
    
    def has_permission(self, permission_code: str) -> bool:
        return permission_code in self.get_permission_codes()

    def landing_endpoint(self) -> str:
        """Where to send this user after login/'/' — the dashboard is Admin/Doctor only."""
        if self.has_role("Admin") or self.has_role("Doctor"):
            return "dashboard.index"
        return "expert_system.diagnose"

    def __repr__(self) -> str:
        return f"<User {self.username}>"
    
        
