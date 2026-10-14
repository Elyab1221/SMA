import secrets 
from flask import Flask, sessions, request,abort
import config
import db

app=Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)
@app.before_request
def csrf_check():
    if "csrf" not in sessions:
        sessions["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        sent=request.form.get("csrf") or request.headers.get("X-CSRF")
    if sent!=sessions["csrf"]:
        abort(400)

@app.context_processor
def inject():
    return {"csrf":sessions.get("csrf",""), "role":sessions.get("role","")}

if __name__=="__main__":
    app.init_db()
    app.run(debug=True)