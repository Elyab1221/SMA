import os
import sys
import sqlite3
import secrets
import string
import config

def generate_code():
    chars = string.ascii_uppercase + string.digits
    return "SMA-" + "".join(secrets.choice(chars) for _ in range(6))

def get_db():
    db_path = config.DATABASE
    if not os.path.isabs(db_path):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    if getattr(sys, "frozen", False):
        schema_path = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "schema.sql")
    else:
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with get_db() as conn:
        # Pre-migration for existing legacy databases before index creation
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        if "users" in tables:
            u_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "leader_id" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN leader_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
            if "leader_code" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN leader_code TEXT")
            if "club_name" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN club_name TEXT")
            if "created_at" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
                conn.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")

        if "messages" in tables:
            m_cols = [r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
            if "leader_id" not in m_cols:
                conn.execute("ALTER TABLE messages ADD COLUMN leader_id INTEGER")
            if "created_at" not in m_cols:
                conn.execute("ALTER TABLE messages ADD COLUMN created_at TEXT")
                conn.execute("UPDATE messages SET created_at = datetime('now') WHERE created_at IS NULL")

        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            
        # Post-migration check: Ensure any additional missing columns or legacy data setup
        if "users" in tables:
            u_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "leader_id" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN leader_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
            if "leader_code" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN leader_code TEXT")
            if "club_name" not in u_cols:
                conn.execute("ALTER TABLE users ADD COLUMN club_name TEXT")
                
            leaders = conn.execute("SELECT id, leader_code, club_name, name FROM users WHERE role='leader'").fetchall()
            for l in leaders:
                if not l["leader_code"]:
                    code = generate_code()
                    while conn.execute("SELECT id FROM users WHERE leader_code=?", (code,)).fetchone():
                        code = generate_code()
                    c_name = l["club_name"] or f"{l['name']}'s Club"
                    conn.execute("UPDATE users SET leader_code=?, club_name=? WHERE id=?", (code, c_name, l["id"]))
