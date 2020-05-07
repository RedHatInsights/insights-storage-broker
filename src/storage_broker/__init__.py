import json
import logging

from datetime import datetime

from storage_broker.utils import config

logger = logging.getLogger(config.APP_NAME)


class TrackerMessage(object):
    def __init__(self, data):
        self.service = data["service"]
        self.account = data["account"]
        if data.get("host"):
            self.inventory_id = data.get("id")
        else:
            self.inventory_id = None

    def message(self, status, status_msg):
        self.status = status
        self.status_msg = status_msg
        self.date = datetime.now().isoformat()

        try:
            _bytes = json.dumps(self.__dict__, ensure_ascii=False).encode("utf-8")
            return _bytes
        except Exception:
            logger.exception("Unable to encode tracker JSON")
