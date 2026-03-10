"""Verify the 4 test fixes without pytest"""

import sys
import os

_project_root = os.path.abspath(os.path.dirname(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

print("=" * 60)
print("VERIFYING TEST FIXES")
print("=" * 60)
print()

# Fix 1: test_classify_viewing_request
print("1. Testing Real Estate viewing_request classification...")
try:
    from agents.real_estate.real_estate_agent import RealEstateAgent

    agent = RealEstateAgent()
    email = {
        "subject": "Schedule a viewing",
        "body": "Can I arrange a visit to see the property?"
    }
    result = agent.classify_email(email)

    if result == "viewing_request":
        print(f"   ✅ PASS: classify_email returned '{result}' (expected: 'viewing_request')")
    else:
        print(f"   ❌ FAIL: classify_email returned '{result}' (expected: 'viewing_request')")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    sys.exit(1)

print()

# Fix 2: test_classify_maintenance
print("2. Testing Real Estate maintenance_request classification...")
try:
    agent = RealEstateAgent()
    email = {
        "subject": "Maintenance Required",
        "body": "The heating is broken in my apartment"
    }
    result = agent.classify_email(email)

    if result == "maintenance_request":
        print(f"   ✅ PASS: classify_email returned '{result}' (expected: 'maintenance_request')")
    else:
        print(f"   ❌ FAIL: classify_email returned '{result}' (expected: 'maintenance_request')")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    sys.exit(1)

print()

# Fix 3: test_classify_supplier
print("3. Testing E-commerce supplier_email classification...")
try:
    from agents.ecommerce.ecommerce_agent import EcommerceAgent

    agent = EcommerceAgent()
    email = {
        "subject": "Invoice for bulk order",
        "body": "Please find attached our invoice for the wholesale order"
    }
    result = agent.classify_email(email)

    if result == "supplier_email":
        print(f"   ✅ PASS: classify_email returned '{result}' (expected: 'supplier_email')")
    else:
        print(f"   ❌ FAIL: classify_email returned '{result}' (expected: 'supplier_email')")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    sys.exit(1)

print()

# Fix 4: test_extract_order_id_none
print("4. Testing E-commerce extract_order_id with no order...")
try:
    from skills.ecommerce_skills import EcommerceSkills

    skills = EcommerceSkills()
    result = skills.extract_order_id("No order number here")

    if result is None:
        print(f"   ✅ PASS: extract_order_id returned None (expected: None)")
    else:
        print(f"   ❌ FAIL: extract_order_id returned '{result}' (expected: None)")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    sys.exit(1)

print()

# Additional test: Make sure valid order IDs still work
print("5. Verifying valid order ID patterns still work...")
try:
    skills = EcommerceSkills()

    # Test pattern 1: #12345
    result1 = skills.extract_order_id("My order #12345 is missing")
    assert result1 == "12345", f"Pattern 1 failed: got '{result1}' expected '12345'"
    print(f"   ✅ Pattern #12345 works: '{result1}'")

    # Test pattern 2: ORDER-ABC123
    result2 = skills.extract_order_id("ORDER-ABC123 not delivered")
    assert result2 == "ABC123", f"Pattern 2 failed: got '{result2}' expected 'ABC123'"
    print(f"   ✅ Pattern ORDER-ABC123 works: '{result2}'")

    # Test pattern 3: ORD-456
    result3 = skills.extract_order_id("ORD-456 is late")
    assert result3 == "456", f"Pattern 3 failed: got '{result3}' expected '456'"
    print(f"   ✅ Pattern ORD-456 works: '{result3}'")

    # Test pattern 4: order number: 98765
    result4 = skills.extract_order_id("order number: 98765 has an issue")
    assert result4 == "98765", f"Pattern 4 failed: got '{result4}' expected '98765'"
    print(f"   ✅ Pattern 'order number: 98765' works: '{result4}'")

except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✅ ALL 4 TEST FIXES VERIFIED")
print("=" * 60)
print()
print("Summary:")
print("  1. ✅ Real Estate viewing_request classification fixed")
print("  2. ✅ Real Estate maintenance_request classification fixed")
print("  3. ✅ E-commerce supplier_email classification fixed")
print("  4. ✅ E-commerce extract_order_id(None) fixed")
print("  5. ✅ Valid order ID patterns still work")
print()
print("All tests should now pass!")
print()
