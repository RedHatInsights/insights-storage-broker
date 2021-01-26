from confluent_kafka import Consumer

from src.storage_broker.utils import config


def init_consumer():
    consumer = Consumer(
        {
            "bootstrap.servers": ",".join(config.BOOTSTRAP_SERVERS),
            "group.id": config.APP_NAME,
            "queued.max.messages.kbytes": config.KAFKA_QUEUE_MAX_KBYTES,
            "enable.auto.commit": True,
            "allow.auto.create.topics": config.KAFKA_ALLOW_CREATE_TOPICS,
        }
    )

    consumer.subscribe(
        [config.VALIDATION_TOPIC, config.EGRESS_TOPIC, config.STORAGE_TOPIC]
    )
    return consumer
