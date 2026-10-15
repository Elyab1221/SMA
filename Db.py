import sqlite3
import configparser

def get_db():
    conn=sqlite3.connect(config.DATABASE)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    with get_db() as conn,open("schema.sql") as f:
        conn.executescript(f.read())