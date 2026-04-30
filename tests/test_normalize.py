from storage_broker import normalizers
from storage_broker.normalizers import resolve_normalizer


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
