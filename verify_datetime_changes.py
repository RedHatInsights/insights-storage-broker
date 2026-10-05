#!/usr/bin/env python3.12
"""
Verification script for PR 339 datetime changes.
Tests that datetime.now(UTC) works correctly in Python 3.12.
"""

import sys
from datetime import datetime, UTC

def test_utc_import():
    """Verify UTC can be imported (Python 3.11+)"""
    print("✓ UTC imported successfully from datetime module")
    return True

def test_datetime_now_utc():
    """Test datetime.now(UTC) works"""
    try:
        timestamp = datetime.now(UTC)
        print(f"✓ datetime.now(UTC) works: {timestamp}")
        return True
    except Exception as e:
        print(f"✗ datetime.now(UTC) failed: {e}")
        return False

def test_timestamp_format():
    """Test timestamp formatting matches expected format"""
    try:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        assert len(timestamp) == 14, f"Expected 14 chars, got {len(timestamp)}"
        assert timestamp.isdigit(), f"Expected digits only, got {timestamp}"
        print(f"✓ Timestamp format correct: {timestamp}")
        return True
    except Exception as e:
        print(f"✗ Timestamp format test failed: {e}")
        return False

def test_normalizers_import():
    """Test that normalizers module imports without errors"""
    try:
        from storage_broker.normalizers import Validation, Openshift
        print("✓ Normalizers module imports successfully")

        # Test Validation class
        v = Validation()
        print(f"✓ Validation class instantiated with timestamp: {v.timestamp}")

        return True
    except Exception as e:
        print(f"✗ Normalizers import failed: {e}")
        return False

def test_validation_from_json():
    """Test Validation.from_json with sample data"""
    try:
        from storage_broker.normalizers import Validation

        msg = {
            "account": "000001",
            "org_id": "123456",
            "reporter": "puptoo",
            "request_id": "12345",
            "system_id": "abdc-1234",
            "hostname": "hostname",
            "validation": "failure",
            "service": "advisor",
            "reason": "error unpacking archive",
            "size": "12345",
        }

        data = Validation.from_json(msg)
        assert data.account == "000001"
        assert data.org_id == "123456"
        assert data.timestamp is not None
        assert len(data.timestamp) == 14

        print(f"✓ Validation.from_json works correctly")
        print(f"  Generated timestamp: {data.timestamp}")
        return True
    except Exception as e:
        print(f"✗ Validation.from_json test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("PR 339 DateTime Verification Tests")
    print("=" * 60)
    print()

    tests = [
        ("UTC Import", test_utc_import),
        ("datetime.now(UTC)", test_datetime_now_utc),
        ("Timestamp Format", test_timestamp_format),
        ("Normalizers Import", test_normalizers_import),
        ("Validation.from_json", test_validation_from_json),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n[Testing: {name}]")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
