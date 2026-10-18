from flask import Blueprint, render_template,redirect, url_for
from db import get_db
from decorators import role_acquired

admin=Blueprint("admin", __name__)
@admin.route("/inbox")
@role_acquired("admin","leader")
def inbox():
    msgs=get_db().execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    return render_template("inbox.html", msgs=msgs)

@admin.route("/inbox/<int:msg_id>/read", methods=["POST"])
@role_required("admin","leader")
def mark_read(msg_id):
    with get_db() as conn:
        conn.execute("UPDATE messages SET is_read=1 WHERE id=?", (msg_id,))
    return redirect(url_for("admin.inbox"))

@admin.route("/inbox/<int:msg_id>/delete", methods=["POST"])
@role_required("admin","leader")
def delete(msg_id):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE id=?", (msg_id,))
    return redirect(url_for("admin.inbox"))