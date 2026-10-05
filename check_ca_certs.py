#!/usr/bin/env python3
"""
Check CA certificate configuration in the container
"""
import ssl
import os
import sys

print("=" * 70)
print("CA Certificate Check")
print("=" * 70)

# Check default SSL context
context = ssl.create_default_context()
ca_certs = context.get_ca_certs()

print(f"\nCA certs loaded in default context: {len(ca_certs)}")
if not ca_certs:
    print("⚠ WARNING: No CA certificates loaded!")
else:
    print(f"✓ {len(ca_certs)} CA certificates loaded")

# Check default paths
print("\nDefault CA paths from Python:")
paths = ssl.get_default_verify_paths()
print(f"  cafile: {paths.cafile}")
print(f"  capath: {paths.capath}")
print(f"  openssl_cafile_env: {paths.openssl_cafile_env}")
print(f"  openssl_cafile: {paths.openssl_cafile}")
print(f"  openssl_capath_env: {paths.openssl_capath_env}")
print(f"  openssl_capath: {paths.openssl_capath}")

# Check if files exist
print("\nChecking if CA files exist:")
if paths.cafile:
    exists = os.path.exists(paths.cafile)
    print(f"  {paths.cafile}: {'✓ EXISTS' if exists else '✗ NOT FOUND'}")
if paths.capath:
    exists = os.path.exists(paths.capath)
    print(f"  {paths.capath}: {'✓ EXISTS' if exists else '✗ NOT FOUND'}")

# Check common CA bundle locations
print("\nChecking common CA bundle locations:")
common_paths = [
    '/etc/pki/tls/certs/ca-bundle.crt',
    '/etc/pki/tls/cert.pem',
    '/etc/ssl/certs/ca-certificates.crt',
    '/etc/ssl/certs/ca-bundle.crt',
    '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem',
    '/etc/ssl/cert.pem',
    '/usr/local/share/certs/ca-root-nss.crt',
]

found_bundles = []
for path in common_paths:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✓ {path} ({size:,} bytes)")
        found_bundles.append(path)
    else:
        print(f"  ✗ {path}")

# Check environment variables
print("\nCA-related environment variables:")
ca_env_vars = ['SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE']
for var in ca_env_vars:
    value = os.getenv(var)
    if value:
        print(f"  {var}={value}")
    else:
        print(f"  {var}: <not set>")

print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

if not ca_certs and not found_bundles:
    print("✗ CRITICAL: No CA certificates found!")
    print("  SSL connections will fail with certificate verification errors.")
    print("\n  To fix, install ca-certificates package in Dockerfile:")
    print("    RUN dnf5 install -y ca-certificates")
elif not ca_certs and found_bundles:
    print("⚠ WARNING: CA bundles exist but not loaded by Python!")
    print(f"  Found bundles: {found_bundles}")
    print(f"  But Python is looking at: {paths.cafile}")
    print("\n  Possible fixes:")
    print(f"    1. Set SSL_CERT_FILE environment variable:")
    print(f"       export SSL_CERT_FILE={found_bundles[0]}")
    print(f"    2. Create symlink:")
    print(f"       ln -s {found_bundles[0]} {paths.cafile or '/etc/ssl/cert.pem'}")
else:
    print("✓ CA certificates appear to be properly configured")

print("=" * 70)
