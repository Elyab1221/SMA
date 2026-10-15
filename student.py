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
    with get_db() as conn:
        row=conn.execute("SELECT * FROM send_limits WHERE sender=? AND date=?",
                          (session["user_id"], today)).fetchone()
        if not row:
            conn.execute("INSERT INTO send_limits VALUES(?,0,?)",
                          (session["user_id"], today, 1))
            sent=0
        else: 
            sent=row["sent_today"] if row["last_Reset"]==today else 0
        if sent>=config.Daily_LIMIT:
            return jsonify(error="Daily limit reached try again tommorow"), 429
        conn.execute("UPDATE send_limits SET sent_today=? ,last_reset=? WHERE user_id=?", 
                     (sent+1, today, session["user_id"]))
        conn.execute("INSERT INTO messages(text) VALUES(?)", (text,)) #no user id stored for simplicity
    return jsonify(ok=True),201