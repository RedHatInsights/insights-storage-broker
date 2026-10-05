#!/usr/bin/env python3
"""
Detailed SSL/TLS Error Debugger for boto3/S3 connections

This script enables maximum verbosity to capture detailed SSL/TLS error information.
"""

import sys
import os
import ssl
import socket
import logging
import traceback


def enable_debug_logging():
    """Enable verbose logging for boto3, botocore, and urllib3"""
    # Set up detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Enable boto3/botocore debug logging
    logging.getLogger('boto3').setLevel(logging.DEBUG)
    logging.getLogger('botocore').setLevel(logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.DEBUG)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.DEBUG)

    # Enable HTTP connection debugging
    try:
        import http.client as http_client
        http_client.HTTPConnection.debuglevel = 1
    except ImportError:
        pass


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_ssl_context():
    """Check SSL context capabilities"""
    print_section("SSL Context Analysis")

    try:
        context = ssl.create_default_context()

        print(f"Protocol: {context.protocol}")
        print(f"Check hostname: {context.check_hostname}")
        print(f"Verify mode: {context.verify_mode}")

        # Get minimum/maximum TLS version
        if hasattr(context, 'minimum_version'):
            print(f"Minimum TLS version: {context.minimum_version}")
        if hasattr(context, 'maximum_version'):
            print(f"Maximum TLS version: {context.maximum_version}")

        # Try to get cipher list
        print("\nAttempting to get cipher list...")
        if hasattr(ssl, 'get_ciphers'):
            try:
                ciphers = ssl.get_ciphers()
                print(f"Available ciphers: {len(ciphers)}")
            except Exception as e:
                print(f"Cannot enumerate ciphers: {e}")
        else:
            print("ssl.get_ciphers() not available (Python 3.14+ removed this)")

        # Check cipher suite on context
        if hasattr(context, 'get_ciphers'):
            try:
                ctx_ciphers = context.get_ciphers()
                print(f"Context ciphers: {len(ctx_ciphers)}")
                print("First 5 ciphers:")
                for cipher in ctx_ciphers[:5]:
                    print(f"  - {cipher['name']}: {cipher['protocol']}, {cipher['bits']} bits")
            except Exception as e:
                print(f"Cannot get context ciphers: {e}")

    except Exception as e:
        print(f"Error checking SSL context: {e}")
        traceback.print_exc()


def test_ssl_handshake(hostname, port=443):
    """Test SSL/TLS handshake manually"""
    print_section(f"Manual SSL Handshake Test: {hostname}:{port}")

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        print(f"Connecting to {hostname}:{port}...")
        sock.connect((hostname, port))
        print("✓ TCP connection established")

        # Wrap with SSL
        context = ssl.create_default_context()

        print("Initiating SSL handshake...")
        try:
            ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
            print("✓ SSL handshake successful!")

            # Get connection info
            print(f"\nSSL Connection Details:")
            print(f"  Protocol version: {ssl_sock.version()}")
            print(f"  Cipher: {ssl_sock.cipher()}")

            # Get peer certificate
            cert = ssl_sock.getpeercert()
            if cert:
                print(f"\nCertificate Info:")
                print(f"  Subject: {dict(x[0] for x in cert['subject'])}")
                print(f"  Issuer: {dict(x[0] for x in cert['issuer'])}")
                print(f"  Valid from: {cert['notBefore']}")
                print(f"  Valid until: {cert['notAfter']}")

            ssl_sock.close()

        except ssl.SSLError as e:
            print(f"\n✗ SSL handshake FAILED!")
            print(f"  Error: {e}")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error args: {e.args}")

            # Print detailed error info
            if hasattr(e, 'reason'):
                print(f"  Reason: {e.reason}")
            if hasattr(e, 'library'):
                print(f"  Library: {e.library}")
            if hasattr(e, 'errno'):
                print(f"  Errno: {e.errno}")

            traceback.print_exc()
            return False

    except socket.error as e:
        print(f"✗ Socket error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        traceback.print_exc()
        return False
    finally:
        try:
            sock.close()
        except:
            pass

    return True


def test_boto3_connection_detailed():
    """Test boto3 S3 connection with maximum verbosity"""
    print_section("boto3 S3 Connection Test (Verbose Mode)")

    # Get configuration
    endpoint_url = os.getenv('S3_ENDPOINT_URL')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    bucket = os.getenv('STAGE_BUCKET', 'test-bucket')

    print(f"Configuration:")
    print(f"  Endpoint URL: {endpoint_url or 'default (AWS)'}")
    print(f"  Access Key: {'***' if access_key else '<not set>'}")
    print(f"  Secret Key: {'***' if secret_key else '<not set>'}")
    print(f"  Bucket: {bucket}")

    if not access_key or not secret_key:
        print("\n⚠ AWS credentials not set. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False

    try:
        import boto3
        import botocore

        print(f"\nboto3 version: {boto3.__version__}")
        print(f"botocore version: {botocore.__version__}")

        print("\nCreating S3 client...")

        # Create client with verbose logging already enabled
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        print("✓ S3 client created")

        print("\nAttempting to list buckets...")
        try:
            response = s3.list_buckets()
            print(f"✓ Successfully listed {len(response['Buckets'])} buckets")
            return True

        except Exception as e:
            print(f"\n✗ list_buckets() FAILED!")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {str(e)}")

            # Detailed error analysis
            if hasattr(e, '__dict__'):
                print(f"\n  Error attributes:")
                for key, value in e.__dict__.items():
                    print(f"    {key}: {value}")

            # Check for SSL-specific errors
            error_str = str(e).lower()
            if 'ssl' in error_str:
                print("\n  ⚠ This appears to be an SSL/TLS error!")
                if 'internal error' in error_str:
                    print("     - 'internal error' suggests OpenSSL/Python version incompatibility")
                if 'certificate' in error_str:
                    print("     - Certificate validation issue")
                if 'handshake' in error_str:
                    print("     - SSL handshake failed")
                if 'protocol' in error_str:
                    print("     - TLS protocol version mismatch")

            print("\n  Full traceback:")
            traceback.print_exc()
            return False

    except ImportError as e:
        print(f"✗ Cannot import boto3: {e}")
        return False


def test_urllib3_connection():
    """Test raw urllib3 connection to S3"""
    print_section("urllib3 Direct Connection Test")

    endpoint_url = os.getenv('S3_ENDPOINT_URL', 'https://s3.us-east-1.amazonaws.com')

    # Parse hostname from URL
    from urllib.parse import urlparse
    parsed = urlparse(endpoint_url)
    hostname = parsed.hostname or 's3.us-east-1.amazonaws.com'

    try:
        import urllib3
        print(f"urllib3 version: {urllib3.__version__}")

        # Try with default SSL
        print(f"\nTesting connection to {endpoint_url}...")
        http = urllib3.PoolManager()

        try:
            response = http.request('GET', endpoint_url)
            print(f"✓ Connection successful! Status: {response.status}")
            return True
        except urllib3.exceptions.SSLError as e:
            print(f"✗ SSL Error: {e}")
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            return False

    except ImportError:
        print("urllib3 not available")
        return False


def check_openssl_compatibility():
    """Check OpenSSL compatibility with Python"""
    print_section("OpenSSL/Python Compatibility Check")

    print(f"Python version: {sys.version}")
    print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
    print(f"OpenSSL version number: {ssl.OPENSSL_VERSION_INFO}")

    # Check for known incompatibilities
    warnings = []

    # Python 3.14 + boto3 incompatibility
    if sys.version_info >= (3, 14):
        warnings.append("⚠ Python 3.14+ has SSL API changes incompatible with current boto3/botocore")
        warnings.append("  Recommendation: Use Python 3.12.x")

    # OpenSSL 3.5+ might have issues
    if ssl.OPENSSL_VERSION_INFO >= (3, 5, 0):
        warnings.append("⚠ OpenSSL 3.5+ is very new and may have compatibility issues")
        warnings.append("  Recommendation: Use OpenSSL 3.2.x if possible")

    if warnings:
        print("\nCompatibility Warnings:")
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("\n✓ No obvious compatibility issues detected")


def main():
    """Main debugging routine"""
    print("=" * 80)
    print("  SSL/TLS Detailed Error Debugger for boto3/S3")
    print("=" * 80)
    print("\nThis script will run comprehensive SSL/TLS diagnostics.")
    print("All logging is enabled for maximum detail.\n")

    # Enable debug logging first
    print("Enabling debug logging...")
    enable_debug_logging()

    # Run diagnostics
    check_openssl_compatibility()
    check_ssl_context()

    # Test SSL handshake to S3
    endpoint_url = os.getenv('S3_ENDPOINT_URL', 'https://s3.us-east-1.amazonaws.com')
    from urllib.parse import urlparse
    parsed = urlparse(endpoint_url)
    hostname = parsed.hostname or 's3.us-east-1.amazonaws.com'
    port = parsed.port or 443

    handshake_ok = test_ssl_handshake(hostname, port)

    # Test urllib3 (lower level than boto3)
    urllib3_ok = test_urllib3_connection()

    # Test boto3 connection
    boto3_ok = test_boto3_connection_detailed()

    # Summary
    print_section("Debugging Summary")
    print(f"SSL Handshake Test:      {'✓ PASS' if handshake_ok else '✗ FAIL'}")
    print(f"urllib3 Connection Test: {'✓ PASS' if urllib3_ok else '✗ FAIL'}")
    print(f"boto3 S3 Test:           {'✓ PASS' if boto3_ok else '✗ FAIL'}")

    if not handshake_ok:
        print("\n⚠ SSL handshake failed at the lowest level!")
        print("  This indicates a fundamental SSL/TLS incompatibility.")
        print("  Check Python version, OpenSSL version, and cipher compatibility.")
    elif not urllib3_ok:
        print("\n⚠ urllib3 failed but raw SSL handshake worked")
        print("  This suggests an issue with urllib3 or certificate validation")
    elif not boto3_ok:
        print("\n⚠ boto3 failed but lower levels worked")
        print("  This suggests a boto3/botocore specific issue")
        print("  Check boto3/botocore versions and compatibility with Python/OpenSSL")
    else:
        print("\n✓ All tests passed! Connection is working.")

    print("\n" + "=" * 80)
    return 0 if (handshake_ok and urllib3_ok and boto3_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
