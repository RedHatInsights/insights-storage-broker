import json
import re

from src.storage_broker import TrackerMessage
from src.storage_broker.mq import msgs


DATA = {
    "account": "000001",
    "org_id": "123456",
    "request_id": "12345",
    "id": "inventory-id",
}


def test_tracker_message_schema():
    raw = TrackerMessage(DATA).message("success", "copied payload")
    assert isinstance(raw, bytes)
    msg = json.loads(raw)
    assert set(msg) == {
        "service",
        "account",
        "org_id",
        "request_id",
        "inventory_id",
        "status",
        "status_msg",
        "date",
    }
    assert msg["service"] == "storage-broker"
    assert msg["account"] == "000001"
    assert msg["org_id"] == "123456"
    assert msg["request_id"] == "12345"
    assert msg["status"] == "success"
    assert msg["status_msg"] == "copied payload"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", msg["date"])


def test_tracker_inventory_id_only_set_for_host_data():
    assert json.loads(TrackerMessage(DATA).message("x", "y"))["inventory_id"] is None
    with_host = dict(DATA, host={"id": "inventory-id"})
    assert json.loads(TrackerMessage(with_host).message("x", "y"))["inventory_id"] == "inventory-id"


def test_tracker_generates_request_id_when_missing():
    msg = json.loads(TrackerMessage({}).message("received", "hi"))
    assert re.match(r"^[0-9a-f]{32}$", msg["request_id"])
    assert msg["account"] is None
    assert msg["org_id"] is None


def test_tracker_message_can_be_reused_with_new_status():
    tracker = TrackerMessage(DATA)
    first = json.loads(tracker.message("received", "one"))
    second = json.loads(tracker.message("success", "two"))
    assert (first["status"], first["status_msg"]) == ("received", "one")
    assert (second["status"], second["status_msg"]) == ("success", "two")


def test_tracker_message_keeps_non_ascii():
    raw = TrackerMessage(DATA).message("success", "café")
    assert "café".encode("utf-8") in raw


def test_create_msg():
    msg = msgs.create_msg(DATA, "success", "done")
    assert msg["service"] == "insights-storage-broker"
    assert msg["account"] == "000001"
    assert msg["request_id"] == "12345"
    assert msg["inventory_id"] == "inventory-id"
    assert msg["status"] == "success"
    assert msg["status_msg"] == "done"
    assert msg["date"]
