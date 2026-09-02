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


class TestDeleteExpenseGetMethod:
    def test_get_is_not_a_valid_way_to_delete(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        response = client.get(f"/expenses/{expense_id}/delete")

        assert response.status_code == 405, (
            "GET must no longer be a valid method for the delete route"
        )
        assert b"coming in Step 9" not in response.data

        row = _get_expense_row(app, expense_id)
        assert row is not None, "A GET request must never delete the row"


class TestDeleteExpenseAuthGuard:
    def test_post_redirects_when_logged_out_without_deleting(self, client, app):
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)

        response = client.post(f"/expenses/{expense_id}/delete")

        assert response.status_code == 302
        assert response.headers["Location"] == "/login"

        row = _get_expense_row(app, expense_id)
        assert row is not None, "Anonymous POST must not delete the row"


class TestDeleteExpenseNotFound:
    def test_post_nonexistent_expense_returns_404(self, client, app):
        _login(client)
        response = client.post("/expenses/999999/delete")
        assert response.status_code == 404

    def test_post_expense_owned_by_other_user_returns_404_and_no_delete(
        self, client, app
    ):
        other_user_id = _register_second_user(client, app)
        other_expense_id = _add_expense(
            app, other_user_id, amount=10.00, category="Bills",
            date="2026-09-05", description="Not yours",
        )

        # Log in as the demo user, not the owner of the expense above.
        _login(client)
        response = client.post(f"/expenses/{other_expense_id}/delete")

        assert response.status_code == 404

        row = _get_expense_row(app, other_expense_id)
        assert row is not None, "Another user's row must not be deleted"
        assert row["amount"] == pytest.approx(10.00)
        assert row["category"] == "Bills"


class TestDeleteExpensePostValid:
    def test_post_owned_expense_removes_row_and_redirects_to_profile(
        self, client, app
    ):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(app, user_id)
        before_count = _count_expenses(app, user_id)

        response = client.post(f"/expenses/{expense_id}/delete")

        assert response.status_code == 302, "Expected redirect on successful delete"
        assert response.headers["Location"] == "/profile"

        after_count = _count_expenses(app, user_id)
        assert after_count == before_count - 1, "Delete must remove exactly one row"

        row = _get_expense_row(app, expense_id)
        assert row is None, "Row must no longer exist in the expenses table"

    def test_post_does_not_delete_other_rows_for_same_user(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        keep_id = _add_expense(
            app, user_id, amount=20.00, category="Food",
            date="2026-09-03", description="Keep me",
        )
        delete_id = _add_expense(
            app, user_id, amount=30.00, category="Transport",
            date="2026-09-04", description="Delete me",
        )

        response = client.post(f"/expenses/{delete_id}/delete")

        assert response.status_code == 302
        assert response.headers["Location"] == "/profile"

        deleted_row = _get_expense_row(app, delete_id)
        kept_row = _get_expense_row(app, keep_id)
        assert deleted_row is None
        assert kept_row is not None, "Only the targeted row should be removed"


class TestProfileReflectsDeletion:
    def test_profile_totals_category_and_transactions_exclude_deleted_expense(
        self, client, app
    ):
        client.post(
            "/register",
            data={
                "name": "Delete Tester",
                "email": "deletetester@spendly.com",
                "password": "delpass123",
            },
        )
        with app.app_context():
            user = get_user_by_email("deletetester@spendly.com")
        user_id = user["id"]

        food_id = _add_expense(
            app, user_id, amount=100.00, category="Food",
            date="2026-09-01", description="Groceries run",
        )
        _add_expense(
            app, user_id, amount=50.00, category="Transport",
            date="2026-09-02", description="Cab ride",
        )

        # Before deletion: total 150.00, 2 transactions, top category Food.
        before = client.get("/profile")
        assert before.status_code == 200
        assert "₹150.00".encode() in before.data
        assert b">2<" in before.data
        assert b"Food" in before.data
        assert b"Groceries run" in before.data

        delete_response = client.post(f"/expenses/{food_id}/delete")
        assert delete_response.status_code == 302
        assert delete_response.headers["Location"] == "/profile"

        after = client.get("/profile")
        assert after.status_code == 200
        assert "₹50.00".encode() in after.data, (
            "Total must be recalculated without the deleted expense"
        )
        assert b">1<" in after.data, "Transaction count must decrease by one"
        assert b"Transport" in after.data, "Top category must recompute"
        assert b"Groceries run" not in after.data, (
            "The deleted expense's description must not appear in Recent Transactions"
        )


class TestProfileDeleteAction:
    def test_recent_transactions_table_has_delete_form_per_row(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(
            app, user_id, amount=15.00, category="Other",
            date="2026-09-25", description="Recent item",
        )

        response = client.get("/profile")

        assert response.status_code == 200
        expected_action = f'action="/expenses/{expense_id}/delete"'.encode()
        assert expected_action in response.data, (
            "Each Recent Transactions row must contain a delete form posting "
            "to the correct expense's delete URL"
        )
        assert b'method="POST"' in response.data, (
            "The delete action must be a POST form, not a GET link"
        )
        assert b"onsubmit=\"return confirm(" in response.data, (
            "The delete form must trigger a browser confirmation dialog "
            "before submitting"
        )
        assert b"Delete" in response.data

    def test_delete_form_appears_alongside_edit_link(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        expense_id = _add_expense(
            app, user_id, amount=25.00, category="Health",
            date="2026-09-26", description="Checkup",
        )

        response = client.get("/profile")

        assert response.status_code == 200
        edit_url = f"/expenses/{expense_id}/edit".encode()
        delete_action = f'action="/expenses/{expense_id}/delete"'.encode()
        assert edit_url in response.data, "Edit link must still be present"
        assert delete_action in response.data, (
            "Delete form must be present alongside the Edit link"
        )
