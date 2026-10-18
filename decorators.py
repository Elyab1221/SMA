from functools import wraps
from flask import session, redirect, url_for, abort, flash
from db import get_db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("auth.login"))
        
        # Verify account status in database
        u = get_db().execute("SELECT role, status FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if not u or u["status"] != "active":
            session.clear()
            flash("Your session has expired or your account is no longer active.")
            return redirect(url_for("auth.login"))
            
        return f(*args, **kwargs)
    return decorated_function

def role_acquired(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.")
                return redirect(url_for("auth.login"))
            
            # Verify account status in database
            u = get_db().execute("SELECT role, status FROM users WHERE id=?", (session["user_id"],)).fetchone()
            if not u or u["status"] != "active":
                session.clear()
                flash("Your session has expired or your account is no longer active.")
                return redirect(url_for("auth.login"))
            
            if u["role"] not in roles:
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

