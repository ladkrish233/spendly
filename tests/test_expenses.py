import pytest

from database.db import get_db, get_user_by_email


def _login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def _count_expenses(app, user_id):
    with app.app_context():
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return row["c"]


def _demo_user_id(app):
    with app.app_context():
        user = get_user_by_email("demo@spendly.com")
    return user["id"]


VALID_EXPENSE = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-09-02",
    "description": "Lunch",
}


class TestAddExpenseGet:
    def test_get_redirects_when_logged_out(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302
        assert response.headers["Location"] == "/login"

    def test_get_renders_form_when_logged_in(self, client):
        _login(client)
        response = client.get("/expenses/add")
        assert response.status_code == 200
        assert b"<form" in response.data
        assert b"amount" in response.data
        assert b"category" in response.data
        assert b"date" in response.data


class TestAddExpensePostValid:
    def test_post_valid_data_creates_row_and_redirects(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        before = _count_expenses(app, user_id)

        response = client.post("/expenses/add", data=VALID_EXPENSE)

        assert response.status_code == 302, "Expected redirect on successful add"
        assert response.headers["Location"] == "/profile"

        after = _count_expenses(app, user_id)
        assert after == before + 1, "Expected exactly one new expense row"

        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT amount, category, date, description FROM expenses "
                "WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            conn.close()
        assert row["amount"] == pytest.approx(42.50)
        assert row["category"] == "Food"
        assert row["date"] == "2026-09-02"
        assert row["description"] == "Lunch"

    def test_post_valid_data_reflected_on_profile(self, client, app):
        _login(client)
        response = client.post(
            "/expenses/add", data=VALID_EXPENSE, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Lunch" in response.data or b"Food" in response.data

    def test_post_blank_description_succeeds(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        before = _count_expenses(app, user_id)

        data = dict(VALID_EXPENSE)
        data["description"] = ""
        response = client.post("/expenses/add", data=data)

        assert response.status_code == 302
        assert response.headers["Location"] == "/profile"
        assert _count_expenses(app, user_id) == before + 1


class TestAddExpensePostValidation:
    @pytest.mark.parametrize(
        "amount",
        ["not-a-number", "0", "-5", "-0.01", ""],
        ids=["non_numeric", "zero", "negative", "negative_decimal", "empty"],
    )
    def test_post_invalid_amount_rerenders_with_error_and_no_insert(
        self, client, app, amount
    ):
        _login(client)
        user_id = _demo_user_id(app)
        before = _count_expenses(app, user_id)

        data = dict(VALID_EXPENSE)
        data["amount"] = amount
        response = client.post("/expenses/add", data=data)

        assert response.status_code == 200, "Expected form re-render, not redirect"
        assert b"<form" in response.data
        assert _count_expenses(app, user_id) == before, "No row should be inserted"

    @pytest.mark.parametrize(
        "category",
        ["", "Groceries", "food", "Not A Real Category"],
        ids=["empty", "outside_fixed_list", "wrong_case", "arbitrary_text"],
    )
    def test_post_invalid_category_rerenders_with_error_and_no_insert(
        self, client, app, category
    ):
        _login(client)
        user_id = _demo_user_id(app)
        before = _count_expenses(app, user_id)

        data = dict(VALID_EXPENSE)
        data["category"] = category
        response = client.post("/expenses/add", data=data)

        assert response.status_code == 200
        assert b"<form" in response.data
        assert _count_expenses(app, user_id) == before

    def test_post_empty_date_rerenders_with_error_and_no_insert(self, client, app):
        _login(client)
        user_id = _demo_user_id(app)
        before = _count_expenses(app, user_id)

        data = dict(VALID_EXPENSE)
        data["date"] = ""
        response = client.post("/expenses/add", data=data)

        assert response.status_code == 200
        assert b"<form" in response.data
        assert _count_expenses(app, user_id) == before

    def test_post_invalid_data_repopulates_previously_entered_values(
        self, client, app
    ):
        _login(client)
        data = dict(VALID_EXPENSE)
        data["amount"] = "not-a-number"
        response = client.post("/expenses/add", data=data)

        assert response.status_code == 200
        # The previously entered category/description should be preserved
        # so the user doesn't have to retype the whole form.
        assert b"Lunch" in response.data


class TestAddExpenseAuthGuard:
    def test_post_redirects_when_logged_out_without_inserting(self, client, app):
        user_id = _demo_user_id(app)
        before = _count_expenses(app, user_id)

        response = client.post("/expenses/add", data=VALID_EXPENSE)

        assert response.status_code == 302
        assert response.headers["Location"] == "/login"
        assert _count_expenses(app, user_id) == before, (
            "No row should be inserted for an anonymous POST"
        )
