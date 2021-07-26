import json
import logging

from confluent_kafka import Producer
from src.storage_broker.utils import config, metrics

logger = logging.getLogger(__name__)


def init_producer():
    connection_info = {}

    if config.KAFKA_BROKER:
        connection_info["bootstrap.servers"] = config.BOOTSTRAP_SERVERS
        if config.KAFKA_BROKER.cacert:
            connection_info["ssl.ca.location"] = "/tmp/cacert.pem"
        if config.KAFKA_BROKER.sasl and config.KAFKA_BROKER.sasl.username:
            connection_info.update({
                "security.protocol": "sasl_ssl",
                "sasl.mechanisms": "SCRAM-SHA-512",
                "sasl.username": config.KAFKA_BROKER.sasl.username,
                "sasl.password": config.KAFKA_BROKER.sasl.password
            })
        return Producer(connection_info)
    else:
        return Producer({"bootstrap.servers": ",".join(config.BOOTSTRAP_SERVERS)})


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
