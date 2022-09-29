import json

from logging import StringTemplateStyle
from storage_broker.normalizers import Validation


MSG = {
    "account": "000001",
    "org_id": "123456",
    "reporter": "puptoo",
    "request_id": "12345",
    "system_id": "abdc-1234",
    "hostname": "hostname",
    "validation": "failure",
    "service": "advisor",
    "reason": "error unpacking archive",
    "size": "12345",
}


def test_validation_normalizer():
    normalizer = Validation()
    data = normalizer.from_json(MSG)
    assert data.account == "000001"
    assert data.org_id == "123456"

