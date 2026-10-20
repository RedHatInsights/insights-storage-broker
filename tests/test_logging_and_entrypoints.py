import logging
import sys
from types import SimpleNamespace

import pytest
import watchtower

from src.storage_broker import consumer_api
from src.storage_broker.utils import broker_logging


@pytest.fixture
def clean_root_logger():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield root
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.fixture
def no_cloudwatch_env(monkeypatch):
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION_NAME", "AWS_LOG_GROUP", "AWS_CREATE_LOG_GROUP"):
        monkeypatch.delenv(key, raising=False)


class FakeCloudWatchHandler(logging.Handler):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs


def test_non_clowder_config_defaults(no_cloudwatch_env):
    assert broker_logging.non_clowder_config() == (None, None, None, "platform", False)


def test_non_clowder_config_from_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_REGION_NAME", "us-east-1")
    monkeypatch.setenv("AWS_LOG_GROUP", "group")
    monkeypatch.setenv("AWS_CREATE_LOG_GROUP", "TRUE")
    assert broker_logging.non_clowder_config() == ("key", "secret", "us-east-1", "group", True)


def test_clowder_config(monkeypatch):
    cw = SimpleNamespace(accessKeyId="k", secretAccessKey="s", region="r", logGroup="g")
    fake_acp = SimpleNamespace(LoadedConfig=SimpleNamespace(logging=SimpleNamespace(cloudwatch=cw)))
    monkeypatch.setenv("ACG_CONFIG", "/dev/null")
    monkeypatch.setitem(sys.modules, "app_common_python", fake_acp)
    assert broker_logging.clowder_config() == ("k", "s", "r", "g", False)


def test_clowder_config_without_logging(monkeypatch):
    fake_acp = SimpleNamespace(LoadedConfig=SimpleNamespace(logging=None))
    monkeypatch.setenv("ACG_CONFIG", "/dev/null")
    monkeypatch.setitem(sys.modules, "app_common_python", fake_acp)
    assert broker_logging.clowder_config() == (None, None, None, None, None)


def test_initialize_logging_local(clean_root_logger, no_cloudwatch_env, monkeypatch):
    monkeypatch.setattr(watchtower, "CloudWatchLogHandler", FakeCloudWatchHandler)
    logger = broker_logging.initialize_logging()
    assert logger.name == "insights-storage-broker"
    assert not any(isinstance(h, FakeCloudWatchHandler) for h in clean_root_logger.handlers)


def test_initialize_logging_openshift_uses_logstash(clean_root_logger, no_cloudwatch_env, monkeypatch):
    monkeypatch.setenv("OPENSHIFT_BUILD_NAME", "x")
    broker_logging.initialize_logging()
    stdout_handlers = [h for h in clean_root_logger.handlers if getattr(h, "stream", None) is sys.stdout]
    assert stdout_handlers
    assert type(stdout_handlers[-1].formatter).__name__ == "LogstashFormatterV1"


def test_initialize_logging_adds_cloudwatch(clean_root_logger, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_REGION_NAME", "us-east-1")
    monkeypatch.setenv("AWS_LOG_GROUP", "group")
    monkeypatch.setattr(watchtower, "CloudWatchLogHandler", FakeCloudWatchHandler)

    broker_logging.initialize_logging()

    [cw] = [h for h in clean_root_logger.handlers if isinstance(h, FakeCloudWatchHandler)]
    assert cw.kwargs["log_group"] == "group"
    assert cw.kwargs["create_log_group"] is False
    assert type(cw.formatter).__name__ == "LogstashFormatterV1"


def test_consumer_api_runs_consumer_and_api(monkeypatch):
    calls = []
    monkeypatch.setattr(consumer_api, "consumer", lambda event: calls.append(("consumer", event)))
    monkeypatch.setattr(consumer_api, "api", lambda: calls.append(("api",)))
    monkeypatch.setattr(consumer_api.signal, "pause", lambda: None)

    consumer_api.main()

    assert ("consumer", consumer_api.event) in calls
    assert ("api",) in calls


def test_consumer_api_signal_handler_sets_event(monkeypatch):
    monkeypatch.setattr(consumer_api, "event", consumer_api.Event())
    consumer_api.signal_handler(15, None)
    assert consumer_api.event.is_set()
