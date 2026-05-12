import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "spendly.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    if row[0] > 0:
        conn.close()
        return

    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    expenses = [
        (user_id, 12.50,  "Food",          "2026-05-01", "Lunch at cafe"),
        (user_id, 45.00,  "Transport",     "2026-05-03", "Monthly bus pass"),
        (user_id, 120.00, "Bills",         "2026-05-05", "Electricity bill"),
        (user_id, 30.00,  "Health",        "2026-05-07", "Pharmacy"),
        (user_id, 18.00,  "Entertainment", "2026-05-10", "Streaming subscription"),
        (user_id, 65.00,  "Shopping",      "2026-05-13", "Clothes"),
        (user_id, 9.99,   "Other",         "2026-05-15", "Miscellaneous"),
        (user_id, 22.75,  "Food",          "2026-05-18", "Grocery run"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()


def create_user(name, email, password):
    password_hash = generate_password_hash(password)
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def get_expense_stats(user_id, date_from=None, date_to=None):
    date_filter = ""
    date_params = ()
    if date_from and date_to:
        date_filter = " AND date BETWEEN ? AND ?"
        date_params = (date_from, date_to)
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
        "FROM expenses WHERE user_id = ?" + date_filter,
        (user_id,) + date_params,
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ?" + date_filter + " "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id,) + date_params,
    ).fetchone()
    conn.close()
    return {
        "total":        row["total"],
        "count":        row["cnt"],
        "top_category": top["category"] if top else None,
    }


def get_recent_expenses(user_id, limit=5, date_from=None, date_to=None):
    date_filter = ""
    date_params = ()
    if date_from and date_to:
        date_filter = " AND date BETWEEN ? AND ?"
        date_params = (date_from, date_to)
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount "
        "FROM expenses WHERE user_id = ?" + date_filter + " ORDER BY date DESC, id DESC LIMIT ?",
        (user_id,) + date_params + (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_category_breakdown(user_id, date_from=None, date_to=None):
    date_filter = ""
    date_params = ()
    if date_from and date_to:
        date_filter = " AND date BETWEEN ? AND ?"
        date_params = (date_from, date_to)
    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS cat_total "
        "FROM expenses WHERE user_id = ?" + date_filter + " "
        "GROUP BY category ORDER BY cat_total DESC",
        (user_id,) + date_params,
    ).fetchall()
    conn.close()
    if not rows:
        return []
    grand = sum(r["cat_total"] for r in rows)
    result = [
        {
            "name":  r["category"],
            "total": f"₹{r['cat_total']:,.2f}",
            "pct":   int(r["cat_total"] / grand * 100),
        }
        for r in rows
    ]
    result[0]["pct"] += 100 - sum(c["pct"] for c in result)
    return result
