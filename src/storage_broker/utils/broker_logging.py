import os
import sys
import logging
import socket
import ssl
from logstash_formatter import LogstashFormatterV1


from src.storage_broker.utils import config


def clowder_config():
    # Cloudwatch Configuration with Clowder
    if os.environ.get("ACG_CONFIG"):
        import app_common_python

        cfg = app_common_python.LoadedConfig
        if cfg.logging:
            cw = cfg.logging.cloudwatch
            return cw.accessKeyId, cw.secretAccessKey, cw.region, cw.logGroup, False
        else:
            return None, None, None, None, None


def non_clowder_config():
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", None)
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    aws_region_name = os.getenv("AWS_REGION_NAME", None)
    aws_log_group = os.getenv("AWS_LOG_GROUP", "platform")
    create_log_group = str(os.getenv("AWS_CREATE_LOG_GROUP")).lower() == "true"
    return aws_access_key_id, aws_secret_access_key, aws_region_name, aws_log_group, create_log_group


def log_ssl_fips_info(logger):
    """
    Log SSL and FIPS configuration for debugging boto3/S3 connection issues.
    This helps diagnose SSL errors in FIPS-enabled environments with Python 3.14+.
    """
    try:
        logger.info("=" * 70)
        logger.info("SSL/FIPS Configuration Debug Information")
        logger.info("=" * 70)

        # Python and OpenSSL versions
        logger.info("Python version: %s", sys.version)
        logger.info("OpenSSL version: %s", ssl.OPENSSL_VERSION)
        logger.info("OpenSSL version info: %s", ssl.OPENSSL_VERSION_INFO)

        # boto3/botocore versions (critical for S3 SSL debugging)
        try:
            import boto3
            import botocore
            logger.info("boto3 version: %s", boto3.__version__)
            logger.info("botocore version: %s", botocore.__version__)
        except ImportError as e:
            logger.warning("Could not import boto3/botocore: %s", e)
        except AttributeError:
            logger.warning("Could not determine boto3/botocore versions")

        # FIPS mode check
        fips_mode = "N/A"
        if hasattr(ssl, 'FIPS_mode'):
            try:
                fips_mode = ssl.FIPS_mode()
            except Exception as e:
                fips_mode = f"Error checking FIPS_mode: {e}"
        logger.info("FIPS mode: %s", fips_mode)

        # SSL protocol support
        logger.info("Default SSL context protocol: %s", ssl.PROTOCOL_TLS)
        logger.info("Has SNI support: %s", ssl.HAS_SNI)
        logger.info("Has ALPN support: %s", ssl.HAS_ALPN)
        logger.info("Has NPN support: %s", ssl.HAS_NPN)

        # Available SSL/TLS versions
        logger.info("TLS 1.2 minimum version: %s",
                   hasattr(ssl, 'TLSVersion') and hasattr(ssl.TLSVersion, 'TLSv1_2'))
        logger.info("TLS 1.3 support: %s",
                   hasattr(ssl, 'TLSVersion') and hasattr(ssl.TLSVersion, 'TLSv1_3'))

        # Create a default context and check its settings
        default_context = ssl.create_default_context()
        logger.info("Default context check_hostname: %s", default_context.check_hostname)
        logger.info("Default context verify_mode: %s", default_context.verify_mode)

        # Get available ciphers (limited to first 10 to avoid log spam)
        try:
            ciphers = ssl.get_ciphers()
            logger.info("Total available ciphers: %d", len(ciphers))
            logger.info("First 10 available ciphers:")
            for i, cipher in enumerate(ciphers[:10], 1):
                logger.info("  %d. %s (protocol: %s, bits: %s)",
                           i, cipher.get('name', 'N/A'),
                           cipher.get('protocol', 'N/A'),
                           cipher.get('bits', 'N/A'))
            if len(ciphers) > 10:
                logger.info("  ... and %d more ciphers", len(ciphers) - 10)
        except Exception as e:
            logger.warning("Could not enumerate ciphers: %s", e)

        # Environment variables that might affect SSL
        ssl_env_vars = [
            'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE',
            'CURL_CA_BUNDLE', 'OPENSSL_CONF', 'OPENSSL_FIPS'
        ]
        logger.info("SSL-related environment variables:")
        for var in ssl_env_vars:
            value = os.getenv(var, '<not set>')
            logger.info("  %s: %s", var, value)

        logger.info("=" * 70)

    except Exception as e:
        logger.error("Error logging SSL/FIPS info: %s", e, exc_info=True)


def initialize_logging():
    kafkalogger = logging.getLogger("kafka")
    kafkalogger.setLevel(config.KAFKA_LOG_LEVEL)
    if any("OPENSHIFT" in k for k in os.environ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(LogstashFormatterV1())
        logging.root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
        logging.root.addHandler(handler)
    else:
        logging.basicConfig(
            level=config.LOG_LEVEL,
            format="%(threadName)s %(levelname)s %(name)s - %(message)s",
        )

    if os.environ.get("ACG_CONFIG"):
        f = clowder_config
    else:
        f = non_clowder_config

    aws_access_key_id, aws_secret_access_key, aws_region_name, aws_log_group, create_log_group = f()

    if all((aws_access_key_id, aws_secret_access_key, aws_region_name, aws_log_group)):
        from boto3.session import Session
        import watchtower

        boto3_session = Session(aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key,
                                region_name=aws_region_name)

        cw_handler = watchtower.CloudWatchLogHandler(boto3_client=boto3_session.client("logs"),
                                                     log_group=aws_log_group,
                                                     stream_name=socket.gethostname(),
                                                     create_log_group=create_log_group)

        cw_handler.setFormatter(LogstashFormatterV1())
        logging.root.addHandler(cw_handler)

    logger = logging.getLogger(config.APP_NAME)

    # Log SSL/FIPS configuration for debugging
    log_ssl_fips_info(logger)

    return logger
