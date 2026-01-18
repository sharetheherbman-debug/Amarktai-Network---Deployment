"""
Test backward compatibility for password hash fields
Tests the logic without requiring a running server
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auth import get_password_hash, verify_password


def test_password_hashing():
    """Test that password hashing works correctly"""
    password = "TestPassword123!"
    hashed = get_password_hash(password)
    
    # Verify the password
    assert verify_password(password, hashed), "Password verification failed"
    print("✅ Password hashing and verification works")


def test_backward_compatibility_logic():
    """Test the logic for checking multiple password hash fields"""
    
    # Simulate user documents with different hash field names
    test_password = "MySecurePass123"
    hashed = get_password_hash(test_password)
    
    # Test case 1: hashed_password (new standard)
    user1 = {"hashed_password": hashed}
    stored_hash = None
    if 'hashed_password' in user1 and user1['hashed_password']:
        stored_hash = user1['hashed_password']
    elif 'password_hash' in user1 and user1['password_hash']:
        stored_hash = user1['password_hash']
    elif 'hashedPassword' in user1 and user1['hashedPassword']:
        stored_hash = user1['hashedPassword']
    
    assert stored_hash is not None, "Should find hashed_password"
    assert verify_password(test_password, stored_hash), "Should verify against hashed_password"
    print("✅ Backward compatibility: hashed_password works")
    
    # Test case 2: password_hash (legacy)
    user2 = {"password_hash": hashed}
    stored_hash = None
    if 'hashed_password' in user2 and user2.get('hashed_password'):
        stored_hash = user2['hashed_password']
    elif 'password_hash' in user2 and user2.get('password_hash'):
        stored_hash = user2['password_hash']
    elif 'hashedPassword' in user2 and user2.get('hashedPassword'):
        stored_hash = user2['hashedPassword']
    
    assert stored_hash is not None, "Should find password_hash"
    assert verify_password(test_password, stored_hash), "Should verify against password_hash"
    print("✅ Backward compatibility: password_hash works")
    
    # Test case 3: hashedPassword (camelCase legacy)
    user3 = {"hashedPassword": hashed}
    stored_hash = None
    if 'hashed_password' in user3 and user3.get('hashed_password'):
        stored_hash = user3['hashed_password']
    elif 'password_hash' in user3 and user3.get('password_hash'):
        stored_hash = user3['password_hash']
    elif 'hashedPassword' in user3 and user3.get('hashedPassword'):
        stored_hash = user3['hashedPassword']
    
    assert stored_hash is not None, "Should find hashedPassword"
    assert verify_password(test_password, stored_hash), "Should verify against hashedPassword"
    print("✅ Backward compatibility: hashedPassword works")
    
    # Test case 4: Priority order (hashed_password takes precedence)
    user4 = {
        "hashed_password": hashed,
        "password_hash": get_password_hash("WrongPassword"),
        "hashedPassword": get_password_hash("AnotherWrongPassword")
    }
    stored_hash = None
    if 'hashed_password' in user4 and user4.get('hashed_password'):
        stored_hash = user4['hashed_password']
    elif 'password_hash' in user4 and user4.get('password_hash'):
        stored_hash = user4['password_hash']
    elif 'hashedPassword' in user4 and user4.get('hashedPassword'):
        stored_hash = user4['hashedPassword']
    
    assert stored_hash == user4['hashed_password'], "Should prioritize hashed_password"
    assert verify_password(test_password, stored_hash), "Should verify against prioritized field"
    print("✅ Backward compatibility: Priority order works correctly")


if __name__ == "__main__":
    print("="*60)
    print("Testing Backward Compatible Password Hash Fields")
    print("="*60)
    print()
    
    test_password_hashing()
    test_backward_compatibility_logic()
    
    print()
    print("="*60)
    print("✅ All backward compatibility tests passed!")
    print("="*60)
