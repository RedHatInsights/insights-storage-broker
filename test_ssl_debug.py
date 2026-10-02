#!/usr/bin/env python3
"""
Quick test script to verify SSL/FIPS debug information.
Run this locally to see what information will be logged at startup.
"""
import sys
import os
import ssl


def log_ssl_fips_info():
    """
    Log SSL and FIPS configuration for debugging boto3/S3 connection issues.
    This helps diagnose SSL errors in FIPS-enabled environments with Python 3.14+.
    """
    try:
        print("=" * 70)
        print("SSL/FIPS Configuration Debug Information")
        print("=" * 70)

        # Python and OpenSSL versions
        print(f"Python version: {sys.version}")
        print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
        print(f"OpenSSL version info: {ssl.OPENSSL_VERSION_INFO}")

        # boto3/botocore versions (critical for S3 SSL debugging)
        try:
            import boto3
            import botocore
            print(f"boto3 version: {boto3.__version__}")
            print(f"botocore version: {botocore.__version__}")
        except ImportError as e:
            print(f"WARNING: Could not import boto3/botocore: {e}")
        except AttributeError:
            print("WARNING: Could not determine boto3/botocore versions")

        # FIPS mode check
        fips_mode = "N/A"
        if hasattr(ssl, 'FIPS_mode'):
            try:
                fips_mode = ssl.FIPS_mode()
            except Exception as e:
                fips_mode = f"Error checking FIPS_mode: {e}"
        print(f"FIPS mode: {fips_mode}")

        # SSL protocol support
        print(f"Default SSL context protocol: {ssl.PROTOCOL_TLS}")
        print(f"Has SNI support: {ssl.HAS_SNI}")
        print(f"Has ALPN support: {ssl.HAS_ALPN}")
        print(f"Has NPN support: {ssl.HAS_NPN}")

        # Available SSL/TLS versions
        print(f"TLS 1.2 minimum version: {hasattr(ssl, 'TLSVersion') and hasattr(ssl.TLSVersion, 'TLSv1_2')}")
        print(f"TLS 1.3 support: {hasattr(ssl, 'TLSVersion') and hasattr(ssl.TLSVersion, 'TLSv1_3')}")

        # Create a default context and check its settings
        default_context = ssl.create_default_context()
        print(f"Default context check_hostname: {default_context.check_hostname}")
        print(f"Default context verify_mode: {default_context.verify_mode}")

        # Get available ciphers (limited to first 10 to avoid log spam)
        try:
            ciphers = ssl.get_ciphers()
            print(f"Total available ciphers: {len(ciphers)}")
            print("First 10 available ciphers:")
            for i, cipher in enumerate(ciphers[:10], 1):
                print(f"  {i}. {cipher.get('name', 'N/A')} (protocol: {cipher.get('protocol', 'N/A')}, bits: {cipher.get('bits', 'N/A')})")
            if len(ciphers) > 10:
                print(f"  ... and {len(ciphers) - 10} more ciphers")
        except AttributeError as e:
            print(f"WARNING: Could not enumerate ciphers: {e}")
            print("NOTE: ssl.get_ciphers() not available - likely Python 3.14+ API change")

        # Environment variables that might affect SSL
        ssl_env_vars = [
            'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE',
            'CURL_CA_BUNDLE', 'OPENSSL_CONF', 'OPENSSL_FIPS'
        ]
        print("SSL-related environment variables:")
        for var in ssl_env_vars:
            value = os.getenv(var, '<not set>')
            print(f"  {var}: {value}")

        print("=" * 70)

    except Exception as e:
        print(f"ERROR: Error logging SSL/FIPS info: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    log_ssl_fips_info()
    print("\nTest complete - SSL/FIPS debug information displayed above")
