import secrets 
from flask import Flask, session, request, abort
import config

app=Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)
@app.before_request
def csrf_check():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        sent=request.form.get("csrf") or request.headers.get("X-CSRF")
        if sent!=session["csrf"]:
            abort(400)

@app.context_processor
def inject():
    return {"csrf":session.get("csrf",""), "role":session.get("role","")}

if __name__=="__main__":
    app.run(debug=True)

