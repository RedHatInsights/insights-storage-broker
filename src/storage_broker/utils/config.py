import os
import logging
import yaml

APP_NAME = os.getenv("APP_NAME", "insights-storage-broker")
BUCKET_MAP_FILE = os.getenv("BUCKET_MAP_FILE", "/opt/app-root/src/default_map.yaml")

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


def load_bucket_map(_file):
    try:
        with open(_file, "rb") as f:
            bucket_map = yaml.safe_load(f)
    except Exception as e:
        logger.exception(e)
        bucket_map = {}

    return bucket_map

def clowderize_bucket_map(bucket_map, topics):
    """
    Convert the bucket map to use clowder derived topic names
    """
    clowderized_map = {}
    for topic, bucket_info in bucket_map.items():
        clowderized_map[topics[topic].name] = bucket_info

    return clowderized_map

# Inventory
INVENTORY_URL = os.getenv(
    "INVENTORY_URL", "http://insights-inventory:8080/api/inventory/v1/hosts"
)

# Kafka
if os.getenv("ACG_CONFIG"):
    from app_common_python import LoadedConfig, KafkaTopics, ObjectBuckets

    cfg = LoadedConfig
    KAFKA_BROKER = cfg.kafka.brokers[0]
    BUCKET_MAP = clowderize_bucket_map(load_bucket_map(BUCKET_MAP_FILE), KafkaTopics)
    VALIDATION_TOPIC = KafkaTopics["platform.upload.validation"].name
    INGRESS_TOPIC = KafkaTopics["platform.upload.announce"].name
    EGRESS_TOPIC = KafkaTopics["platform.inventory.events"].name
    NOTIFICATIONS_TOPIC = KafkaTopics["platform.notifications.ingress"].name
    TRACKER_TOPIC = KafkaTopics["platform.payload-status"].name
    BOOTSTRAP_SERVERS = f"{KAFKA_BROKER.hostname}:{KAFKA_BROKER.port}"
    # S3
    AWS_ACCESS_KEY_ID = cfg.objectStore.accessKey
    AWS_SECRET_ACCESS_KEY = cfg.objectStore.secretKey
    STAGE_BUCKET = ObjectBuckets[os.environ.get("PERM_BUCKET")].name
    REJECT_BUCKET = ObjectBuckets[os.environ.get("REJECT_BUCKET")].name
    if cfg.objectStore.port != 443:
        S3_ENDPOINT_URL = f"http://{cfg.objectStore.hostname}:{cfg.objectStore.port}"
    else:
        S3_ENDPOINT_URL = f"https://{cfg.objectStore.hostname}:{cfg.objectStore.port}"
    # Logging
    CW_AWS_ACCESS_KEY_ID = os.getenv(
        "CW_AWS_ACCESS_KEY_ID", cfg.logging.cloudwatch.accessKeyId
    )
    CW_AWS_SECRET_ACCESS_KEY = os.getenv(
        "CW_AWS_SECRET_ACCESS_KEY", cfg.logging.cloudwatch.secretAccessKey
    )
    LOG_GROUP = os.getenv("LOG_GROUP", cfg.logging.cloudwatch.logGroup)
    # Metrics
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", cfg.metricsPort))
    API_PORT = int(os.getenv("API_PORT", cfg.publicPort))
else:
    KAFKA_BROKER = None
    BUCKET_MAP = load_bucket_map(BUCKET_MAP_FILE)
    VALIDATION_TOPIC = os.getenv("CONSUME_TOPIC", "platform.upload.validation")
    INGRESS_TOPIC = os.getenv("INGRESS_TOPIC", "platform.upload.announce")
    EGRESS_TOPIC = os.getenv("EGRESS_TOPIC", "platform.inventory.events")
    NOTIFICATIONS_TOPIC = os.getenv("NOTIFICATIONS_TOPIC", "platform.notifications.ingress")
    TRACKER_TOPIC = os.getenv("TRACKER_TOPIC", "platform.payload-status")
    BOOTSTRAP_SERVERS = os.getenv("BOOTSTRAP_SERVERS", "kafka:29092").split()
    # S3
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    STAGE_BUCKET = os.getenv("STAGE_BUCKET", "insights-dev-upload-perm")
    REJECT_BUCKET = os.getenv("REJECT_BUCKET", "insights-dev-upload-rejected")
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)
    # Logging
    CW_AWS_ACCESS_KEY_ID = os.getenv("CW_AWS_ACCESS_KEY_ID", None)
    CW_AWS_SECRET_ACCESS_KEY = os.getenv("CW_AWS_SECRET_ACCESS_KEY", None)
    LOG_GROUP = os.getenv("LOG_GROUP", "platform-dev")
    # Metrics
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 8080))
    API_PORT = int(os.getenv("API_PORT", 5000))

GROUP_ID = os.getenv("GROUP_ID", APP_NAME)
KAFKA_QUEUE_MAX_KBYTES = os.getenv("KAFKA_QUEUE_MAX_KBYTES", 1024)
KAFKA_ALLOW_CREATE_TOPICS = os.getenv("KAFKA_ALLOW_CREATE_TOPICS", False)
KAFKA_LOG_LEVEL = os.getenv("KAFKA_LOG_LEVEL", "ERROR")
MONITORED_SERVICES = os.getenv("MONITORED_SERVICES", "openshift,ansible").split(",")

API_LISTEN_ADDRESS = os.getenv("API_LISTEN_ADDRESS", "0.0.0.0")
API_URL_EXPIRY = int(os.getenv("API_URL_EXPIRY", 30))

# We need to support local or policy based keys that don't work with clowder
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
NAMESPACE = get_namespace()
HOSTNAME = os.environ.get("HOSTNAME")

PROMETHEUS = os.getenv("PROMETHEUS", "True")
