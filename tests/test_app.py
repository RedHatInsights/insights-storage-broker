import json
import re
from threading import Event

import attr
import pytest
from confluent_kafka import KafkaError

from src.storage_broker import TrackerMessage, app
from src.storage_broker.normalizers import Openshift, Validation
from src.storage_broker.utils import config
from tests.conftest import (
    REQUEST_ID,
    FakeConsumer,
    FakeMessage,
    FakeProducer,
    b64_identity,
    object_exists,
)

VALIDATION_TOPIC = config.VALIDATION_TOPIC
ANNOUNCE_TOPIC = config.INGRESS_TOPIC
TRACKER_TOPIC = config.TRACKER_TOPIC

OPENSHIFT_IDENTITY = {
    "account_number": "000001",
    "org_id": "123456",
    "internal": {"org_id": "123456"},
    "system": {"cluster_id": "cluster-1"},
}


def validation_msg(validation="success", **overrides):
    msg = {
        "account": "000001",
        "org_id": "123456",
        "reporter": "puptoo",
        "request_id": REQUEST_ID,
        "system_id": "abdc-1234",
        "hostname": "hostname",
        "validation": validation,
        "service": "advisor",
        "reason": "",
        "size": 7,
    }
    msg.update(overrides)
    return msg


def announce_msg(service="openshift", identity=OPENSHIFT_IDENTITY, **overrides):
    msg = {
        "b64_identity": b64_identity(identity),
        "service": service,
        "request_id": REQUEST_ID,
        "size": 7,
    }
    msg.update(overrides)
    return msg


def announce(service="openshift", header_service=None, **overrides):
    header_service = service if header_service is None else header_service
    headers = [("service", header_service.encode("utf-8"))] if header_service else None
    return FakeMessage(ANNOUNCE_TOPIC, announce_msg(service, **overrides), headers=headers)


@pytest.fixture
def producer(monkeypatch):
    p = FakeProducer()
    monkeypatch.setattr(app, "producer", p)
    return p


@pytest.fixture
def run_main(monkeypatch):
    """Run app.main() over a list of messages and return (consumer, producer)."""
    monkeypatch.setattr(config, "PROMETHEUS", "False")
    monkeypatch.setattr(config, "KAFKA_BROKER", None)

    def _run(messages):
        exit_event = Event()
        consumer = FakeConsumer(messages, exit_event)
        producer = FakeProducer()
        monkeypatch.setattr(app.consume, "init_consumer", lambda logger: consumer)
        monkeypatch.setattr(app.produce, "init_producer", lambda: producer)
        app.main(exit_event=exit_event)
        return consumer, producer

    return _run


@pytest.fixture
def staged(s3):
    s3.put_object(Bucket=config.STAGE_BUCKET, Key=REQUEST_ID, Body=b"payload")
    return s3


def statuses(producer):
    return [(m["status"], m["status_msg"]) for m in producer.messages(TRACKER_TOPIC)]


def keys_in(client, bucket):
    return [o["Key"] for o in client.list_objects_v2(Bucket=bucket).get("Contents", [])]


# --- service_check ------------------------------------------------------------


@pytest.mark.parametrize("service", config.MONITORED_SERVICES)
def test_service_check_monitored(service):
    assert app.service_check(FakeMessage(ANNOUNCE_TOPIC, "{}", headers=[("service", service.encode())]))


def test_service_check_unmonitored():
    assert not app.service_check(FakeMessage(ANNOUNCE_TOPIC, "{}", headers=[("service", b"advisor")]))


@pytest.mark.parametrize("headers", [None, [], [("other", b"x")]])
def test_service_check_without_service_header(headers):
    assert not app.service_check(FakeMessage(ANNOUNCE_TOPIC, "{}", headers=headers))


# --- get_bucket / normalize ---------------------------------------------------


@pytest.mark.parametrize(
    "service,bucket,key",
    [
        ("openshift", "insights-buck-it-openshift", "123456/cluster-1/20260101120000-rid"),
        ("ansible", "insights-buck-it-ansible", "123456/cluster-1/20260101120000-rid"),
        ("tower", "insights-upload-tower-analytics-stage", "123456/rid"),
        ("automation-hub", "insights-upload-tower-analytics-stage", "123456/rid"),
        ("pinakes", "insights-upload-tower-analytics-stage", "123456/rid"),
    ],
)
def test_get_bucket_for_every_default_map_service(service, bucket, key):
    data = Openshift(
        size=7,
        request_id="rid",
        cluster_id="cluster-1",
        org_id="123456",
        account="000001",
        service=service,
        timestamp="20260101120000",
    )
    assert app.get_bucket(config.BUCKET_MAP[ANNOUNCE_TOPIC], data) == (key, bucket)


def test_get_bucket_unknown_service_raises():
    data = Openshift(service="advisor", org_id="1", request_id="rid")
    with pytest.raises(KeyError):
        app.get_bucket(config.BUCKET_MAP[ANNOUNCE_TOPIC], data)


def test_get_bucket_format_with_unknown_field_raises():
    _map = {"services": {"svc": {"format": "{nope}", "bucket": "b"}}}
    with pytest.raises(KeyError):
        app.get_bucket(_map, Openshift(service="svc"))


def test_normalize_uses_topic_normalizer():
    data = app.normalize(config.BUCKET_MAP[VALIDATION_TOPIC], validation_msg(), service="advisor")
    assert isinstance(data, Validation)


def test_normalize_uses_service_normalizer():
    data = app.normalize(config.BUCKET_MAP[ANNOUNCE_TOPIC], announce_msg(), service="openshift")
    assert isinstance(data, Openshift)
    assert data.cluster_id == "cluster-1"


# --- send_message -------------------------------------------------------------


def test_send_message_produces_with_delivery_callback(producer):
    app.send_message(TRACKER_TOPIC, b'{"a": 1}', request_id="rid")
    assert producer.polls == 1
    [produced] = producer.produced
    assert produced["topic"] == TRACKER_TOPIC
    assert produced["value"] == b'{"a": 1}'
    assert produced["headers"] is None
    assert produced["callback"].keywords == {"request_id": "rid"}


def test_send_message_passes_headers(producer):
    app.send_message(TRACKER_TOPIC, b"{}", headers=[("h", b"v")])
    assert producer.produced[0]["headers"] == [("h", b"v")]


def test_kafka_error_is_not_an_exception_class():
    # send_message does `except KafkaError`, which can never match anything
    assert not issubclass(KafkaError, BaseException)


@pytest.mark.xfail(raises=BufferError, reason="BUG: send_message catches KafkaError, which is not an exception class, so produce errors escape")
def test_send_message_handles_produce_errors(monkeypatch):
    monkeypatch.setattr(app, "producer", FakeProducer(produce_exc=BufferError("queue full")))
    app.send_message(TRACKER_TOPIC, b"{}", request_id="rid")


# --- handle_validation --------------------------------------------------------


def handle(msg):
    data = Validation.from_json(msg)
    app.handle_validation(data, TrackerMessage(attr.asdict(data)))


def test_handle_validation_success(producer, s3):
    handle(validation_msg("success"))
    assert statuses(producer) == [
        ("received", "received validation response from advisor"),
        ("success", "payload validation successful for advisor payload"),
    ]
    assert keys_in(s3, config.REJECT_BUCKET) == []
    assert all(p["callback"].keywords["request_id"] == REQUEST_ID for p in producer.produced)


def test_handle_validation_failure_copies_to_reject_bucket(producer, staged):
    handle(validation_msg("failure"))
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)
    assert statuses(producer) == [
        ("received", "received validation response from advisor"),
        ("success", f"copied payload to {config.REJECT_BUCKET}"),
    ]


def test_handle_validation_invalid_status(producer, s3, metric_delta):
    invalid = metric_delta("storage_broker_invalid_status_count_total", {"service": "advisor"})
    handle(validation_msg("maybe"))
    assert invalid.delta == 1
    assert statuses(producer) == [
        ("received", "received validation response from advisor"),
        ("error", "invalid validation response: maybe from advisor"),
    ]
    assert keys_in(s3, config.REJECT_BUCKET) == []


def test_handle_validation_tracker_carries_ids(producer, s3):
    handle(validation_msg("success"))
    for msg in producer.messages(TRACKER_TOPIC):
        assert msg["service"] == "storage-broker"
        assert msg["request_id"] == REQUEST_ID
        assert msg["account"] == "000001"
        assert msg["org_id"] == "123456"


@pytest.mark.xfail(raises=AssertionError, reason="BUG: aws.copy swallows S3 errors so a failed reject copy is still reported as success")
def test_handle_validation_failure_reports_copy_error(producer, s3):
    # nothing staged, so the copy to the reject bucket fails
    handle(validation_msg("failure"))
    assert statuses(producer)[-1][0] == "error"


# --- main loop ----------------------------------------------------------------


def test_main_validation_success(run_main, s3, metric_delta):
    consumed = metric_delta("storage_broker_message_consume_count_total")
    consumer, producer = run_main([FakeMessage(VALIDATION_TOPIC, validation_msg("success"))])
    assert statuses(producer) == [
        ("received", "received message from advisor"),
        ("received", "received validation response from advisor"),
        ("success", "payload validation successful for advisor payload"),
    ]
    assert consumed.delta == 1
    assert consumer.commits >= 1
    assert producer.flushes >= 1


def test_main_validation_messages_ignore_service_header(run_main, s3):
    msg = FakeMessage(VALIDATION_TOPIC, validation_msg("success"), headers=[("service", b"advisor")])
    _, producer = run_main([msg])
    assert len(statuses(producer)) == 3


def test_main_validation_failure_copies_to_reject(run_main, staged):
    _, producer = run_main([FakeMessage(VALIDATION_TOPIC, validation_msg("failure"))])
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)
    assert statuses(producer)[-1] == ("success", f"copied payload to {config.REJECT_BUCKET}")


def test_main_validation_failure_without_size(run_main, staged):
    msg = validation_msg("failure")
    del msg["size"]
    run_main([FakeMessage(VALIDATION_TOPIC, msg)])
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)


def test_main_validation_failure_with_string_size(run_main, staged):
    run_main([FakeMessage(VALIDATION_TOPIC, validation_msg("failure", size="7"))])
    assert object_exists(staged, config.REJECT_BUCKET, REQUEST_ID)


@pytest.mark.parametrize("service,bucket", [("openshift", "insights-buck-it-openshift"), ("ansible", "insights-buck-it-ansible")])
def test_main_announce_copies_to_service_bucket(run_main, staged, service, bucket):
    _, producer = run_main([announce(service)])

    [key] = keys_in(staged, bucket)
    assert re.match(rf"^123456/cluster-1/\d{{14}}-{REQUEST_ID}$", key)
    assert statuses(producer) == [
        ("received", f"received message from {service}"),
        ("success", f"copied payload to {bucket} as {key}"),
    ]


def test_main_announce_unmonitored_service_is_skipped(run_main, staged, metric_delta):
    consumed = metric_delta("storage_broker_message_consume_count_total")
    _, producer = run_main([announce("advisor")])
    assert producer.produced == []
    assert consumed.delta == 0


def test_main_announce_without_service_header_is_skipped(run_main, staged):
    _, producer = run_main([announce("openshift", header_service="")])
    assert producer.produced == []
    assert keys_in(staged, "insights-buck-it-openshift") == []


def test_main_header_decides_filtering_not_body(run_main, staged):
    # body says openshift but the header says advisor: skipped
    _, producer = run_main([announce("openshift", header_service="advisor")])
    assert producer.produced == []


def test_main_monitored_header_without_bucket_mapping(run_main, staged, metric_delta, monkeypatch):
    monkeypatch.setattr(config, "MONITORED_SERVICES", ["openshift", "unmapped"])
    unpack = metric_delta("storage_broker_message_json_upack_error_count_total", {"topic": ANNOUNCE_TOPIC})
    _, producer = run_main([announce("unmapped")])
    assert unpack.delta == 1
    assert statuses(producer) == [("received", "received message from unmapped")]


def test_main_skips_empty_polls(run_main, s3):
    consumer, producer = run_main([None, FakeMessage(VALIDATION_TOPIC, validation_msg())])
    assert len(statuses(producer)) == 3


def test_main_consumer_error(run_main, metric_delta):
    errors = metric_delta("storage_broker_message_consume_error_count_total")
    _, producer = run_main([FakeMessage(VALIDATION_TOPIC, b"", error="broker down")])
    assert errors.delta == 1
    assert producer.produced == []


def test_main_undecodable_message(run_main, metric_delta):
    errors = metric_delta("storage_broker_message_consume_error_count_total")
    consumed = metric_delta("storage_broker_message_consume_count_total")
    consumer, producer = run_main([FakeMessage(VALIDATION_TOPIC, b"not json")])
    assert errors.delta == 1
    assert consumed.delta == 0
    assert producer.produced == []
    assert consumer.commits >= 1


def test_main_normalization_failure(run_main, metric_delta):
    unpack = metric_delta("storage_broker_message_json_upack_error_count_total", {"topic": VALIDATION_TOPIC})
    msg = validation_msg()
    del msg["validation"]
    _, producer = run_main([FakeMessage(VALIDATION_TOPIC, msg)])
    assert unpack.delta == 1
    assert statuses(producer) == [("received", "received message from advisor")]


def test_main_continues_after_bad_message(run_main, s3):
    _, producer = run_main([
        FakeMessage(VALIDATION_TOPIC, b"not json"),
        FakeMessage(VALIDATION_TOPIC, validation_msg("success")),
    ])
    assert statuses(producer)[-1][0] == "success"


def test_main_commits_and_flushes_on_exit(run_main):
    consumer, producer = run_main([])
    assert consumer.commits == 1
    assert producer.flushes == 1


def test_main_starts_prometheus_and_writes_cert(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "PROMETHEUS", "True")
    monkeypatch.setattr(app, "start_prometheus", lambda: calls.append("prometheus"))
    monkeypatch.setattr(app, "write_cert", lambda cert: calls.append(cert))

    class Broker:
        cacert = "CERT"

    monkeypatch.setattr(config, "KAFKA_BROKER", Broker())
    exit_event = Event()
    monkeypatch.setattr(app.consume, "init_consumer", lambda logger: FakeConsumer([], exit_event))
    monkeypatch.setattr(app.produce, "init_producer", FakeProducer)
    app.main(exit_event=exit_event)
    assert calls == ["prometheus", "CERT"]


def test_write_cert(monkeypatch, tmp_path):
    target = tmp_path / "cacert.pem"
    real_open = open
    monkeypatch.setattr(app, "open", lambda path, mode: real_open(target, mode), raising=False)
    app.write_cert("CERT")
    assert target.read_text() == "CERT"


def test_start_prometheus(monkeypatch):
    ports = []
    monkeypatch.setattr(app, "start_http_server", ports.append)
    app.start_prometheus()
    assert ports == [config.PROMETHEUS_PORT]


def test_handle_signal_sets_exit_event(monkeypatch):
    event = Event()
    monkeypatch.setattr(app, "event", event)
    app.handle_signal(15, None)
    assert event.is_set()


def test_tracker_messages_are_valid_json(run_main, staged):
    _, producer = run_main([announce("openshift")])
    for produced in producer.produced:
        assert produced["topic"] == TRACKER_TOPIC
        json.loads(produced["value"])
