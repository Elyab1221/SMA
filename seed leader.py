# run once to create the leader acoount
from getpass import getpass
from werkzeug.security import generate_password_hash
import db

db.init_db()
name=input("leader name: ").strip()
email= input("leader email: ").strip().lower()
password= "Elyab@1221"
# assert len(password)>=8, "password too short"
with db.get_db() as conn:
    conn.execute(
        "INSERT INTO users(name,email,password_hash,role,status) VALUES (?,?,?, 'leader','active')",
        (name,email,generate_password_hash(password))
    )
print("leader created. now run app.py")