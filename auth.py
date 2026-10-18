import re
import secrets
import string
import sqlite3
import time
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import config
from db import get_db
from decorators import login_required

auth = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def generate_leader_code():
    chars = string.ascii_uppercase + string.digits
    return "SMA-" + "".join(secrets.choice(chars) for _ in range(6))

def home_for(role):
    if role == "student":
        return url_for("student.send_page")
    elif role == "admin":
        return url_for("admin.inbox")
    elif role == "leader":
        return url_for("leader.dashboard")
    return url_for("auth.landing")

@auth.route("/")
def landing():
    if "user_id" in session:
        return redirect(home_for(session.get("role")))
    return render_template("landing.html")

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student").strip().lower()
        code = request.form.get("code", "").strip().upper()

        if role not in ("student", "admin", "leader"):
            role = "student"

        # Basic input validation
        if not name or len(name) > 60:
            flash("Please enter a valid name (up to 60 characters).")
            return render_template("register.html")
            
        if not EMAIL_RE.match(email):
            flash("Please enter a valid email address.")
            return render_template("register.html")
            
        if len(password) < 8 or len(password) > 128:
            flash("Password must be between 8 and 128 characters.")
            return render_template("register.html")

        with get_db() as conn:
            existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if existing:
                flash("This email address is already registered.")
                return render_template("register.html")

            if role == "leader":
                # Leader creates a new club and receives a unique Leader Code
                club_name = request.form.get("club_name", "").strip() or f"{name}'s Club"
                leader_code = generate_leader_code()
                while conn.execute("SELECT id FROM users WHERE leader_code=?", (leader_code,)).fetchone():
                    leader_code = generate_leader_code()
                status = "active"
                
                conn.execute(
                    """INSERT INTO users (name, email, password_hash, role, status, leader_id, leader_code, club_name) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, email, generate_password_hash(password), role, status, None, leader_code, club_name)
                )
                flash(f"Club Leader account created for '{club_name}'! Your Club Code is: {leader_code}. Share this code with your admins and students.")
                return redirect(url_for("auth.login"))

            else:
                # Students and Admins must provide an active Leader's code
                if not code:
                    flash("Club / Leader Code is required to sign up as a member or admin.")
                    return render_template("register.html")

                leader = conn.execute(
                    "SELECT id, name, club_name FROM users WHERE role='leader' AND leader_code=? AND status='active'",
                    (code,)
                ).fetchone()

                if not leader:
                    flash("Invalid Leader Code. Please request the exact Club Code from your club leader.")
                    return render_template("register.html")

                leader_id = leader["id"]

                if role == "admin":
                    status = "pending"
                    conn.execute(
                        """INSERT INTO users (name, email, password_hash, role, status, leader_id, leader_code, club_name) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (name, email, generate_password_hash(password), role, status, leader_id, None, None)
                    )
                    flash("Admin registration submitted! You must wait for your Club Leader's approval before logging in.")
                    return redirect(url_for("auth.login"))
                else:
                    status = "active"
                    conn.execute(
                        """INSERT INTO users (name, email, password_hash, role, status, leader_id, leader_code, club_name) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (name, email, generate_password_hash(password), role, status, leader_id, None, None)
                    )
                    flash("Account created successfully! You can now log in.")
                    return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        now = time.time()

        with get_db() as conn:
            att = conn.execute("SELECT * FROM login_attempts WHERE email=?", (email,)).fetchone()
            if att and att["locked_until"] > now:
                remaining = int((att["locked_until"] - now) // 60) + 1
                flash(f"Too many failed login attempts. Account temporarily locked. Try again in {remaining} minute(s).")
                return render_template("login.html")

            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                fails = (att["fails"] if att else 0) + 1
                lock = (now + config.LOCK_SECONDS) if fails >= config.MAX_FAILS else 0
                conn.execute(
                    "INSERT OR REPLACE INTO login_attempts (email, fails, locked_until) VALUES (?, ?, ?)",
                    (email, 0 if lock else fails, lock)
                )
                if lock:
                    flash(f"Too many incorrect attempts. Account locked for {config.LOCK_SECONDS // 60} minutes.")
                else:
                    flash(f"Invalid email or password. Attempt {fails} of {config.MAX_FAILS}.")
                return render_template("login.html")

            if user["status"] == "pending":
                flash("Your admin account is pending approval by your Club Leader. Please check back later.")
                return render_template("login.html")
            elif user["status"] == "suspended":
                flash("Your account has been suspended. Please speak with your Club Leader.")
                return render_template("login.html")
            elif user["status"] == "rejected":
                flash("Your account request was declined by the Club Leader.")
                return render_template("login.html")

            conn.execute("DELETE FROM login_attempts WHERE email=?", (email,))
            session.clear()
            session.update(
                user_id=user["id"],
                user_name=user["name"],
                user_email=user["email"],
                role=user["role"],
                leader_id=user["leader_id"],
                leader_code=user["leader_code"],
                club_name=user["club_name"] if "club_name" in user.keys() else None
            )
            session.permanent = True
            return redirect(home_for(user["role"]))

    return render_template("login.html")

@auth.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password or not confirm_password:
            flash("All password fields are required.")
            return render_template("change_password.html")

        if len(new_password) < 8 or len(new_password) > 128:
            flash("New password must be between 8 and 128 characters.")
            return render_template("change_password.html")

        if new_password != confirm_password:
            flash("New password and confirmation do not match.")
            return render_template("change_password.html")

        with get_db() as conn:
            user = conn.execute("SELECT password_hash FROM users WHERE id=?", (session["user_id"],)).fetchone()
            if not user or not check_password_hash(user["password_hash"], current_password):
                flash("Your current password was incorrect.")
                return render_template("change_password.html")

            if check_password_hash(user["password_hash"], new_password):
                flash("New password must be different from your current password.")
                return render_template("change_password.html")

            conn.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(new_password), session["user_id"])
            )
            flash("Your password has been updated successfully!")
            return redirect(home_for(session.get("role")))

    return render_template("change_password.html")

@auth.route("/profile")
@login_required
def profile():
    with get_db() as conn:
        user = conn.execute(
            """SELECT u.*, l.name AS leader_name, l.leader_code AS club_code, l.club_name AS leader_club_name
               FROM users u
               LEFT JOIN users l ON u.leader_id = l.id
               WHERE u.id=?""",
            (session["user_id"],)
        ).fetchone()
        return render_template("profile.html", user=user)

@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("auth.landing"))
