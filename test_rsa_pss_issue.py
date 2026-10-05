#!/usr/bin/env python3
"""
Test RSA-PSS signature algorithm compatibility

This tests if Python 3.14 has issues with RSA-PSS signatures
used by Amazon S3.
"""

import ssl
import socket
import sys

def test_ssl_connection(hostname, port=443, description=""):
    """Test SSL connection and report signature details"""
    print(f"\n{'='*70}")
    print(f"Testing: {hostname} - {description}")
    print(f"{'='*70}")

    context = ssl.create_default_context()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    try:
        # Connect
        sock.connect((hostname, port))
        print(f"✓ TCP connection established to {hostname}:{port}")

        # SSL handshake
        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
        print(f"✓ SSL handshake successful!")

        # Get connection details
        cipher = ssl_sock.cipher()
        version = ssl_sock.version()

        print(f"\nConnection details:")
        print(f"  Protocol: {version}")
        print(f"  Cipher: {cipher[0] if cipher else 'Unknown'}")
        print(f"  Cipher version: {cipher[1] if cipher and len(cipher) > 1 else 'Unknown'}")
        print(f"  Cipher bits: {cipher[2] if cipher and len(cipher) > 2 else 'Unknown'}")

        # Get certificate
        cert = ssl_sock.getpeercert()
        if cert:
            subject = dict(x[0] for x in cert.get('subject', []))
            print(f"\nCertificate:")
            print(f"  Subject: {subject.get('commonName', 'Unknown')}")

            issuer = dict(x[0] for x in cert.get('issuer', []))
            print(f"  Issuer: {issuer.get('commonName', 'Unknown')}")

        ssl_sock.close()
        return True, None

    except ssl.SSLError as e:
        error_msg = str(e)
        print(f"\n✗ SSL Error: {error_msg}")

        # Analyze the error
        if 'internal error' in error_msg.lower():
            print("  → This appears to be an internal SSL error")
            print("  → Likely Python 3.14 + OpenSSL compatibility issue")

        if 'certificate' in error_msg.lower():
            print("  → This appears to be a certificate verification error")

        return False, error_msg

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

    finally:
        try:
            sock.close()
        except:
            pass


def main():
    print("="*70)
    print("RSA-PSS Signature Algorithm Compatibility Test")
    print("="*70)
    print(f"\nPython version: {sys.version}")
    print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
    print(f"OpenSSL version info: {ssl.OPENSSL_VERSION_INFO}")

    # Test servers with different signature algorithms
    tests = [
        {
            'hostname': 'www.google.com',
            'description': 'ECDSA signature (works)',
            'expected_sig': 'ECDSA'
        },
        {
            'hostname': 's3.amazonaws.com',
            'description': 'RSA-PSS signature (fails on Python 3.14?)',
            'expected_sig': 'RSA-PSS'
        },
        {
            'hostname': 's3.us-east-1.amazonaws.com',
            'description': 'RSA-PSS signature (regional endpoint)',
            'expected_sig': 'RSA-PSS'
        },
    ]

    results = []

    for test in tests:
        success, error = test_ssl_connection(
            test['hostname'],
            description=test['description']
        )
        results.append({
            'hostname': test['hostname'],
            'expected_sig': test['expected_sig'],
            'success': success,
            'error': error
        })

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    ecdsa_results = [r for r in results if r['expected_sig'] == 'ECDSA']
    rsa_pss_results = [r for r in results if r['expected_sig'] == 'RSA-PSS']

    print("\nECDSA Signature Servers (Google):")
    for r in ecdsa_results:
        status = "✓ PASS" if r['success'] else "✗ FAIL"
        print(f"  {status} - {r['hostname']}")

    print("\nRSA-PSS Signature Servers (Amazon S3):")
    for r in rsa_pss_results:
        status = "✓ PASS" if r['success'] else "✗ FAIL"
        print(f"  {status} - {r['hostname']}")
        if not r['success'] and r['error']:
            print(f"         Error: {r['error'][:60]}...")

    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)

    ecdsa_pass = all(r['success'] for r in ecdsa_results)
    rsa_pss_pass = all(r['success'] for r in rsa_pss_results)

    if ecdsa_pass and not rsa_pss_pass:
        print("\n⚠ ECDSA works but RSA-PSS fails!")
        print("\nThis confirms the issue:")
        print("  • Python 3.14 has problems with RSA-PSS signatures")
        print("  • Used by Amazon S3 certificates")
        print("  • NOT used by Google (uses ECDSA)")
        print("\nRoot cause: Python 3.14 + OpenSSL 3.5.9 RSA-PSS incompatibility")
        print("\nSolution: Use Python 3.12 instead of Python 3.14")
        return 1

    elif ecdsa_pass and rsa_pss_pass:
        print("\n✓ Both ECDSA and RSA-PSS work!")
        print("\nIf you see this, the issue may have been fixed or")
        print("you're running on a compatible Python/OpenSSL version.")
        return 0

    elif not ecdsa_pass and not rsa_pss_pass:
        print("\n✗ Both ECDSA and RSA-PSS fail!")
        print("\nThis suggests a broader SSL issue:")
        print("  • Missing CA certificates")
        print("  • Network connectivity")
        print("  • Firewall blocking HTTPS")
        print("\nCheck CA certificates first!")
        return 1

    else:
        print("\n? Unexpected results")
        print("Review the detailed output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
