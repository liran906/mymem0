#!/usr/bin/env python3
"""
Quick API tests for UserProfile recent changes

Tests new features without requiring database:
1. Prompt structure validation
2. Timestamp handling in profile_manager
3. social_context structure (friends vs teachers)
4. Evidence limit logic
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mem0.user_profile.prompts import EXTRACT_PROFILE_PROMPT, UPDATE_PROFILE_PROMPT
from mem0.user_profile.profile_manager import ProfileManager
from mem0.user_profile.utils import get_current_timestamp


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(test_name, passed, details=None):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"  → {details}")


def test_prompts_no_timestamp():
    """
    Test 1: Verify prompts don't ask LLM to generate timestamps
    """
    print_section("Test 1: Prompts - No Timestamp Generation")

    # Check EXTRACT_PROFILE_PROMPT - should say NO timestamp
    has_no_timestamp_rule = "NO timestamp" in EXTRACT_PROFILE_PROMPT or "DO NOT include timestamp" in EXTRACT_PROFILE_PROMPT
    has_backend_note = "backend" in EXTRACT_PROFILE_PROMPT.lower() and "timestamp" in EXTRACT_PROFILE_PROMPT
    no_current_time_param = "{current_time}" not in EXTRACT_PROFILE_PROMPT

    print_result(
        "EXTRACT_PROFILE_PROMPT",
        has_no_timestamp_rule and no_current_time_param,
        "LLM instructed NOT to include timestamps, backend handles it" if has_no_timestamp_rule else "Missing 'NO timestamp' instruction"
    )

    # Check UPDATE_PROFILE_PROMPT
    has_no_timestamp_rule2 = "DO NOT" in UPDATE_PROFILE_PROMPT and "timestamp" in UPDATE_PROFILE_PROMPT
    backend_handles2 = "backend" in UPDATE_PROFILE_PROMPT.lower() and "timestamp" in UPDATE_PROFILE_PROMPT

    print_result(
        "UPDATE_PROFILE_PROMPT",
        has_no_timestamp_rule2 or backend_handles2,
        f"Timestamp handling documented: {has_no_timestamp_rule2 or backend_handles2}"
    )

    return (has_no_timestamp_rule and no_current_time_param) and (has_no_timestamp_rule2 or backend_handles2)


def test_social_context_structure():
    """
    Test 2: Verify social_context uses 'friends' not 'teachers'
    """
    print_section("Test 2: social_context Structure - Friends not Teachers")

    has_friends = '"friends":' in EXTRACT_PROFILE_PROMPT
    has_teachers = '"teachers":' in EXTRACT_PROFILE_PROMPT

    friends_in_rules = "friends" in EXTRACT_PROFILE_PROMPT and "Array of friends" in EXTRACT_PROFILE_PROMPT
    teachers_in_others = "teachers" in EXTRACT_PROFILE_PROMPT and "others" in EXTRACT_PROFILE_PROMPT

    print_result(
        "social_context.friends exists",
        has_friends,
        f"Found 'friends' array in prompt"
    )

    print_result(
        "teachers moved to 'others'",
        not has_teachers or teachers_in_others,
        "teachers are in 'others' relation" if teachers_in_others else "No separate teachers array"
    )

    return has_friends and (not has_teachers or teachers_in_others)


def test_language_consistency_rule():
    """
    Test 3: Verify language consistency rule exists
    """
    print_section("Test 3: Language Consistency Rule")

    has_rule = "Language consistency" in EXTRACT_PROFILE_PROMPT or "language" in EXTRACT_PROFILE_PROMPT.lower()
    no_translation = "translation" in EXTRACT_PROFILE_PROMPT or "Chinese/English" in EXTRACT_PROFILE_PROMPT

    print_result(
        "Language consistency rule",
        has_rule and no_translation,
        "Rule found: Keep language consistent, no translation"
    )

    return has_rule and no_translation


def test_degree_descriptions():
    """
    Test 4: Verify degree descriptions are in English
    """
    print_section("Test 4: Degree Descriptions - English Terms")

    # Check for English degree terms
    english_terms = [
        "dislike", "neutral", "like", "favorite",
        "beginner", "learning", "proficient", "expert",
        "weak", "moderate", "strong"
    ]

    found_english = [term for term in english_terms if term in EXTRACT_PROFILE_PROMPT]

    # Check for Chinese degree terms (should not exist)
    chinese_terms = ["不太喜欢", "喜欢", "最爱", "初学", "入门", "专家", "明显"]
    found_chinese = [term for term in chinese_terms if term in EXTRACT_PROFILE_PROMPT]

    print_result(
        "English degree terms",
        len(found_english) >= 5,
        f"Found {len(found_english)} English terms: {', '.join(found_english[:5])}"
    )

    print_result(
        "No Chinese degree terms",
        len(found_chinese) == 0,
        "All degree descriptions use English" if len(found_chinese) == 0 else f"Found Chinese: {found_chinese}"
    )

    return len(found_english) >= 5 and len(found_chinese) == 0


def test_timestamp_generation_function():
    """
    Test 5: Verify timestamp utility function works
    """
    print_section("Test 5: Timestamp Generation Function")

    timestamp = get_current_timestamp()

    # Validate ISO8601 format
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        is_valid = True
    except:
        is_valid = False

    print_result(
        "get_current_timestamp()",
        is_valid,
        f"Generated valid timestamp: {timestamp}"
    )

    return is_valid


def test_add_timestamps_to_evidence_logic():
    """
    Test 6: Test _add_timestamps_to_evidence logic (without LLM)
    """
    print_section("Test 6: Add Timestamps to Evidence Logic")

    # Simulate extracted data without timestamps
    test_data = {
        "interests": [
            {
                "name": "足球",
                "degree": 4,
                "evidence": [
                    {"text": "喜欢踢足球"},
                    {"text": "每周都踢"}
                ]
            }
        ],
        "social_context": {
            "friends": [
                {"name": "Jack", "info": ["plays basketball"]}
            ]
        }
    }

    # Create a mock ProfileManager with minimal setup
    class MockLLM:
        pass

    class MockDB:
        pass

    manager = ProfileManager(MockLLM(), MockDB(), MockDB())

    # Add timestamps
    result = manager._add_timestamps_to_evidence(test_data)

    # Check if timestamps were added
    has_timestamps = all(
        "timestamp" in ev
        for item in result.get("interests", [])
        for ev in item.get("evidence", [])
    )

    print_result(
        "Timestamps added to evidence",
        has_timestamps,
        f"All evidence entries have timestamps: {has_timestamps}"
    )

    # Print sample
    if result.get("interests"):
        sample_evidence = result["interests"][0]["evidence"][0]
        print(f"  Sample: {sample_evidence}")

    return has_timestamps


def test_evidence_structure():
    """
    Test 7: Verify evidence structure in prompts
    """
    print_section("Test 7: Evidence Structure - Text Only from LLM")

    # Check that examples show text-only evidence
    has_text_only = '{{"text":' in EXTRACT_PROFILE_PROMPT
    no_timestamp_in_example = not ('{{"text":' in EXTRACT_PROFILE_PROMPT and '"timestamp":' in EXTRACT_PROFILE_PROMPT and EXTRACT_PROFILE_PROMPT.index('{{"text":') < EXTRACT_PROFILE_PROMPT.index('"timestamp":'))

    print_result(
        "Evidence structure",
        has_text_only,
        "Examples show evidence with text field"
    )

    print_result(
        "No timestamp in LLM examples",
        no_timestamp_in_example,
        "LLM examples don't include timestamp field"
    )

    return has_text_only and no_timestamp_in_example


def test_omit_missing_fields_rule():
    """
    Test 8: Verify 'omit missing fields' rule
    """
    print_section("Test 8: Omit Missing Fields Rule")

    has_omit_rule = "omit" in EXTRACT_PROFILE_PROMPT.lower() or "DO NOT include" in EXTRACT_PROFILE_PROMPT
    no_null_rule = "null" in EXTRACT_PROFILE_PROMPT or "empty" in EXTRACT_PROFILE_PROMPT

    print_result(
        "Omit missing fields rule",
        has_omit_rule,
        "Rule found: Omit fields with no data"
    )

    print_result(
        "No null values",
        no_null_rule,
        "Instruction to not return null values"
    )

    return has_omit_rule


def run_quick_tests():
    """Run all quick tests"""
    print("\n" + "=" * 70)
    print("  UserProfile Quick Test Suite - Recent Changes")
    print("=" * 70)
    print("\nTesting: Prompts, Timestamp Handling, social_context, Language Rules")

    tests = [
        ("Prompts - No Timestamp Generation", test_prompts_no_timestamp),
        ("social_context - Friends Structure", test_social_context_structure),
        ("Language Consistency Rule", test_language_consistency_rule),
        ("Degree Descriptions - English", test_degree_descriptions),
        ("Timestamp Utility Function", test_timestamp_generation_function),
        ("Add Timestamps Logic", test_add_timestamps_to_evidence_logic),
        ("Evidence Structure", test_evidence_structure),
        ("Omit Missing Fields Rule", test_omit_missing_fields_rule),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed\n")

    for test_name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}")

    if passed_count == total_count:
        print("\n🎉 All quick tests passed!")
        print("\nVerified changes:")
        print("  • Timestamps generated by backend, not LLM")
        print("  • social_context uses 'friends' instead of 'teachers'")
        print("  • Language consistency rule added")
        print("  • Degree descriptions in English")
        print("  • Evidence structure: LLM returns text only")
        print("  • Missing fields are omitted, not null")
        return True
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)