import os
import sys
import logging


from src.storage_broker.utils import config


def initialize_logging():
    kafkalogger = logging.getLogger("kafka")
    kafkalogger.setLevel("ERROR")
    if any("OPENSHIFT" in k for k in os.environ):
        handler = logging.StreamHandler(sys.stderr)
        logging.root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
        logging.root.addHandler(handler)
    else:
        logging.basicConfig(
            level=config.LOG_LEVEL,
            format="%(threadName)s %(levelname)s %(name)s - %(message)s",
        )

    logger = logging.getLogger(config.APP_NAME)

    return logger
