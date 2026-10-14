import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.storage_broker import api
from src.storage_broker.utils import config
from tests.conftest import REQUEST_ID


@pytest.fixture
def client():
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c


def test_health_check(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_archive_url_missing_request_id(client):
    resp = client.get("/archive/url/")
    assert resp.status_code == 400
    assert resp.get_json() == {"message": "request_id param missing"}


@pytest.mark.parametrize("request_id", ["abc", "123", "not-a-uuid", "0b2d8c4e7f9a"])
def test_archive_url_invalid_request_id(client, request_id):
    resp = client.get("/archive/url/", query_string={"request_id": request_id})
    assert resp.status_code == 400
    assert resp.get_json() == {"message": "invalid request_id"}


def test_archive_url_unknown_key(client, s3):
    resp = client.get("/archive/url/", query_string={"request_id": REQUEST_ID})
    assert resp.status_code == 400
    assert resp.get_json() == {"message": "Not Found - 404"}


@pytest.mark.parametrize("request_id", [REQUEST_ID, str(uuid.UUID(REQUEST_ID))])
def test_archive_url_success(client, s3, request_id):
    s3.put_object(Bucket=config.STAGE_BUCKET, Key=request_id, Body=b"payload")
    before = datetime.now(timezone.utc).replace(microsecond=0)

    resp = client.get("/archive/url/", query_string={"request_id": request_id})

    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"request_id", "url", "timeout"}
    assert body["request_id"] == request_id
    assert request_id in body["url"]
    assert config.STAGE_BUCKET in body["url"]

    timeout = datetime.fromisoformat(body["timeout"])
    assert timeout.tzinfo is not None
    expected = before + timedelta(seconds=config.API_URL_EXPIRY)
    assert expected <= timeout <= expected + timedelta(seconds=5)


def test_archive_url_without_trailing_slash_redirects(client):
    resp = client.get("/archive/url", query_string={"request_id": REQUEST_ID})
    assert resp.status_code == 308


def test_archive_url_records_metrics(client, s3, metric_delta):
    s3.put_object(Bucket=config.STAGE_BUCKET, Key=REQUEST_ID, Body=b"payload")
    key_check = metric_delta("storage_broker_storage_key_check_time_seconds_count")
    presign = metric_delta("storage_broker_presigned_url_gen_time_seconds_count")
    client.get("/archive/url/", query_string={"request_id": REQUEST_ID})
    assert key_check.delta == 1
    assert presign.delta == 1


def test_main_runs_flask(monkeypatch):
    calls = []
    monkeypatch.setattr(api.app, "run", lambda **kwargs: calls.append(kwargs))
    api.main()
    assert calls == [{"host": config.API_LISTEN_ADDRESS, "port": config.API_PORT}]
