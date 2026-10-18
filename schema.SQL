CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN('student','admin','leader')),
    status TEXT NOT NULL CHECK (status IN ('acitve','pending','rejected','suspended'))
);
--No user id on purpose to make it anonymous
--cretaed at is a date only(notime) so timing cant identify anyone.
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (date('now'))
);

--daily limit counter
CREATE TABLE IF NOT EXISTS send_limits(
    user_id INTEGER PRIMARY KEY,
    sent_today INTEGER NOT NULL DEFAULT 0,
    last_sent TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts(
    email TEXT PRIMARY KEY,
    fails INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0
);