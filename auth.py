import sqllite3
from flask import Blueprint, lueprint,render_template, request, redirect, url_for, session,flash
from werkzeug.security import check_password_hash, generate_password_hash,check_password_hash
from db import get_db

auth=Blueprint("auth", __name__)

def home_for(role):
    return url_for("student.send_page") if role=="student" else url_for("admin.inbox") if role=="admin" else url_for("leader.pending_admins")

@auth.route(/)
def index():
    if "user_id" in session:
        return redirect(home_for(session.get("role")))
    return redirect(url_for("auth.login"))

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        role=request.form.get("role","")
        if role not in ("student","admin"):
            role="student"
        if not name or "@" not in email or len(password)<8:
            flash("Enter your name, email and password of 8+ characters")
            return render_template("register.html")
            status="acitve" if role=="student" else "pending"
            try:
                with get_db() as conn:
                    conn.execute("INSERT INTO users(name,email,password_hash,role,status) VALUES(?,?,?,?,?)",
                                 (name,email,generate_password_hash(password),role,status))
            except sqllite3.IntegrityError:
                flash("Email already registered")
                return render_template("register.html")
            flash("Registration successful, please login")
            return redirect(url_for("auth.login"))
    return render_template("register.html")  

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        # role=request.form.get("role","")
        user=get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password")
        elif user["status"]!="active":
            flash("Your account is not active yet. Please wait for approval." 
                  if user["status"]=="pending"
                else "Your account has been rejected.")
        else:
            session.clear()
            session.update(user_id=user["id"], role=user["role"])
            return redirect(home_for(user["role"]))
        return render_template("login.html")

@auth.route("/logout",methods=["POST"])   
def logout():
    session.clear()
    return redirect(url_for("auth.login"))         