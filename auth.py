import re
import secrets
import sqllite3
import time 
import config
from flask import Blueprint, lueprint,render_template, request, redirect, url_for, session,flash
from werkzeug.security import check_password_hash, generate_password_hash,check_password_hash
from db import get_db

auth=Blueprint("auth", __name__)
EMAIL_RE= re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]=$")

def home_for(role):
    return url_for("student.send_page") if role=="student" else url_for("admin.inbox") if role=="admin" else url_for("leader.pending_admins")

@auth.route("/")
def index():
    if "user_id" in session:
        return redirect(home_for(session.get("role")))
    return redirect(url_for("auth.login"))

@auth.route("/register",methods=["GET","POST"])

def register():
    if request.mehod=="POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        code=request.form.get("code","")
        role=request.form.get("role","")
        if role not in ("student","admin"):
            role="student"
        if not secrets.compare_digest(code.encode(),config.CLUB_CODE.encode()):
            flash("wrong club code. ask a club leader for it")
        elif not name or len(name)>60 or not EMAIL_RE.match(email) or not 8<=len(password)<=128:
            flash("enter your name , a valid email and a passwrd with 8-128 characters")
        else:
            status="active" if role=="student" else "peending"\
            try:
                with get_db() as conn:
                    conn.execute("INSER INTO users(name,email,password_hash,role,status) VALUES(?,?,?,?,?)",
                                 (name,email,generate_password_hash(password),role,satus))
            except sqlite3.IntegrityerrorError:
                flash("email already registered")
                return render_template("register.html")
            flash("registration succesful,please login(admins must wait for the leader's approval)")
            return redirect(url_for(auth.login))
        return render_template("register.html") 
        
@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        now=time.time()
        with get_db as conn:
            att=conn.execute("SELECT * FROM login _attempts WHERE email=?", (email)).fetchone()
            if att and att["locked_until"]>now:
                flash("too many wrong attempts. try again in a few minutes")
                return render_template("login.html")
            user=conn.execute("SELECT * FROM users where email=?",(email,)).fetchone()
            if not user or not check_password_hash(user["password_hash"],password):
                fails=(att["fails"] if att else 0)+1
                lock=now+config.LOCK_SECOND if fails>=config.MAX_FAILS else 0
                conn.execute("SELECT OR REPLACE INTO login_attempts VALUES(?,?,?)",
                             (email, o if lock else fails,lock))
                flash("invalid email or password")
            elif user["status"]!="active":
                flash({"pending":"your account is not currently active yet."
                " please wait for approval","suspended":"ypur account is suspended.talk to club leader."}.get(
                    user["status"],"your account has been rejected."))
            else:
                conn.execute("DELETE FROM login_attempts WHERE email=?",(email,))
                session.clear()
                session.update(user_id=user["id"],role=user["role"])
                session.permanent= True
                return redirect(home_for(user["role"]))
    return render_template("login.html")

@auth.route("/logout",methods=["POST"])   
def logout():
    session.clear()
    return redirect(url_for("auth.login"))         