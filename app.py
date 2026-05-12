import sqlite3
from flask import Flask, flash, render_template, redirect, request, session, url_for, abort
from werkzeug.security import check_password_hash
from datetime import datetime, date
from database.db import (
    get_db, init_db, seed_db, create_user, get_user_by_email,
    get_user_by_id, get_expense_stats, get_recent_expenses, get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


def _first_of_month_offset(ref, months_back):
    month, year = ref.month - months_back, ref.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Name is required.", email=email)
    if not email:
        return render_template("register.html", error="Email address is required.", name=name)
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.", name=name, email=email)

    try:
        user_id = create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.", name=name, email=email)

    session["user_id"] = user_id
    session["user_name"] = name
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email:
        return render_template("login.html", error="Email address is required.", email=email)
    if not password:
        return render_template("login.html", error="Password is required.", email=email)

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    raw_from = request.args.get("date_from", "").strip()
    raw_to   = request.args.get("date_to",   "").strip()

    date_from = None
    date_to   = None
    try:
        if raw_from:
            date_from = datetime.strptime(raw_from, "%Y-%m-%d").date()
    except ValueError:
        raw_from = ""
    try:
        if raw_to:
            date_to = datetime.strptime(raw_to, "%Y-%m-%d").date()
    except ValueError:
        raw_to = ""

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to   = None
        raw_from  = ""
        raw_to    = ""

    df_str = date_from.strftime("%Y-%m-%d") if date_from else None
    dt_str = date_to.strftime("%Y-%m-%d")   if date_to   else None

    user_row = get_user_by_id(session["user_id"])
    if user_row is None:
        abort(404)
    user = {
        "name":         user_row["name"],
        "email":        user_row["email"],
        "member_since": datetime.strptime(
                            user_row["created_at"][:10], "%Y-%m-%d"
                        ).strftime("%B %-d, %Y"),
    }

    raw_stats = get_expense_stats(session["user_id"], date_from=df_str, date_to=dt_str)
    stats = {
        "total_spent":       f"₹{raw_stats['total']:,.2f}",
        "transaction_count": raw_stats["count"],
        "top_category":      raw_stats["top_category"] or "—",
    }
    raw_txns = get_recent_expenses(session["user_id"], date_from=df_str, date_to=dt_str)
    transactions = [
        {
            "date":        datetime.strptime(t["date"], "%Y-%m-%d").strftime("%B %-d, %Y"),
            "description": t["description"] or "",
            "category":    t["category"],
            "amount":      f"₹{t['amount']:,.2f}",
        }
        for t in raw_txns
    ]
    categories = get_category_breakdown(session["user_id"], date_from=df_str, date_to=dt_str)

    today          = date.today()
    today_str      = today.strftime("%Y-%m-%d")
    this_month_str = today.replace(day=1).strftime("%Y-%m-%d")
    last3_str      = _first_of_month_offset(today, 3).strftime("%Y-%m-%d")
    last6_str      = _first_of_month_offset(today, 6).strftime("%Y-%m-%d")

    presets = {
        "this_month": url_for("profile", date_from=this_month_str, date_to=today_str),
        "last3":      url_for("profile", date_from=last3_str,      date_to=today_str),
        "last6":      url_for("profile", date_from=last6_str,      date_to=today_str),
        "all_time":   url_for("profile"),
    }

    if not raw_from and not raw_to:
        active_preset = "all_time"
    elif raw_from == this_month_str and raw_to == today_str:
        active_preset = "this_month"
    elif raw_from == last3_str and raw_to == today_str:
        active_preset = "last3"
    elif raw_from == last6_str and raw_to == today_str:
        active_preset = "last6"
    else:
        active_preset = None

    return render_template(
        "profile.html",
        user=user, stats=stats, transactions=transactions, categories=categories,
        presets=presets, active_preset=active_preset,
        date_from=raw_from, date_to=raw_to,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
