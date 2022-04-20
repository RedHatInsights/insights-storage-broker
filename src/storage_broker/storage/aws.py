import logging
import boto3
from botocore.exceptions import ClientError

from src.storage_broker.utils import config
from src.storage_broker.utils import metrics

logger = logging.getLogger(config.APP_NAME)

s3 = boto3.client(
    "s3",
    endpoint_url=config.S3_ENDPOINT_URL,
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)


@metrics.storage_copy_time.time()
def copy(key, src, dest, new_key, size, service):
    metrics.payload_size.labels(service=service).observe(size)
    copy_src = {"Bucket": src, "Key": key}
    try:
        s3.copy(copy_src, dest, new_key)
        logger.info("Request ID [%s] moved to [%s]", new_key, dest)
        metrics.storage_copy_success.labels(bucket=dest).inc()
    except Exception:
        logger.exception("Unable to move %s to %s bucket", key, dest)
        metrics.storage_copy_error.labels(bucket=dest).inc()

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
