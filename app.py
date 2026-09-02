import re
from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from database.db import (
    create_user,
    get_db,
    get_expense_by_id,
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    update_expense,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _parse_date_filter(args):
    start_raw = args.get("start_date", "").strip()
    end_raw = args.get("end_date", "").strip()
    if not start_raw and not end_raw:
        return None, None

    def _valid(value):
        if not value:
            return True
        if not DATE_RE.match(value):
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return False
        return True

    if not _valid(start_raw) or not _valid(end_raw):
        return None, None

    start_date, end_date = start_raw or None, end_raw or None
    if start_date and end_date and start_date > end_date:
        return None, None
    return start_date, end_date


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if get_user_by_email(email):
        return render_template("register.html", error="An account with that email already exists.")

    password_hash = generate_password_hash(password)
    user_id = create_user(name, email, password_hash)
    session["user_id"] = user_id
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("login"))

    member_since = datetime.strptime(
        user["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %Y")
    start_date, end_date = _parse_date_filter(request.args)
    summary = get_expense_summary(
        user_id, start_date=start_date, end_date=end_date
    )
    recent_expenses = get_recent_expenses(
        user_id, start_date=start_date, end_date=end_date
    )
    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        summary=summary,
        recent_expenses=recent_expenses,
        filter_start=start_date,
        filter_end=end_date,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("expenses_add.html", categories=CATEGORIES)

    amount_raw = request.form.get("amount", "")
    category_raw = request.form.get("category", "")
    date_raw = request.form.get("date", "")
    description_raw = request.form.get("description", "")
    form = {
        "amount": amount_raw,
        "category": category_raw,
        "date": date_raw,
        "description": description_raw,
    }

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return render_template(
            "expenses_add.html",
            categories=CATEGORIES,
            error="Enter a valid amount greater than 0.",
            form=form,
        )

    category = category_raw.strip()
    if not category or category not in CATEGORIES:
        return render_template(
            "expenses_add.html",
            categories=CATEGORIES,
            error="Select a valid category.",
            form=form,
        )

    date = date_raw.strip()
    if not date or not DATE_RE.match(date):
        return render_template(
            "expenses_add.html",
            categories=CATEGORIES,
            error="Enter a valid date.",
            form=form,
        )

    description = description_raw.strip() or None
    db.add_expense(user_id, amount, category, date, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "expenses_edit.html", categories=CATEGORIES, expense=expense
        )

    amount_raw = request.form.get("amount", "")
    category_raw = request.form.get("category", "")
    date_raw = request.form.get("date", "")
    description_raw = request.form.get("description", "")
    form = {
        "amount": amount_raw,
        "category": category_raw,
        "date": date_raw,
        "description": description_raw,
    }

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return render_template(
            "expenses_edit.html",
            categories=CATEGORIES,
            expense=expense,
            error="Enter a valid amount greater than 0.",
            form=form,
        )

    category = category_raw.strip()
    if not category or category not in CATEGORIES:
        return render_template(
            "expenses_edit.html",
            categories=CATEGORIES,
            expense=expense,
            error="Select a valid category.",
            form=form,
        )

    date = date_raw.strip()
    if not date or not DATE_RE.match(date):
        return render_template(
            "expenses_edit.html",
            categories=CATEGORIES,
            expense=expense,
            error="Enter a valid date.",
            form=form,
        )

    description = description_raw.strip() or None
    update_expense(id, user_id, amount, category, date, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
