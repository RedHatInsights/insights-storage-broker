import json
import logging

from confluent_kafka import Producer
from src.storage_broker.utils import config, metrics
from src.storage_broker.mq import common

logger = logging.getLogger(__name__)


def init_producer():

   connection_info = common.build_confluent_kafka_config(config)

   return Producer(connection_info)


def delivery_report(err, msg=None, request_id=None):
    """
    Callback function for produced messages
    """
    if err is not None:
        logger.error(
            "Message delivery for topic %s failed for request_id [%s]: %s",
            msg.topic(),
            err,
            request_id,
        )
        logger.debug("Message contents: %s", json.loads(msg.value().decode("utf-8")))
        metrics.message_publish_error.inc()
    else:
        logger.info(
            "Message delivered to %s [%s] for request_id [%s]",
            msg.topic(),
            msg.partition(),
            request_id,
        )
        logger.debug("Message contents: %s", json.loads(msg.value().decode("utf-8")))
        metrics.message_publish_count.inc()
