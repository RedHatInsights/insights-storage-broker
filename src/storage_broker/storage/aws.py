import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.storage_broker.utils import config
from src.storage_broker.utils import metrics

logger = logging.getLogger(config.APP_NAME)


def _count_retries(parsed=None, model=None, **kwargs):
    attempts = (parsed or {}).get("ResponseMetadata", {}).get("RetryAttempts", 0)
    if attempts:
        metrics.storage_retry_count.labels(operation=model.name).inc(attempts)


def make_client():
    client = boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT_URL,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        # botocore normalizes Config's "max_attempts" into "total_max_attempts"
        # (value + 1), so pass total_max_attempts directly: it is the real
        # attempt ceiling, initial request included.
        config=Config(retries={"mode": "standard", "total_max_attempts": config.S3_MAX_ATTEMPTS}),
    )
    client.meta.events.register("after-call.s3", _count_retries)
    return client


s3 = make_client()


def _observe_size(size, service):
    # Upstream services send size as an int, a numeric string, or not at all.
    # A bad size must never stop the payload from being copied.
    try:
        metrics.payload_size.labels(service=service).observe(float(size))
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid payload size %r for service %s", size, service)


@metrics.storage_copy_time.time()
def copy(key, src, dest, new_key, size, service):
    _observe_size(size, service)
    copy_src = {"Bucket": src, "Key": key}
    try:
        s3.copy(copy_src, dest, new_key)
        logger.info("Request ID [%s] moved to [%s]", new_key, dest)
        metrics.storage_copy_success.labels(bucket=dest).inc()
    except Exception:
        logger.exception("Unable to move %s to %s bucket", key, dest)
        metrics.storage_copy_error.labels(bucket=dest).inc()
        raise


@metrics.storage_key_check_time.time()
def check_key(bucket, request_id):
    try:
        s3.head_object(Bucket=bucket, Key=request_id)
        return None
    except ClientError as e:
        return e


@metrics.presigned_url_gen_time.time()
def get_url(bucket, request_id, expiry):
    try:
        return s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": request_id}, ExpiresIn=expiry)
    except ClientError:
        raise
