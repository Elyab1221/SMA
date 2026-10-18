# Script to manually seed or create a club leader account
import sys
import secrets
import string
from getpass import getpass
from werkzeug.security import generate_password_hash
import db

def generate_leader_code():
    chars = string.ascii_uppercase + string.digits
    return "SMA-" + "".join(secrets.choice(chars) for _ in range(6))

def main():
    print("=== Create Club Leader Account ===")
    db.init_db()
    
    name = input("Enter Leader Name: ").strip()
    if not name:
        print("Error: Name cannot be empty.")
        sys.exit(1)
        
    club_name = input("Enter Club Name (e.g. Cyber Talent Club): ").strip() or f"{name}'s Club"
        
    email = input("Enter Leader Email: ").strip().lower()
    if not email or "@" not in email:
        print("Error: Invalid email address.")
        sys.exit(1)
        
    password = getpass("Enter Leader Password (min 8 chars): ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)
        
    confirm = getpass("Confirm Password: ")
    if password != confirm:
        print("Error: Passwords do not match.")
        sys.exit(1)

    leader_code = generate_leader_code()

    with db.get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            print("Error: This email address is already registered.")
            sys.exit(1)
            
        conn.execute(
            """INSERT INTO users (name, email, password_hash, role, status, leader_id, leader_code, club_name)
               VALUES (?, ?, ?, 'leader', 'active', NULL, ?, ?)""",
            (name, email, generate_password_hash(password), leader_code, club_name)
        )

    print("\n[SUCCESS] Club Leader account created successfully!")
    print(f"Name:        {name}")
    print(f"Club:        {club_name}")
    print(f"Email:       {email}")
    print(f"Club Code:   {leader_code}  (Share this code with your admins and students)")
    print("\nYou can now run 'python app.py' and log in.\n")

if __name__ == "__main__":
    main()
