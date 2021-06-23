import json
import signal
from functools import partial

import attr
import yaml
from confluent_kafka import KafkaError
from prometheus_client import start_http_server
from src.storage_broker import TrackerMessage, normalizers
from src.storage_broker.mq import consume, produce
from src.storage_broker.storage import aws
from src.storage_broker.utils import broker_logging, config, metrics

logger = broker_logging.initialize_logging()

running = True
producer = None


def start_prometheus():
    start_http_server(config.PROMETHEUS_PORT)


def write_cert(cert):
    with open("/tmp/cacert.pem", "w") as f:
        f.write(cert)


def load_bucket_map(_file):
    try:
        with open(_file, "rb") as f:
            bucket_map = yaml.safe_load(f)
    except Exception as e:
        logger.exception(e)
        bucket_map = {}

    return bucket_map


def handle_signal(signal, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, handle_signal)


def handle_failure(msg, decoded_msg, data, tracker_msg):
    def track(m):
        send_message(config.TRACKER_TOPIC, m, request_id=data.request_id)

    track(tracker_msg.message("received", "received validation response"))
    if data.validation == "success":
        send_message(config.ANNOUNCER_TOPIC, json.dumps(decoded_msg), data.request_id)
        track(tracker_msg.message("success", f"announced to {config.ANNOUNCER_TOPIC}"))
        return

    if data.validation == "failure":
        aws.copy(
            data.request_id,
            config.STAGE_BUCKET,
            config.REJECT_BUCKET,
            data.request_id,
            data.size,
            data.service,
        )
        track(
            tracker_msg.message(
                "success", f"copied failed payload to {config.REJECT_BUCKET}"
            )
        )
        return

    logger.error(f"Invalid validation response: {data.validation}")
    metrics.invalid_validation_status.labels(service=data.service).inc()
    track(
        tracker_msg.message("error", f"invalid validation response: {data.validation}")
    )


def main():

    logger.info("Starting Storage Broker")

    config.log_config()

    if config.PROMETHEUS == "True":
        start_prometheus()

    if config.KAFKA_BROKER and config.KAFKA_BROKER.cacert:
        write_cert(config.KAFKA_BROKER.cacert)

    bucket_map = load_bucket_map(config.BUCKET_MAP_FILE)

    consumer = consume.init_consumer()
    global producer
    producer = produce.init_producer()

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            metrics.message_consume_error_count.inc()
            logger.error("Consumer error: %s", msg.error())
            continue

        try:
            decoded_msg = json.loads(msg.value().decode("utf-8"))
        except Exception:
            logger.exception("Unable to decode message from topic: %s - %s", msg.topic(), msg.value())
            metrics.message_consume_error_count.inc()
            consumer.commit()
            continue

        metrics.message_consume_count.inc()
        if msg.topic() == config.EGRESS_TOPIC:
            if decoded_msg['type'] in ('updated', 'created'):
                announce(decoded_msg)
            continue

        try:
            _map = bucket_map[msg.topic()]
            data = normalize(_map, decoded_msg)
            tracker_msg = TrackerMessage(attr.asdict(data))
            if msg.topic() == config.VALIDATION_TOPIC:
                handle_failure(msg, decoded_msg, data, tracker_msg)
            else:
                key, bucket = handle_bucket(_map, data)
                aws.copy(
                    data.request_id,
                    config.STAGE_BUCKET,
                    bucket,
                    key,
                    data.size,
                    data.service,
                )
        except Exception:
            metrics.message_json_unpack_error.labels(topic=msg.topic()).inc()
            logger.exception("An error occured during message processing")

        consumer.commit()
        producer.flush()

    consumer.commit()
    producer.flush()


def normalize(_map, decoded_msg):
    normalizer = getattr(normalizers, _map["normalizer"])
    data = normalizer.from_json(decoded_msg)
    return data


def handle_bucket(_map, data):
    try:
        formatter = _map["services"][data.service]["format"]
        key = formatter.format(**attr.asdict(data))
        bucket = _map["services"][data.service]["bucket"]
        return key, bucket
    except Exception:
        logger.exception("Unable to find bucket map for %s", data.service)
        raise


# This is is a way to support legacy uploads that are expected to be on the
# platform.upload.available queue
def announce(msg):
    logger.debug("Incoming Egress Message Content: %s", msg)
    platform_metadata = msg.pop("platform_metadata")
    msg["id"] = msg["host"].get("id")
    if msg["host"].get("system_profile"):
        del msg["host"]["system_profile"]
    if platform_metadata is not None:
        available_message = {**msg, **platform_metadata}
    else:
        available_message = msg
    send_message(config.ANNOUNCER_TOPIC, json.dumps(available_message))
    tracker_msg = TrackerMessage(available_message)
    send_message(
        config.TRACKER_TOPIC,
        tracker_msg.message("success", f"sent message to {config.ANNOUNCER_TOPIC}"),
        available_message.get("request_id"),
    )


def send_message(topic, msg, request_id=None):
    try:
        producer.poll(0)
        producer.produce(
            topic, msg, callback=partial(produce.delivery_report, request_id=request_id)
        )
    except KafkaError:
        logger.exception(
            "Unable to produce to topic [%s] for request id [%s]",
            topic,
            msg.get("request_id"),
        )


if __name__ == "__main__":
    main()
