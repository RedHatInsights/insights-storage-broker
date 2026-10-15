import json
import logging
from types import SimpleNamespace

import pytest

from src.storage_broker.mq import common, consume, produce
from src.storage_broker.utils import config
from tests.conftest import FakeMessage


def kafka_config(broker=None, servers=("kafka:29092",)):
    return SimpleNamespace(KAFKA_BROKER=broker, BOOTSTRAP_SERVERS=list(servers))


# --- build_confluent_kafka_config ---------------------------------------------


def test_kafka_config_plain():
    assert common.build_confluent_kafka_config(kafka_config(servers=["a:1", "b:2"])) == {
        "bootstrap.servers": "a:1,b:2",
    }


def test_kafka_config_with_cacert_only():
    broker = SimpleNamespace(cacert="CERT", sasl=None)
    assert common.build_confluent_kafka_config(kafka_config(broker)) == {
        "bootstrap.servers": "kafka:29092",
        "ssl.ca.location": "/tmp/cacert.pem",
    }


def test_kafka_config_with_sasl():
    sasl = SimpleNamespace(
        username="user",
        password="pass",
        securityProtocol="SASL_SSL",
        saslMechanism="SCRAM-SHA-512",
    )
    broker = SimpleNamespace(cacert="CERT", sasl=sasl)
    assert common.build_confluent_kafka_config(kafka_config(broker)) == {
        "bootstrap.servers": "kafka:29092",
        "ssl.ca.location": "/tmp/cacert.pem",
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "SCRAM-SHA-512",
        "sasl.username": "user",
        "sasl.password": "pass",
    }


def test_kafka_config_sasl_without_username_is_ignored():
    sasl = SimpleNamespace(username=None, password=None, securityProtocol="SASL_SSL", saslMechanism="PLAIN")
    broker = SimpleNamespace(cacert=None, sasl=sasl)
    assert common.build_confluent_kafka_config(kafka_config(broker)) == {"bootstrap.servers": "kafka:29092"}


# --- init_consumer / init_producer --------------------------------------------


class RecordingConsumer:
    def __init__(self, conf):
        self.conf = conf
        self.topics = None

    def subscribe(self, topics):
        self.topics = topics


def test_init_consumer(monkeypatch):
    monkeypatch.setattr(consume, "Consumer", RecordingConsumer)
    consumer = consume.init_consumer(logging.getLogger("test"))
    assert consumer.topics == [config.VALIDATION_TOPIC, config.INGRESS_TOPIC]
    assert consumer.conf["group.id"] == config.APP_NAME
    assert consumer.conf["enable.auto.commit"] is True
    assert consumer.conf["bootstrap.servers"] == ",".join(config.BOOTSTRAP_SERVERS)
    assert consumer.conf["queued.max.messages.kbytes"] == config.KAFKA_QUEUE_MAX_KBYTES
    assert consumer.conf["allow.auto.create.topics"] == config.KAFKA_ALLOW_CREATE_TOPICS


def test_init_consumer_returns_none_on_failure(monkeypatch):
    def boom(conf):
        raise RuntimeError("no kafka")

    monkeypatch.setattr(consume, "Consumer", boom)
    assert consume.init_consumer(logging.getLogger("test")) is None


@pytest.mark.xfail(raises=TypeError, reason="BUG: init_consumer logs 3 %s placeholders with only 2 arguments")
def test_init_consumer_subscribe_log_formats(monkeypatch):
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("test.consume")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(Capture())
    monkeypatch.setattr(consume, "Consumer", RecordingConsumer)
    try:
        consume.init_consumer(logger)
    finally:
        logger.handlers.clear()

    for record in records:
        record.getMessage()


def test_init_producer(monkeypatch):
    seen = []
    monkeypatch.setattr(produce, "Producer", lambda conf: seen.append(conf) or "producer")
    assert produce.init_producer() == "producer"
    assert seen == [{"bootstrap.servers": ",".join(config.BOOTSTRAP_SERVERS)}]


# --- delivery_report ----------------------------------------------------------


def tracker_msg():
    return FakeMessage(config.TRACKER_TOPIC, json.dumps({"status": "success"}), partition=3)


def test_delivery_report_success(metric_delta, caplog):
    published = metric_delta("storage_broker_message_publish_count_total")
    with caplog.at_level(logging.INFO, logger=produce.__name__):
        produce.delivery_report(None, tracker_msg(), request_id="rid")
    assert published.delta == 1
    assert f"Message delivered to {config.TRACKER_TOPIC} [3] for request_id [rid]" in caplog.text


def test_delivery_report_failure(metric_delta):
    failed = metric_delta("storage_broker_message_publish_error_count_total")
    published = metric_delta("storage_broker_message_publish_count_total")
    produce.delivery_report("delivery failed", tracker_msg(), request_id="rid")
    assert failed.delta == 1
    assert published.delta == 0


@pytest.mark.xfail(raises=AssertionError, reason="BUG: delivery_report passes err and request_id to the log in the wrong order")
def test_delivery_report_failure_log_names_request_id(caplog):
    with caplog.at_level(logging.ERROR, logger=produce.__name__):
        produce.delivery_report("delivery failed", tracker_msg(), request_id="rid")
    assert "for request_id [rid]: delivery failed" in caplog.text
