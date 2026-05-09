import sqlite3
from flask import Flask, render_template, redirect, request, session, url_for, abort
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


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

    user = {
        "name": session["user_name"],
        "email": "demo@spendly.com",
        "member_since": "January 15, 2025",
    }
    stats = {
        "total_spent": "₹18,240",
        "transaction_count": 12,
        "top_category": "Food",
    }
    transactions = [
        {"date": "May 8, 2025", "description": "Grocery run",         "category": "Food",          "amount": "₹1,240"},
        {"date": "May 7, 2025", "description": "Metro card recharge",  "category": "Transport",     "amount": "₹500"},
        {"date": "May 6, 2025", "description": "Electricity bill",     "category": "Bills",         "amount": "₹2,100"},
        {"date": "May 5, 2025", "description": "Doctor visit",         "category": "Health",        "amount": "₹800"},
        {"date": "May 3, 2025", "description": "Movie tickets",        "category": "Entertainment", "amount": "₹640"},
    ]
    categories = [
        {"name": "Food",          "total": "₹6,800", "pct": 37},
        {"name": "Bills",         "total": "₹4,200", "pct": 23},
        {"name": "Transport",     "total": "₹2,500", "pct": 14},
        {"name": "Health",        "total": "₹1,800", "pct": 10},
        {"name": "Entertainment", "total": "₹1,240", "pct":  7},
        {"name": "Shopping",      "total": "₹1,700", "pct":  9},
    ]
    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


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
