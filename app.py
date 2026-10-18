import secrets 
from flask import Flask, session, request, abort
import config
import db 
from auth import auth 
from student import student
from admin import admin 
from leader import leader 

app=Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE= config.HTTPS,
    PERMANENT_SESSION_LIFETIME = config.SESSION_LIFETIME,
)

for bp in (auth,student,admin,leader):
    app.register_blueprint(bp)

@app.before_request
def csrf_check():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        sent=request.form.get("csrf") or request.headers.get("X-CSRF")
        if sent!=session["csrf"]:
            abort(400)

@app.after_request
def security_headers(resp):
    resp.headers["Content-Security-Policy"]="default-src 'self' "
    resp.headers["X-Content-Type-Options"]="nosniff"
    resp.headers["X-Frame-Options"]="DENY"
    resp.headers["Referrer-Policy"]="same-origin"
    return resp

@app.context_processor
def inject():
    return {"csrf":session.get("csrf",""), "role":session.get("role","")}

if __name__=="__main__":
    db.init_db()
    app.run(debug=config.DEBUG)

