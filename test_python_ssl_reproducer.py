#!/usr/bin/env python3
"""
SSL/TLS Reproducer using detected cipher suite
Generated: 2026-10-05T11:41:04.960160
"""

import ssl
import socket
import sys

CIPHER_STRING = 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:TLS_AES_128_CCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-CCM:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-CCM:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:AES256-GCM-SHA384:AES256-CCM:AES128-GCM-SHA256:AES128-CCM:AES256-SHA256:AES128-SHA256:AES256-SHA:AES128-SHA:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES256-CCM:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES128-CCM:DHE-RSA-AES256-SHA256:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:PSK-AES256-GCM-SHA384:PSK-CHACHA20-POLY1305:PSK-AES256-CCM:PSK-AES128-GCM-SHA256:PSK-AES128-CCM:PSK-AES256-CBC-SHA:PSK-AES128-CBC-SHA256:PSK-AES128-CBC-SHA:DHE-PSK-AES256-GCM-SHA384:DHE-PSK-CHACHA20-POLY1305:DHE-PSK-AES256-CCM:DHE-PSK-AES128-GCM-SHA256:DHE-PSK-AES128-CCM:DHE-PSK-AES256-CBC-SHA:DHE-PSK-AES128-CBC-SHA256:DHE-PSK-AES128-CBC-SHA:ECDHE-PSK-CHACHA20-POLY1305:ECDHE-PSK-AES256-CBC-SHA:ECDHE-PSK-AES128-CBC-SHA256:ECDHE-PSK-AES128-CBC-SHA:RSA-PSK-AES256-GCM-SHA384:RSA-PSK-CHACHA20-POLY1305:RSA-PSK-AES128-GCM-SHA256:RSA-PSK-AES256-CBC-SHA:RSA-PSK-AES128-CBC-SHA256:RSA-PSK-AES128-CBC-SHA'

def test_ssl_with_ciphers(hostname, port=443):
    """Test SSL connection using specific cipher suite"""
    print(f"Testing SSL to {hostname}:{port} with detected ciphers...")
    print(f"Python: {sys.version}")
    print(f"OpenSSL: {ssl.OPENSSL_VERSION}")
    print(f"\nCipher string: {CIPHER_STRING}\n")

    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    try:
        # Connect
        sock.connect((hostname, port))
        print("✓ TCP connection established")

        # Create SSL context with specific ciphers
        context = ssl.create_default_context()
        context.set_ciphers(CIPHER_STRING)
        print("✓ SSL context created with cipher restriction")

        # Wrap socket
        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
        print("✓ SSL handshake successful!")

        # Show what was negotiated
        print(f"  Protocol: {ssl_sock.version()}")
        print(f"  Cipher: {ssl_sock.cipher()}")

        ssl_sock.close()
        return True

    except ssl.SSLError as e:
        print(f"\n✗ SSL Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    import os
    from urllib.parse import urlparse

    # Get endpoint from environment or use default
    endpoint = os.getenv("S3_ENDPOINT_URL", "https://s3.us-east-1.amazonaws.com")
    parsed = urlparse(endpoint)
    hostname = parsed.hostname or "s3.us-east-1.amazonaws.com"
    port = parsed.port or 443

    success = test_ssl_with_ciphers(hostname, port)
    sys.exit(0 if success else 1)
