#!/usr/bin/env python3
"""
S3 Connection Test Script

This script tests boto3/S3 connectivity using the same configuration
as the storage-broker application. Use it to diagnose SSL/TLS issues.

Usage:
    # Set environment variables (same as storage-broker)
    export AWS_ACCESS_KEY_ID="your-key"
    export AWS_SECRET_ACCESS_KEY="your-secret"
    export S3_ENDPOINT_URL="https://s3.us-east-1.amazonaws.com"
    export STAGE_BUCKET="your-bucket-name"

    # Run the test
    python3 test_s3_connection.py

    # Or with verbose SSL debugging
    python3 test_s3_connection.py --verbose
"""

import sys
import os
import ssl
import argparse
from datetime import datetime


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text):
    """Print a section header"""
    print(f"\n>>> {text}")


def print_success(text):
    """Print success message"""
    print(f"✓ {text}")


def print_error(text):
    """Print error message"""
    print(f"✗ {text}")


def print_warning(text):
    """Print warning message"""
    print(f"⚠ {text}")


def check_ssl_environment(verbose=False):
    """Check SSL/TLS environment and configuration"""
    print_header("SSL/TLS Environment Check")

    # Python and OpenSSL versions
    print_section("Python & OpenSSL")
    print(f"Python version: {sys.version}")
    print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
    print(f"OpenSSL version info: {ssl.OPENSSL_VERSION_INFO}")

    # Check for Python 3.14 (known issue)
    if sys.version_info >= (3, 14):
        print_error("Python 3.14+ detected - known boto3/SSL compatibility issues!")
        print_warning("Recommended: Use Python 3.12.x")
    else:
        print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} is compatible")

    # Check boto3/botocore
    print_section("boto3/botocore")
    try:
        import boto3
        import botocore
        print(f"boto3 version: {boto3.__version__}")
        print(f"botocore version: {botocore.__version__}")
        print_success("boto3 and botocore imported successfully")
    except ImportError as e:
        print_error(f"Failed to import boto3/botocore: {e}")
        sys.exit(1)

    # SSL configuration
    if verbose:
        print_section("SSL Configuration")
        print(f"Default SSL protocol: {ssl.PROTOCOL_TLS}")
        print(f"SNI support: {ssl.HAS_SNI}")
        print(f"ALPN support: {ssl.HAS_ALPN}")
        print(f"TLS 1.2: {hasattr(ssl, 'TLSVersion') and hasattr(ssl.TLSVersion, 'TLSv1_2')}")
        print(f"TLS 1.3: {hasattr(ssl, 'TLSVersion') and hasattr(ssl.TLSVersion, 'TLSv1_3')}")

        # Default context
        default_context = ssl.create_default_context()
        print(f"Check hostname: {default_context.check_hostname}")
        print(f"Verify mode: {default_context.verify_mode}")

    # Environment variables
    print_section("SSL Environment Variables")
    ssl_env_vars = ['SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE',
                    'CURL_CA_BUNDLE', 'OPENSSL_CONF', 'OPENSSL_FIPS']
    has_custom = False
    for var in ssl_env_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var}: {value}")
            has_custom = True

    if not has_custom:
        print_success("No custom SSL environment variables set (using defaults)")

    return boto3, botocore


def get_s3_config():
    """Get S3 configuration from environment (matches storage-broker config)"""
    print_header("S3 Configuration")

    config = {
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        's3_endpoint_url': os.getenv('S3_ENDPOINT_URL'),
        'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
        'stage_bucket': os.getenv('STAGE_BUCKET', 'insights-dev-upload-perm'),
        'reject_bucket': os.getenv('REJECT_BUCKET', 'insights-dev-upload-rejected'),
    }

    # Display config (hide secrets)
    print_section("Configuration from Environment")
    for key, value in config.items():
        if 'secret' in key.lower():
            display_value = '***' if value else '<not set>'
        else:
            display_value = value if value else '<not set>'
        print(f"  {key}: {display_value}")

    # Validation
    print_section("Configuration Validation")
    issues = []

    if not config['aws_access_key_id']:
        issues.append("AWS_ACCESS_KEY_ID is not set")
    else:
        print_success("AWS_ACCESS_KEY_ID is set")

    if not config['aws_secret_access_key']:
        issues.append("AWS_SECRET_ACCESS_KEY is not set")
    else:
        print_success("AWS_SECRET_ACCESS_KEY is set")

    if config['s3_endpoint_url']:
        print_success(f"S3_ENDPOINT_URL: {config['s3_endpoint_url']}")
        if not config['s3_endpoint_url'].startswith(('http://', 'https://')):
            print_warning("S3_ENDPOINT_URL should start with http:// or https://")
    else:
        print_warning("S3_ENDPOINT_URL not set (will use AWS defaults)")

    if issues:
        print_error("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nSet missing environment variables and try again.")
        sys.exit(1)

    return config


def create_s3_client(boto3, config, verbose=False):
    """Create S3 client using the same approach as storage-broker"""
    print_header("Creating S3 Client")

    print_section("Client Configuration")
    client_kwargs = {
        's3': {
            'endpoint_url': config['s3_endpoint_url'],
            'aws_access_key_id': config['aws_access_key_id'],
            'aws_secret_access_key': config['aws_secret_access_key'],
        }
    }

    # Display what we're using (matches storage-broker/aws.py approach)
    print("Creating boto3.client with:")
    print(f"  service: 's3'")
    print(f"  endpoint_url: {config['s3_endpoint_url'] or 'default'}")
    print(f"  aws_access_key_id: {'***' if config['aws_access_key_id'] else None}")
    print(f"  aws_secret_access_key: {'***' if config['aws_secret_access_key'] else None}")

    try:
        # This matches exactly how storage-broker creates its client
        # See: src/storage_broker/storage/aws.py
        s3 = boto3.client(
            "s3",
            endpoint_url=config['s3_endpoint_url'],
            aws_access_key_id=config['aws_access_key_id'],
            aws_secret_access_key=config['aws_secret_access_key'],
        )
        print_success("S3 client created successfully")

        if verbose:
            print(f"  Client region: {s3.meta.region_name}")
            print(f"  Client endpoint: {s3.meta.endpoint_url}")

        return s3

    except Exception as e:
        print_error(f"Failed to create S3 client: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_s3_operations(s3, config, verbose=False):
    """Test S3 operations to diagnose connectivity issues"""
    print_header("Testing S3 Operations")

    results = {
        'passed': 0,
        'failed': 0,
        'warnings': 0
    }

    # Test 1: List buckets
    print_section("Test 1: List Buckets")
    try:
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        print_success(f"Successfully listed {len(buckets)} buckets")
        if verbose and buckets:
            for bucket in buckets[:5]:  # Show first 5
                print(f"  - {bucket}")
            if len(buckets) > 5:
                print(f"  ... and {len(buckets) - 5} more")
        results['passed'] += 1
    except Exception as e:
        print_error(f"Failed to list buckets: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        results['failed'] += 1

        # Check for SSL errors
        if 'SSL' in str(e) or 'ssl' in str(e).lower():
            print_warning("This appears to be an SSL/TLS error!")
            print("Common causes:")
            print("  - Python 3.14+ incompatibility with boto3")
            print("  - OpenSSL version mismatch")
            print("  - FIPS mode restrictions")
            print("  - Certificate validation issues")

    # Test 2: Check if stage bucket exists
    print_section(f"Test 2: Check Bucket Access ({config['stage_bucket']})")
    try:
        s3.head_bucket(Bucket=config['stage_bucket'])
        print_success(f"Successfully accessed bucket: {config['stage_bucket']}")
        results['passed'] += 1
    except Exception as e:
        error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown')
        if error_code == '404' or 'NotFound' in str(e):
            print_warning(f"Bucket not found: {config['stage_bucket']}")
            print("  This may be expected if the bucket doesn't exist yet")
            results['warnings'] += 1
        elif error_code == '403' or 'Forbidden' in str(e):
            print_error(f"Access denied to bucket: {config['stage_bucket']}")
            print("  Check your AWS credentials and bucket permissions")
            results['failed'] += 1
        else:
            print_error(f"Failed to access bucket: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            results['failed'] += 1

    # Test 3: Test object operations (if bucket accessible)
    print_section("Test 3: Object Operations")
    test_key = f"test-connection-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    try:
        # Try to check if a test object exists (head_object)
        # This operation tests the same SSL/TLS path as the actual app
        print(f"Testing head_object with key: {test_key}")
        try:
            s3.head_object(Bucket=config['stage_bucket'], Key=test_key)
            print_warning(f"Test object unexpectedly exists: {test_key}")
        except Exception as e:
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown')
            if error_code == '404' or 'NotFound' in str(e):
                print_success("head_object operation works (object not found as expected)")
                results['passed'] += 1
            else:
                raise
    except Exception as e:
        print_error(f"Failed object operation: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        results['failed'] += 1

    # Test 4: Test presigned URL generation
    print_section("Test 4: Presigned URL Generation")
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': config['stage_bucket'], 'Key': test_key},
            ExpiresIn=30
        )
        print_success("Successfully generated presigned URL")
        if verbose:
            print(f"  URL: {url[:100]}...")
        results['passed'] += 1
    except Exception as e:
        print_error(f"Failed to generate presigned URL: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        results['failed'] += 1

    return results


def print_summary(results):
    """Print test summary"""
    print_header("Test Summary")

    total = results['passed'] + results['failed'] + results['warnings']
    print(f"\nTotal tests: {total}")
    print(f"  ✓ Passed:   {results['passed']}")
    print(f"  ✗ Failed:   {results['failed']}")
    print(f"  ⚠ Warnings: {results['warnings']}")

    if results['failed'] == 0:
        print("\n✓ All critical tests passed!")
        print("S3 connection is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed!")
        print("Review the errors above for troubleshooting.")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Test S3 connectivity using storage-broker configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Environment Variables (same as storage-broker):
  AWS_ACCESS_KEY_ID       - AWS access key
  AWS_SECRET_ACCESS_KEY   - AWS secret key
  S3_ENDPOINT_URL         - S3 endpoint (optional, for custom endpoints)
  AWS_REGION              - AWS region (default: us-east-1)
  STAGE_BUCKET            - Bucket to test (default: insights-dev-upload-perm)
  REJECT_BUCKET           - Reject bucket name

Examples:
  # Test with AWS defaults
  export AWS_ACCESS_KEY_ID="AKIA..."
  export AWS_SECRET_ACCESS_KEY="..."
  python3 test_s3_connection.py

  # Test with custom endpoint
  export S3_ENDPOINT_URL="https://s3.us-east-1.amazonaws.com"
  python3 test_s3_connection.py --verbose
        '''
    )
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    print_header("S3 Connection Test for storage-broker")
    print("This script uses the same boto3 configuration as the storage-broker app")

    # Step 1: Check SSL/TLS environment
    boto3, botocore = check_ssl_environment(verbose=args.verbose)

    # Step 2: Get S3 configuration
    config = get_s3_config()

    # Step 3: Create S3 client (same as storage-broker)
    s3 = create_s3_client(boto3, config, verbose=args.verbose)

    # Step 4: Test S3 operations
    results = test_s3_operations(s3, config, verbose=args.verbose)

    # Step 5: Print summary
    exit_code = print_summary(results)

    print("\n" + "=" * 70)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
