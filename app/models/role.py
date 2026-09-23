# app/models/role.py
from utils.timezone import now_kh
from extensions import db
from app.models.associations import tbl_user_roles, tbl_role_permissions


class RoleTable(db.Model):
    __tablename__= "tbl_roles"
    
    id = db.Column(db.Integer, db.Sequence('seq_roles_id'), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_kh, onupdate=now_kh, nullable=False)
    
    # NOTE: matches UserTable.roles
    users = db.relationship("UserTable", secondary=tbl_user_roles,back_populates="roles" )
    
    # NOTE: matches PermissionTable.roles
    permissions = db.relationship("PermissionTable", secondary=tbl_role_permissions, back_populates="roles")
    
    def has_permission(self, permission_code: str) -> bool:
        return any(p.code == permission_code for p in self.permissions)
    
    def __repr__(self) -> str:
        return f"<Role{self.name}>"
