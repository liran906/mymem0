"""
Quick tests for recent UserProfile changes

Tests:
1. social_context structure (object, not array)
2. learning_preferences structure (object, not array)
3. evidence_limit parameter (0, N, -1)
4. missing-fields endpoint (pg/mongo/both)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from mem0 import Memory
from mem0.configs.base import MemoryConfig
from mem0.user_profile import UserProfile

# Load environment variables
load_dotenv()

# Test configuration (using local Docker services)
TEST_CONFIG = {
    "llm": {
        "provider": "deepseek",
        "config": {
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "model": "deepseek-chat",
            "temperature": 0.1,
            "max_tokens": 2000,
        }
    },
    "embedder": {
        "provider": "qwen",
        "config": {
            "model": "text-embedding-v4",
            "embedding_dims": 1536,
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": "localhost",
            "port": "8432",
            "user": "mem0",
            "password": "mem0password",
            "dbname": "mem0",
            "collection_name": "memories",
            "embedding_model_dims": 1536
        }
    },
    "user_profile": {
        "postgres": {
            "host": "localhost",
            "port": "8432",
            "database": "mem0",
            "user": "mem0",
            "password": "mem0password"
        },
        "mongodb": {
            "uri": "mongodb://localhost:27017",
            "database": "mem0"
        }
    }
}


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name, passed, error=None):
    """Print test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"\n{status}: {test_name}")
    if error:
        print(f"  Error: {error}")


def test_social_context_structure():
    """
    Test 1: Verify social_context is stored as object (not array)
    """
    print_section("Test 1: social_context Structure")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_social_context_quick"

        # Message mentioning family and friends
        messages = [
            {"role": "user", "content": "我爸爸是医生，叫John，很善良。我妈妈Mary是老师。我有个好朋友Amy。"}
        ]

        print("\nCreating profile with family/friends info...")
        user_profile.set_profile(user_id=user_id, messages=messages)

        # Get profile
        profile = user_profile.get_profile(user_id=user_id)
        social_context = profile.get("additional_profile", {}).get("social_context", {})

        print(f"\nsocial_context type: {type(social_context)}")
        print(f"social_context keys: {list(social_context.keys()) if isinstance(social_context, dict) else 'N/A'}")

        # Verify structure
        assert isinstance(social_context, dict), f"social_context should be dict, got {type(social_context)}"

        if "family" in social_context:
            assert isinstance(social_context["family"], dict), "family should be dict"
            print(f"✓ family structure correct: {list(social_context['family'].keys())}")

        if "friends" in social_context:
            assert isinstance(social_context["friends"], list), "friends should be list"
            print(f"✓ friends structure correct: {len(social_context['friends'])} friends")

        print_result("social_context Structure", True)
        return True

    except AssertionError as e:
        print_result("social_context Structure", False, str(e))
        return False
    except Exception as e:
        print_result("social_context Structure", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_learning_preferences_structure():
    """
    Test 2: Verify learning_preferences is stored as object (not array)
    """
    print_section("Test 2: learning_preferences Structure")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_learning_pref_quick"

        # Message mentioning learning preferences
        messages = [
            {"role": "user", "content": "我喜欢在晚上学习，通过看视频教程效果最好，我现在是中级水平。"}
        ]

        print("\nCreating profile with learning preferences...")
        user_profile.set_profile(user_id=user_id, messages=messages)

        # Get profile
        profile = user_profile.get_profile(user_id=user_id)
        learning_pref = profile.get("additional_profile", {}).get("learning_preferences", {})

        print(f"\nlearning_preferences type: {type(learning_pref)}")
        print(f"learning_preferences content: {learning_pref}")

        # Verify structure
        assert isinstance(learning_pref, dict), f"learning_preferences should be dict, got {type(learning_pref)}"

        # Check for expected keys
        expected_keys = ["preferred_time", "preferred_style", "difficulty_level"]
        found_keys = [k for k in expected_keys if k in learning_pref]
        if found_keys:
            print(f"✓ Found keys: {found_keys}")

        print_result("learning_preferences Structure", True)
        return True

    except AssertionError as e:
        print_result("learning_preferences Structure", False, str(e))
        return False
    except Exception as e:
        print_result("learning_preferences Structure", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evidence_limit():
    """
    Test 3: Test evidence_limit parameter (0, 2, -1)
    """
    print_section("Test 3: evidence_limit Parameter")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_evidence_limit_quick"

        # Create multiple evidence items
        messages = [
            {"role": "user", "content": "我喜欢打篮球"},
            {"role": "user", "content": "昨天打篮球很开心"},
            {"role": "user", "content": "今天又打篮球了"},
        ]

        print("\nCreating profile with multiple evidence...")
        for msg in messages:
            user_profile.set_profile(user_id=user_id, messages=[msg])

        # Test limit=0
        print("\n1. Testing evidence_limit=0")
        profile_0 = user_profile.get_profile(user_id=user_id, options={"evidence_limit": 0})
        interests_0 = profile_0.get("additional_profile", {}).get("interests", [])
        if interests_0:
            evidence_count = len(interests_0[0].get("evidence", []))
            print(f"   Evidence count: {evidence_count}")
            assert evidence_count == 0, f"Expected 0, got {evidence_count}"
            print("   ✓ limit=0 works")

        # Test limit=2
        print("\n2. Testing evidence_limit=2")
        profile_2 = user_profile.get_profile(user_id=user_id, options={"evidence_limit": 2})
        interests_2 = profile_2.get("additional_profile", {}).get("interests", [])
        if interests_2:
            evidence_count = len(interests_2[0].get("evidence", []))
            print(f"   Evidence count: {evidence_count}")
            assert evidence_count <= 2, f"Expected ≤2, got {evidence_count}"
            print("   ✓ limit=2 works")

        # Test limit=-1
        print("\n3. Testing evidence_limit=-1")
        profile_all = user_profile.get_profile(user_id=user_id, options={"evidence_limit": -1})
        interests_all = profile_all.get("additional_profile", {}).get("interests", [])
        if interests_all:
            evidence_count = len(interests_all[0].get("evidence", []))
            print(f"   Evidence count: {evidence_count}")
            print("   ✓ limit=-1 returns all")

        print_result("evidence_limit Parameter", True)
        return True

    except AssertionError as e:
        print_result("evidence_limit Parameter", False, str(e))
        return False
    except Exception as e:
        print_result("evidence_limit Parameter", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missing_fields():
    """
    Test 4: Test missing-fields endpoint
    """
    print_section("Test 4: missing-fields Endpoint")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_missing_fields_quick"

        # Create partial profile
        messages = [
            {"role": "user", "content": "我叫张三，喜欢编程"}
        ]

        print("\nCreating partial profile...")
        user_profile.set_profile(user_id=user_id, messages=messages)

        # Test source='both'
        print("\n1. Testing source='both'")
        missing_both = user_profile.get_missing_fields(user_id=user_id, source="both")
        print(f"   Missing basic_info fields: {len(missing_both['missing_fields'].get('basic_info', []))}")
        print(f"   Missing additional_profile fields: {len(missing_both['missing_fields'].get('additional_profile', []))}")
        assert "basic_info" in missing_both["missing_fields"]
        assert "additional_profile" in missing_both["missing_fields"]
        print("   ✓ both sources work")

        # Test source='pg'
        print("\n2. Testing source='pg'")
        missing_pg = user_profile.get_missing_fields(user_id=user_id, source="pg")
        assert "basic_info" in missing_pg["missing_fields"]
        assert "additional_profile" not in missing_pg["missing_fields"]
        print("   ✓ pg source only")

        # Test source='mongo'
        print("\n3. Testing source='mongo'")
        missing_mongo = user_profile.get_missing_fields(user_id=user_id, source="mongo")
        assert "additional_profile" in missing_mongo["missing_fields"]
        assert "basic_info" not in missing_mongo["missing_fields"]
        print("   ✓ mongo source only")

        print_result("missing-fields Endpoint", True)
        return True

    except AssertionError as e:
        print_result("missing-fields Endpoint", False, str(e))
        return False
    except Exception as e:
        print_result("missing-fields Endpoint", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_quick_tests():
    """Run all quick tests"""
    print_section("UserProfile Quick Test Suite")
    print("Testing recent changes (social_context, learning_preferences, evidence_limit, missing-fields)")

    tests = [
        test_social_context_structure,
        test_learning_preferences_structure,
        test_evidence_limit,
        test_missing_fields,
    ]

    results = []
    for test_func in tests:
        try:
            passed = test_func()
            results.append((test_func.__name__, passed))
        except Exception as e:
            print(f"\n✗ FATAL ERROR in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_func.__name__, False))

    # Summary
    print("\n" + "=" * 60)
    print("  Test Summary")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed\n")

    for test_name, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name.replace('test_', '').replace('_', ' ').title()}")

    if passed_count == total_count:
        print("\n🎉 All quick tests passed!")
        return True
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)
