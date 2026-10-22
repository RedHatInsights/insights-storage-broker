import time
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.exceptions import ClientError

from src.storage_broker.storage import aws
from src.storage_broker.utils import config
from tests.conftest import REQUEST_ID, object_exists


@pytest.fixture
def staged(s3):
    s3.put_object(Bucket=config.STAGE_BUCKET, Key=REQUEST_ID, Body=b"payload")
    return s3


def test_copy_moves_object_to_destination(staged, metric_delta):
    success = metric_delta("storage_broker_object_copy_success_count_total", {"bucket": config.REJECT_BUCKET})
    size = metric_delta("storage_broker_payload_size_bytes_sum", {"service": "advisor"})

    aws.copy(REQUEST_ID, config.STAGE_BUCKET, config.REJECT_BUCKET, "new/key", 7, "advisor")

    assert object_exists(staged, config.REJECT_BUCKET, "new/key")
    assert staged.get_object(Bucket=config.REJECT_BUCKET, Key="new/key")["Body"].read() == b"payload"
    # it's a copy, the staged object stays put
    assert object_exists(staged, config.STAGE_BUCKET, REQUEST_ID)
    assert success.delta == 1
    assert size.delta == 7


def test_copy_records_timing(staged, metric_delta):
    timing = metric_delta("storage_broker_object_copy_time_seconds_count")
    aws.copy(REQUEST_ID, config.STAGE_BUCKET, config.REJECT_BUCKET, REQUEST_ID, 7, "advisor")
    assert timing.delta == 1


def test_copy_missing_source_counts_error(s3, metric_delta):
    error = metric_delta("storage_broker_object_copy_error_count_total", {"bucket": config.REJECT_BUCKET})
    with pytest.raises(Exception):
        aws.copy("missing", config.STAGE_BUCKET, config.REJECT_BUCKET, "missing", 1, "advisor")
    assert error.delta == 1
    assert not object_exists(s3, config.REJECT_BUCKET, "missing")


def test_copy_failure_is_reported_to_caller(s3):
    with pytest.raises(Exception):
        aws.copy("missing", config.STAGE_BUCKET, config.REJECT_BUCKET, "missing", 1, "advisor")


def test_copy_accepts_string_size(staged):
    aws.copy(REQUEST_ID, config.STAGE_BUCKET, config.REJECT_BUCKET, REQUEST_ID, "7", "advisor")
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)


def test_copy_records_numeric_string_size(staged, metric_delta):
    size = metric_delta("storage_broker_payload_size_bytes_sum", {"service": "advisor"})
    aws.copy(REQUEST_ID, config.STAGE_BUCKET, config.REJECT_BUCKET, REQUEST_ID, "7", "advisor")
    assert size.delta == 7


def test_copy_ignores_unparseable_size(staged, metric_delta):
    count = metric_delta("storage_broker_payload_size_bytes_count", {"service": "advisor"})
    aws.copy(REQUEST_ID, config.STAGE_BUCKET, config.REJECT_BUCKET, REQUEST_ID, "big", "advisor")
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)
    assert count.delta == 0


def test_copy_accepts_missing_size(staged):
    aws.copy(REQUEST_ID, config.STAGE_BUCKET, config.REJECT_BUCKET, REQUEST_ID, None, "advisor")
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)


def test_check_key_returns_none_when_present(staged):
    assert aws.check_key(config.STAGE_BUCKET, REQUEST_ID) is None


def test_check_key_returns_client_error_when_missing(s3):
    err = aws.check_key(config.STAGE_BUCKET, REQUEST_ID)
    assert isinstance(err, ClientError)
    assert err.response["Error"]["Code"] == "404"


def test_get_url_returns_presigned_url(staged):
    now = int(time.time())
    url = aws.get_url(config.STAGE_BUCKET, REQUEST_ID, 30)
    parsed = urlparse(url)
    assert REQUEST_ID in parsed.path
    assert config.STAGE_BUCKET in url
    query = parse_qs(parsed.query)
    # boto3's default presigner for this client uses SigV2 query auth (absolute epoch Expires)
    assert now + 30 <= int(query["Expires"][0]) <= now + 35


def test_get_url_propagates_client_error(monkeypatch):
    class Boom:
        def generate_presigned_url(self, *args, **kwargs):
            raise ClientError({"Error": {"Code": "500", "Message": "boom"}}, "GeneratePresignedUrl")

    monkeypatch.setattr(aws, "s3", Boom())
    with pytest.raises(ClientError):
        aws.get_url(config.STAGE_BUCKET, REQUEST_ID, 30)
