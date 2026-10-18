from flask import Blueprint, render_template, redirect, url_for, request, session, abort, flash
from db import get_db
from decorators import role_acquired

admin = Blueprint("admin", __name__)

def get_club_leader_id():
    role = session.get("role")
    if role == "leader":
        return session.get("user_id")
    elif role == "admin":
        with get_db() as conn:
            user = conn.execute("SELECT leader_id FROM users WHERE id=?", (session["user_id"],)).fetchone()
            return user["leader_id"] if user else None
    return None

@admin.route("/inbox")
@role_acquired("admin", "leader")
def inbox():
    leader_id = get_club_leader_id()
    if not leader_id:
        abort(403)

    filter_type = request.args.get("filter", "all")
    
    with get_db() as conn:
        unread_count = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE leader_id=? AND is_read=0",
            (leader_id,)
        ).fetchone()["c"]

        total_count = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE leader_id=?",
            (leader_id,)
        ).fetchone()["c"]

        if filter_type == "unread":
            msgs = conn.execute(
                "SELECT * FROM messages WHERE leader_id=? AND is_read=0 ORDER BY id DESC",
                (leader_id,)
            ).fetchall()
        else:
            msgs = conn.execute(
                "SELECT * FROM messages WHERE leader_id=? ORDER BY id DESC",
                (leader_id,)
            ).fetchall()

    return render_template(
        "inbox.html",
        msgs=msgs,
        filter_type=filter_type,
        unread_count=unread_count,
        total_count=total_count
    )

@admin.route("/inbox/<int:msg_id>/read", methods=["POST"])
@role_acquired("admin", "leader")
def mark_read(msg_id):
    leader_id = get_club_leader_id()
    if not leader_id:
        abort(403)

    with get_db() as conn:
        conn.execute("UPDATE messages SET is_read=1 WHERE id=? AND leader_id=?", (msg_id, leader_id))
    
    flash("Message marked as read.")
    return redirect(url_for("admin.inbox"))

@admin.route("/inbox/<int:msg_id>/delete", methods=["POST"])
@role_acquired("admin", "leader")
def delete(msg_id):
    leader_id = get_club_leader_id()
    if not leader_id:
        abort(403)

    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE id=? AND leader_id=?", (msg_id, leader_id))
    
    flash("Message deleted.")
    return redirect(url_for("admin.inbox"))
