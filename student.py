from datetime import date
from flask import Blueprint, render_template, request,jsonify,session
import config
from db import get_db
from decorators import role_acquired

student=Blueprint("student", __name__)

@student.route("/send")
@role_acquired("student")
def send():
    return render_template("send.html")

@student.route("/api/messages", methods=["POST"])
@role_acquired("student")
def send_message():
    text=((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text or len(text)>1000:
        return jsonify(error="write between 1-1000 characters"), 400
    today=date.today().isoformat()
    uid=session["user_id"]
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO send_limits VALUES(?,0,?)",(uid,today))
        conn.execute("UPDATE send_limits SET sent_today=0, last_reseet=? where user id=? AND last_reset!=?",
                     (today,uid,today))
        used=conn.execute("UPDATE send_limits SET sent_today= sent_today+1 WHERE user_id=? AND sent_today<?",
                          (uid,config.DAILY_LIMIT)).rowcount
        if not used:
            return jsonify(error="Daily limit reached try again tommorow"),429
        conn.execute("INSERT INTO messages(text) VALUES(?)",(text,)) # no user id stored that is hwat makes it anonymous
        return jsonify(ok=True),201