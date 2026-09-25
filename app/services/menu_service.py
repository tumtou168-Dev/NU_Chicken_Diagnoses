# app/services/menu_service.py
from extensions import db
from app.models import PermissionTable, RoleTable

# key -> (Khmer label, English label, icon, endpoint to reach it). Matches the "main" nav
# group in layouts/base.html. Keys double as the PageFeatureService "page" name.
MENU_ITEMS = {
    "dashboard": ("ផ្ទាំងគ្រប់គ្រង", "Dashboard", "grid-1x2", "dashboard.index"),
    "diagnose": ("ធ្វើរោគវិនិច្ឆ័យ", "Diagnose", "activity", "expert_system.diagnose"),
    "cases": ("ប្រវត្តិ", "History", "clock-history", "expert_system.cases_index"),
    "library": ("បណ្ណាល័យជំងឺ", "Disease library", "book", "expert_system.library_index"),
}

PERMISSION = ("manage_menu", "Manage Menu", "System")


class MenuService:
    @staticmethod
    def ensure_defaults() -> None:
        code, name, module = PERMISSION
        perm = db.session.scalar(db.select(PermissionTable).filter_by(code=code))
        if perm is None:
            perm = PermissionTable(code=code, name=name, module=module)
            db.session.add(perm)
            admin = db.session.scalar(db.select(RoleTable).filter_by(name="Admin"))
            if admin is not None:
                admin.permissions.append(perm)
            db.session.commit()
