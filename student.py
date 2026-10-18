from datetime import date
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
import config
from db import get_db
from decorators import role_acquired

student = Blueprint("student", __name__)

def get_quota(uid):
    today = date.today().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT sent_today, last_reset FROM send_limits WHERE user_id=?", (uid,)).fetchone()
        if not row or row["last_reset"] != today:
            return config.DAILY_LIMIT, 0
        used = row["sent_today"]
        remaining = max(0, config.DAILY_LIMIT - used)
        return remaining, used

@student.route("/send")
@role_acquired("student")
def send_page():
    uid = session["user_id"]
    remaining, used = get_quota(uid)
    
    # Retrieve club leader details
    with get_db() as conn:
        leader_info = conn.execute(
            """SELECT l.name AS leader_name, l.leader_code, l.club_name
               FROM users u
               JOIN users l ON u.leader_id = l.id
               WHERE u.id=?""",
            (uid,)
        ).fetchone()

    return render_template(
        "send.html",
        remaining=remaining,
        daily_limit=config.DAILY_LIMIT,
        leader_info=leader_info
    )

@student.route("/api/messages", methods=["POST"])
@role_acquired("student")
def send_message():
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text or len(text) > 1000:
        return jsonify(error="Message must be between 1 and 1000 characters."), 400

    today = date.today().isoformat()
    uid = session["user_id"]

    with get_db() as conn:
        user = conn.execute("SELECT leader_id FROM users WHERE id=?", (uid,)).fetchone()
        if not user or not user["leader_id"]:
            return jsonify(error="Club not found or you are not affiliated with a leader."), 400

        leader_id = user["leader_id"]

        conn.execute("INSERT OR IGNORE INTO send_limits (user_id, sent_today, last_reset) VALUES (?, 0, ?)", (uid, today))
        conn.execute(
            "UPDATE send_limits SET sent_today = 0, last_reset = ? WHERE user_id = ? AND last_reset != ?",
            (today, uid, today)
        )
        used = conn.execute(
            "UPDATE send_limits SET sent_today = sent_today + 1 WHERE user_id = ? AND sent_today < ?",
            (uid, config.DAILY_LIMIT)
        ).rowcount

        if not used:
            return jsonify(error=f"Daily limit reached. You can send up to {config.DAILY_LIMIT} messages per day."), 429

        # Crucial: NO student user_id or name is stored. Only leader_id is saved.
        conn.execute("INSERT INTO messages (leader_id, text) VALUES (?, ?)", (leader_id, text))
        
        rem_row = conn.execute("SELECT sent_today FROM send_limits WHERE user_id=?", (uid,)).fetchone()
        sent_today = rem_row["sent_today"] if rem_row else 1
        remaining = max(0, config.DAILY_LIMIT - sent_today)

        return jsonify(ok=True, remaining=remaining, message="Message sent anonymously!"), 201

@student.route("/create-club", methods=["GET", "POST"])
@role_acquired("student")
def create_club():
    uid = session["user_id"]
    if request.method == "POST":
        club_name = request.form.get("club_name", "").strip()
        if not club_name or len(club_name) > 80:
            flash("Please enter a valid club name (1 to 80 characters).")
            return render_template("create_club.html")

        from auth import generate_leader_code
        new_code = generate_leader_code()

        with get_db() as conn:
            while conn.execute("SELECT id FROM users WHERE leader_code=?", (new_code,)).fetchone():
                new_code = generate_leader_code()

            conn.execute(
                """UPDATE users 
                   SET role='leader', leader_id=NULL, leader_code=?, club_name=? 
                   WHERE id=?""",
                (new_code, club_name, uid)
            )

        session["role"] = "leader"
        session["leader_code"] = new_code
        session["club_name"] = club_name

        flash(f"Congratulations! You created '{club_name}'! Your new Club Code is: {new_code}. Share it with your admins and students.")
        return redirect(url_for("leader.dashboard"))

    return render_template("create_club.html")
