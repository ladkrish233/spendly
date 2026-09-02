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
