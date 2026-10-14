import importlib
import json
import os
import sys
from types import SimpleNamespace

import pytest

from src.storage_broker.utils import config
from tests.conftest import REPO_ROOT

CLOWDER_CONFIG = {
    "metricsPort": 9000,
    "metricsPath": "/metrics",
    "publicPort": 8000,
    "webPort": 8000,
    "logging": {
        "type": "cloudwatch",
        "cloudwatch": {
            "accessKeyId": "cw-key",
            "secretAccessKey": "cw-secret",
            "region": "us-east-1",
            "logGroup": "cw-group",
        },
    },
    "kafka": {
        "brokers": [
            {
                "hostname": "broker-1",
                "port": 9092,
                "cacert": "CERT",
                "authtype": "sasl",
                "sasl": {
                    "username": "user",
                    "password": "sasl-s3cr3t",
                    "securityProtocol": "SASL_SSL",
                    "saslMechanism": "SCRAM-SHA-512",
                },
            }
        ],
        "topics": [
            {"requestedName": "platform.upload.validation", "name": "env-validation"},
            {"requestedName": "platform.upload.announce", "name": "env-announce"},
            {"requestedName": "platform.payload-status", "name": "env-tracker"},
        ],
    },
    "objectStore": {
        "hostname": "minio",
        "port": 9000,
        "accessKey": "os-key",
        "secretKey": "os-secret",
        "tls": False,
        "buckets": [
            {"requestedName": "insights-upload-perm", "name": "env-perm"},
            {"requestedName": "insights-upload-rejected", "name": "env-rejected"},
        ],
    },
}


@pytest.fixture
def reload_config():
    """Reload config.py under a modified environment, then restore the original module state.

    config is imported by reference everywhere, so reloading mutates the module
    other code sees. Teardown reloads it again under the original environment.
    """
    saved_env = dict(os.environ)

    def _reload(**env):
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        sys.modules.pop("app_common_python", None)
        return importlib.reload(config)

    yield _reload

    os.environ.clear()
    os.environ.update(saved_env)
    sys.modules.pop("app_common_python", None)
    importlib.reload(config)


@pytest.fixture
def clowder_env(tmp_path, reload_config):
    def _load(cdapp=CLOWDER_CONFIG, **env):
        path = tmp_path / "cdappconfig.json"
        path.write_text(json.dumps(cdapp))
        env = {
            "ACG_CONFIG": str(path),
            "PERM_BUCKET": "insights-upload-perm",
            "REJECT_BUCKET": "insights-upload-rejected",
            "AWS_ACCESS_KEY_ID": None,
            "AWS_SECRET_ACCESS_KEY": None,
            **env,
        }
        return reload_config(**env)

    return _load


# --- bucket map helpers -------------------------------------------------------


def test_load_bucket_map(tmp_path):
    path = tmp_path / "map.yaml"
    path.write_text("topic.a:\n  normalizer: Validation\n")
    assert config.load_bucket_map(str(path)) == {"topic.a": {"normalizer": "Validation"}}


def test_load_bucket_map_missing_file_returns_empty(tmp_path):
    assert config.load_bucket_map(str(tmp_path / "nope.yaml")) == {}


def test_load_bucket_map_rejects_unsafe_yaml(tmp_path):
    path = tmp_path / "map.yaml"
    path.write_text("a: !!python/object/apply:os.system ['true']\n")
    assert config.load_bucket_map(str(path)) == {}


@pytest.mark.parametrize("map_file", ["default_map.yaml", "rhosak_map.yaml"])
def test_shipped_bucket_maps_are_well_formed(map_file):
    bucket_map = config.load_bucket_map(str(REPO_ROOT / map_file))
    assert bucket_map
    for topic, conf in bucket_map.items():
        assert "normalizer" in conf, topic
        for service, svc in conf.get("services", {}).items():
            assert svc.get("bucket"), (topic, service)
            assert svc.get("format"), (topic, service)


def test_clowderize_bucket_map():
    topics = {"platform.upload.announce": SimpleNamespace(name="env-announce")}
    assert config.clowderize_bucket_map({"platform.upload.announce": {"normalizer": "Openshift"}}, topics) == {
        "env-announce": {"normalizer": "Openshift"}
    }


def test_clowderize_bucket_map_unknown_topic_raises():
    with pytest.raises(KeyError):
        config.clowderize_bucket_map({"not.provisioned": {}}, {})


def test_get_namespace_outside_openshift():
    assert config.get_namespace() is None


def test_log_config_skips_aws_secrets(caplog):
    with caplog.at_level("INFO", logger=config.APP_NAME):
        config.log_config()
    assert "Using STAGE_BUCKET" in caplog.text
    assert "AWS_SECRET_ACCESS_KEY" not in caplog.text
    assert "AWS_ACCESS_KEY_ID" not in caplog.text


def test_log_config_skips_cloudwatch_secret(caplog, reload_config):
    reload_config(CW_AWS_SECRET_ACCESS_KEY="cw-secret")
    with caplog.at_level("INFO", logger=config.APP_NAME):
        config.log_config()
    assert "cw-secret" not in caplog.text


def test_log_config_does_not_leak_kafka_sasl_password(caplog, clowder_env):
    clowder_env()
    with caplog.at_level("INFO", logger=config.APP_NAME):
        config.log_config()
    assert "Using KAFKA_BROKER" in caplog.text
    assert "sasl-s3cr3t" not in caplog.text


# --- environment (non-Clowder) ------------------------------------------------


def test_defaults(reload_config):
    cfg = reload_config(
        CONSUME_TOPIC=None,
        INGRESS_TOPIC=None,
        TRACKER_TOPIC=None,
        BOOTSTRAP_SERVERS=None,
        STAGE_BUCKET=None,
        REJECT_BUCKET=None,
        MONITORED_SERVICES=None,
        API_URL_EXPIRY=None,
        PROMETHEUS_PORT=None,
        API_PORT=None,
    )
    assert cfg.KAFKA_BROKER is None
    assert cfg.VALIDATION_TOPIC == "platform.upload.validation"
    assert cfg.INGRESS_TOPIC == "platform.upload.announce"
    assert cfg.TRACKER_TOPIC == "platform.payload-status"
    assert cfg.BOOTSTRAP_SERVERS == ["kafka:29092"]
    assert cfg.STAGE_BUCKET == "insights-dev-upload-perm"
    assert cfg.REJECT_BUCKET == "insights-dev-upload-rejected"
    assert cfg.MONITORED_SERVICES == ["openshift", "ansible"]
    assert cfg.API_URL_EXPIRY == 30
    assert cfg.PROMETHEUS_PORT == 8080
    assert cfg.API_PORT == 5000
    assert cfg.BUCKET_MAP == config.load_bucket_map(str(REPO_ROOT / "default_map.yaml"))


def test_env_overrides(reload_config):
    cfg = reload_config(
        CONSUME_TOPIC="v",
        INGRESS_TOPIC="i",
        TRACKER_TOPIC="t",
        BOOTSTRAP_SERVERS="a:1 b:2",
        STAGE_BUCKET="perm",
        REJECT_BUCKET="rej",
        MONITORED_SERVICES="openshift,ansible,tower",
        API_URL_EXPIRY="60",
    )
    assert (cfg.VALIDATION_TOPIC, cfg.INGRESS_TOPIC, cfg.TRACKER_TOPIC) == ("v", "i", "t")
    assert cfg.BOOTSTRAP_SERVERS == ["a:1", "b:2"]
    assert (cfg.STAGE_BUCKET, cfg.REJECT_BUCKET) == ("perm", "rej")
    assert cfg.MONITORED_SERVICES == ["openshift", "ansible", "tower"]
    assert cfg.API_URL_EXPIRY == 60


def test_allow_create_topics_defaults_off(reload_config):
    assert not reload_config(KAFKA_ALLOW_CREATE_TOPICS=None).KAFKA_ALLOW_CREATE_TOPICS


@pytest.mark.xfail(raises=AssertionError, reason="BUG: KAFKA_ALLOW_CREATE_TOPICS is the raw env string, so 'false' is truthy")
def test_allow_create_topics_false_string(reload_config):
    assert not reload_config(KAFKA_ALLOW_CREATE_TOPICS="false").KAFKA_ALLOW_CREATE_TOPICS


@pytest.mark.xfail(raises=AssertionError, reason="BUG: KAFKA_QUEUE_MAX_KBYTES is the raw env string when set, an int only by default")
def test_queue_max_kbytes_is_int(reload_config):
    assert reload_config(KAFKA_QUEUE_MAX_KBYTES="2048").KAFKA_QUEUE_MAX_KBYTES == 2048


# --- Clowder ------------------------------------------------------------------


def test_clowder_config(clowder_env):
    cfg = clowder_env()
    assert cfg.KAFKA_BROKER.hostname == "broker-1"
    assert cfg.KAFKA_BROKER.cacert == "CERT"
    assert cfg.BOOTSTRAP_SERVERS == ["broker-1:9092"]
    assert cfg.VALIDATION_TOPIC == "env-validation"
    assert cfg.INGRESS_TOPIC == "env-announce"
    assert cfg.TRACKER_TOPIC == "env-tracker"
    assert cfg.STAGE_BUCKET == "env-perm"
    assert cfg.REJECT_BUCKET == "env-rejected"
    assert cfg.AWS_ACCESS_KEY_ID == "os-key"
    assert cfg.AWS_SECRET_ACCESS_KEY == "os-secret"
    assert cfg.S3_ENDPOINT_URL == "http://minio:9000"
    assert cfg.CW_AWS_ACCESS_KEY_ID == "cw-key"
    assert cfg.LOG_GROUP == "cw-group"
    assert cfg.PROMETHEUS_PORT == 9000
    assert cfg.API_PORT == 8000


def test_clowder_bucket_map_uses_clowder_topic_names(clowder_env):
    cfg = clowder_env()
    assert set(cfg.BUCKET_MAP) == {"env-validation", "env-announce"}
    assert cfg.BUCKET_MAP["env-announce"]["services"]["openshift"]["bucket"] == "insights-buck-it-openshift"


def test_clowder_https_endpoint_on_443(clowder_env):
    cdapp = json.loads(json.dumps(CLOWDER_CONFIG))
    cdapp["objectStore"]["port"] = 443
    assert clowder_env(cdapp).S3_ENDPOINT_URL == "https://minio:443"


def test_clowder_env_overrides_aws_keys(clowder_env):
    cfg = clowder_env(AWS_ACCESS_KEY_ID="env-key", AWS_SECRET_ACCESS_KEY="env-secret")
    assert cfg.AWS_ACCESS_KEY_ID == "env-key"
    assert cfg.AWS_SECRET_ACCESS_KEY == "env-secret"


def test_clowder_kafka_config(clowder_env):
    from src.storage_broker.mq import common

    cfg = clowder_env()
    assert common.build_confluent_kafka_config(cfg) == {
        "bootstrap.servers": "broker-1:9092",
        "ssl.ca.location": "/tmp/cacert.pem",
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "SCRAM-SHA-512",
        "sasl.username": "user",
        "sasl.password": "sasl-s3cr3t",
    }


def test_clowder_bucket_map_with_unprovisioned_topic_fails(clowder_env, tmp_path):
    map_file = tmp_path / "map.yaml"
    map_file.write_text("platform.not.provisioned:\n  normalizer: Validation\n")
    with pytest.raises(KeyError):
        clowder_env(BUCKET_MAP_FILE=str(map_file))
