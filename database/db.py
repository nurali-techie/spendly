import os
import sqlite3

from werkzeug.security import generate_password_hash


_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "spendly.db",
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,
    date        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


def get_db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        (count,) = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if count > 0:
            return

        password_hash = generate_password_hash("demo123")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cur.lastrowid

        expenses = [
            (450.00,  "Food",          "2026-05-02", "Lunch at office canteen"),
            (1200.00, "Transport",     "2026-05-03", "Monthly metro pass"),
            (2800.00, "Bills",         "2026-05-04", "Electricity bill - April"),
            (650.00,  "Health",        "2026-05-05", "Pharmacy - vitamins"),
            (350.00,  "Entertainment", "2026-05-06", "Movie ticket"),
            (1850.00, "Shopping",      "2026-05-07", "Cotton kurta"),
            (199.00,  "Other",         "2026-05-08", "Newspaper subscription"),
            (820.00,  "Food",          "2026-05-09", "Groceries from BigBasket"),
        ]

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [(user_id, amt, cat, dt, desc) for (amt, cat, dt, desc) in expenses],
        )
        conn.commit()
    finally:
        conn.close()
