import json
import signal
from functools import partial
from uuid import uuid4

import attr
from confluent_kafka import KafkaError
from prometheus_client import start_http_server
from threading import Event
from src.storage_broker import TrackerMessage, normalizers
from src.storage_broker.mq import consume, produce, msgs
from src.storage_broker.storage import aws
from src.storage_broker.utils import broker_logging, config, metrics

logger = broker_logging.initialize_logging()

event = Event()
producer = None


def start_prometheus():
    start_http_server(config.PROMETHEUS_PORT)


def write_cert(cert):
    with open("/tmp/cacert.pem", "w") as f:
        f.write(cert)


def handle_signal(signal, frame):
    event.set()


signal.signal(signal.SIGTERM, handle_signal)


def service_check(msg):
    """
    Check if the service header in the message contains a monitored
    service
    """
    service = dict(msg.headers() or []).get('service')
    if service:
        service = service.decode('utf-8')
        return service in config.MONITORED_SERVICES
    return False


def handle_validation(data, tracker_msg):
    def track(m):
        send_message(config.TRACKER_TOPIC, m, request_id=data.request_id)

    track(tracker_msg.message("received", f"received validation response from {data.service}"))
    if data.validation == "success":
        track(tracker_msg.message("success", f"payload validation successful for {data.service} payload"))
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
                "success", f"copied payload to {config.REJECT_BUCKET}"
            )
        )
        if data.reason:
            notification_id = uuid4().hex.encode('utf-8')
            message = msgs.notification_msg(data)
            send_message(config.NOTIFICATIONS_TOPIC, json.dumps(message), data.request_id, headers=[("rh-message-id", notification_id)])
        return

    logger.error(f"Invalid validation response: {data.validation}")
    metrics.invalid_validation_status.labels(service=data.service).inc()
    track(
        tracker_msg.message("error", f"invalid validation response: {data.validation} from {data.service}")
    )


def main(exit_event=event):

    logger.info("Starting Storage Broker")

    config.log_config()

    if config.PROMETHEUS == "True":
        start_prometheus()

    if config.KAFKA_BROKER:
        if config.KAFKA_BROKER.cacert:
            write_cert(config.KAFKA_BROKER.cacert)

    bucket_map = config.BUCKET_MAP

    consumer = consume.init_consumer(logger)
    global producer
    producer = produce.init_producer()

    while not exit_event.is_set():
        logger.debug("Polling Broker")
        msg = consumer.poll(1.0)
        logger.debug("Finished Polling")

        if msg is None:
            continue
        if msg.error():
            metrics.message_consume_error_count.inc()
            logger.error("Consumer error: %s", msg.error())
            continue

        if not service_check(msg) and msg.topic() != config.VALIDATION_TOPIC:
            continue

        try:
            decoded_msg = json.loads(msg.value().decode("utf-8"))
            logger.debug("Incoming Message Content: %s", decoded_msg)
            tracker_msg = TrackerMessage(decoded_msg)
            message = tracker_msg.message("received", "received message from {}".format(decoded_msg.get("service")))
            send_message(config.TRACKER_TOPIC, message, request_id=decoded_msg.get("request_id"))
        except Exception:
            logger.exception("Unable to decode message from topic: %s - %s", msg.topic(), msg.value())
            metrics.message_consume_error_count.inc()
            consumer.commit()
            continue

        metrics.message_consume_count.inc()

        try:
            _map = bucket_map[msg.topic()]
            data = normalize(_map, decoded_msg)
            tracker_msg = TrackerMessage(attr.asdict(data))
            if msg.topic() == config.VALIDATION_TOPIC:
                handle_validation(data, tracker_msg)
            else:
                key, bucket = get_bucket(_map, data)
                aws.copy(
                    data.request_id,
                    config.STAGE_BUCKET,
                    bucket,
                    key,
                    data.size,
                    data.service,
                )
                message = tracker_msg.message("success", f"copied payload to {bucket} as {key}")
                send_message(config.TRACKER_TOPIC, message, request_id=data.request_id)
        except Exception:
            metrics.message_json_unpack_error.labels(topic=msg.topic()).inc()
            logger.exception("An error occured during message processing")

        consumer.commit()
        producer.flush()

    logger.info("Exit event received. Exiting consumer.")
    consumer.commit()
    producer.flush()


def normalize(_map, decoded_msg):
    normalizer = getattr(normalizers, _map["normalizer"])
    data = normalizer.from_json(decoded_msg)
    logger.debug("Normalized Data structure: %s", data)
    return data


def get_bucket(_map, data):
    try:
        formatter = _map["services"][data.service]["format"]
        key = formatter.format(**attr.asdict(data))
        bucket = _map["services"][data.service]["bucket"]
        return key, bucket
    except Exception:
        logger.exception("Unable to find bucket map for %s", data.service)
        raise


def send_message(topic, msg, request_id=None, headers=None):
    try:
        producer.poll(0)
        producer.produce(
            topic, msg, headers=headers, callback=partial(produce.delivery_report, request_id=request_id)
        )
    except KafkaError:
        logger.exception(
            "Unable to produce to topic [%s] for request id [%s]",
            topic,
            msg.get("request_id"),
        )


if __name__ == "__main__":
    main()
