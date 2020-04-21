import logging
import boto3

from botocore.exceptions import ClientError

from storage_broker.utils import config
from storage_broker.utils import metrics

logger = logging.getLogger(config.APP_NAME)

s3 = boto3.client(
    "s3",
    endpoint_url=config.S3_ENDPOINT_URL,
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)


def upload(key, _object, dest):
    try:
        s3.put_object(Body=_object, Key=key, Bucket=dest)
        metrics.storage_put_success.inc()
    except ClientError:
        logger.exception(f"Unable to upload object {key} to {dest}")
        metrics.storage_put_error.inc()


@metrics.storage_copy_time.time()
def copy(key, src, dest, new_key):
    copy_src = {"Bucket": src, "Key": key}
    try:
        s3.copy(copy_src, dest, new_key)
        s3.delete_object(Bucket=src, Key=key)
        logger.info("Request ID [%s] moved to [%s]", new_key, dest)
        metrics.storage_copy_success.inc()
    except ClientError:
        logger.exception(
            "Unable to move %s to %s bucket",
            key,
            dest,
        )
        metrics.storage_copy_error.inc()
