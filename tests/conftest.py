import base64
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# config.py reads the environment at import time, so this has to happen
# before anything under src.storage_broker is imported.
os.environ.pop("ACG_CONFIG", None)
os.environ["BUCKET_MAP_FILE"] = str(REPO_ROOT / "default_map.yaml")
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ.pop("AWS_REGION_NAME", None)
os.environ.pop("S3_ENDPOINT_URL", None)

from botocore.awsrequest import AWSResponse  # noqa: E402
from moto import mock_aws  # noqa: E402
from prometheus_client import REGISTRY  # noqa: E402

from src.storage_broker.storage import aws  # noqa: E402
from src.storage_broker.utils import config  # noqa: E402

REQUEST_ID = "0b2d8c4e7f9a4b1c8d3e5f6a7b8c9d0e"


def b64_identity(identity):
    return base64.b64encode(json.dumps({"identity": identity}).encode("utf-8")).decode("utf-8")


def metric(name, labels=None):
    """Current value of a prometheus sample (0.0 if it was never touched)."""
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


class MetricDelta:
    """Snapshot a metric so tests can assert on how much it moved."""

    def __init__(self, name, labels=None):
        self.name = name
        self.labels = labels
        self.start = metric(name, labels)

    @property
    def delta(self):
        return metric(self.name, self.labels) - self.start


@pytest.fixture
def metric_delta():
    return MetricDelta


class FakeMessage:
    """Stand-in for confluent_kafka.Message."""

    def __init__(self, topic, value, headers=None, error=None, partition=0):
        self._topic = topic
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        if isinstance(value, str):
            value = value.encode("utf-8")
        self._value = value
        self._headers = headers
        self._error = error
        self._partition = partition

    def topic(self):
        return self._topic

    def value(self):
        return self._value

    def headers(self):
        return self._headers

    def error(self):
        return self._error

    def partition(self):
        return self._partition


class FakeProducer:
    """Records everything produced instead of talking to Kafka."""

    def __init__(self, produce_exc=None):
        self.produced = []
        self.polls = 0
        self.flushes = 0
        self.produce_exc = produce_exc

    def poll(self, timeout):
        self.polls += 1

    def produce(self, topic, value, headers=None, callback=None):
        if self.produce_exc:
            raise self.produce_exc
        self.produced.append({"topic": topic, "value": value, "headers": headers, "callback": callback})

    def flush(self):
        self.flushes += 1

    def messages(self, topic=None):
        """Decoded payloads, optionally filtered by topic."""
        return [json.loads(p["value"]) for p in self.produced if topic is None or p["topic"] == topic]


class FakeConsumer:
    """Hands out queued messages, then sets the exit event so main() returns."""

    def __init__(self, messages, exit_event):
        self.queue = list(messages)
        self.exit_event = exit_event
        self.commits = 0

    def poll(self, timeout):
        if not self.queue:
            self.exit_event.set()
            return None
        msg = self.queue.pop(0)
        if not self.queue:
            self.exit_event.set()
        return msg

    def commit(self):
        self.commits += 1


@pytest.fixture
def fake_producer():
    return FakeProducer()


@pytest.fixture
def s3(monkeypatch):
    """A moto-backed S3 client wired into storage.aws with the standard buckets created."""
    with mock_aws():
        client = aws.make_client()
        for bucket in (
            config.STAGE_BUCKET,
            config.REJECT_BUCKET,
            "insights-buck-it-openshift",
            "insights-buck-it-ansible",
        ):
            client.create_bucket(Bucket=bucket)
        monkeypatch.setattr(aws, "s3", client)
        yield client


def object_exists(client, bucket, key):
    resp = client.list_objects_v2(Bucket=bucket, Prefix=key)
    return any(o["Key"] == key for o in resp.get("Contents", []))


class _FakeRaw:
    """Minimal raw body for AWSResponse: botocore only calls stream()."""

    def __init__(self, body):
        self._body = body

    def stream(self, **kwargs):
        yield self._body


@pytest.fixture
def fast_retries(monkeypatch):
    """Standard retry mode sleeps with exponential backoff; drop the sleeps."""
    monkeypatch.setattr("botocore.endpoint.time.sleep", lambda s: None)


@pytest.fixture
def inject_503():
    """Return a helper that 503s the first N requests of an operation.

    The handler is registered first on before-send so it runs before moto's
    own before-send hook and short-circuits the real call with a 503.
    """

    def _inject(client, operation, failures):
        calls = []

        def handler(request, **kwargs):
            calls.append(request)
            if len(calls) <= failures:
                body = b"<Error><Code>SlowDown</Code><Message>slow</Message></Error>"
                return AWSResponse(request.url, 503, headers={}, raw=_FakeRaw(body))

        client.meta.events.register_first(f"before-send.s3.{operation}", handler)
        return calls

    return _inject
