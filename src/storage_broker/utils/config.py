import os
import logging

APP_NAME = os.getenv("APP_NAME", "insights-storage-broker")

logger = logging.getLogger(APP_NAME)


def log_config():
    import sys

    for k, v in sys.modules[__name__].__dict__.items():
        if k == k.upper():
            if "AWS" in k.split("_"):
                continue
            logger.info("Using %s: %s", k, v)


def get_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            namespace = f.read()
        return namespace
    except EnvironmentError:
        logger.info("Not running in openshift")


if os.getenv("CLOWDER_ENABLED") == "true":
    from app_common_python import LoadedConfig, KafkaTopics, ObjectBuckets

    cfg = LoadedConfig


# Inventory
INVENTORY_URL = os.getenv(
    "INVENTORY_URL", "http://insights-inventory:8080/api/inventory/v1/hosts"
)

# Kafka
if os.getenv("CLOWDER_ENABLED") == "true":
    KAFKA_BROKER = cfg.kafka.brokers[0]
    VALIDATION_TOPIC = KafkaTopics["platform.upload.validation"].name
    ANNOUNCER_TOPIC = KafkaTopics["platform.upload.available"].name
    STORAGE_TOPIC = KafkaTopics["platform.upload.buckit"].name
    EGRESS_TOPIC = KafkaTopics["platform.inventory.events"].name
    TRACKER_TOPIC = KafkaTopics["platform.payload-status"].name
    BOOTSTRAP_SERVERS = [f"{KAFKA_BROKER.hostname}:{KAFKA_BROKER.port}"]
else:
    VALIDATION_TOPIC = os.getenv("CONSUME_TOPIC", "platform.upload.validation")
    ANNOUNCER_TOPIC = os.getenv("ANNOUNCER_TOPIC", "platform.upload.available")
    STORAGE_TOPIC = os.getenv("STORAGE_TOPIC", "platform.upload.buckit")
    EGRESS_TOPIC = os.getenv("EGRESS_TOPIC", "platform.inventory.events")
    TRACKER_TOPIC = os.getenv("TRACKER_TOPIC", "platform.payload-status")
    BOOTSTRAP_SERVERS = os.getenv("BOOTSTRAP_SERVERS", "kafka:29092").split()

GROUP_ID = os.getenv("GROUP_ID", APP_NAME)
KAFKA_QUEUE_MAX_KBYTES = os.getenv("KAFKA_QUEUE_MAX_KBYTES", 1024)
KAFKA_ALLOW_CREATE_TOPICS = os.getenv("KAFKA_ALLOW_CREATE_TOPICS", False)

# S3
if os.getenv("CLOWDER_ENABLED") == "true":
    AWS_ACCESS_KEY_ID = cfg.objectStore.accessKey
    AWS_SECRET_ACCESS_KEY = cfg.objectStore.secretKey
    STAGE_BUCKET = ObjectBuckets[os.environ.get("PERM_BUCKET")].name
    REJECT_BUCKET = ObjectBuckets[os.environ.get("REJECT_BUCKET")].name
else:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    STAGE_BUCKET = os.getenv("STAGE_BUCKET", "insights-dev-upload-perm")
    REJECT_BUCKET = os.getenv("REJECT_BUCKET", "insights-dev-upload-rejected")

# We need to support local or policy based keys that don't work with clowder
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)
BUCKET_MAP_FILE = os.getenv("BUCKET_MAP_FILE", "/opt/app-root/src/default_map.yaml")

# Logging
if os.getenv("CLOWDER_ENABLED") == "true":
    CW_AWS_ACCESS_KEY_ID = os.getenv(
        "CW_AWS_ACCESS_KEY_ID", cfg.logging.cloudwatch.accessKeyId
    )
    CW_AWS_SECRET_ACCESS_KEY = os.getenv(
        "CW_AWS_SECRET_ACCESS_KEY", cfg.logging.cloudwatch.secretAccessKey
    )
    LOG_GROUP = os.getenv("LOG_GROUP", cfg.logging.cloudwatch.logGroup)
else:
    CW_AWS_ACCESS_KEY_ID = os.getenv("CW_AWS_ACCESS_KEY_ID", None)
    CW_AWS_SECRET_ACCESS_KEY = os.getenv("CW_AWS_SECRET_ACCESS_KEY", None)
    LOG_GROUP = os.getenv("LOG_GROUP", "platform-dev")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
NAMESPACE = get_namespace()
HOSTNAME = os.environ.get("HOSTNAME")

# Metrics
if os.getenv("CLOWDER_ENABLED") == "true":
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", cfg.metricsPort))
else:
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 8080))

PROMETHEUS = os.getenv("PROMETHEUS", "True")
