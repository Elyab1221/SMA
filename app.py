import secrets
from flask import Flask, session, request, abort, render_template, redirect, url_for
import config
import db
from auth import auth
from student import student
from admin import admin
from leader import leader

import os
import sys

# Support PyInstaller frozen bundles
if getattr(sys, "frozen", False):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    app = Flask(
        __name__,
        template_folder=os.path.join(bundle_dir, "templates"),
        static_folder=os.path.join(bundle_dir, "static")
    )
else:
    app = Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=config.HTTPS,
    PERMANENT_SESSION_LIFETIME=config.SESSION_LIFETIME,
)

# Register Blueprints
for bp in (auth, student, admin, leader):
    app.register_blueprint(bp)

@app.before_request
def csrf_check():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
        
    if request.method == "POST":
        sent = request.form.get("csrf") or request.headers.get("X-CSRF")
        if not sent or sent != session.get("csrf"):
            abort(400, description="Invalid or missing CSRF token. Please refresh the page and try again.")

@app.after_request
def security_headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "script-src 'self';"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp

@app.context_processor
def inject():
    role = session.get("role", "")
    unread_count = 0
    
    if role in ("admin", "leader") and "user_id" in session:
        try:
            with db.get_db() as conn:
                if role == "leader":
                    leader_id = session.get("user_id")
                else:
                    u = conn.execute("SELECT leader_id FROM users WHERE id=?", (session.get("user_id"),)).fetchone()
                    leader_id = u["leader_id"] if u else None
                    
                if leader_id:
                    row = conn.execute(
                        "SELECT COUNT(*) AS c FROM messages WHERE leader_id=? AND is_read=0",
                        (leader_id,)
                    ).fetchone()
                    unread_count = row["c"] if row else 0
        except Exception:
            unread_count = 0

    return {
        "csrf": session.get("csrf", ""),
        "role": role,
        "user_name": session.get("user_name", ""),
        "user_email": session.get("user_email", ""),
        "club_name": session.get("club_name", ""),
        "unread_count": unread_count
    }

# Friendly error handlers
@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message=str(e)), 400

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="Access forbidden. You do not have permission for this resource."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="The requested page could not be found."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="An internal server error occurred. Please try again later."), 500

if __name__ == "__main__":
    import os
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    db.init_db()
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 60)
    print("  [OK] Cyber Talent Club SMA - Server is ACTIVE!")
    print(f"  --> Open in browser: http://127.0.0.1:{port}")
    print(f"  --> Or try:          http://localhost:{port}")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=config.DEBUG)
