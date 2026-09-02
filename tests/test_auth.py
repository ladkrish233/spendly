def test_login_get_renders_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_login_valid_credentials_redirects_to_profile(client):
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"


def test_login_invalid_credentials_shows_error(client):
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "wrong-password"},
    )
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_register_creates_user_and_logs_in(client):
    response = client.post(
        "/register",
        data={
            "name": "New User",
            "email": "newuser@example.com",
            "password": "supersecret",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"


def test_register_duplicate_email_shows_error(client):
    response = client.post(
        "/register",
        data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "password": "demo123",
        },
    )
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_logout_clears_session(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    profile_response = client.get("/profile")
    assert profile_response.status_code == 302
    assert profile_response.headers["Location"] == "/login"
