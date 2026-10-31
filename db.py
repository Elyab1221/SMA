import os
import sys
import string
import secrets
import urllib.parse
from flask import g, has_app_context
import config

# PostgreSQL driver
try:
    import psycopg2
    from psycopg2.extras import DictCursor as PGDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

# MySQL driver (pre-installed on PythonAnywhere)
try:
    import pymysql
    import pymysql.cursors
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

import sqlite3

def generate_code():
    chars = string.ascii_uppercase + string.digits
    return "SMA-" + "".join(secrets.choice(chars) for _ in range(6))

def get_db_type():
    db_url = (config.DATABASE_URL or "").strip().lower()
    if db_url.startswith(("postgres://", "postgresql://")) or (
        os.environ.get("PGDATABASE") and (os.environ.get("PGUSER") or os.environ.get("PGHOST"))
    ):
        return "postgres"
    if db_url.startswith(("mysql://", "mysql+pymysql://")) or os.environ.get("MYSQL_DATABASE"):
        return "mysql"
    return "sqlite"

def is_postgres_configured():
    return HAS_POSTGRES and get_db_type() == "postgres"

def is_mysql_configured():
    return HAS_MYSQL and get_db_type() == "mysql"

def parse_database_url(url, default_port=5432):
    """Parses a database URL and handles percent-encoded credentials safely."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    elif url.startswith("mysql+pymysql://"):
        url = "mysql://" + url[len("mysql+pymysql://"):]

    parsed = urllib.parse.urlparse(url)
    username = urllib.parse.unquote(parsed.username) if parsed.username else None
    password = urllib.parse.unquote(parsed.password) if parsed.password else None
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port or default_port
    database = parsed.path.lstrip("/") if parsed.path else ""

    return {
        "dbname": database,
        "user": username,
        "password": password,
        "host": hostname,
        "port": port
    }

class RowWrapper:
    """Provides sqlite3.Row-like access (by column name, by index, keys(), etc.)"""
    def __init__(self, row):
        self._row = row

    def __getitem__(self, item):
        return self._row[item]

    def keys(self):
        return self._row.keys()

    def get(self, key, default=None):
        try:
            return self._row[key]
        except (KeyError, IndexError):
            return default

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)

    def __repr__(self):
        return repr(dict(self._row))

class CursorWrapper:
    def __init__(self, cursor, db_type="postgres"):
        self._cursor = cursor
        self._db_type = db_type

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def fetchone(self):
        row = self._cursor.fetchone()
        return RowWrapper(row) if row is not None else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [RowWrapper(r) for r in rows]

    def execute(self, sql, params=None):
        sql = self._adapt_sql(sql)
        if params is not None:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)
        return self

    def _adapt_sql(self, sql):
        if self._db_type == "postgres":
            if "INSERT OR REPLACE INTO login_attempts" in sql:
                sql = sql.replace(
                    "INSERT OR REPLACE INTO login_attempts (email, fails, locked_until) VALUES (?, ?, ?)",
                    "INSERT INTO login_attempts (email, fails, locked_until) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET fails = EXCLUDED.fails, locked_until = EXCLUDED.locked_until"
                )
            if "INSERT OR IGNORE INTO send_limits" in sql:
                sql = sql.replace(
                    "INSERT OR IGNORE INTO send_limits (user_id, sent_today, last_reset) VALUES (?, 0, ?)",
                    "INSERT INTO send_limits (user_id, sent_today, last_reset) VALUES (%s, 0, %s) ON CONFLICT (user_id) DO NOTHING"
                )
        elif self._db_type == "mysql":
            if "INSERT OR REPLACE INTO login_attempts" in sql:
                sql = sql.replace(
                    "INSERT OR REPLACE INTO login_attempts (email, fails, locked_until) VALUES (?, ?, ?)",
                    "INSERT INTO login_attempts (email, fails, locked_until) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE fails = VALUES(fails), locked_until = VALUES(locked_until)"
                )
            if "INSERT OR IGNORE INTO send_limits" in sql:
                sql = sql.replace(
                    "INSERT OR IGNORE INTO send_limits (user_id, sent_today, last_reset) VALUES (?, 0, ?)",
                    "INSERT IGNORE INTO send_limits (user_id, sent_today, last_reset) VALUES (%s, 0, %s)"
                )

        # Translate ? parameter markers to %s for Postgres and MySQL
        if self._db_type in ("postgres", "mysql"):
            sql = sql.replace("?", "%s")
            sql = sql.replace("datetime('now')", "CURRENT_TIMESTAMP")
        return sql

class ConnectionWrapper:
    def __init__(self, raw_conn, db_type, is_scoped=False):
        self._conn = raw_conn
        self._db_type = db_type
        self._is_scoped = is_scoped

    def execute(self, sql, params=None):
        if self._db_type == "postgres":
            cur = self._conn.cursor(cursor_factory=PGDictCursor)
            wrapper = CursorWrapper(cur, db_type="postgres")
            return wrapper.execute(sql, params)
        elif self._db_type == "mysql":
            cur = self._conn.cursor(pymysql.cursors.DictCursor)
            wrapper = CursorWrapper(cur, db_type="mysql")
            return wrapper.execute(sql, params)
        else:
            # SQLite
            if params is not None:
                return self._conn.execute(sql, params)
            return self._conn.execute(sql)

    def executescript(self, sql):
        if self._db_type == "sqlite":
            return self._conn.executescript(sql)
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                self.execute(stmt)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._db_type == "sqlite":
            self._conn.close()
        elif hasattr(self._conn, "closed") and not self._conn.closed:
            self._conn.close()
        elif hasattr(self._conn, "open") and self._conn.open:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        if not self._is_scoped:
            self.close()
        return False

def _create_raw_connection(is_scoped=False):
    db_type = get_db_type()
    
    if db_type == "postgres" and HAS_POSTGRES:
        if config.DATABASE_URL:
            conn_params = parse_database_url(config.DATABASE_URL, default_port=5432)
            raw = psycopg2.connect(**conn_params)
        else:
            raw = psycopg2.connect(
                dbname=os.environ.get("PGDATABASE", "club_sma"),
                user=os.environ.get("PGUSER", "postgres"),
                password=os.environ.get("PGPASSWORD", ""),
                host=os.environ.get("PGHOST", "127.0.0.1"),
                port=int(os.environ.get("PGPORT", 5432))
            )
        return ConnectionWrapper(raw, "postgres", is_scoped=is_scoped)

    elif db_type == "mysql" and HAS_MYSQL:
        if config.DATABASE_URL:
            params = parse_database_url(config.DATABASE_URL, default_port=3306)
            raw = pymysql.connect(
                host=params["host"],
                user=params["user"],
                password=params["password"],
                database=params["dbname"],
                port=params["port"],
                autocommit=False
            )
        else:
            raw = pymysql.connect(
                host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
                user=os.environ.get("MYSQL_USER", "root"),
                password=os.environ.get("MYSQL_PASSWORD", ""),
                database=os.environ.get("MYSQL_DATABASE", "club_sma"),
                port=int(os.environ.get("MYSQL_PORT", 3306)),
                autocommit=False
            )
        return ConnectionWrapper(raw, "mysql", is_scoped=is_scoped)

    else:
        # SQLite fallback (Works immediately with persistent storage on PythonAnywhere)
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
        return ConnectionWrapper(conn, "sqlite", is_scoped=is_scoped)

def get_db():
    """Returns a connection. In a Flask request context, reuses g._database and closes on teardown."""
    if has_app_context():
        if "_database" not in g:
            g._database = _create_raw_connection(is_scoped=True)
        return g._database
    return _create_raw_connection(is_scoped=False)

def close_db(e=None):
    """Closes request-scoped database connection."""
    if has_app_context():
        db = g.pop("_database", None)
        if db is not None:
            db.close()

def init_db():
    """Initializes schema and runs automatic data migration if needed."""
    db_type = get_db_type()
    if db_type == "postgres":
        _init_postgres()
    elif db_type == "mysql":
        _init_mysql()
    else:
        _init_sqlite()

def _init_postgres():
    pg_schema = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role VARCHAR(50) NOT NULL CHECK (role IN ('student', 'admin', 'leader')),
        status VARCHAR(50) NOT NULL CHECK (status IN ('active', 'pending', 'rejected', 'suspended')),
        leader_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        leader_code VARCHAR(50) UNIQUE,
        club_name VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        leader_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_users_leader ON users(leader_id);
    CREATE INDEX IF NOT EXISTS idx_users_code ON users(leader_code);
    CREATE INDEX IF NOT EXISTS idx_messages_leader ON messages(leader_id);

    CREATE TABLE IF NOT EXISTS send_limits (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        sent_today INTEGER NOT NULL DEFAULT 0,
        last_reset VARCHAR(50) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS login_attempts (
        email VARCHAR(255) PRIMARY KEY,
        fails INTEGER NOT NULL DEFAULT 0,
        locked_until DOUBLE PRECISION NOT NULL DEFAULT 0
    );
    """
    with get_db() as conn:
        with conn._conn.cursor() as cur:
            cur.execute(pg_schema)
        conn.commit()

        # Migrate legacy SQLite if needed
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_file = os.path.join(base_dir, "sma.db")
        if os.path.exists(sqlite_file):
            _migrate_sqlite_to_rdbms(conn, sqlite_file, db_type="postgres")

def _init_mysql():
    mysql_schema = [
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            leader_id INT NULL,
            leader_code VARCHAR(50) NULL UNIQUE,
            club_name VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (leader_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

        """CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            leader_id INT NOT NULL,
            text TEXT NOT NULL,
            is_read INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (leader_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

        """CREATE TABLE IF NOT EXISTS send_limits (
            user_id INT PRIMARY KEY,
            sent_today INT NOT NULL DEFAULT 0,
            last_reset VARCHAR(50) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

        """CREATE TABLE IF NOT EXISTS login_attempts (
            email VARCHAR(255) PRIMARY KEY,
            fails INT NOT NULL DEFAULT 0,
            locked_until DOUBLE NOT NULL DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""
    ]
    with get_db() as conn:
        for stmt in mysql_schema:
            conn.execute(stmt)
        conn.commit()

        base_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_file = os.path.join(base_dir, "sma.db")
        if os.path.exists(sqlite_file):
            _migrate_sqlite_to_rdbms(conn, sqlite_file, db_type="mysql")

def _migrate_sqlite_to_rdbms(target_conn, sqlite_file, db_type="postgres"):
    try:
        cur = target_conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        if cur and cur["c"] > 0:
            return

        s_conn = sqlite3.connect(sqlite_file)
        s_conn.row_factory = sqlite3.Row
        
        t_check = s_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if not t_check:
            s_conn.close()
            return

        users = s_conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        for u in users:
            if db_type == "postgres":
                target_conn.execute(
                    """INSERT INTO users (id, name, email, password_hash, role, status, leader_id, leader_code, club_name)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT (id) DO NOTHING""",
                    (u["id"], u["name"], u["email"], u["password_hash"], u["role"], u["status"], u["leader_id"], u["leader_code"], u["club_name"])
                )
            else:
                target_conn.execute(
                    """INSERT IGNORE INTO users (id, name, email, password_hash, role, status, leader_id, leader_code, club_name)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (u["id"], u["name"], u["email"], u["password_hash"], u["role"], u["status"], u["leader_id"], u["leader_code"], u["club_name"])
                )

        if db_type == "postgres":
            target_conn.execute("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))")

        m_check = s_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'").fetchone()
        if m_check:
            msgs = s_conn.execute("SELECT * FROM messages ORDER BY id").fetchall()
            for m in msgs:
                lid = m["leader_id"] if m["leader_id"] is not None else 1
                if db_type == "postgres":
                    target_conn.execute(
                        """INSERT INTO messages (id, leader_id, text, is_read)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT (id) DO NOTHING""",
                        (m["id"], lid, m["text"], m["is_read"])
                    )
                else:
                    target_conn.execute(
                        """INSERT IGNORE INTO messages (id, leader_id, text, is_read)
                           VALUES (?, ?, ?, ?)""",
                        (m["id"], lid, m["text"], m["is_read"])
                    )
            if db_type == "postgres":
                target_conn.execute("SELECT setval('messages_id_seq', COALESCE((SELECT MAX(id) FROM messages), 1))")

        sl_check = s_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='send_limits'").fetchone()
        if sl_check:
            limits = s_conn.execute("SELECT * FROM send_limits").fetchall()
            for sl in limits:
                if db_type == "postgres":
                    target_conn.execute(
                        """INSERT INTO send_limits (user_id, sent_today, last_reset)
                           VALUES (?, ?, ?)
                           ON CONFLICT (user_id) DO NOTHING""",
                        (sl["user_id"], sl["sent_today"], sl["last_reset"])
                    )
                else:
                    target_conn.execute(
                        """INSERT IGNORE INTO send_limits (user_id, sent_today, last_reset)
                           VALUES (?, ?, ?)""",
                        (sl["user_id"], sl["sent_today"], sl["last_reset"])
                    )

        target_conn.commit()
        s_conn.close()
        print(f"[OK] Migrated data from SQLite to {db_type.upper()} successfully!")
    except Exception as e:
        print(f"[NOTE] Migration check completed ({e}).")

def _init_sqlite():
    if getattr(sys, "frozen", False):
        schema_path = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "schema.sql")
    else:
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

    with get_db() as conn:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
