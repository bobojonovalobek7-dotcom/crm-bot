import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient
from webapp.app import app
from webapp.auth import (
    validate_telegram_init_data,
    create_session_token,
    verify_session_token,
    SESSION_COOKIE_NAME,
)
from config import BOT_TOKEN, ADMIN_PASSWORD

client = TestClient(app)


def test_session_token_creation_and_verification():
    payload = {"telegram_id": 5341602920, "role": "super_admin"}
    token = create_session_token(payload, secret=BOT_TOKEN)
    assert token is not None
    assert "." in token

    verified = verify_session_token(token, secret=BOT_TOKEN)
    assert verified is not None
    assert verified["telegram_id"] == 5341602920
    assert verified["role"] == "super_admin"

    # Tampered token
    tampered_token = token[:-4] + "fake"
    assert verify_session_token(tampered_token, secret=BOT_TOKEN) is None


def test_telegram_init_data_validation():
    # Valid synthetic init_data test
    test_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    parsed_items = [("auth_date", "1710000000"), ("query_id", "AAG_test"), ("user", '{"id":5341602920,"first_name":"SuperAdmin"}')]
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_items))
    secret_key = hmac.new(b"WebAppData", test_token.encode("utf-8"), hashlib.sha256).digest()
    valid_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    init_data_str = f"auth_date=1710000000&query_id=AAG_test&user=%7B%22id%22%3A5341602920%2C%22first_name%22%3A%22SuperAdmin%22%7D&hash={valid_hash}"
    validated = validate_telegram_init_data(init_data_str, bot_token=test_token)
    assert validated is not None
    assert validated["user"]["id"] == 5341602920

    # Invalid hash
    fake_init_data = f"{init_data_str}_fake"
    assert validate_telegram_init_data(fake_init_data, bot_token=test_token) is None


def test_login_flow():
    # Wrong password
    res = client.post("/api/auth/login", json={"telegram_id": "5341602920", "password": "wrong"})
    assert res.status_code == 401

    # Correct password
    res_ok = client.post("/api/auth/login", json={"telegram_id": "5341602920", "password": ADMIN_PASSWORD})
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "success"
    assert data["role"] == "super_admin"
    assert SESSION_COOKIE_NAME in res_ok.cookies
