import signal
import json
import yaml

from storage_broker.mq import consume, produce, msgs
from storage_broker.storage import aws
from storage_broker.utils import broker_logging, config, metrics
from storage_broker import KeyMap

from confluent_kafka import KafkaError
from prometheus_client import start_http_server
from functools import partial

logger = broker_logging.initialize_logging()

running = True
producer = None


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

        metrics.message_consume_count.inc()
        try:
            data = json.loads(msg.value().decode("utf-8"))
            if msg.topic() == config.VALIDATION_TOPIC:
                tracker_msg = msgs.create_msg(data, "received", "received validation response")
                send_message(config.TRACKER_TOPIC, tracker_msg)
                if data.get("validation") == "success":
                    send_message(config.ANNOUNCER_TOPIC, data)
                    tracker_msg = msgs.create_msg(data, "success", f"announced to {config.ANNOUNCER_TOPIC}")
                    send_message(config.TRACKER_TOPIC, tracker_msg)
                elif data.get("validation") == "failure":
                    aws.copy(data["request_id"], config.STAGE_BUCKET, config.REJECT_BUCKET, data["request_id"])
                    tracker_msg = msgs.create_msg(
                        data, "success", "copied failed payload to reject bucket"
                    )
                    send_message(config.TRACKER_TOPIC, tracker_msg)
                else:
                    logger.error("Invalid validation response")
                    metrics.invalid_validation_status.labels(service=data.get("service")).inc()
                    tracker_msg = msgs.create_msg(data, "error", f"invalid validation response: {data.get('validation')}")
                    send_message(config.TRACKER_TOPIC, tracker_msg)
            elif msg.topic() == config.STORAGE_TOPIC:
                key, bucket = get_key(data, bucket_map)
                if key != "pass":
                    aws.copy(data["request_id"], config.STAGE_BUCKET, bucket, key)
                    metrics.payload_size.labels(service=data.get("service")).observe(data.get("size"))
            else:
                announce(data)
        except Exception:
            metrics.message_json_unpack_error.labels(topic=msg.topic()).inc()
            logger.exception("An error occurred during message processing")

        consumer.commit()
        producer.flush()

    consumer.close()
    producer.flush()


def delivery_report(err, msg=None, request_id=None):
    """
    Callback function for produced messages
    """
    if err is not None:
        logger.error(
            "Message delivery for topic %s failed for request_id [%s]: %s",
            msg.topic(),
            err,
            request_id
        )
        logger.info("Message contents: %s", json.loads(msg.value().decode("utf-8")))
        metrics.message_publish_error.inc()
    else:
        logger.info(
            "Message delivered to %s [%s] for request_id [%s]",
            msg.topic(),
            msg.partition(),
            request_id,
        )
        logger.info("Message contents: %s", json.loads(msg.value().decode("utf-8")))
        metrics.message_publish_count.inc()


@metrics.get_key_time.time()
def get_key(msg, bucket_map):
    """
    Get the key that will be used when transferring file to the new bucket
    """
    key_map = KeyMap.from_json(msg)

    if msg["service"] in bucket_map.keys():
        service = msg["service"]
        ident = key_map.identity()
        key_map.org_id = ident["identity"]["internal"].get("org_id")
        key_map.account = ident["identity"]["account_number"]
        if ident["identity"].get("system"):
            key_map.cluster_id = ident["identity"]["system"].get("cluster_id")
        formatter = bucket_map[service]["format"]
        key = formatter.format(**key_map.__dict__)
        bucket = bucket_map[service]["bucket"]
    else:
        key = "pass"
        bucket = "pass"

    return key, bucket


# This is is a way to support legacy uploads that are expected to be on the
# platform.upload.available queue
def announce(msg):
    logger.debug("Incoming Egress Message Content: %s", msg)
    platform_metadata = msg.pop("platform_metadata")
    msg["id"] = msg["host"].get("id")
    if msg["host"].get("system_profile"):
        del msg["host"]["system_profile"]
    available_message = {**msg, **platform_metadata}
    tracker_msg = msgs.create_msg(
        available_message, "received", "received egress message"
    )
    send_message(config.TRACKER_TOPIC, tracker_msg)
    send_message(config.ANNOUNCER_TOPIC, available_message)
    tracker_msg = msgs.create_msg(
        available_message, "success", f"sent message to {config.ANNOUNCER_TOPIC}"
    )
    send_message(config.TRACKER_TOPIC, tracker_msg)


def send_message(topic, msg):
    try:
        producer.poll(0)
        _bytes = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        producer.produce(topic, _bytes, callback=partial(delivery_report, request_id=msg.get("request_id")))
    except KafkaError:
        logger.exception(
            "Unable to topic [%s] for request id [%s]", topic, msg.get("request_id")
        )


if __name__ == "__main__":
    main()
