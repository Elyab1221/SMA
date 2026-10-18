from flask import Blueprint, render_template, redirect, url_for, flash, abort, session
from db import get_db
from decorators import role_acquired

leader = Blueprint("leader", __name__)

@leader.route("/leader")
@role_acquired("leader")
def dashboard():
    leader_id = session["user_id"]
    
    with get_db() as conn:
        leader_record = conn.execute(
            "SELECT id, name, email, leader_code, club_name FROM users WHERE id=?",
            (leader_id,)
        ).fetchone()

        admins = conn.execute(
            "SELECT id, name, email, status, created_at FROM users WHERE role='admin' AND leader_id=? ORDER BY CASE status WHEN 'pending' THEN 1 WHEN 'active' THEN 2 ELSE 3 END, name",
            (leader_id,)
        ).fetchall()

        students = conn.execute(
            "SELECT id, name, email, status, created_at FROM users WHERE role='student' AND leader_id=? ORDER BY status, name",
            (leader_id,)
        ).fetchall()

        pending_admins_count = sum(1 for a in admins if a["status"] == "pending")
        active_admins_count = sum(1 for a in admins if a["status"] == "active")
        total_students_count = len(students)
        
        total_messages_count = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE leader_id=?",
            (leader_id,)
        ).fetchone()["c"]

    return render_template(
        "pending.html",
        leader_record=leader_record,
        admins=admins,
        students=students,
        pending_admins_count=pending_admins_count,
        active_admins_count=active_admins_count,
        total_students_count=total_students_count,
        total_messages_count=total_messages_count
    )

# Alias for backwards compatibility
@leader.route("/leader/pending")
@role_acquired("leader")
def pending_admins():
    return dashboard()

STATUS_ACTIONS = {
    "approve": "active",
    "activate": "active",
    "reject": "rejected",
    "suspend": "suspended"
}

@leader.route("/leader/<int:user_id>/<action>", methods=["POST"])
@role_acquired("leader")
def decide(user_id, action):
    leader_id = session["user_id"]
    
    with get_db() as conn:
        target = conn.execute(
            "SELECT * FROM users WHERE id=? AND leader_id=? AND role!='leader'",
            (user_id, leader_id)
        ).fetchone()

        if not target:
            abort(404)

        if action in STATUS_ACTIONS:
            new_status = STATUS_ACTIONS[action]
            conn.execute("UPDATE users SET status=? WHERE id=?", (new_status, user_id))
            action_names = {
                "approve": "approved",
                "activate": "activated",
                "reject": "rejected",
                "suspend": "suspended"
            }
            flash(f"User {target['name']} ({target['role']}) has been {action_names.get(action, new_status)}.")

        elif action == "remove":
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.execute("DELETE FROM send_limits WHERE user_id=?", (user_id,))
            flash(f"User {target['name']} has been removed from the club.")

        else:
            abort(400)

    return redirect(url_for("leader.dashboard"))
