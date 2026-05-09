import database.db as db_module
from werkzeug.security import check_password_hash


VALID = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "securepass",
}


def test_get_register_returns_200(client):
    response = client.get("/register")
    assert response.status_code == 200


def test_register_valid_creates_user(client):
    response = client.post("/register", data=VALID)
    assert response.status_code == 302
    conn = db_module.get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (VALID["email"],)).fetchone()
    conn.close()
    assert row is not None


def test_register_password_is_hashed(client):
    client.post("/register", data=VALID)
    conn = db_module.get_db()
    row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (VALID["email"],)).fetchone()
    conn.close()
    assert row["password_hash"] != VALID["password"]
    assert check_password_hash(row["password_hash"], VALID["password"])


def test_register_sets_session(client):
    with client.session_transaction() as pre:
        assert "user_id" not in pre
    client.post("/register", data=VALID)
    with client.session_transaction() as sess:
        assert isinstance(sess["user_id"], int)
        assert sess["user_name"] == VALID["name"]


def test_register_success_redirects_to_profile(client):
    response = client.post("/register", data=VALID)
    assert response.status_code == 302
    assert response.location.endswith("/profile")


def test_register_duplicate_email_shows_error(client):
    client.post("/register", data=VALID)
    response = client.post("/register", data={**VALID, "name": "Other User"})
    assert response.status_code == 200
    assert b"An account with that email already exists." in response.data


def test_register_short_password_shows_error(client):
    response = client.post("/register", data={**VALID, "password": "short1"})
    assert response.status_code == 200
    assert b"at least 8 characters" in response.data


def test_register_empty_name_shows_error(client):
    response = client.post("/register", data={**VALID, "name": ""})
    assert response.status_code == 200
    assert b"Name is required." in response.data


def test_register_empty_email_shows_error(client):
    response = client.post("/register", data={**VALID, "email": ""})
    assert response.status_code == 200
    assert b"Email address is required." in response.data


def test_form_action_renders_correct_url(client):
    # url_for('register') renders to /register — verify the form action is present and correct
    response = client.get("/register")
    assert b'action="/register"' in response.data
