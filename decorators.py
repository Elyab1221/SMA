from functools import wraps
from flask import session, redirect, url_for,abort
from db import get_db

def role_acquired(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))
            #checking the DB for sespenede user and typ shi liek taht 
            u=get_db().execute("SELECT role,stauts FROM users where ID=?",(session["user_id"],)).fetchone()
            if not u or u["status"]!="active":
                session.clear()
                flash("your session ended.please log in again.")
                return redirect(url_for("auth.login"))
            if u["role"] not in roles:
                abort(403)
            # if session.get("role") not in roles:
            #     abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
    #     return wrapper
    # return deco