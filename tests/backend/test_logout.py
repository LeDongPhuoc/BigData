import pytest

pytestmark = pytest.mark.integration


def test_logout_refresh_body_must_belong_to_access_session(client, register):
    actor, user = register()
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers=actor,
            json={
                "refresh_token": "invalid-session-key." + "x" * 48,
            },
        ).status_code
        == 401
    )
    different_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": user["email"],
            "password": "Integration passphrase 2026!",
        },
    ).json()
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers=actor,
            json={
                "refresh_token": different_login["refresh_token"],
            },
        ).status_code
        == 403
    )
    assert client.get("/api/v1/auth/me", headers=actor).status_code == 200
    owned = {"Authorization": "Bearer " + different_login["access_token"]}
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers=owned,
            json={
                "refresh_token": different_login["refresh_token"],
            },
        ).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me", headers=owned).status_code == 401
