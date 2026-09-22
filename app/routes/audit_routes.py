from flask import Blueprint, render_template, abort, Response, request
from flask_login import login_required, current_user
from app.services.audit_service import AuditService
from app.services.user_service import UserService
import csv
import io

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")

@audit_bp.route("/")
@login_required
def index():
    if not current_user.has_role("Admin"):
        abort(403)
    
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    pager = AuditService.get_page(page, search_query)
    return render_template("audit/index.html", logs=pager.items, pager=pager, search_query=search_query)

@audit_bp.route("/user/<int:user_id>")
@login_required
def user_logs(user_id):
    if not current_user.has_role("Admin"):
        abort(403)

    user = UserService.get_user_by_id(user_id)
    if not user:
        abort(404)

    page = request.args.get("page", 1, type=int)
    pager = AuditService.get_user_logs_page(user_id, page)
    return render_template("audit/user_logs.html", logs=pager.items, pager=pager, user=user)

@audit_bp.route("/export")
@login_required
def export():
    if not current_user.has_role("Admin"):
        abort(403)
        
    search_query = request.args.get("q", "").strip()
    
    if search_query:
        logs = AuditService.search_logs(search_query)
    else:
        logs = AuditService.get_all_logs()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["ID", "User", "Action", "Target Type", "Target ID", "Details", "IP Address", "Timestamp"])
    
    # Write data
    for log in logs:
        username = log.user.username if log.user else "System/Guest"
        writer.writerow([
            log.id, 
            username, 
            log.action, 
            log.target_type, 
            log.target_id, 
            log.details, 
            log.ip_address, 
            log.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
        
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=audit_logs.csv"}
    )
