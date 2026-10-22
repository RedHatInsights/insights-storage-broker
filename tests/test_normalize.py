import re

import pytest

from src.storage_broker import normalizers
from src.storage_broker.normalizers import resolve_normalizer
from tests.conftest import b64_identity


VALIDATION_MSG = {
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

TIMESTAMP_RE = re.compile(r"^\d{14}$")


def openshift_msg(identity, **overrides):
    msg = {
        "b64_identity": b64_identity(identity),
        "service": "openshift",
        "request_id": "abc123",
        "size": 2048,
    }
    msg.update(overrides)
    return msg


# --- resolve_normalizer -------------------------------------------------------


def test_topic_level_normalizer():
    """When no service is specified, use topic-level normalizer."""
    _map = {"normalizer": "Validation"}
    cls = resolve_normalizer(_map)
    assert cls is normalizers.Validation
    data = cls.from_json(VALIDATION_MSG)
    assert data.account == "000001"


def test_topic_level_fallback_when_service_has_no_normalizer():
    """When service config has no normalizer key, fall back to
    topic-level normalizer."""
    _map = {
        "normalizer": "Validation",
        "services": {
            "advisor": {
                "format": "{org_id}/{request_id}",
                "bucket": "test-bucket",
            }
        },
    }
    cls = resolve_normalizer(_map, service="advisor")
    assert cls is normalizers.Validation
    data = cls.from_json(VALIDATION_MSG)
    assert data.service == "advisor"


def test_service_level_normalizer_overrides_topic():
    """When service config has a normalizer key, use it instead
    of the topic-level normalizer."""
    _map = {
        "normalizer": "Openshift",
        "services": {
            "advisor": {
                "normalizer": "Validation",
                "format": "{org_id}/{request_id}",
                "bucket": "test-bucket",
            }
        },
    }
    cls = resolve_normalizer(_map, service="advisor")
    assert cls is normalizers.Validation
    data = cls.from_json(VALIDATION_MSG)
    assert data.service == "advisor"


def test_unknown_service_uses_topic_level():
    """When service is not in services config, use topic-level normalizer."""
    _map = {
        "normalizer": "Validation",
        "services": {
            "openshift": {
                "normalizer": "Openshift",
                "format": "{org_id}/{request_id}",
                "bucket": "test-bucket",
            }
        },
    }
    cls = resolve_normalizer(_map, service="advisor")
    assert cls is normalizers.Validation
    data = cls.from_json(VALIDATION_MSG)
    assert data.account == "000001"


def test_no_services_section_uses_topic_level():
    """When config has no services section, use topic-level normalizer."""
    _map = {"normalizer": "Validation"}
    cls = resolve_normalizer(_map, service="advisor")
    assert cls is normalizers.Validation
    data = cls.from_json(VALIDATION_MSG)
    assert data.org_id == "123456"


def test_different_services_different_normalizers():
    """Different services on the same topic can use different normalizers."""
    _map = {
        "normalizer": "Openshift",
        "services": {
            "openshift": {
                "normalizer": "Openshift",
                "format": "{org_id}/{cluster_id}/{timestamp}-{request_id}",
                "bucket": "insights-buck-it-openshift",
            },
            "advisor": {
                "normalizer": "Validation",
                "format": "{org_id}/{request_id}",
                "bucket": "test-bucket",
            },
        },
    }
    assert resolve_normalizer(_map, service="openshift") is normalizers.Openshift
    assert resolve_normalizer(_map, service="advisor") is normalizers.Validation


def test_missing_topic_normalizer_raises():
    with pytest.raises(KeyError):
        resolve_normalizer({"services": {}})


def test_unknown_normalizer_name_raises():
    with pytest.raises(AttributeError):
        resolve_normalizer({"normalizer": "DoesNotExist"})


# --- parse_identity -----------------------------------------------------------


def test_parse_identity_decodes_base64_json():
    ident = normalizers.parse_identity(b64_identity({"org_id": "42"}))
    assert ident == {"identity": {"org_id": "42"}}


def test_parse_identity_rejects_garbage():
    with pytest.raises(Exception):
        normalizers.parse_identity("not-base64-json")


# --- Validation ---------------------------------------------------------------


def test_validation_copies_message_fields():
    data = normalizers.Validation.from_json(VALIDATION_MSG)
    assert data.validation == "failure"
    assert data.service == "advisor"
    assert data.request_id == "12345"
    assert data.reason == "error unpacking archive"
    assert data.account == "000001"
    assert data.org_id == "123456"
    assert data.reporter == "puptoo"
    assert data.system_id == "abdc-1234"
    assert data.hostname == "hostname"
    assert data.size == "12345"
    assert TIMESTAMP_RE.match(data.timestamp)


def test_validation_requires_validation_key():
    msg = dict(VALIDATION_MSG)
    del msg["validation"]
    with pytest.raises(KeyError):
        normalizers.Validation.from_json(msg)


def test_validation_generates_request_id_when_missing():
    msg = dict(VALIDATION_MSG)
    del msg["request_id"]
    data = normalizers.Validation.from_json(msg)
    assert re.match(r"^[0-9a-f]{32}$", data.request_id)


def test_validation_without_identity_or_ids_yields_none():
    msg = {"validation": "success", "service": "advisor", "request_id": "r1"}
    data = normalizers.Validation.from_json(msg)
    assert data.account is None
    assert data.org_id is None


def test_validation_takes_ids_from_identity_when_missing_in_message():
    msg = {
        "validation": "success",
        "service": "advisor",
        "request_id": "r1",
        "b64_identity": b64_identity({"account_number": "acct", "org_id": "org", "internal": {"org_id": "org"}}),
    }
    data = normalizers.Validation.from_json(msg)
    assert data.account == "acct"
    assert data.org_id == "org"


def test_validation_message_ids_win_over_identity():
    msg = dict(VALIDATION_MSG)
    msg["b64_identity"] = b64_identity({"account_number": "other", "org_id": "other", "internal": {"org_id": "other"}})
    data = normalizers.Validation.from_json(msg)
    assert data.account == "000001"
    assert data.org_id == "123456"


def test_validation_falls_back_to_internal_org_id():
    msg = {
        "validation": "success",
        "service": "advisor",
        "request_id": "r1",
        "b64_identity": b64_identity({"org_id": None, "internal": {"org_id": "internal-org"}}),
    }
    data = normalizers.Validation.from_json(msg)
    assert data.org_id == "internal-org"


def test_validation_identity_without_org_id_key():
    msg = {
        "validation": "success",
        "service": "advisor",
        "request_id": "r1",
        "b64_identity": b64_identity({"internal": {"org_id": "internal-org"}}),
    }
    data = normalizers.Validation.from_json(msg)
    assert data.org_id == "internal-org"


# --- Openshift ----------------------------------------------------------------


def test_openshift_extracts_identity_fields():
    identity = {
        "account_number": "acct",
        "org_id": "org",
        "internal": {"org_id": "org"},
        "system": {"cluster_id": "cluster-1"},
    }
    data = normalizers.Openshift.from_json(openshift_msg(identity))
    assert data.cluster_id == "cluster-1"
    assert data.org_id == "org"
    assert data.account == "acct"
    assert data.service == "openshift"
    assert data.request_id == "abc123"
    assert data.size == 2048
    assert TIMESTAMP_RE.match(data.timestamp)


def test_openshift_without_system_has_no_cluster_id():
    identity = {"org_id": "org", "internal": {"org_id": "org"}}
    data = normalizers.Openshift.from_json(openshift_msg(identity))
    assert data.cluster_id is None


def test_openshift_falls_back_to_internal_org_id():
    identity = {"internal": {"org_id": "internal-org"}}
    data = normalizers.Openshift.from_json(openshift_msg(identity))
    assert data.org_id == "internal-org"


def test_openshift_generates_request_id_when_missing():
    msg = openshift_msg({"org_id": "org", "internal": {"org_id": "org"}})
    del msg["request_id"]
    data = normalizers.Openshift.from_json(msg)
    assert re.match(r"^[0-9a-f]{32}$", data.request_id)


def test_openshift_requires_identity():
    msg = openshift_msg({"org_id": "org"})
    del msg["b64_identity"]
    with pytest.raises(KeyError):
        normalizers.Openshift.from_json(msg)


def test_openshift_requires_service():
    msg = openshift_msg({"org_id": "org", "internal": {"org_id": "org"}})
    del msg["service"]
    with pytest.raises(KeyError):
        normalizers.Openshift.from_json(msg)


def test_default_request_ids_are_unique():
    assert normalizers.Openshift().request_id != normalizers.Openshift().request_id
