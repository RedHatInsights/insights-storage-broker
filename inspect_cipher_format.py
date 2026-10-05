#!/usr/bin/env python3
"""
Quick script to inspect cipher data structure in Python 3.14+
"""
import ssl
import pprint

print("Python SSL Cipher Structure Inspector")
print("=" * 70)

try:
    # Create default context
    context = ssl.create_default_context()
    print("✓ Created default SSL context")

    # Try to get ciphers
    if hasattr(context, 'get_ciphers'):
        print("✓ context.get_ciphers() is available")

        try:
            ciphers = context.get_ciphers()
            print(f"✓ Got {len(ciphers)} ciphers")

            if ciphers:
                first = ciphers[0]
                print(f"\nFirst cipher type: {type(first)}")
                print(f"First cipher repr: {repr(first)}")

                if isinstance(first, dict):
                    print(f"\nCipher is a dictionary with keys: {list(first.keys())}")
                    print("\nFull first cipher:")
                    pprint.pprint(first)
                elif isinstance(first, tuple):
                    print(f"\nCipher is a tuple with {len(first)} elements")
                    print(f"Elements: {first}")
                else:
                    print(f"\nCipher is: {first}")

                print("\nFirst 3 ciphers:")
                for i, cipher in enumerate(ciphers[:3], 1):
                    print(f"\n  [{i}] Type: {type(cipher)}")
                    if isinstance(cipher, dict):
                        # Try to extract common fields
                        name = cipher.get('name', cipher.get('cipher', 'unknown'))
                        protocol = cipher.get('protocol', cipher.get('version', 'unknown'))
                        print(f"      Name: {name}")
                        print(f"      Protocol: {protocol}")
                        print(f"      All keys: {list(cipher.keys())}")
                    else:
                        print(f"      Value: {cipher}")

        except Exception as e:
            print(f"✗ Error getting ciphers: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("✗ context.get_ciphers() is NOT available")

    # Try module-level get_ciphers (removed in 3.14)
    if hasattr(ssl, 'get_ciphers'):
        print("\n✓ ssl.get_ciphers() exists (pre-3.14)")
    else:
        print("\n✗ ssl.get_ciphers() does NOT exist (Python 3.14+)")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
