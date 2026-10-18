import os
import sqlite3
import config

def get_db():
    conn=sqlite3.connect(config.DATABASE)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)))
    with get_db() as conn,open("schema.sql") as f:
        conn.executescript(f.read())