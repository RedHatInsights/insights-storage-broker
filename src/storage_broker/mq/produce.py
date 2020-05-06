import logging
import json

from confluent_kafka import Producer

from storage_broker.utils import config, metrics

logger = logging.getLogger(__name__)


def init_producer():
    producer = Producer(
        {
            "bootstrap.servers": ",".join(config.BOOTSTRAP_SERVERS),
        }
    )
    return producer


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
