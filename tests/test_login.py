import database.db as db_module


VALID = {
    "email": "test@example.com",
    "password": "securepass",
}


def test_get_login_returns_200(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_login_valid_redirects_to_profile(client):
    db_module.create_user("Test User", VALID["email"], VALID["password"])
    response = client.post("/login", data=VALID)
    assert response.status_code == 302
    assert response.location.endswith("/profile")


def test_login_valid_sets_session(client):
    db_module.create_user("Test User", VALID["email"], VALID["password"])
    with client.session_transaction() as pre:
        assert "user_id" not in pre
    client.post("/login", data=VALID)
    with client.session_transaction() as sess:
        assert isinstance(sess["user_id"], int)
        assert sess["user_name"] == "Test User"


def test_login_wrong_password_shows_error(client):
    db_module.create_user("Test User", VALID["email"], VALID["password"])
    response = client.post("/login", data={**VALID, "password": "wrongpassword"})
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_login_unknown_email_shows_error(client):
    response = client.post("/login", data=VALID)
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_login_blank_email_shows_error(client):
    response = client.post("/login", data={**VALID, "email": ""})
    assert response.status_code == 200
    assert b"required" in response.data.lower()


def test_login_blank_password_shows_error(client):
    response = client.post("/login", data={**VALID, "password": ""})
    assert response.status_code == 200
    assert b"required" in response.data.lower()


def test_login_email_repopulated_on_error(client):
    response = client.post("/login", data=VALID)
    assert VALID["email"].encode() in response.data


def test_logout_clears_session_and_redirects(client):
    db_module.create_user("Test User", VALID["email"], VALID["password"])
    client.post("/login", data=VALID)
    with client.session_transaction() as sess:
        assert "user_id" in sess
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.location.endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_logout_when_not_logged_in_redirects(client):
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_login_form_action_uses_url_for(client):
    response = client.get("/login")
    assert b'action="/login"' in response.data


def test_logged_in_user_get_login_redirects_to_landing(client):
    db_module.create_user("Test User", VALID["email"], VALID["password"])
    client.post("/login", data=VALID)
    response = client.get("/login")
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_logged_in_user_get_register_redirects_to_landing(client):
    db_module.create_user("Test User", VALID["email"], VALID["password"])
    client.post("/login", data=VALID)
    response = client.get("/register")
    assert response.status_code == 302
    assert response.location.endswith("/")
