import attr
import logging
import json
import uuid

from datetime import datetime
from base64 import b64decode

logger = logging.getLogger(__name__)


def parse_identity(b64_identity):
    ident = json.loads(b64decode(b64_identity).decode("utf-8"))
    return ident


@attr.s
class Validation(object):
    """
    A class meant to handle validation messages from the platform
    """

    validation = attr.ib(default=None)
    service = attr.ib(default=None)
    request_id = attr.ib(default=str(uuid.uuid4().hex))
    reason = attr.ib(default=None)
    account = attr.ib(default=None)
    org_id = attr.ib(default=None)
    reporter = attr.ib(default=None)
    system_id = attr.ib(default=None)
    hostname = attr.ib(default=None)
    size = attr.ib(default=None)
    timestamp = attr.ib(default=datetime.utcnow().strftime("%Y%m%d%H%M%S"))


    @classmethod
    def from_json(cls, doc):
        try:
            # default dictionary in case we don't have an identity
            ident = {"identity": {"account": None,
                                  "org_id": None,
                                  "internal": {
                                      "org_id": None,
                                      }
                                  }
                     }
            if doc.get("b64_identity"):
                ident = parse_identity(doc["b64_identity"])
            if not ident["identity"].get("org_id") and ident["identity"]["internal"].get("org_id"):
                ident["identity"]["org_id"] == ident["identity"]["internal"]["org_id"]
            validation = doc["validation"]
            service = doc.get("service")
            request_id = doc.get("request_id", str(uuid.uuid4().hex))
            reason = doc.get("reason")
            account = doc.get("account") if doc.get("account") else ident["identity"].get("account_number")
            org_id = doc.get("org_id") if doc.get("org_id") else ident["identity"]["org_id"]
            reporter = doc.get("reporter")
            system_id = doc.get("system_id")
            hostname = doc.get("hostname")
            size = doc.get("size")
            return cls(
                validation=validation, service=service, request_id=request_id,
                reason=reason, reporter=reporter, system_id=system_id,
                hostname=hostname, account=account, org_id=org_id, size=size,
                timestamp=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            )
        except Exception:
            logger.exception("Unable to deserialize JSON: %s", doc)
            raise


@attr.s
class Openshift(object):
    size = attr.ib(default="0")
    request_id = attr.ib(default=str(uuid.uuid4().hex))
    cluster_id = attr.ib(default=None)
    org_id = attr.ib(default=None)
    account = attr.ib(default=None)
    service = attr.ib(default=None)
    timestamp = attr.ib(default=datetime.utcnow().strftime("%Y%m%d%H%M%S"))

    @classmethod
    def from_json(cls, doc):
        cluster_id = None
        try:
            ident = parse_identity(doc["b64_identity"])
            if ident["identity"].get("system"):
                cluster_id = ident["identity"]["system"].get("cluster_id")
            if not ident["identity"].get("org_id") and ident["identity"]["internal"].get("org_id"):
                ident["identity"]["org_id"] = ident["identity"]["internal"]["org_id"]
            org_id = ident["identity"]["org_id"]
            account = ident["identity"].get("account_number")
            service = doc["service"]
            request_id = doc.get("request_id", str(uuid.uuid4().hex))
            size = doc.get("size")
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
