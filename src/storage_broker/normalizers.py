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
    request_id = attr.ib(default=None)
    size = attr.ib(default=None)

    @classmethod
    def from_json(cls, doc):
        try:
            validation = doc["validation"]
            service = doc["service"]
            request_id = doc["request_id"]
            size = doc["size"]
            return cls(
                validation=validation, service=service, request_id=request_id, size=size
            )
        except Exception:
            logger.exception("Unable to deserialize JSON: %s", doc)
            raise


@attr.s
class Ansible(object):
    size = attr.ib(default="0")
    request_id = attr.ib(default="-1")
    cluster_id = attr.ib(default=None)
    org_id = attr.ib(default=None)
    account = attr.ib(default=None)
    service = attr.ib(default=None)
    timestamp = attr.ib(default=datetime.utcnow().strftime("%Y%m%d%H%M%S"))

    @classmethod
    def from_json(cls, doc):
        try:
            ident = json.loads(b64decode(doc["b64_identity"]).decode("utf-8"))
            if ident["identity"].get("system"):
                cluster_id = ident["identity"]["system"].get("cluster_id")
            org_id = ident["identity"]["internal"].get("org_id")
            account = ident["identity"]["account_number"]
            service = doc["service"]
            request_id = doc["request_id"]
            size = doc["size"]
            return cls(
                cluster_id=cluster_id,
                org_id=org_id,
                account=account,
                service=service,
                request_id=request_id,
                size=size,
                timestamp=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            )
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
    timestamp = attr.ib(default=datetime.utcnow().strftime("%Y%m%d%H%M%S"))

    @classmethod
    def from_json(cls, doc):
        try:
            ident = json.loads(b64decode(doc["b64_identity"]).decode("utf-8"))
            if ident["identity"].get("system"):
                cluster_id = ident["identity"]["system"].get("cluster_id")
            org_id = ident["identity"]["internal"].get("org_id")
            account = ident["identity"]["account_number"]
            service = doc["service"]
            request_id = doc["request_id"]
            size = doc["size"]
            return cls(
                cluster_id=cluster_id,
                org_id=org_id,
                account=account,
                service=service,
                request_id=request_id,
                size=size,
                timestamp=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            )
        except Exception:
            logger.exception("Unable to deserialize JSON")
            raise
