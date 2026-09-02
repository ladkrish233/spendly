from database.db import get_user_by_email, get_db


def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_profile_renders_when_logged_in(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get("/profile")
    assert response.status_code == 200
    assert b"Demo User" in response.data
    assert b"demo@spendly.com" in response.data


def test_profile_shows_expense_summary_for_seeded_user(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get("/profile")
    assert response.status_code == 200
    assert b"Total spent" in response.data
    assert b"Transactions" in response.data
    assert b"Top category" in response.data
    assert b"Recent Transactions" in response.data
    assert b"By Category" in response.data
    assert b"No transactions yet" not in response.data
    assert b"No expenses yet" not in response.data


def test_profile_shows_empty_states_for_new_user_with_no_expenses(client):
    client.post(
        "/register",
        data={
            "name": "Fresh User",
            "email": "fresh@example.com",
            "password": "supersecret",
        },
    )
    response = client.get("/profile")
    assert response.status_code == 200
    assert "₹0.00".encode() in response.data
    assert b"No transactions yet" in response.data
    assert b"No expenses yet" in response.data


def test_profile_redirects_when_session_user_deleted(client, app):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )

    user = get_user_by_email("demo@spendly.com")
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (user["id"],))
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        conn.commit()
        conn.close()

    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_profile_filters_expenses_to_date_range(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-09-05", "end_date": "2026-09-15"},
    )
    assert response.status_code == 200
    # Only Bills (120.00), Health (35.75), Entertainment (60.00),
    # Shopping (89.99) fall inside 2026-09-05..2026-09-15 -> total 305.74
    assert "₹305.74".encode() in response.data
    assert b">4<" in response.data
    assert b"Bills" in response.data
    # Out-of-range expenses must not appear in the filtered recent list
    assert b"Coffee and breakfast" not in response.data
    assert b"Groceries" not in response.data


def test_profile_with_no_filter_shows_all_time_data(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get("/profile")
    assert response.status_code == 200
    # All 8 seeded expenses total 406.64
    assert "₹406.64".encode() in response.data
    assert b"Showing expenses" not in response.data
    assert b"profile-filter-clear" not in response.data


def test_profile_date_inputs_repopulate_from_query_string(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-09-05", "end_date": "2026-09-15"},
    )
    assert response.status_code == 200
    assert b'id="start_date" name="start_date" value="2026-09-05"' in response.data
    assert b'id="end_date" name="end_date" value="2026-09-15"' in response.data


def test_profile_clear_link_shown_only_when_filter_active(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )

    unfiltered = client.get("/profile")
    assert b"profile-filter-clear" not in unfiltered.data

    filtered = client.get(
        "/profile",
        query_string={"start_date": "2026-09-05", "end_date": "2026-09-15"},
    )
    assert b"profile-filter-clear" in filtered.data
    assert b"Showing expenses" in filtered.data


def test_profile_invalid_range_falls_back_to_all_time(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-09-15", "end_date": "2026-09-01"},
    )
    assert response.status_code == 200
    assert "₹406.64".encode() in response.data
    assert b"Showing expenses" not in response.data
    assert b"profile-filter-clear" not in response.data


def test_profile_malformed_date_falls_back_to_all_time(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "not-a-date", "end_date": "2026-09-30"},
    )
    assert response.status_code == 200
    assert "₹406.64".encode() in response.data
    assert b"Showing expenses" not in response.data


def test_profile_filtered_range_with_no_matches_shows_empty_state(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-10-01", "end_date": "2026-10-31"},
    )
    assert response.status_code == 200
    assert "₹0.00".encode() in response.data
    assert b"No transactions yet" in response.data
    assert b"No expenses yet" in response.data
    assert b"Showing expenses" in response.data


def test_profile_redirects_when_logged_out_with_filter_params(client):
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-09-01", "end_date": "2026-09-30"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_profile_filter_with_only_start_date_is_open_ended(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-09-12"},
    )
    assert response.status_code == 200
    # Expenses from 2026-09-12 onward: Entertainment(60.00) + Shopping(89.99)
    # + Other(15.00) + Food/Groceries(28.40) = 193.39
    assert "₹193.39".encode() in response.data
    assert b">4<" in response.data
    assert b"Shopping" in response.data  # highest single-category total
    assert b"Showing expenses" in response.data
    assert b"from 2026-09-12 onward" in response.data
    assert b"profile-filter-clear" in response.data
    # Out-of-range (before the start date) expenses must be excluded
    assert b"Coffee and breakfast" not in response.data
    assert b"Monthly metro pass" not in response.data


def test_profile_filter_with_only_end_date_is_open_ended(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"end_date": "2026-09-05"},
    )
    assert response.status_code == 200
    # Expenses up to 2026-09-05: Food(12.50) + Transport(45.00) + Bills(120.00) = 177.50
    assert "₹177.50".encode() in response.data
    assert b">3<" in response.data
    assert b"Bills" in response.data  # highest single-category total
    assert b"Showing expenses" in response.data
    assert b"up to 2026-09-05" in response.data
    assert b"profile-filter-clear" in response.data
    # Out-of-range (after the end date) expenses must be excluded
    assert b"Groceries" not in response.data


def test_profile_filter_with_equal_start_and_end_date_is_valid(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get(
        "/profile",
        query_string={"start_date": "2026-09-08", "end_date": "2026-09-08"},
    )
    assert response.status_code == 200
    # A single-day range (start == end) is not "after" and must not be
    # treated as an invalid range - only that day's expense should show.
    assert "₹35.75".encode() in response.data
    assert b">1<" in response.data
    assert b"Health" in response.data
    assert b"Showing expenses" in response.data
    assert b"from 2026-09-08 to 2026-09-08" in response.data
