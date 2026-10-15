from flask import blueprint, render_template, redirect, url_for
from db import get_db
from decorators import role_acquired

leader=blprint("leader", __name__)

@leader.route("/leader")
@role_acquired("leader")
def pending_admins():
    rows=get_db().execute(
        "SELECT id ,name,email,status FROM users WHERE role='admin' ORDER BY status").fetchall()
    return render_template("pending_admins.html", admins=rows)

@leader.route("/leader/<int:user_id>/action", methods=["POST"])
@role_acquired("leader")
def decide(user_id,action):
    status={"approve":"active", "reject":"rejected"}.get(action)
    if status:
        with get_db() as conn:
            conn.execute("UPDATE users SET status=? WHERE id=? and role='admin'", (status, user_id))
            return redirect(url_for("leader.pending"))