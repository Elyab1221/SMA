-- Users table with club hierarchy support
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin', 'leader')),
    status TEXT NOT NULL CHECK (status IN ('active', 'pending', 'rejected', 'suspended')),
    leader_id INTEGER,
    leader_code TEXT UNIQUE,
    club_name TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (leader_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Anonymous messages table
-- Crucial security design: No student user_id is ever stored on messages.
-- leader_id allows messages to route to the correct club's leader and admins.
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leader_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (leader_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for optimal lookup performance
CREATE INDEX IF NOT EXISTS idx_users_leader ON users(leader_id);
CREATE INDEX IF NOT EXISTS idx_users_code ON users(leader_code);
CREATE INDEX IF NOT EXISTS idx_messages_leader ON messages(leader_id);

-- Daily rate limit per student
CREATE TABLE IF NOT EXISTS send_limits (
    user_id INTEGER PRIMARY KEY,
    sent_today INTEGER NOT NULL DEFAULT 0,
    last_reset TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Brute-force protection for login
CREATE TABLE IF NOT EXISTS login_attempts (
    email TEXT PRIMARY KEY,
    fails INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0
);
