import secrets
from flask import Blueprint, render_template, redirect, url_for,flash,abort
from werkzeug.security import generate_password_hash
from db import get_db
from decorators import role_acquired

leader=Blueprint("leader", __name__)

@leader.route("/leader")
@role_acquired("leader")
def pending_admins():
    q="SELECT id,name,email,status FROM users WHERE role=? ORDER BY status,name"
    conn=get_db()
    admins=conn.execute(q,("admin",)).fetchall()
    students=conn.execute(q,("student",)).fetchall()
    return render_template("pending.html",admins=admins, students=students)
STATUS_ACTIONS={"approve":"active","activate":"active","reject":"rejected","suspend":"suspended"}

@leader.route("/leader/<int:user_id>/<action>", methods=["POST"])
@role_acquired("leader")
def decide(user_id,action):
    with get_db() as conn:
        target=conn.execute("SELECT * FROM users WHERE id=? AND role !='leader' ", (user_id,)).fetchone()
        if not target:
            abort(404)
        if action in STATUS_ACTIONS:
            conn.execute ("UPDATE users SET status=? WHERE id=?",(STATUS_ACTIONS[action],user_id,))
        elif action=="reset":
            temp=secrets.token_urlsafe(8)
            conn.execute("UPDATE users SET password_hash=? where id=?", (generate_password_hash(temp),user_id,))
            flash(f"temporary password for {target['name']}:{temp}(share it privately,it wont be shown again)")
        elif action=="remove":
            conn.execute("DELETE FROM users WHERE id=?",(user_id,))
            conn.execute("DELETE FROM send_limits WHERE user_id=?",(user_id,))
        else:
            abort(404)
    return redirect(url_for("leader.pending admins"))