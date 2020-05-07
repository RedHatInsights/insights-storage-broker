import signal
import json
import yaml
import attr

from storage_broker.mq import consume, produce, msgs
from storage_broker.storage import aws
from storage_broker.utils import broker_logging, config, metrics
from storage_broker import TrackerMessage, normalizers

from confluent_kafka import KafkaError
from prometheus_client import start_http_server
from functools import partial

logger = broker_logging.initialize_logging()

running = True
producer = None
bucket_map = {}


def start_prometheus():
    start_http_server(config.PROMETHEUS_PORT)


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


def main():

    logger.info("Starting Storage Broker")

    config.log_config()

    if config.PROMETHEUS == "True":
        start_prometheus()

    global bucket_map
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
            logger.exception("Unable to decode message from topic: %s", msg.topic())

        metrics.message_consume_count.inc()
        if msg.topic() == config.EGRESS_TOPIC:
            announce(decoded_msg)
            continue

        try:
            _map = get_map(bucket_map, msg.topic(), decoded_msg)
            data = normalize(_map, decoded_msg)
            tracker_msg = TrackerMessage(attr.asdict(data))
            if msg.topic() == config.VALIDATION_TOPIC:
                send_message(config.TRACKER_TOPIC, tracker_msg.message("received", "received validation response"), data.request_id)
                result = handle_validation(data)
                if result == "success":
                    send_message(config.ANNOUNCER_TOPIC, decoded_msg, data.request_id)
                    send_message(config.TRACKER_TOPIC, tracker_msg.message("success", f"announced to {config.ANNOUNCER_TOPIC}"), data.request_id)
                elif result == "failure":
                    aws.copy(data.request_id, config.STAGE_BUCKET, config.REJECT_BUCKET, data.request_id, data.size, data.service)
                    send_message(config.TRACKER_TOPIC, tracker_msg.message("success", f"copied failed payload to {config.REJECT_BUCKET}"), data.request_id)
                else:
                    logger.error(f"Invalid validation response: {data.validation}")
                    metrics.invalid_validation_status.labels(service=data.service).inc()
                    send_message(config.TRACKER_TOPIC, tracker_msg.message("error", f"invalid validation response: {data.validation}"), data.request_id)
            else:
                key, bucket = handle_bucket(msg.topic(), data)
                aws.copy(data.request_id, config.STAGE_BUCKET, bucket, key, data.size, data.service)
        except Exception:
            metrics.message_json_unpack_error.labels(topic=msg.topic()).inc()
            logger.exception("An error occured during message processing")

        consumer.commit()
        producer.flush()

    consumer.commit()
    producer.flush()


def get_map(bucket_map, topic, decoded_msg):
    _map = bucket_map[topic].get(decoded_msg["service"])
    if _map is not None:
        return _map
    else:
        logger.error("Service key not in decoded msg: %s", decoded_msg)


def normalize(_map, decoded_msg):
    normalizer = getattr(normalizers, _map["normalizer"])
    data = normalizer.from_json(decoded_msg)
    return data


def handle_validation(data):
    if data.validation == "success":
        return "success"
    elif data.validation == "failure":
        return "failure"
    else:
        return "invalid"


def handle_bucket(topic, data):
    try:
        _map = bucket_map[topic][data.service]
        formatter = _map["format"]
        key = formatter.format(attr.asdict(data))
        bucket = _map["bucket"]
        return key, bucket
    except Exception:
        logger.exception("Unable to find bucket map for %s", data.service)


# This is is a way to support legacy uploads that are expected to be on the
# platform.upload.available queue
def announce(msg):
    logger.debug("Incoming Egress Message Content: %s", msg)
    platform_metadata = msg.pop("platform_metadata")
    msg["id"] = msg["host"].get("id")
    if msg["host"].get("system_profile"):
        del msg["host"]["system_profile"]
    available_message = {**msg, **platform_metadata}
    send_message(config.ANNOUNCER_TOPIC, available_message)
    tracker_msg = msgs.create_msg(
        available_message, "success", f"sent message to {config.ANNOUNCER_TOPIC}"
    )
    send_message(config.TRACKER_TOPIC, tracker_msg)


def send_message(topic, msg, request_id=None):
    try:
        producer.poll(0)
        if type(msg) != bytes:
            msg = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        producer.produce(topic, msg, callback=partial(produce.delivery_report, request_id=request_id))
    except KafkaError:
        logger.exception(
            "Unable to produce to topic [%s] for request id [%s]", topic, msg.get("request_id")
        )


if __name__ == "__main__":
    main()
