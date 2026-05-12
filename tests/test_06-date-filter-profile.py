"""
Tests for Step 6: Date-range filter on the /profile route.

Covers:
- Auth guard
- Unfiltered (no params) baseline
- Preset quick-select filters: this_month, last3, last6, all_time
- Custom date range
- Inverted range flash error + fallback
- Malformed date strings — no crash, silent fallback
- Empty result set for a valid range with no matching expenses
- DB helpers (get_expense_stats, get_recent_expenses, get_category_breakdown)
  respond correctly with and without date filters
- ₹ symbol always present in amounts
"""

import pytest
from datetime import date, timedelta

import database.db as db_module
from database.db import (
    get_expense_stats,
    get_recent_expenses,
    get_category_breakdown,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def _insert_expense(user_id, amount, category, expense_date, description=""):
    """Insert a single expense row using parameterized SQL."""
    conn = db_module.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


def _make_auth_session(client, user_id, user_name):
    """Force the test client's session to be authenticated."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name


# ── date anchors ─────────────────────────────────────────────────────────────

TODAY = date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")
FIRST_OF_MONTH_STR = TODAY.replace(day=1).strftime("%Y-%m-%d")

# "3 months ago" / "6 months ago" mirrors the app's _first_of_month_offset
def _first_of_month_offset(ref, months_back):
    month, year = ref.month - months_back, ref.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)

LAST3_START = _first_of_month_offset(TODAY, 3)
LAST3_START_STR = LAST3_START.strftime("%Y-%m-%d")
LAST6_START = _first_of_month_offset(TODAY, 6)
LAST6_START_STR = LAST6_START.strftime("%Y-%m-%d")

# A date definitely before LAST6_START (7 months back, first of that month)
OLD_DATE = _first_of_month_offset(TODAY, 7)
OLD_DATE_STR = OLD_DATE.strftime("%Y-%m-%d")


# ── fixtures ─────────────────────────────────────────────────────────────────
# conftest.py already provides a `client` fixture that points at a temp SQLite
# file and calls init_db(). We rely on it here without re-defining it.

# ── auth guard ───────────────────────────────────────────────────────────────

class TestAuthGuard:
    def test_unauthenticated_request_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in response.location, "Redirect target should be /login"

    def test_unauthenticated_with_date_params_still_redirects(self, client):
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-12-31")
        assert response.status_code == 302
        assert "/login" in response.location


# ── unfiltered baseline ───────────────────────────────────────────────────────

class TestUnfilteredBaseline:
    def test_no_params_returns_200(self, client):
        uid = db_module.create_user("Base1", "base1@example.com", "password1")
        _make_auth_session(client, uid, "Base1")
        response = client.get("/profile")
        assert response.status_code == 200

    def test_no_params_shows_all_expenses(self, client):
        uid = db_module.create_user("Base2", "base2@example.com", "password1")
        _insert_expense(uid, 100.00, "Food", "2025-01-15", "Old lunch")
        _insert_expense(uid, 200.00, "Bills", TODAY_STR, "Recent bill")
        _make_auth_session(client, uid, "Base2")
        response = client.get("/profile")
        assert b"Old lunch" in response.data, "Unfiltered view should include old expense"
        assert b"Recent bill" in response.data, "Unfiltered view should include recent expense"

    def test_no_params_active_preset_is_all_time(self, client):
        """The template receives active_preset='all_time' when no query params given."""
        uid = db_module.create_user("Base3", "base3@example.com", "password1")
        _make_auth_session(client, uid, "Base3")
        response = client.get("/profile")
        # The template should mark the "All Time" button as active.
        # We check for the text "All Time" in the page and a 200 response.
        assert response.status_code == 200
        assert b"All Time" in response.data, "All Time preset should appear in filter bar"


# ── preset filters — route level ──────────────────────────────────────────────

class TestPresetFiltersRoute:
    def test_this_month_includes_current_month_expense(self, client):
        uid = db_module.create_user("PM1", "pm1@example.com", "password1")
        _insert_expense(uid, 50.00, "Food", TODAY_STR, "Todays meal")
        _make_auth_session(client, uid, "PM1")
        response = client.get(
            f"/profile?date_from={FIRST_OF_MONTH_STR}&date_to={TODAY_STR}"
        )
        assert response.status_code == 200
        assert b"Todays meal" in response.data

    def test_this_month_excludes_previous_month_expense(self, client):
        uid = db_module.create_user("PM2", "pm2@example.com", "password1")
        # Build a date that is definitely before the first of this month
        pre_month = (TODAY.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        _insert_expense(uid, 75.00, "Bills", pre_month, "Old bill")
        _make_auth_session(client, uid, "PM2")
        response = client.get(
            f"/profile?date_from={FIRST_OF_MONTH_STR}&date_to={TODAY_STR}"
        )
        assert b"Old bill" not in response.data

    def test_last3_includes_expense_within_window(self, client):
        uid = db_module.create_user("PM3", "pm3@example.com", "password1")
        # A date one day after LAST3_START is inside the window
        inside = (LAST3_START + timedelta(days=1)).strftime("%Y-%m-%d")
        _insert_expense(uid, 30.00, "Transport", inside, "Bus fare")
        _make_auth_session(client, uid, "PM3")
        response = client.get(
            f"/profile?date_from={LAST3_START_STR}&date_to={TODAY_STR}"
        )
        assert b"Bus fare" in response.data

    def test_last3_excludes_expense_older_than_window(self, client):
        uid = db_module.create_user("PM4", "pm4@example.com", "password1")
        _insert_expense(uid, 40.00, "Health", OLD_DATE_STR, "Old pharmacy")
        _make_auth_session(client, uid, "PM4")
        response = client.get(
            f"/profile?date_from={LAST3_START_STR}&date_to={TODAY_STR}"
        )
        assert b"Old pharmacy" not in response.data

    def test_last6_includes_expense_within_window(self, client):
        uid = db_module.create_user("PM5", "pm5@example.com", "password1")
        inside = (LAST6_START + timedelta(days=1)).strftime("%Y-%m-%d")
        _insert_expense(uid, 60.00, "Shopping", inside, "Shopping item")
        _make_auth_session(client, uid, "PM5")
        response = client.get(
            f"/profile?date_from={LAST6_START_STR}&date_to={TODAY_STR}"
        )
        assert b"Shopping item" in response.data

    def test_last6_excludes_expense_older_than_window(self, client):
        uid = db_module.create_user("PM6", "pm6@example.com", "password1")
        _insert_expense(uid, 90.00, "Bills", OLD_DATE_STR, "Very old bill")
        _make_auth_session(client, uid, "PM6")
        response = client.get(
            f"/profile?date_from={LAST6_START_STR}&date_to={TODAY_STR}"
        )
        assert b"Very old bill" not in response.data

    def test_all_time_preset_no_params_shows_all(self, client):
        uid = db_module.create_user("PM7", "pm7@example.com", "password1")
        _insert_expense(uid, 10.00, "Food", "2020-01-01", "Ancient expense")
        _insert_expense(uid, 20.00, "Food", TODAY_STR, "Current expense")
        _make_auth_session(client, uid, "PM7")
        response = client.get("/profile")
        assert b"Ancient expense" in response.data
        assert b"Current expense" in response.data


# ── custom date range ─────────────────────────────────────────────────────────

class TestCustomDateRange:
    def test_custom_range_returns_only_matching_transactions(self, client):
        uid = db_module.create_user("CR1", "cr1@example.com", "password1")
        _insert_expense(uid, 100.00, "Food", "2025-03-10", "March meal")
        _insert_expense(uid, 200.00, "Bills", "2025-06-15", "June bill")
        _insert_expense(uid, 300.00, "Health", "2025-09-20", "Sept health")
        _make_auth_session(client, uid, "CR1")
        response = client.get("/profile?date_from=2025-05-01&date_to=2025-07-31")
        assert b"June bill" in response.data
        assert b"March meal" not in response.data
        assert b"Sept health" not in response.data

    def test_custom_range_stats_reflect_filtered_total(self, client):
        uid = db_module.create_user("CR2", "cr2@example.com", "password1")
        _insert_expense(uid, 1000.00, "Bills", "2025-03-01", "Outside range")
        _insert_expense(uid, 250.00, "Food", "2025-06-10", "In range")
        _make_auth_session(client, uid, "CR2")
        response = client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        # ₹250.00 should appear; ₹1,000.00 should not be the total
        assert "₹250.00".encode() in response.data

    def test_custom_range_category_breakdown_filtered(self, client):
        uid = db_module.create_user("CR3", "cr3@example.com", "password1")
        _insert_expense(uid, 500.00, "Entertainment", "2025-01-05", "Old entertainment")
        _insert_expense(uid, 150.00, "Transport", "2025-08-20", "Transport in range")
        _make_auth_session(client, uid, "CR3")
        response = client.get("/profile?date_from=2025-08-01&date_to=2025-08-31")
        assert b"Transport" in response.data
        assert b"Entertainment" not in response.data

    def test_custom_range_amounts_have_rupee_symbol(self, client):
        uid = db_module.create_user("CR4", "cr4@example.com", "password1")
        _insert_expense(uid, 999.00, "Shopping", "2025-07-04", "Gadget")
        _make_auth_session(client, uid, "CR4")
        response = client.get("/profile?date_from=2025-07-01&date_to=2025-07-31")
        assert "₹".encode() in response.data, "Amounts must display ₹ symbol"


# ── inverted date range ───────────────────────────────────────────────────────

class TestInvertedDateRange:
    def test_date_from_after_date_to_flashes_error(self, client):
        uid = db_module.create_user("INV1", "inv1@example.com", "password1")
        _make_auth_session(client, uid, "INV1")
        response = client.get(
            "/profile?date_from=2025-12-31&date_to=2025-01-01",
            follow_redirects=True,
        )
        assert b"Start date must be before end date." in response.data

    def test_date_from_after_date_to_returns_unfiltered_view(self, client):
        uid = db_module.create_user("INV2", "inv2@example.com", "password1")
        _insert_expense(uid, 80.00, "Food", "2024-03-15", "Old food expense")
        _make_auth_session(client, uid, "INV2")
        response = client.get(
            "/profile?date_from=2025-12-31&date_to=2025-01-01",
            follow_redirects=True,
        )
        # Unfiltered — the old expense should still appear
        assert b"Old food expense" in response.data

    def test_date_from_after_date_to_still_returns_200(self, client):
        uid = db_module.create_user("INV3", "inv3@example.com", "password1")
        _make_auth_session(client, uid, "INV3")
        response = client.get(
            "/profile?date_from=2026-06-01&date_to=2026-01-01",
            follow_redirects=True,
        )
        assert response.status_code == 200


# ── malformed date strings ────────────────────────────────────────────────────

class TestMalformedDates:
    @pytest.mark.parametrize("bad_from,bad_to", [
        ("not-a-date", "2025-12-31"),
        ("2025-01-01", "not-a-date"),
        ("not-a-date", "not-a-date"),
        ("2025-13-01", "2025-12-31"),   # invalid month
        ("2025-01-99", "2025-12-31"),   # invalid day
        ("25-01-01",   "2025-12-31"),   # wrong format
    ])
    def test_malformed_date_does_not_crash(self, client, bad_from, bad_to):
        uid = db_module.create_user(
            f"MAL_{bad_from[:5]}", f"mal_{hash((bad_from,bad_to))}@example.com", "password1"
        )
        _make_auth_session(client, uid, "MAL")
        response = client.get(
            f"/profile?date_from={bad_from}&date_to={bad_to}",
            follow_redirects=True,
        )
        assert response.status_code == 200, (
            f"App crashed for date_from={bad_from!r} date_to={bad_to!r}"
        )

    def test_malformed_date_from_falls_back_to_unfiltered(self, client):
        uid = db_module.create_user("MAL2", "mal2@example.com", "password1")
        _insert_expense(uid, 55.00, "Food", "2024-06-10", "Backdate lunch")
        _make_auth_session(client, uid, "MAL2")
        response = client.get("/profile?date_from=bad-date&date_to=2025-12-31")
        # Unfiltered — old expense should still appear
        assert b"Backdate lunch" in response.data

    def test_malformed_date_to_falls_back_to_unfiltered(self, client):
        uid = db_module.create_user("MAL3", "mal3@example.com", "password1")
        _insert_expense(uid, 33.00, "Bills", "2024-06-10", "Backdate bill")
        _make_auth_session(client, uid, "MAL3")
        response = client.get("/profile?date_from=2024-01-01&date_to=oops")
        assert b"Backdate bill" in response.data


# ── empty result set ──────────────────────────────────────────────────────────

class TestEmptyResultSet:
    def test_no_matching_expenses_total_is_zero(self, client):
        uid = db_module.create_user("EMP1", "emp1@example.com", "password1")
        _insert_expense(uid, 500.00, "Bills", "2023-06-01", "Way old bill")
        _make_auth_session(client, uid, "EMP1")
        # Filter to a range with no expenses
        response = client.get("/profile?date_from=2030-01-01&date_to=2030-12-31")
        assert response.status_code == 200
        assert "₹0.00".encode() in response.data, "Should show ₹0.00 when no matching expenses"

    def test_no_matching_expenses_transaction_count_zero(self, client):
        uid = db_module.create_user("EMP2", "emp2@example.com", "password1")
        _make_auth_session(client, uid, "EMP2")
        response = client.get("/profile?date_from=2030-01-01&date_to=2030-12-31")
        assert response.status_code == 200
        # The transaction count stat should be 0
        assert b"0" in response.data

    def test_no_matching_expenses_no_server_error(self, client):
        uid = db_module.create_user("EMP3", "emp3@example.com", "password1")
        _make_auth_session(client, uid, "EMP3")
        response = client.get("/profile?date_from=2030-01-01&date_to=2030-12-31")
        assert response.status_code == 200


# ── DB helper: get_expense_stats ──────────────────────────────────────────────

class TestGetExpenseStats:
    def test_with_date_filter_returns_only_matching_total(self, client):
        uid = db_module.create_user("GS1", "gs1@example.com", "password1")
        _insert_expense(uid, 100.00, "Food",  "2025-03-01")
        _insert_expense(uid, 200.00, "Bills", "2025-06-15")
        stats = get_expense_stats(uid, date_from="2025-06-01", date_to="2025-06-30")
        assert stats["total"] == 200.00
        assert stats["count"] == 1

    def test_with_date_filter_returns_correct_top_category(self, client):
        uid = db_module.create_user("GS2", "gs2@example.com", "password1")
        _insert_expense(uid, 300.00, "Entertainment", "2025-05-10")
        _insert_expense(uid, 100.00, "Food",          "2025-05-15")
        stats = get_expense_stats(uid, date_from="2025-05-01", date_to="2025-05-31")
        assert stats["top_category"] == "Entertainment"

    def test_without_date_filter_returns_all_expenses(self, client):
        uid = db_module.create_user("GS3", "gs3@example.com", "password1")
        _insert_expense(uid, 50.00,  "Food",  "2024-01-01")
        _insert_expense(uid, 150.00, "Bills", "2025-12-31")
        stats = get_expense_stats(uid)
        assert stats["total"] == 200.00
        assert stats["count"] == 2

    def test_no_expenses_in_range_returns_zero(self, client):
        uid = db_module.create_user("GS4", "gs4@example.com", "password1")
        _insert_expense(uid, 999.00, "Shopping", "2023-06-01")
        stats = get_expense_stats(uid, date_from="2030-01-01", date_to="2030-12-31")
        assert stats["total"] == 0.0
        assert stats["count"] == 0
        assert stats["top_category"] is None

    def test_only_date_from_no_date_to_returns_all(self, client):
        """When only one bound is given, the helper should fall back to unfiltered."""
        uid = db_module.create_user("GS5", "gs5@example.com", "password1")
        _insert_expense(uid, 10.00, "Food",  "2024-01-01")
        _insert_expense(uid, 20.00, "Bills", "2025-01-01")
        stats = get_expense_stats(uid, date_from="2025-01-01", date_to=None)
        assert stats["count"] == 2, "Partial filter should behave as unfiltered"

    def test_only_date_to_no_date_from_returns_all(self, client):
        uid = db_module.create_user("GS6", "gs6@example.com", "password1")
        _insert_expense(uid, 10.00, "Food",  "2024-01-01")
        _insert_expense(uid, 20.00, "Bills", "2025-01-01")
        stats = get_expense_stats(uid, date_from=None, date_to="2024-12-31")
        assert stats["count"] == 2, "Partial filter should behave as unfiltered"

    def test_date_filter_isolates_to_single_user(self, client):
        uid1 = db_module.create_user("GS7a", "gs7a@example.com", "password1")
        uid2 = db_module.create_user("GS7b", "gs7b@example.com", "password1")
        _insert_expense(uid1, 400.00, "Food",  "2025-07-01")
        _insert_expense(uid2, 900.00, "Bills", "2025-07-01")
        stats = get_expense_stats(uid1, date_from="2025-07-01", date_to="2025-07-31")
        assert stats["total"] == 400.00, "Stats should not include other users' expenses"


# ── DB helper: get_recent_expenses ────────────────────────────────────────────

class TestGetRecentExpenses:
    def test_with_date_filter_returns_only_matching_rows(self, client):
        uid = db_module.create_user("GR1", "gr1@example.com", "password1")
        _insert_expense(uid, 10.00, "Food",  "2025-02-01", "Feb expense")
        _insert_expense(uid, 20.00, "Bills", "2025-08-01", "Aug expense")
        rows = get_recent_expenses(uid, date_from="2025-08-01", date_to="2025-08-31")
        assert len(rows) == 1
        assert rows[0]["description"] == "Aug expense"

    def test_with_date_filter_order_is_newest_first(self, client):
        uid = db_module.create_user("GR2", "gr2@example.com", "password1")
        _insert_expense(uid, 10.00, "Food",      "2025-06-01", "First")
        _insert_expense(uid, 20.00, "Transport", "2025-06-20", "Second")
        rows = get_recent_expenses(uid, date_from="2025-06-01", date_to="2025-06-30")
        assert rows[0]["date"] == "2025-06-20"
        assert rows[1]["date"] == "2025-06-01"

    def test_without_date_filter_returns_all_rows(self, client):
        uid = db_module.create_user("GR3", "gr3@example.com", "password1")
        _insert_expense(uid, 5.00,  "Food",  "2020-01-01", "Ancient")
        _insert_expense(uid, 10.00, "Bills", "2025-12-31", "Recent")
        rows = get_recent_expenses(uid, limit=10)
        descriptions = [r["description"] for r in rows]
        assert "Ancient" in descriptions
        assert "Recent" in descriptions

    def test_limit_respected_with_date_filter(self, client):
        uid = db_module.create_user("GR4", "gr4@example.com", "password1")
        for day in range(1, 11):
            _insert_expense(uid, float(day), "Food", f"2025-07-{day:02d}", f"item{day}")
        rows = get_recent_expenses(uid, limit=3, date_from="2025-07-01", date_to="2025-07-31")
        assert len(rows) == 3

    def test_no_matching_rows_returns_empty_list(self, client):
        uid = db_module.create_user("GR5", "gr5@example.com", "password1")
        _insert_expense(uid, 100.00, "Bills", "2023-01-01")
        rows = get_recent_expenses(uid, date_from="2030-01-01", date_to="2030-12-31")
        assert rows == []

    def test_date_filter_isolates_to_single_user(self, client):
        uid1 = db_module.create_user("GR6a", "gr6a@example.com", "password1")
        uid2 = db_module.create_user("GR6b", "gr6b@example.com", "password1")
        _insert_expense(uid1, 10.00, "Food",  "2025-06-10", "User1 expense")
        _insert_expense(uid2, 20.00, "Bills", "2025-06-10", "User2 expense")
        rows = get_recent_expenses(uid1, date_from="2025-06-01", date_to="2025-06-30")
        descriptions = [r["description"] for r in rows]
        assert "User1 expense" in descriptions
        assert "User2 expense" not in descriptions


# ── DB helper: get_category_breakdown ────────────────────────────────────────

class TestGetCategoryBreakdown:
    def test_with_date_filter_returns_only_matching_categories(self, client):
        uid = db_module.create_user("GB1", "gb1@example.com", "password1")
        _insert_expense(uid, 200.00, "Entertainment", "2025-01-10")
        _insert_expense(uid, 100.00, "Transport",     "2025-09-10")
        cats = get_category_breakdown(uid, date_from="2025-09-01", date_to="2025-09-30")
        names = [c["name"] for c in cats]
        assert "Transport" in names
        assert "Entertainment" not in names

    def test_with_date_filter_pct_sums_to_100(self, client):
        uid = db_module.create_user("GB2", "gb2@example.com", "password1")
        _insert_expense(uid, 100.00, "Food",      "2025-05-01")
        _insert_expense(uid, 200.00, "Bills",     "2025-05-10")
        _insert_expense(uid, 300.00, "Transport", "2025-05-20")
        cats = get_category_breakdown(uid, date_from="2025-05-01", date_to="2025-05-31")
        assert sum(c["pct"] for c in cats) == 100

    def test_with_date_filter_total_formatted_with_rupee(self, client):
        uid = db_module.create_user("GB3", "gb3@example.com", "password1")
        _insert_expense(uid, 1500.00, "Bills", "2025-07-01")
        cats = get_category_breakdown(uid, date_from="2025-07-01", date_to="2025-07-31")
        assert cats[0]["total"] == "₹1,500.00"

    def test_without_date_filter_returns_all_categories(self, client):
        uid = db_module.create_user("GB4", "gb4@example.com", "password1")
        _insert_expense(uid, 50.00, "Food",    "2024-01-01")
        _insert_expense(uid, 80.00, "Bills",   "2025-01-01")
        _insert_expense(uid, 30.00, "Health",  "2025-06-01")
        cats = get_category_breakdown(uid)
        names = [c["name"] for c in cats]
        assert "Food" in names
        assert "Bills" in names
        assert "Health" in names

    def test_no_matching_expenses_returns_empty_list(self, client):
        uid = db_module.create_user("GB5", "gb5@example.com", "password1")
        _insert_expense(uid, 100.00, "Bills", "2022-01-01")
        cats = get_category_breakdown(uid, date_from="2030-01-01", date_to="2030-12-31")
        assert cats == []

    def test_date_filter_ordered_by_total_desc(self, client):
        uid = db_module.create_user("GB6", "gb6@example.com", "password1")
        _insert_expense(uid, 50.00,  "Food",    "2025-04-01")
        _insert_expense(uid, 300.00, "Bills",   "2025-04-10")
        _insert_expense(uid, 100.00, "Health",  "2025-04-20")
        cats = get_category_breakdown(uid, date_from="2025-04-01", date_to="2025-04-30")
        assert cats[0]["name"] == "Bills"
        assert cats[1]["name"] == "Health"
        assert cats[2]["name"] == "Food"

    def test_date_filter_isolates_to_single_user(self, client):
        uid1 = db_module.create_user("GB7a", "gb7a@example.com", "password1")
        uid2 = db_module.create_user("GB7b", "gb7b@example.com", "password1")
        _insert_expense(uid1, 100.00, "Food",  "2025-04-01")
        _insert_expense(uid2, 500.00, "Bills", "2025-04-01")
        cats = get_category_breakdown(uid1, date_from="2025-04-01", date_to="2025-04-30")
        names = [c["name"] for c in cats]
        assert "Food" in names
        assert "Bills" not in names


# ── filter bar UI smoke tests ─────────────────────────────────────────────────

class TestFilterBarUI:
    def test_filter_bar_contains_preset_links(self, client):
        uid = db_module.create_user("UI1", "ui1@example.com", "password1")
        _make_auth_session(client, uid, "UI1")
        response = client.get("/profile")
        assert b"This Month" in response.data
        assert b"Last 3 Months" in response.data
        assert b"Last 6 Months" in response.data
        assert b"All Time" in response.data

    def test_filter_bar_has_date_input_fields(self, client):
        uid = db_module.create_user("UI2", "ui2@example.com", "password1")
        _make_auth_session(client, uid, "UI2")
        response = client.get("/profile")
        assert b'name="date_from"' in response.data
        assert b'name="date_to"' in response.data

    def test_filter_bar_has_apply_button(self, client):
        uid = db_module.create_user("UI3", "ui3@example.com", "password1")
        _make_auth_session(client, uid, "UI3")
        response = client.get("/profile")
        assert b"Apply" in response.data

    def test_amounts_always_show_rupee_symbol(self, client):
        uid = db_module.create_user("UI4", "ui4@example.com", "password1")
        _insert_expense(uid, 123.45, "Food", TODAY_STR, "Test rupee display")
        _make_auth_session(client, uid, "UI4")
        response = client.get(
            f"/profile?date_from={FIRST_OF_MONTH_STR}&date_to={TODAY_STR}"
        )
        assert "₹".encode() in response.data, "₹ symbol must appear for all amounts"

    def test_amounts_show_rupee_symbol_unfiltered(self, client):
        uid = db_module.create_user("UI5", "ui5@example.com", "password1")
        _insert_expense(uid, 456.78, "Bills", "2025-06-01", "Rupee unfiltered")
        _make_auth_session(client, uid, "UI5")
        response = client.get("/profile")
        assert "₹".encode() in response.data, "₹ symbol must appear in unfiltered view"
