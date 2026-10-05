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
from datetime import datetime


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


def save_cipher_reproducers(context):
    """Save cipher lists in formats for building reproducers"""
    try:
        if not hasattr(context, 'get_ciphers'):
            return

        ciphers = context.get_ciphers()
        if not ciphers:
            return

        cipher_names = []
        for cipher in ciphers:
            if isinstance(cipher, dict):
                name = cipher.get('name', '')
                if name:
                    cipher_names.append(name)
            elif isinstance(cipher, tuple) and len(cipher) > 0:
                cipher_names.append(str(cipher[0]))

        if not cipher_names:
            return

        print(f"\n{'='*70}")
        print("CIPHER REPRODUCER FORMATS")
        print(f"{'='*70}")

        # 1. OpenSSL command line format
        openssl_cipher_string = ':'.join(cipher_names)
        print("\n1. OpenSSL command line format:")
        print(f"   Use with: openssl s_client -cipher '<cipher_string>'")
        print(f"\n   Cipher string (copy this):")
        print(f"   {openssl_cipher_string}")

        # 2. Python ssl.SSLContext format (same as OpenSSL)
        print("\n2. Python ssl.SSLContext.set_ciphers() format:")
        print(f"   context.set_ciphers('{openssl_cipher_string}')")

        # 3. Save to files
        try:
            # Save full cipher string
            with open('cipher_string.txt', 'w') as f:
                f.write(openssl_cipher_string)
            print("\n3. Saved cipher string to: cipher_string.txt")

            # Save OpenSSL test command
            with open('test_openssl_ciphers.sh', 'w') as f:
                f.write("#!/bin/bash\n")
                f.write("# OpenSSL cipher test using detected ciphers\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                f.write(f"ENDPOINT=\"{os.getenv('S3_ENDPOINT_URL', 'https://s3.us-east-1.amazonaws.com')}\"\n")
                f.write(f"CIPHER_STRING=\"{openssl_cipher_string}\"\n\n")
                f.write("# Parse hostname and port from endpoint\n")
                f.write("HOSTNAME=$(echo \"$ENDPOINT\" | sed -e 's|^[^/]*//||' -e 's|:.*||' -e 's|/.*||')\n")
                f.write("PORT=$(echo \"$ENDPOINT\" | sed -n 's|.*:\\([0-9]*\\).*|\\1|p')\n")
                f.write("PORT=${PORT:-443}\n\n")
                f.write('echo "Testing SSL connection to $HOSTNAME:$PORT with detected ciphers..."\n')
                f.write('echo ""\n\n')
                f.write('openssl s_client -connect "$HOSTNAME:$PORT" -servername "$HOSTNAME" -cipher "$CIPHER_STRING"\n')
            os.chmod('test_openssl_ciphers.sh', 0o755)
            print("4. Saved OpenSSL test script to: test_openssl_ciphers.sh")

            # Save Python reproducer
            with open('test_python_ssl_reproducer.py', 'w') as f:
                f.write("#!/usr/bin/env python3\n")
                f.write('"""\n')
                f.write("SSL/TLS Reproducer using detected cipher suite\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write('"""\n\n')
                f.write("import ssl\n")
                f.write("import socket\n")
                f.write("import sys\n\n")
                f.write(f"CIPHER_STRING = '{openssl_cipher_string}'\n\n")
                f.write("def test_ssl_with_ciphers(hostname, port=443):\n")
                f.write('    """Test SSL connection using specific cipher suite"""\n')
                f.write(f'    print(f"Testing SSL to {{hostname}}:{{port}} with detected ciphers...")\n')
                f.write(f'    print(f"Python: {{sys.version}}")\n')
                f.write(f'    print(f"OpenSSL: {{ssl.OPENSSL_VERSION}}")\n')
                f.write('    print(f"\\nCipher string: {CIPHER_STRING}\\n")\n\n')
                f.write("    # Create socket\n")
                f.write("    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n")
                f.write("    sock.settimeout(10)\n\n")
                f.write("    try:\n")
                f.write("        # Connect\n")
                f.write("        sock.connect((hostname, port))\n")
                f.write('        print("✓ TCP connection established")\n\n')
                f.write("        # Create SSL context with specific ciphers\n")
                f.write("        context = ssl.create_default_context()\n")
                f.write("        context.set_ciphers(CIPHER_STRING)\n")
                f.write('        print("✓ SSL context created with cipher restriction")\n\n')
                f.write("        # Wrap socket\n")
                f.write("        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)\n")
                f.write('        print("✓ SSL handshake successful!")\n\n')
                f.write("        # Show what was negotiated\n")
                f.write('        print(f"  Protocol: {ssl_sock.version()}")\n')
                f.write('        print(f"  Cipher: {ssl_sock.cipher()}")\n\n')
                f.write("        ssl_sock.close()\n")
                f.write("        return True\n\n")
                f.write("    except ssl.SSLError as e:\n")
                f.write('        print(f"\\n✗ SSL Error: {e}")\n')
                f.write("        import traceback\n")
                f.write("        traceback.print_exc()\n")
                f.write("        return False\n")
                f.write("    finally:\n")
                f.write("        sock.close()\n\n")
                f.write('if __name__ == "__main__":\n')
                f.write('    import os\n')
                f.write('    from urllib.parse import urlparse\n\n')
                f.write('    # Get endpoint from environment or use default\n')
                f.write(f'    endpoint = os.getenv("S3_ENDPOINT_URL", "https://s3.us-east-1.amazonaws.com")\n')
                f.write('    parsed = urlparse(endpoint)\n')
                f.write('    hostname = parsed.hostname or "s3.us-east-1.amazonaws.com"\n')
                f.write('    port = parsed.port or 443\n\n')
                f.write('    success = test_ssl_with_ciphers(hostname, port)\n')
                f.write('    sys.exit(0 if success else 1)\n')
            os.chmod('test_python_ssl_reproducer.py', 0o755)
            print("5. Saved Python reproducer to: test_python_ssl_reproducer.py")

            # Save boto3 reproducer
            with open('test_boto3_reproducer.py', 'w') as f:
                f.write("#!/usr/bin/env python3\n")
                f.write('"""\n')
                f.write("boto3 S3 Reproducer using detected cipher suite\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write('"""\n\n')
                f.write("import ssl\n")
                f.write("import sys\n")
                f.write("import os\n")
                f.write("import logging\n\n")
                f.write("# Enable debug logging\n")
                f.write("logging.basicConfig(level=logging.DEBUG)\n\n")
                f.write(f"CIPHER_STRING = '{openssl_cipher_string}'\n\n")
                f.write("def test_boto3_with_ciphers():\n")
                f.write('    """Test boto3 S3 with specific cipher suite"""\n')
                f.write('    print("="*70)\n')
                f.write('    print("boto3 S3 Reproducer with Detected Ciphers")\n')
                f.write('    print("="*70)\n')
                f.write(f'    print(f"Python: {{sys.version}}")\n')
                f.write(f'    print(f"OpenSSL: {{ssl.OPENSSL_VERSION}}")\n\n')
                f.write("    try:\n")
                f.write("        import boto3\n")
                f.write("        import botocore\n")
                f.write('        print(f"boto3: {boto3.__version__}")\n')
                f.write('        print(f"botocore: {botocore.__version__}")\n')
                f.write("    except ImportError as e:\n")
                f.write('        print(f"Cannot import boto3: {e}")\n')
                f.write("        return False\n\n")
                f.write('    print(f"\\nCipher string: {CIPHER_STRING}\\n")\n\n')
                f.write("    # Monkey-patch SSL context creation to use our ciphers\n")
                f.write("    original_create_default_context = ssl.create_default_context\n\n")
                f.write("    def patched_create_default_context(*args, **kwargs):\n")
                f.write("        context = original_create_default_context(*args, **kwargs)\n")
                f.write("        context.set_ciphers(CIPHER_STRING)\n")
                f.write('        print("✓ Patched SSL context to use detected ciphers")\n')
                f.write("        return context\n\n")
                f.write("    ssl.create_default_context = patched_create_default_context\n\n")
                f.write("    try:\n")
                f.write("        # Create S3 client\n")
                f.write("        s3 = boto3.client(\n")
                f.write("            's3',\n")
                f.write("            endpoint_url=os.getenv('S3_ENDPOINT_URL'),\n")
                f.write("            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),\n")
                f.write("            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),\n")
                f.write("        )\n")
                f.write('        print("✓ S3 client created\\n")\n\n')
                f.write("        # Test list_buckets\n")
                f.write('        print("Attempting to list buckets...")\n')
                f.write("        response = s3.list_buckets()\n")
                f.write("        print(f\"✓ Successfully listed {len(response['Buckets'])} buckets\")\n")
                f.write("        return True\n\n")
                f.write("    except Exception as e:\n")
                f.write('        print(f"\\n✗ Error: {e}")\n')
                f.write("        import traceback\n")
                f.write("        traceback.print_exc()\n")
                f.write("        return False\n")
                f.write("    finally:\n")
                f.write("        # Restore original\n")
                f.write("        ssl.create_default_context = original_create_default_context\n\n")
                f.write('if __name__ == "__main__":\n')
                f.write("    success = test_boto3_with_ciphers()\n")
                f.write("    sys.exit(0 if success else 1)\n")
            os.chmod('test_boto3_reproducer.py', 0o755)
            print("6. Saved boto3 reproducer to: test_boto3_reproducer.py")

            # Save cipher list (one per line)
            with open('cipher_list.txt', 'w') as f:
                for name in cipher_names:
                    f.write(f"{name}\n")
            print("7. Saved cipher list to: cipher_list.txt")

            print(f"\n{'='*70}")
            print("USAGE:")
            print(f"{'='*70}")
            print("\n  Test with OpenSSL:")
            print("    ./test_openssl_ciphers.sh")
            print("\n  Test with Python SSL:")
            print("    python3 test_python_ssl_reproducer.py")
            print("\n  Test with boto3:")
            print("    export AWS_ACCESS_KEY_ID='your-key'")
            print("    export AWS_SECRET_ACCESS_KEY='your-secret'")
            print("    python3 test_boto3_reproducer.py")
            print(f"\n{'='*70}\n")

        except Exception as e:
            print(f"Warning: Could not save reproducer files: {e}")

    except Exception as e:
        print(f"Error creating cipher reproducers: {e}")
        import traceback
        traceback.print_exc()


def inspect_cipher_structure(context):
    """Inspect the actual structure of cipher data"""
    try:
        if hasattr(context, 'get_ciphers'):
            ciphers = context.get_ciphers()
            if ciphers:
                first_cipher = ciphers[0]
                print(f"\nCipher data type: {type(first_cipher)}")
                if isinstance(first_cipher, dict):
                    print(f"Cipher keys: {list(first_cipher.keys())}")
                    print(f"First cipher full data: {first_cipher}")
                else:
                    print(f"First cipher: {first_cipher}")
    except Exception as e:
        print(f"Cannot inspect cipher structure: {e}")


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

        # Inspect cipher structure to understand the data format
        inspect_cipher_structure(context)

        # Save cipher reproducers
        save_cipher_reproducers(context)

        # Check cipher suite on context
        if hasattr(context, 'get_ciphers'):
            try:
                ctx_ciphers = context.get_ciphers()
                print(f"Context ciphers: {len(ctx_ciphers)}")
                print("First 5 ciphers:")
                for cipher in ctx_ciphers[:5]:
                    # Handle different cipher data structures
                    if isinstance(cipher, dict):
                        name = cipher.get('name', 'Unknown')
                        protocol = cipher.get('protocol', 'Unknown')
                        # Python 3.14 uses 'strength_bits', older versions used 'bits'
                        bits = cipher.get('strength_bits', cipher.get('bits', 'Unknown'))
                        print(f"  - {name}: {protocol}, {bits} bits")
                    elif isinstance(cipher, tuple):
                        # Some Python versions return tuples
                        print(f"  - {cipher}")
                    else:
                        print(f"  - {cipher}")
            except KeyError as e:
                print(f"Cannot access cipher attribute '{e}' - Python 3.14+ API change")
                print("Cipher structure changed in Python 3.14+")
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
