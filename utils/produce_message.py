import imp
import os
import json
from functools import partial
from confluent_kafka import KafkaError

from src.storage_broker.mq import produce


KAFKA_PRODUCER_TOPIC = os.environ.get("KAFKA_PRODUCER_TOPIC","platform.upload.validation")


SAMPLE_MSG = {
    "account": "000001",
    "org_id": "123456",
    "reporter": "puptoo",
    "request_id": "12345",
    "system_id": "abdc-1234",
    "hostname": "hostname",
    "validation": "success",
    "service": "localhost",
    "reason": "validation success",
    "size": "12345",
}

def send_message(topic, producer, msg, headers=None):
    try:
        producer.poll(0)
        producer.produce(
            topic, msg, headers=headers, callback=partial(produce.delivery_report)
        )
    except KafkaError:
        print("Unable to producer message", KafkaError)
    producer.flush()

def main():
    producer = produce.init_producer()
    send_message(KAFKA_PRODUCER_TOPIC, producer, json.dumps(SAMPLE_MSG))
    print("Validation message produced. Done.")


if __name__ == "__main__":
    main()
