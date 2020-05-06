import attr
import logging
import json

from datetime import datetime
from base64 import b64decode

logger = logging.getLogger(__name__)


@attr.s
class Validation(object):
    """
    A class meant to handle validation messages from the platform
    """
    validation = attr.ib(default=None)
    service = attr.ib(default=None)
    topic = attr.ib(default=None)

    @classmethod
    def from_json(cls, msg):
        try:
            data = json.loads(msg.value().decode("utf-8"))
            cls.validation = data["validation"]
            cls.service = data["service"]
            cls.topic = msg.topic()
            return cls
        except Exception:
            logger.exception("Unable to deserialize JSON: %s", msg.value())
            raise


@attr.s
class Ansible(object):
    size = attr.ib(default="0")
    request_id = attr.ib(default="-1")
    cluster_id = attr.ib(default=None)
    org_id = attr.ib(default=None)
    account = attr.ib(default=None)
    service = attr.ib(default=None)
    topic = attr.ib(default=None)
    timestamp = attr.ib(default=datetime.utcnow().strftime("%Y%m%d%H%M%S"))

    @classmethod
    def from_json(cls, doc, topic):
        try:
            ident = json.loads(b64decode(doc["b64_identity"]).decode("utf-8"))
            if ident["identity"].get("system"):
                cls.cluster_id = ident["identity"]["system"].get("cluster_id")
            cls.org_id = ident["identity"]["internal"].get("org_id")
            cls.account = ident["identity"]["account_number"]
            cls.service = doc["service"]
            cls.request_id = doc["request_id"]
            cls.size = doc["size"]
            cls.topic = topic
            cls.timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            return cls
        except Exception:
            logger.exception("Unable to deserialize JSON")
            raise


@attr.s
class Openshift(object):
    size = attr.ib(default="0")
    request_id = attr.ib(default="-1")
    cluster_id = attr.ib(default=None)
    org_id = attr.ib(default=None)
    account = attr.ib(default=None)
    service = attr.ib(default=None)
    topic = attr.ib(default=None)
    timestamp = attr.ib(default=datetime.utcnow().strftime("%Y%m%d%H%M%S"))

    @classmethod
    def from_json(cls, doc, topic):
        try:
            ident = json.loads(b64decode(doc["b64_identity"]).decode("utf-8"))
            if ident["identity"].get("system"):
                cls.cluster_id = ident["identity"]["system"].get("cluster_id")
            cls.org_id = ident["identity"]["internal"].get("org_id")
            cls.account = ident["identity"]["account_number"]
            cls.service = doc["service"]
            cls.request_id = doc["request_id"]
            cls.size = doc["size"]
            cls.topic = topic
            cls.timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            return cls
        except Exception:
            logger.exception("Unable to deserialize JSON")
            raise
