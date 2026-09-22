# app/__init__.py
import os
from flask import Flask, redirect, url_for, flash, request, render_template
from flask_login import current_user
from sqlalchemy import inspect, text
from config import Config
from extensions import db, csrf, login_manager
from app.models.user import UserTable


def create_app(config_class: type[Config] = Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    #init extensions
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    # Flask-Login settings
    login_manager.login_view = "auth.login"
    login_manager.login_message = "សូមចូលគណនីដើម្បីចូលមើលទំព័រនេះ។"
    login_manager.login_message_category = "warning"
    
    @login_manager.user_loader
    def load_user(user_id: str):
        return UserTable.query.get(int(user_id))
    
    # register blueprints
    from app.routes.user_routes import user_bp
    from app.routes.role_routes import role_bp
    from app.routes.permission_routes import permission_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.expert_system import expert_system_bp
    from app.routes.audit_routes import audit_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.lang_routes import lang_bp
    from app.routes.menu_routes import menu_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(permission_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(expert_system_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(lang_bp)
    app.register_blueprint(menu_bp)
    
    from app.services.avatar_service import AvatarService

    from app.forms.permission_forms import MODULE_LABELS

    @app.template_filter("module_label")
    def module_label(value):
        """Khmer display name for a permission module (falls back to the stored value)."""
        return MODULE_LABELS.get(value, value)

    from app.i18n import LANGUAGES, gettext, gettext_html, gettext_pair, gettext_inline, data_text, audit_target, audit_action, audit_detail, get_locale

    app.jinja_env.globals["_"] = gettext
    app.jinja_env.globals["_h"] = gettext_html
    app.jinja_env.globals["bi"] = gettext_pair   # bilingual (Khmer + English) label
    app.jinja_env.filters["audit_target"] = audit_target
    app.jinja_env.filters["audit_action"] = audit_action
    app.jinja_env.filters["audit_detail"] = audit_detail
    app.jinja_env.filters["dt"] = data_text   # Khmer display of built-in role/permission names
    app.jinja_env.globals["bit"] = gettext_inline   # same, as one line of plain text

    from app.services.page_text_service import PageTextService
    app.jinja_env.globals["t"] = PageTextService.text
    app.jinja_env.globals["tb"] = PageTextService.block   # editable page text stored in the database

    from app.services.page_feature_service import PageFeatureService
    app.jinja_env.globals["menu_enabled"] = PageFeatureService.is_enabled   # hide a nav link an admin disabled
    login_manager.localize_callback = gettext

    @app.context_processor
    def inject_helpers():
        return {"avatar_url": AvatarService.url, "current_lang": get_locale(), "languages": LANGUAGES}

    ERROR_PAGES = {
        403: ("គ្មានសិទ្ធិចូលប្រើ", "អ្នកមិនមានសិទ្ធិមើលទំព័រនេះទេ។ សូមទាក់ទងអ្នកគ្រប់គ្រង ប្រសិនបើអ្នកគិតថាមានកំហុស។"),
        404: ("រកមិនឃើញទំព័រ", "ទំព័រដែលអ្នកកំពុងស្វែងរកមិនមាន ឬត្រូវបានផ្លាស់ទីហើយ។"),
        405: ("វិធីសាស្ត្រមិនត្រូវបានអនុញ្ញាត", "សកម្មភាពដែលអ្នកស្នើមិនត្រូវបានអនុញ្ញាតសម្រាប់ទំព័រនេះទេ។"),
        500: ("មានបញ្ហាកើតឡើងលើប្រព័ន្ធ", "យើងជួបបញ្ហាបច្ចេកទេសមួយ។ សូមព្យាយាមម្តងទៀតក្នុងពេលបន្តិចទៀត។"),
    }

    def render_error(error):
        code = getattr(error, "code", 500) or 500
        if code == 500:
            db.session.rollback()
        title, message = (gettext(s) for s in ERROR_PAGES.get(code, ERROR_PAGES[500]))
        try:
            return render_template("errors/error.html", code=code, title=title, message=message), code
        except Exception:  # never let the error page itself fail
            return f"{code} {title}", code

    for _code in ERROR_PAGES:
        app.register_error_handler(_code, render_error)

    @app.errorhandler(413)
    def file_too_large(_error):
        flash(gettext("ឯកសារដែលបានផ្ទុកឡើងធំពេក។ ទំហំអតិបរមាគឺ 2MB។"), "danger")
        return redirect(request.referrer or url_for("tbl_users.profile"))

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for(current_user.landing_endpoint()))
        return redirect(url_for("auth.login"))
    
    # create tables
    with app.app_context():
        from app.models.user import UserTable
        from app.models.role import RoleTable
        from app.models.permission import PermissionTable
        from app.models.expert_system import Category, Symptom, Disease, Rule, Case
        from app.models.audit_log import AuditLog
        from app.models.page_text import PageText
        from app.models.page_feature import PageFeature

        # Default RESET_DB to 0 to prevent database reset on restart
        if os.environ.get("RESET_DB", "0") == "1":
            db.drop_all()

        db.create_all()
        _ensure_user_avatar_column()
        _ensure_khmer_columns()
        _ensure_page_feature_columns()
        
        # Only seed if the database is empty (e.g. check if any users exist)
        if not UserTable.query.first():
            from app.services.seed_service import seed_all
            seed_all()

        _backfill_khmer_content()

        # Runs on every start so existing databases also receive newly added page texts.
        PageTextService.ensure_defaults()

        from app.services.menu_service import MenuService
        MenuService.ensure_defaults()

    return app


def _ensure_user_avatar_column() -> None:
    """create_all() never alters existing tables, so add tbl_users.avatar if it is missing."""
    columns = {c["name"] for c in inspect(db.engine).get_columns("tbl_users")}
    if "avatar" not in columns:
        db.session.execute(text("ALTER TABLE tbl_users ADD COLUMN avatar VARCHAR(255)"))
        db.session.commit()


# Khmer siblings of the English knowledge-base columns: table -> {column: length}
KHMER_COLUMNS = {
    "tbl_categories": {"name_km": 120, "description_km": 255},
    "tbl_symptoms": {"name_km": 120, "description_km": 255},
    "tbl_diseases": {"name_km": 120, "description_km": 255, "treatment_km": 255},
    "tbl_rules": {"title_km": 120, "description_km": 255},
    "tbl_page_texts": {"description_km": 255},
}


def _ensure_page_feature_columns() -> None:
    """create_all() never alters existing tables, so add tbl_page_features.disabled_until if it is missing."""
    columns = {c["name"] for c in inspect(db.engine).get_columns("tbl_page_features")}
    if "disabled_until" not in columns:
        db.session.execute(text("ALTER TABLE tbl_page_features ADD COLUMN disabled_until TIMESTAMP"))
        db.session.commit()


def _ensure_khmer_columns() -> None:
    """create_all() never alters existing tables, so add the *_km columns where they are missing."""
    inspector = inspect(db.engine)
    for table, columns in KHMER_COLUMNS.items():
        existing = {c["name"] for c in inspector.get_columns(table)}
        for name, length in columns.items():
            if name not in existing:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} VARCHAR({length})"))
    db.session.commit()


def _backfill_khmer_content() -> None:
    """Fill the Khmer text of the sample data. Only empty columns are touched, so admin edits survive."""
    from app.models.expert_system import Category, Disease, Rule
    from app.services import khmer_data as kd

    plans = [
        (Category, "name", kd.CATEGORIES, ("name_km", "description_km")),
        (Disease, "name", kd.DISEASES, ("name_km", "description_km", "treatment_km")),
        (Rule, "title", kd.RULES, ("title_km", "description_km")),
    ]
    changed = False
    for model, key, table, fields in plans:
        for row in model.query.all():
            values = table.get(getattr(row, key))
            if not values:
                continue
            for field, value in zip(fields, values):
                if not getattr(row, field):
                    setattr(row, field, value)
                    changed = True
    if changed:
        db.session.commit()
