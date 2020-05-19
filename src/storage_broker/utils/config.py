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


# Inventory
INVENTORY_URL = os.getenv(
    "INVENTORY_URL", "http://insights-inventory:8080/api/inventory/v1/hosts"
)

# Kafka
VALIDATION_TOPIC = os.getenv("CONSUME_TOPIC", "platform.upload.validation")
ANNOUNCER_TOPIC = os.getenv("ANNOUNCER_TOPIC", "platform.upload.available")
STORAGE_TOPIC = os.getenv("STORAGE_TOPIC", "platform.upload.buckit")
EGRESS_TOPIC = os.getenv("EGRESS_TOPIC", "platform.inventory.host-egress")
TRACKER_TOPIC = os.getenv("TRACKER_TOPIC", "platform.payload-status")
BOOTSTRAP_SERVERS = os.getenv("BOOTSTRAP_SERVERS", "kafka:29092").split()
GROUP_ID = os.getenv("GROUP_ID", APP_NAME)
KAFKA_QUEUE_MAX_KBYTES = os.getenv("KAFKA_QUEUE_MAX_KBYTES", 1024)

# S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
STAGE_BUCKET = os.getenv("STAGE_BUCKET", "insights-dev-upload-perm")
REJECT_BUCKET = os.getenv("REJECT_BUCKET", "insights-dev-upload-rejected")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)
BUCKET_MAP_FILE = os.getenv("BUCKET_MAP_FILE", "/opt/app-root/src/default_map.yaml")

# Logging
CW_AWS_ACCESS_KEY_ID = os.getenv("CW_AWS_ACCESS_KEY_ID", None)
CW_AWS_SECRET_ACCESS_KEY = os.getenv("CW_AWS_SECRET_ACCESS_KEY", None)
LOG_GROUP = os.getenv("LOG_GROUP", "platform-dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
NAMESPACE = get_namespace()

# Metrics
PROMETHEUS_PORT = os.getenv("PROMETHEUS_PORT", 8080)
PROMETHEUS = os.getenv("PROMETHEUS", "True")
