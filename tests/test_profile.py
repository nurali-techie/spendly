import database.db as db_module
from database.db import (
    get_recent_expenses,
    get_user_by_id,
    get_expense_stats,
    get_category_breakdown,
)


def _insert_expense(user_id, amount, category, date, description=""):
    conn = db_module.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


# ── get_recent_expenses ──────────────────────────────────────────────────────

def test_get_recent_expenses_returns_newest_first(client):
    uid = db_module.create_user("T1", "t1@example.com", "password1")
    _insert_expense(uid, 10.00, "Food", "2026-04-01", "Lunch")
    _insert_expense(uid, 20.00, "Transport", "2026-04-05", "Bus")
    rows = get_recent_expenses(uid)
    assert rows[0]["date"] == "2026-04-05"
    assert rows[1]["date"] == "2026-04-01"


def test_get_recent_expenses_empty_user(client):
    uid = db_module.create_user("T2", "t2@example.com", "password1")
    assert get_recent_expenses(uid) == []


def test_get_recent_expenses_respects_limit(client):
    uid = db_module.create_user("T3", "t3@example.com", "password1")
    for i in range(10):
        _insert_expense(uid, float(i + 1), "Other", f"2026-01-{i+1:02d}", f"item{i}")
    rows = get_recent_expenses(uid, limit=3)
    assert len(rows) == 3


def test_profile_transactions_shows_real_data(client):
    uid = db_module.create_user("RouteUser", "route@example.com", "password1")
    _insert_expense(uid, 500.00, "Transport", "2026-05-07", "Metro card recharge")
    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "RouteUser"
    response = client.get("/profile")
    assert b"Metro card recharge" in response.data
    assert b"Transport" in response.data


# ── get_user_by_id ───────────────────────────────────────────────────────────

def test_get_user_by_id_returns_correct_fields(client):
    uid = db_module.create_user("Alice", "alice@example.com", "password1")
    result = get_user_by_id(uid)
    assert result["name"] == "Alice"
    assert result["email"] == "alice@example.com"
    assert result["created_at"]


def test_get_user_by_id_nonexistent_returns_none(client):
    assert get_user_by_id(9999) is None


# ── get_expense_stats ────────────────────────────────────────────────────────

def test_get_expense_stats_with_expenses(client):
    uid = db_module.create_user("S1", "s1@example.com", "password1")
    _insert_expense(uid, 100.00, "Food",  "2026-04-01")
    _insert_expense(uid, 200.00, "Bills", "2026-04-02")
    stats = get_expense_stats(uid)
    assert stats["total"] == 300.00
    assert stats["count"] == 2
    assert stats["top_category"] == "Bills"


def test_get_expense_stats_no_expenses(client):
    uid = db_module.create_user("S2", "s2@example.com", "password1")
    stats = get_expense_stats(uid)
    assert stats["total"] == 0.0
    assert stats["count"] == 0
    assert stats["top_category"] is None


def test_profile_shows_real_email(client):
    uid = db_module.create_user("Ravi", "ravi@example.com", "password1")
    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "Ravi"
    response = client.get("/profile")
    assert b"ravi@example.com" in response.data


def test_profile_unauthenticated_redirects(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.location


# ── get_category_breakdown ───────────────────────────────────────────────────

def test_get_category_breakdown_ordered_by_total(client):
    uid = db_module.create_user("C1", "c1@example.com", "password1")
    _insert_expense(uid, 50.00,  "Food",      "2026-04-01")
    _insert_expense(uid, 200.00, "Bills",     "2026-04-02")
    _insert_expense(uid, 30.00,  "Transport", "2026-04-03")
    cats = get_category_breakdown(uid)
    assert cats[0]["name"] == "Bills"
    assert cats[1]["name"] == "Food"
    assert cats[2]["name"] == "Transport"


def test_get_category_breakdown_pct_sums_to_100(client):
    uid = db_module.create_user("C2", "c2@example.com", "password1")
    _insert_expense(uid, 10.00, "Food",    "2026-04-01")
    _insert_expense(uid, 20.00, "Bills",   "2026-04-02")
    _insert_expense(uid, 30.00, "Health",  "2026-04-03")
    cats = get_category_breakdown(uid)
    assert sum(c["pct"] for c in cats) == 100


def test_get_category_breakdown_formats_total(client):
    uid = db_module.create_user("C3", "c3@example.com", "password1")
    _insert_expense(uid, 6800.00, "Food", "2026-04-01")
    cats = get_category_breakdown(uid)
    assert cats[0]["total"] == "₹6,800.00"


def test_get_category_breakdown_empty_user(client):
    uid = db_module.create_user("C4", "c4@example.com", "password1")
    assert get_category_breakdown(uid) == []


def test_profile_category_breakdown_renders(client):
    uid = db_module.create_user("C5", "c5@example.com", "password1")
    _insert_expense(uid, 100.00, "Shopping", "2026-04-01")
    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "C5"
    response = client.get("/profile")
    assert b"Shopping" in response.data
