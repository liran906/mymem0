#!/usr/bin/env python3
"""
Simple test script for UserProfile module

Tests the basic functionality of UserProfile:
1. Database initialization
2. Profile creation from messages
3. Profile retrieval
4. Profile update
5. Profile deletion
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from mem0.configs.base import MemoryConfig
from mem0.user_profile import UserProfile

# Load environment variables
load_dotenv()

# Test configuration
TEST_CONFIG = {
    "llm": {
        "provider": "deepseek",
        "config": {
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "model": "deepseek-chat",
            "temperature": 0.2,
            "max_tokens": 2000
        }
    },
    "user_profile": {
        "postgres": {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "8432")),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "database": os.getenv("POSTGRES_DB", "postgres"),
            "minconn": 1,
            "maxconn": 5,
        },
        "mongodb": {
            "uri": os.getenv("MONGODB_URI", "mongodb://mongo:mongo@localhost:27017/"),
            "database": os.getenv("MONGODB_DATABASE", "mem0"),
            "collection": "user_additional_profile",
        },
    }
}


def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def test_user_profile():
    """Run UserProfile tests"""

    print_section("UserProfile Module Test")

    try:
        # Initialize UserProfile
        print("\n1. Initializing UserProfile...")
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        print("✓ UserProfile initialized successfully")

        # Initialize databases
        print("\n2. Initializing databases...")
        user_profile.initialize_databases()
        print("✓ Databases initialized successfully")

        # Test user ID
        test_user_id = "test_user_001"

        # Test 1: Create profile from messages
        print_section("Test 1: Create Profile from Messages")

        messages = [
            {"role": "user", "content": "我叫李明，今年30岁，住在杭州"},
            {"role": "assistant", "content": "你好李明！很高兴认识你"},
            {"role": "user", "content": "我很喜欢摄影，每个周末都出去拍照"},
            {"role": "assistant", "content": "摄影是个很好的爱好！"},
            {"role": "user", "content": "我是一名Python工程师，有5年经验"},
        ]

        print("\nMessages:")
        for msg in messages:
            print(f"  {msg['role']}: {msg['content']}")

        print("\nExtracting profile...")
        result = user_profile.set_profile(
            user_id=test_user_id,
            messages=messages
        )

        print("\nResult:")
        print(f"  Success: {result.get('success')}")
        print(f"  Basic info updated: {result.get('basic_info_updated')}")
        print(f"  Additional profile updated: {result.get('additional_profile_updated')}")
        print(f"  Operations: {result.get('operations_performed')}")

        if result.get('errors'):
            print(f"  Errors: {result.get('errors')}")

        # Test 2: Get profile
        print_section("Test 2: Get Profile")

        profile = user_profile.get_profile(user_id=test_user_id)

        print("\nBasic Info:")
        for key, value in profile.get('basic_info', {}).items():
            if value and key not in ['user_id', 'created_at', 'updated_at']:
                print(f"  {key}: {value}")

        print("\nAdditional Profile:")
        for category, items in profile.get('additional_profile', {}).items():
            if items:
                print(f"  {category}:")
                for item in items:
                    name = item.get('name', 'N/A')
                    degree = item.get('degree', 'N/A')
                    evidence_count = len(item.get('evidence', []))
                    print(f"    - {name} (degree: {degree}, evidence: {evidence_count})")

        # Test 3: Update profile
        print_section("Test 3: Update Profile")

        update_messages = [
            {"role": "user", "content": "我现在搬到上海了"},
            {"role": "assistant", "content": "祝贺你搬到上海！"},
            {"role": "user", "content": "我最近在学习 React 开发"},
        ]

        print("\nUpdate Messages:")
        for msg in update_messages:
            print(f"  {msg['role']}: {msg['content']}")

        print("\nUpdating profile...")
        update_result = user_profile.set_profile(
            user_id=test_user_id,
            messages=update_messages
        )

        print("\nUpdate Result:")
        print(f"  Success: {update_result.get('success')}")
        print(f"  Operations: {update_result.get('operations_performed')}")

        # Test 4: Get updated profile
        print_section("Test 4: Get Updated Profile")

        updated_profile = user_profile.get_profile(user_id=test_user_id)

        print("\nBasic Info:")
        for key, value in updated_profile.get('basic_info', {}).items():
            if value and key not in ['user_id', 'created_at', 'updated_at']:
                print(f"  {key}: {value}")

        # Test 5: Get specific fields only
        print_section("Test 5: Get Specific Fields (skills only)")

        skills_only = user_profile.get_profile(
            user_id=test_user_id,
            options={"fields": ["skills"]}
        )

        print("\nSkills:")
        for item in skills_only.get('additional_profile', {}).get('skills', []):
            name = item.get('name', 'N/A')
            degree = item.get('degree', 'N/A')
            print(f"  - {name} (degree: {degree})")

        # Test 6: Delete profile (commented out to preserve test data)
        print_section("Test 6: Delete Profile")
        print("\n⚠️  Skipping deletion to preserve test data")
        print("To test deletion, uncomment the following code:")
        print("  delete_result = user_profile.delete_profile(user_id=test_user_id)")

        # Uncomment to test deletion:
        # delete_result = user_profile.delete_profile(user_id=test_user_id)
        # print("\nDelete Result:")
        # print(f"  Success: {delete_result.get('success')}")
        # print(f"  Basic info deleted: {delete_result.get('basic_info_deleted')}")
        # print(f"  Additional profile deleted: {delete_result.get('additional_profile_deleted')}")

        # Close connections
        user_profile.close()

        print_section("All Tests Completed Successfully! ✓")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_user_profile()
    sys.exit(0 if success else 1)
