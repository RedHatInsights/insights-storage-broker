from confluent_kafka import Consumer

from src.storage_broker.utils import config


def init_consumer():
    connection_info = {
            "bootstrap.servers": ",".join(config.BOOTSTRAP_SERVERS),
            "group.id": config.APP_NAME,
            "queued.max.messages.kbytes": config.KAFKA_QUEUE_MAX_KBYTES,
            "enable.auto.commit": True,
            "allow.auto.create.topics": config.KAFKA_ALLOW_CREATE_TOPICS,
    }

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

    consumer = Consumer(connection_info)

    consumer.subscribe(
        [config.VALIDATION_TOPIC, config.EGRESS_TOPIC, config.STORAGE_TOPIC]
    )
    return consumer
