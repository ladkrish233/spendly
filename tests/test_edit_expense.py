import pytest

from database.db import add_expense, get_db, get_user_by_email


def _login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def _demo_user_id(app):
    with app.app_context():
        user = get_user_by_email("demo@spendly.com")
    return user["id"]


def _register_second_user(client, app):
    client.post(
        "/register",
        data={"name": "Other User", "email": "other@spendly.com", "password": "other123"},
    )
    with app.app_context():
        user = get_user_by_email("other@spendly.com")
    return user["id"]


def _add_expense(app, user_id, amount=42.50, category="Food",
                  date="2026-09-02", description="Lunch"):
    with app.app_context():
        expense_id = add_expense(user_id, amount, category, date, description)
    return expense_id


def _get_expense_row(app, expense_id):
    with app.app_context():
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
    return row


def _count_expenses(app, user_id):
    with app.app_context():
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return row["c"]


VALID_UPDATE = {
    "amount": "99.99",
    "category": "Transport",
    "date": "2026-09-10",
    "description": "Updated cab ride",
}


class TestEditExpenseGet:
    def test_get_redirects_when_logged_out(self, client, app):
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        response = client.get(f"/expenses/{expense_id}/edit")

        assert response.status_code == 302
        assert response.headers["Location"] == "/login"

    def test_get_renders_form_prefilled_for_owned_expense(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(
            app, user_id, amount=42.50, category="Food",
            date="2026-09-02", description="Lunch",
        )

        response = client.get(f"/expenses/{expense_id}/edit")

        assert response.status_code == 200
        assert b"<form" in response.data
        assert b"42.5" in response.data or b"42.50" in response.data
        assert b"Food" in response.data
        assert b"2026-09-02" in response.data
        assert b"Lunch" in response.data

    def test_get_nonexistent_expense_returns_404(self, client, app):
        _login(client)
        response = client.get("/expenses/999999/edit")
        assert response.status_code == 404

    def test_get_expense_owned_by_other_user_returns_404(self, client, app):
        other_user_id = _register_second_user(client, app)
        other_expense_id = _add_expense(
            app, other_user_id, amount=10.00, category="Bills",
            date="2026-09-05", description="Not yours",
        )

        # Log in as the demo user, not the owner of the expense above.
        _login(client)
        response = client.get(f"/expenses/{other_expense_id}/edit")

        assert response.status_code == 404
        assert b"Not yours" not in response.data, (
            "Another user's expense data must never leak into the response"
        )


class TestEditExpensePostValid:
    def test_post_valid_data_updates_row_without_inserting(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)
        before_count = _count_expenses(app, user_id)

        response = client.post(f"/expenses/{expense_id}/edit", data=VALID_UPDATE)

        assert response.status_code == 302, "Expected redirect on successful update"
        assert response.headers["Location"] == "/profile"

        after_count = _count_expenses(app, user_id)
        assert after_count == before_count, "Update must not insert a new row"

        row = _get_expense_row(app, expense_id)
        assert row["amount"] == pytest.approx(99.99)
        assert row["category"] == "Transport"
        assert row["date"] == "2026-09-10"
        assert row["description"] == "Updated cab ride"

    def test_post_valid_data_reflected_on_profile(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        response = client.post(
            f"/expenses/{expense_id}/edit", data=VALID_UPDATE, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Updated cab ride" in response.data or b"Transport" in response.data

    def test_post_blank_description_succeeds(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        data = dict(VALID_UPDATE)
        data["description"] = ""
        response = client.post(f"/expenses/{expense_id}/edit", data=data)

        assert response.status_code == 302
        assert response.headers["Location"] == "/profile"

        row = _get_expense_row(app, expense_id)
        assert row["description"] in ("", None)
        assert row["amount"] == pytest.approx(99.99)


class TestEditExpensePostValidation:
    @pytest.mark.parametrize(
        "amount",
        ["not-a-number", "0", "-5", "-0.01", ""],
        ids=["non_numeric", "zero", "negative", "negative_decimal", "empty"],
    )
    def test_post_invalid_amount_rerenders_with_error_and_no_update(
        self, client, app, amount
    ):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        data = dict(VALID_UPDATE)
        data["amount"] = amount
        response = client.post(f"/expenses/{expense_id}/edit", data=data)

        assert response.status_code == 200, "Expected form re-render, not redirect"
        assert b"<form" in response.data

        row = _get_expense_row(app, expense_id)
        assert row["amount"] == pytest.approx(42.50), "Row must remain unchanged"
        assert row["category"] == "Food"

    @pytest.mark.parametrize(
        "category",
        ["", "Groceries", "food", "Not A Real Category"],
        ids=["empty", "outside_fixed_list", "wrong_case", "arbitrary_text"],
    )
    def test_post_invalid_category_rerenders_with_error_and_no_update(
        self, client, app, category
    ):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        data = dict(VALID_UPDATE)
        data["category"] = category
        response = client.post(f"/expenses/{expense_id}/edit", data=data)

        assert response.status_code == 200
        assert b"<form" in response.data

        row = _get_expense_row(app, expense_id)
        assert row["category"] == "Food", "Row must remain unchanged"
        assert row["amount"] == pytest.approx(42.50)

    def test_post_empty_date_rerenders_with_error_and_no_update(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        data = dict(VALID_UPDATE)
        data["date"] = ""
        response = client.post(f"/expenses/{expense_id}/edit", data=data)

        assert response.status_code == 200
        assert b"<form" in response.data

        row = _get_expense_row(app, expense_id)
        assert row["date"] == "2026-09-02", "Row must remain unchanged"

    def test_post_invalid_data_repopulates_previously_entered_values(
        self, client, app
    ):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        data = dict(VALID_UPDATE)
        data["amount"] = "not-a-number"
        response = client.post(f"/expenses/{expense_id}/edit", data=data)

        assert response.status_code == 200
        # The previously entered (invalid) values should be re-shown, not
        # the stale DB values, so the user doesn't lose their edits.
        assert b"Updated cab ride" in response.data
        assert b"Transport" in response.data


class TestEditExpenseNotFound:
    def test_post_nonexistent_expense_returns_404(self, client, app):
        _login(client)
        response = client.post("/expenses/999999/edit", data=VALID_UPDATE)
        assert response.status_code == 404

    def test_post_expense_owned_by_other_user_returns_404_and_no_update(
        self, client, app
    ):
        other_user_id = _register_second_user(client, app)
        other_expense_id = _add_expense(
            app, other_user_id, amount=10.00, category="Bills",
            date="2026-09-05", description="Not yours",
        )

        _login(client)
        response = client.post(f"/expenses/{other_expense_id}/edit", data=VALID_UPDATE)

        assert response.status_code == 404

        row = _get_expense_row(app, other_expense_id)
        assert row["amount"] == pytest.approx(10.00), "Other user's row must be untouched"
        assert row["category"] == "Bills"


class TestEditExpenseAuthGuard:
    def test_post_redirects_when_logged_out_without_updating(self, client, app):
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        response = client.post(f"/expenses/{expense_id}/edit", data=VALID_UPDATE)

        assert response.status_code == 302
        assert response.headers["Location"] == "/login"

        row = _get_expense_row(app, expense_id)
        assert row["amount"] == pytest.approx(42.50), (
            "Anonymous POST must not modify the row"
        )
        assert row["category"] == "Food"


class TestProfileEditLinks:
    def test_recent_transactions_table_has_edit_link_per_row(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(
            app, user_id, amount=15.00, category="Other",
            date="2026-09-25", description="Recent item",
        )

        response = client.get("/profile")

        assert response.status_code == 200
        assert b"Edit" in response.data
        expected_url = f"/expenses/{expense_id}/edit".encode()
        assert expected_url in response.data, (
            "Recent Transactions table must link to the correct edit URL "
            "for each expense row"
        )
