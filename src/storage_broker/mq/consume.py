from confluent_kafka import Consumer

from src.storage_broker.utils import config


def init_consumer(logger):
    logger.debug("initializing consumer")
    try:
       connection_info = _build_confluent_kafka_config(config)

       consumer_config = {
               "group.id": config.APP_NAME,
               "queued.max.messages.kbytes": config.KAFKA_QUEUE_MAX_KBYTES,
               "enable.auto.commit": True,
               "allow.auto.create.topics": config.KAFKA_ALLOW_CREATE_TOPICS,
       }

       connection_info.update(consumer_config)

       consumer = Consumer(connection_info)
       logger.debug("Connected to consumer")

       consumer.subscribe(
           [config.VALIDATION_TOPIC, config.INGRESS_TOPIC]
       )
       logger.debug("Subscribed to topics [%s, %s, %s]", config.VALIDATION_TOPIC,
                                                         config.INGRESS_TOPIC)
       return consumer
    except Exception as e:
        logger.error("Failed to initialize consumer: %s", e)
