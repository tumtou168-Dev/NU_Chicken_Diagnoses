# app/models/permission.py
from utils.timezone import now_kh
from extensions import db
from app.models.associations import tbl_role_permissions


class PermissionTable(db.Model):
    __tablename__ = "tbl_permissions"
    
    id = db.Column(db.Integer, db.Sequence('seq_permissions_id'), primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    module = db.Column(db.String(80), nullable=False, default="General")
    
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_kh, onupdate=now_kh, nullable=False)
    
    # NOTE: matches RoleTable.permissions
    roles = db.relationship("RoleTable", secondary=tbl_role_permissions, back_populates="permissions")
    
    def __repr__(self) -> str:
        return f"<Permission {self.code}>"
