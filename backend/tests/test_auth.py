def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "test@example.com"
    assert "id" in data


def test_duplicate_register_rejected(client):
    user = {
        "email": "duplicate@example.com",
        "password": "TestPassword123",
    }

    first_response = client.post(
        "/auth/register",
        json=user,
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/auth/register",
        json=user,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Email already registered"


def test_login_success(client):
    credentials = {
        "email": "login@example.com",
        "password": "TestPassword123",
    }

    register_response = client.post(
        "/auth/register",
        json=credentials,
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login-json",
        json=credentials,
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_wrong_password_rejected(client):
    credentials = {
        "email": "wrong-password@example.com",
        "password": "CorrectPassword123",
    }

    register_response = client.post(
        "/auth/register",
        json=credentials,
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login-json",
        json={
            "email": credentials["email"],
            "password": "WrongPassword123",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/files/")

    assert response.status_code == 401


def test_invalid_token_rejected(client):
    response = client.get(
        "/files/",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}