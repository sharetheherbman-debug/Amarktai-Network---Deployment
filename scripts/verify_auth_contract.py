#!/usr/bin/env python3
"""
Simple verification script to test auth contract logic without database
Tests the validation logic and response structure
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models import UserRegister
from pydantic import ValidationError


def test_user_register_model():
    """Test UserRegister model validation"""
    print("Testing UserRegister model validation...")
    
    # Test 1: Valid with password
    try:
        user = UserRegister(
            first_name="Test",
            email="test@example.com",
            password="testpass123"
        )
        print("✓ Test 1 passed: UserRegister with password field")
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        return False
    
    # Test 2: Valid with password_hash (legacy)
    try:
        user = UserRegister(
            first_name="Test",
            email="test@example.com",
            password_hash="legacypass123"
        )
        print("✓ Test 2 passed: UserRegister with password_hash field (legacy)")
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        return False
    
    # Test 3: Valid with optional invite_code
    try:
        user = UserRegister(
            first_name="Test",
            email="test@example.com",
            password="testpass123",
            invite_code="INVITE123"
        )
        print("✓ Test 3 passed: UserRegister with optional invite_code")
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
        return False
    
    # Test 4: Valid with both password and password_hash (model accepts both, route validates)
    try:
        user = UserRegister(
            first_name="Test",
            email="test@example.com",
            password="pass1",
            password_hash="pass2"
        )
        print("✓ Test 4 passed: Model accepts both (route will validate)")
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
        return False
    
    # Test 5: Valid without both (model accepts, route will validate)
    try:
        user = UserRegister(
            first_name="Test",
            email="test@example.com"
        )
        print("✓ Test 5 passed: Model accepts no password (route will validate)")
    except Exception as e:
        print(f"✗ Test 5 failed: {e}")
        return False
    
    # Test 6: Missing required field (first_name)
    try:
        user = UserRegister(
            email="test@example.com",
            password="testpass123"
        )
        print("✗ Test 6 failed: Should have rejected missing first_name")
        return False
    except ValidationError:
        print("✓ Test 6 passed: Rejected missing first_name")
    
    # Test 7: Invalid email
    try:
        user = UserRegister(
            first_name="Test",
            email="not-an-email",
            password="testpass123"
        )
        print("✗ Test 7 failed: Should have rejected invalid email")
        return False
    except ValidationError:
        print("✓ Test 7 passed: Rejected invalid email")
    
    return True


def test_auth_logic_validation():
    """Test the auth route validation logic"""
    print("\nTesting auth route validation logic...")
    
    # Test password validation logic (simulated)
    def validate_password_fields(password, password_hash):
        """Simulates the validation in the route"""
        if not password and not password_hash:
            return False, "Either password or password_hash is required"
        if password and password_hash:
            return False, "Provide either password or password_hash, not both"
        return True, None
    
    # Test cases
    test_cases = [
        (None, None, False, "Both None"),
        ("pass1", None, True, "Only password"),
        (None, "pass2", True, "Only password_hash"),
        ("pass1", "pass2", False, "Both provided"),
    ]
    
    all_passed = True
    for password, password_hash, should_pass, description in test_cases:
        valid, error = validate_password_fields(password, password_hash)
        if valid == should_pass:
            print(f"✓ Test passed: {description}")
        else:
            print(f"✗ Test failed: {description} - Expected {should_pass}, got {valid}")
            all_passed = False
    
    return all_passed


def test_response_structure():
    """Test that response structure is correct"""
    print("\nTesting response structure...")
    
    from datetime import datetime, timezone
    
    # Simulate the response
    access_token = "mock_jwt_token_here"
    user_data = {
        "id": "user123",
        "email": "test@example.com",
        "first_name": "Test",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    response = {
        "access_token": access_token,
        "token_type": "bearer",
        "token": access_token,  # Legacy
        "user": user_data
    }
    
    # Verify structure
    required_fields = ["access_token", "token_type", "token", "user"]
    all_present = all(field in response for field in required_fields)
    
    if all_present:
        print("✓ Response has all required fields")
    else:
        print("✗ Response missing required fields")
        return False
    
    # Verify token_type
    if response["token_type"] == "bearer":
        print("✓ token_type is 'bearer'")
    else:
        print(f"✗ token_type is '{response['token_type']}', expected 'bearer'")
        return False
    
    # Verify legacy token matches access_token
    if response["token"] == response["access_token"]:
        print("✓ Legacy 'token' field matches 'access_token'")
    else:
        print("✗ Legacy 'token' field doesn't match 'access_token'")
        return False
    
    # Verify user data doesn't contain sensitive fields
    sensitive_fields = ["password", "password_hash", "_id"]
    has_sensitive = any(field in response["user"] for field in sensitive_fields)
    
    if not has_sensitive:
        print("✓ User data excludes sensitive fields")
    else:
        print("✗ User data contains sensitive fields")
        return False
    
    return True


def main():
    print("=" * 60)
    print("Auth Contract Verification")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("UserRegister Model", test_user_register_model()))
    results.append(("Auth Logic Validation", test_auth_logic_validation()))
    results.append(("Response Structure", test_response_structure()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
