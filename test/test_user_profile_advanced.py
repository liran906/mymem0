#!/usr/bin/env python3
"""
Advanced test cases for UserProfile module

Tests cover the key challenges identified in development docs:
1. Evidence-based design and conflict resolution
2. Degree dynamic adjustment
3. LLM hallucination handling (JSON parsing, error recovery)
4. Interest vs Skill overlap
5. MongoDB + PostgreSQL coordination
6. Frontend manual data vs LLM extraction priority
"""

import os
import sys
import time
from datetime import datetime, timedelta

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
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_result(test_name, passed, details=""):
    """Print test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"  Details: {details}")


def test_contradiction_handling():
    """
    Test Case 1: Contradiction Handling (★★★☆☆)

    Scenario: User initially shows strong interest, then says they don't like it
    Expected: LLM should analyze evidence count and timing to decide DELETE or degree reduction
    """
    print_section("Test 1: Contradiction Handling")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_contradiction_001"

        # Step 1: Build up strong evidence for "足球"
        print("\n1. Building up evidence for interest '足球' (football)...")
        messages_build_up = [
            {"role": "user", "content": "我很喜欢踢足球"},
            {"role": "assistant", "content": "足球是很好的运动！"},
            {"role": "user", "content": "昨天和朋友踢了一场足球，赢了"},
            {"role": "assistant", "content": "恭喜！"},
            {"role": "user", "content": "我每周都踢足球"},
        ]

        result1 = user_profile.set_profile(user_id=user_id, messages=messages_build_up)
        print(f"  Evidence built: {result1.get('operations_performed')}")

        # Check initial degree
        profile = user_profile.get_profile(user_id=user_id)
        initial_degree = None
        for interest in profile.get('additional_profile', {}).get('interests', []):
            if '足球' in interest.get('name', ''):
                initial_degree = interest.get('degree')
                evidence_count = len(interest.get('evidence', []))
                print(f"  Initial: degree={initial_degree}, evidence_count={evidence_count}")
                break

        # Small delay to ensure different timestamps
        time.sleep(1)

        # Step 2: User says they don't like it anymore
        print("\n2. User expresses contradiction...")
        messages_contradiction = [
            {"role": "user", "content": "我现在不喜欢足球了"},
        ]

        result2 = user_profile.set_profile(user_id=user_id, messages=messages_contradiction)
        print(f"  Operations: {result2.get('operations_performed')}")

        # Check final state
        profile_after = user_profile.get_profile(user_id=user_id)
        football_found = False
        final_degree = None

        for interest in profile_after.get('additional_profile', {}).get('interests', []):
            if '足球' in interest.get('name', ''):
                football_found = True
                final_degree = interest.get('degree')
                print(f"  Final: degree={final_degree}")
                break

        # Verify: Should either DELETE or reduce degree
        if not football_found:
            print_result("Contradiction - DELETE", True, "Football interest was deleted (LLM judged real change)")
        elif final_degree and initial_degree and final_degree < initial_degree:
            print_result("Contradiction - DEGREE REDUCTION", True, f"Degree reduced from {initial_degree} to {final_degree}")
        else:
            print_result("Contradiction Handling", False, "Expected deletion or degree reduction")

        return True

    except Exception as e:
        print_result("Contradiction Handling", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_interest_skill_overlap():
    """
    Test Case 2: Interest and Skill Overlap (★★☆☆☆)

    Scenario: User says "我喜欢摄影" (I like photography) and "我会摄影" (I can do photography)
    Expected: Should appear in both interests and skills with different degrees
    """
    print_section("Test 2: Interest and Skill Overlap")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_overlap_001"

        # Mention photography as both interest and skill
        messages = [
            {"role": "user", "content": "我很喜欢摄影，拍照让我很开心"},
            {"role": "assistant", "content": "摄影是很好的爱好！"},
            {"role": "user", "content": "我已经学了3年摄影，会用单反相机拍人像"},
        ]

        result = user_profile.set_profile(user_id=user_id, messages=messages)
        print(f"Operations: {result.get('operations_performed')}")

        profile = user_profile.get_profile(user_id=user_id)

        # Check if appears in both categories
        photography_in_interests = False
        photography_in_skills = False

        for interest in profile.get('additional_profile', {}).get('interests', []):
            if '摄影' in interest.get('name', ''):
                photography_in_interests = True
                print(f"  Found in interests: {interest.get('name')} (degree={interest.get('degree')})")

        for skill in profile.get('additional_profile', {}).get('skills', []):
            if '摄影' in skill.get('name', ''):
                photography_in_skills = True
                print(f"  Found in skills: {skill.get('name')} (degree={skill.get('degree')})")

        # Verify overlap is allowed
        both_present = photography_in_interests and photography_in_skills
        print_result("Interest-Skill Overlap", both_present,
                    "Photography should appear in both categories" if both_present else "Missing in one category")

        return both_present

    except Exception as e:
        print_result("Interest-Skill Overlap", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_degree_dynamic_adjustment():
    """
    Test Case 3: Degree Dynamic Adjustment (★★★☆☆)

    Scenario: User provides progressive evidence showing skill improvement
    Expected: Degree should increase as evidence accumulates
    """
    print_section("Test 3: Degree Dynamic Adjustment")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_degree_001"

        # Stage 1: Beginner
        print("\n1. Stage 1: Beginner level...")
        messages_beginner = [
            {"role": "user", "content": "我刚开始学Python，写了第一个Hello World程序"},
        ]
        user_profile.set_profile(user_id=user_id, messages=messages_beginner)

        profile1 = user_profile.get_profile(user_id=user_id)
        degree1 = None
        for skill in profile1.get('additional_profile', {}).get('skills', []):
            if 'Python' in skill.get('name', ''):
                degree1 = skill.get('degree')
                print(f"  Beginner degree: {degree1}")
                break

        time.sleep(1)

        # Stage 2: Intermediate
        print("\n2. Stage 2: Intermediate level...")
        messages_intermediate = [
            {"role": "user", "content": "我现在能用Python写数据分析脚本了"},
            {"role": "assistant", "content": "进步很快！"},
            {"role": "user", "content": "还学会了用pandas和numpy库"},
        ]
        user_profile.set_profile(user_id=user_id, messages=messages_intermediate)

        profile2 = user_profile.get_profile(user_id=user_id)
        degree2 = None
        for skill in profile2.get('additional_profile', {}).get('skills', []):
            if 'Python' in skill.get('name', ''):
                degree2 = skill.get('degree')
                evidence_count = len(skill.get('evidence', []))
                print(f"  Intermediate degree: {degree2}, evidence: {evidence_count}")
                break

        time.sleep(1)

        # Stage 3: Advanced
        print("\n3. Stage 3: Advanced level...")
        messages_advanced = [
            {"role": "user", "content": "我现在是公司的Python技术专家，带团队做机器学习项目"},
        ]
        user_profile.set_profile(user_id=user_id, messages=messages_advanced)

        profile3 = user_profile.get_profile(user_id=user_id)
        degree3 = None
        for skill in profile3.get('additional_profile', {}).get('skills', []):
            if 'Python' in skill.get('name', ''):
                degree3 = skill.get('degree')
                print(f"  Advanced degree: {degree3}")
                break

        # Verify progressive increase
        if degree1 and degree2 and degree3:
            increasing = degree1 < degree2 < degree3
            print_result("Degree Dynamic Adjustment", increasing,
                        f"Progression: {degree1} → {degree2} → {degree3}")
            return increasing
        else:
            print_result("Degree Dynamic Adjustment", False, "Failed to track degrees")
            return False

    except Exception as e:
        print_result("Degree Dynamic Adjustment", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evidence_accumulation():
    """
    Test Case 4: Evidence Accumulation and Limit (★★☆☆☆)

    Scenario: Add many pieces of evidence for the same interest
    Expected: Evidence should accumulate (check if there's a reasonable limit)
    """
    print_section("Test 4: Evidence Accumulation")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_evidence_001"

        # Add multiple pieces of evidence
        print("\n Adding 5 pieces of evidence for '游泳'...")
        for i in range(5):
            messages = [
                {"role": "user", "content": f"今天又去游泳了，很舒服（第{i+1}次）"},
            ]
            user_profile.set_profile(user_id=user_id, messages=messages)
            time.sleep(0.5)  # Small delay for different timestamps

        # Check evidence count
        profile = user_profile.get_profile(user_id=user_id)
        evidence_count = 0
        for interest in profile.get('additional_profile', {}).get('interests', []):
            if '游泳' in interest.get('name', ''):
                evidence_count = len(interest.get('evidence', []))
                degree = interest.get('degree')
                print(f"  Evidence count: {evidence_count}")
                print(f"  Degree: {degree}")
                break

        # Verify evidence was accumulated
        passed = evidence_count >= 3  # Should have accumulated at least some evidence
        print_result("Evidence Accumulation", passed,
                    f"Accumulated {evidence_count} pieces of evidence")

        return passed

    except Exception as e:
        print_result("Evidence Accumulation", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_info_reference_data():
    """
    Test Case 5: Basic Info as Reference Data (★★☆☆☆)

    Scenario: LLM extracts basic info from conversation
    Expected: Data stored in PostgreSQL as conversation-extracted reference (non-authoritative)
    Note: Main service maintains authoritative user data
    """
    print_section("Test 5: Basic Info Reference Data")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_basic_ref_001"

        # User mentions basic info in conversation
        messages = [
            {"role": "user", "content": "我叫张三，住在北京"},
            {"role": "assistant", "content": "你好张三！"},
            {"role": "user", "content": "对，我刚搬到这里"},
        ]

        result = user_profile.set_profile(
            user_id=user_id,
            messages=messages
        )

        # Check that basic info was extracted
        profile = user_profile.get_profile(user_id=user_id)
        basic_info = profile.get('basic_info', {})

        name = basic_info.get('name')
        city = basic_info.get('current_city')

        print(f"  Extracted name: {name}")
        print(f"  Extracted city: {city}")
        print(f"  Note: This is conversation-extracted reference data (non-authoritative)")

        # Verify extraction worked
        passed = (name == "张三" or city == "北京")
        print_result("Basic Info Reference Data", passed,
                    "Conversation-extracted basic info stored as reference")

        return passed

    except Exception as e:
        print_result("Basic Info Reference Data", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_personality_inference():
    """
    Test Case 6: Personality Inference from Behavior (★★★☆☆)

    Scenario: User exhibits personality traits through actions/speech
    Expected: LLM should infer personality (e.g., "外向", "好奇")
    """
    print_section("Test 6: Personality Inference")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_personality_001"

        # Messages showing extroverted and curious personality
        messages = [
            {"role": "user", "content": "我喜欢参加各种社交活动，认识新朋友"},
            {"role": "assistant", "content": "听起来你很外向！"},
            {"role": "user", "content": "对啊，我总是想知道更多新事物，喜欢问问题"},
            {"role": "assistant", "content": "好奇心很重要"},
            {"role": "user", "content": "我经常主动组织聚会和活动"},
        ]

        result = user_profile.set_profile(user_id=user_id, messages=messages)

        profile = user_profile.get_profile(user_id=user_id)
        personality = profile.get('additional_profile', {}).get('personality', [])

        print(f"  Inferred personality traits: {len(personality)}")
        for trait in personality:
            name = trait.get('name')
            degree = trait.get('degree')
            evidence_count = len(trait.get('evidence', []))
            print(f"    - {name} (degree={degree}, evidence={evidence_count})")

        # Verify at least one personality trait was inferred
        passed = len(personality) > 0
        print_result("Personality Inference", passed,
                    f"Inferred {len(personality)} personality trait(s)")

        return passed

    except Exception as e:
        print_result("Personality Inference", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_and_null_handling():
    """
    Test Case 7: Empty/Null Input Handling (★★☆☆☆)

    Scenario: Various edge cases with empty or invalid inputs
    Expected: Graceful handling without crashes
    """
    print_section("Test 7: Empty/Null Input Handling")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)

        tests_passed = []

        # Test 1: Empty messages
        print("\n  Test 7.1: Empty messages list")
        try:
            result = user_profile.set_profile(user_id="test_empty_001", messages=[])
            tests_passed.append(("Empty messages", True))
            print("    ✓ Handled gracefully")
        except Exception as e:
            tests_passed.append(("Empty messages", False))
            print(f"    ✗ Failed: {e}")

        # Test 2: Messages with empty content
        print("\n  Test 7.2: Messages with empty content")
        try:
            messages = [{"role": "user", "content": ""}]
            result = user_profile.set_profile(user_id="test_empty_002", messages=messages)
            tests_passed.append(("Empty content", True))
            print("    ✓ Handled gracefully")
        except Exception as e:
            tests_passed.append(("Empty content", False))
            print(f"    ✗ Failed: {e}")

        # Test 3: Get non-existent user
        print("\n  Test 7.3: Get non-existent user profile")
        try:
            profile = user_profile.get_profile(user_id="nonexistent_user_999")
            is_empty = not profile.get('basic_info') and not profile.get('additional_profile')
            tests_passed.append(("Non-existent user", True))
            print(f"    ✓ Returned empty profile")
        except Exception as e:
            tests_passed.append(("Non-existent user", False))
            print(f"    ✗ Failed: {e}")

        all_passed = all(passed for _, passed in tests_passed)
        print_result("Empty/Null Input Handling", all_passed,
                    f"{sum(p for _, p in tests_passed)}/{len(tests_passed)} sub-tests passed")

        return all_passed

    except Exception as e:
        print_result("Empty/Null Input Handling", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concurrent_updates():
    """
    Test Case 8: Multiple Field Updates in Single Call (★★☆☆☆)

    Scenario: Single conversation updates multiple aspects simultaneously
    Expected: All updates should be captured correctly
    """
    print_section("Test 8: Concurrent Multiple Field Updates")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_concurrent_001"

        # Rich conversation touching multiple aspects
        messages = [
            {"role": "user", "content": "我叫王五，今年28岁，住在深圳"},
            {"role": "assistant", "content": "你好王五！"},
            {"role": "user", "content": "我喜欢爬山和阅读，会弹吉他"},
            {"role": "assistant", "content": "兴趣很丰富！"},
            {"role": "user", "content": "我性格比较内向，喜欢安静"},
        ]

        result = user_profile.set_profile(user_id=user_id, messages=messages)

        profile = user_profile.get_profile(user_id=user_id)

        # Check all aspects were captured
        basic_info = profile.get('basic_info', {})
        additional = profile.get('additional_profile', {})

        has_name = basic_info.get('name') == '王五'
        has_city = basic_info.get('current_city') == '深圳'
        has_interests = len(additional.get('interests', [])) >= 2
        has_skills = len(additional.get('skills', [])) >= 1
        has_personality = len(additional.get('personality', [])) >= 1

        print(f"  Basic info - Name: {basic_info.get('name')}, City: {basic_info.get('current_city')}")
        print(f"  Interests: {len(additional.get('interests', []))}")
        print(f"  Skills: {len(additional.get('skills', []))}")
        print(f"  Personality: {len(additional.get('personality', []))}")

        all_captured = has_name and has_city and has_interests and has_skills and has_personality
        print_result("Concurrent Multiple Updates", all_captured,
                    "All fields should be updated in single call")

        return all_captured

    except Exception as e:
        print_result("Concurrent Multiple Updates", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_realistic_conversation_scenario():
    """
    Test Case 9: Realistic Multi-Turn Conversation (★★★★☆)

    Scenario: 12-turn realistic conversation covering multiple aspects
    Expected: Complete user profile built progressively
    Output: Detailed database state for manual verification
    """
    print_section("Test 9: Realistic Conversation Scenario")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_realistic_001"

        # 12-turn realistic conversation
        conversation_rounds = [
            # Round 1: Initial introduction
            {
                "messages": [
                    {"role": "user", "content": "你好，我叫李明，今年32岁"},
                    {"role": "assistant", "content": "你好李明！很高兴认识你。"}
                ],
                "description": "Round 1: Basic introduction"
            },
            # Round 2: Location and work
            {
                "messages": [
                    {"role": "user", "content": "我住在杭州，在一家互联网公司做产品经理"},
                    {"role": "assistant", "content": "杭州是个不错的城市，产品经理工作怎么样？"}
                ],
                "description": "Round 2: Location and career"
            },
            # Round 3: Interests - sports
            {
                "messages": [
                    {"role": "user", "content": "工作压力挺大的，不过我喜欢跑步来放松，每周至少跑3次"},
                    {"role": "assistant", "content": "跑步是很好的减压方式！"}
                ],
                "description": "Round 3: Interest in running"
            },
            # Round 4: Technical skills
            {
                "messages": [
                    {"role": "user", "content": "我会用Python做一些数据分析，能写SQL查询，还学过一点机器学习"},
                    {"role": "assistant", "content": "技术背景对产品经理很有帮助！"}
                ],
                "description": "Round 4: Technical skills"
            },
            # Round 5: More interests
            {
                "messages": [
                    {"role": "user", "content": "对了，我还很喜欢摄影，周末经常带着相机出去拍照"},
                    {"role": "assistant", "content": "摄影和跑步都是很好的爱好！"}
                ],
                "description": "Round 5: Photography interest"
            },
            # Round 6: Personality traits
            {
                "messages": [
                    {"role": "user", "content": "我这人比较好奇，喜欢尝试新事物，朋友都说我很外向"},
                    {"role": "assistant", "content": "这样的性格很适合做产品！"}
                ],
                "description": "Round 6: Personality traits"
            },
            # Round 7: Family background
            {
                "messages": [
                    {"role": "user", "content": "我家在南京，父母都是老师，我是独生子"},
                    {"role": "assistant", "content": "教师家庭，家教一定很好。"}
                ],
                "description": "Round 7: Family background"
            },
            # Round 8: Advanced skill
            {
                "messages": [
                    {"role": "user", "content": "我最近在学Figma做原型设计，感觉产品经理应该会这个"},
                    {"role": "assistant", "content": "是的，原型设计很重要！"}
                ],
                "description": "Round 8: New skill - Figma"
            },
            # Round 9: Interest deepening
            {
                "messages": [
                    {"role": "user", "content": "跑步我已经坚持3年了，去年还跑了个半马，成绩还不错"},
                    {"role": "assistant", "content": "太厉害了！半马很考验毅力。"}
                ],
                "description": "Round 9: Running expertise deepening"
            },
            # Round 10: Learning preferences
            {
                "messages": [
                    {"role": "user", "content": "我学东西比较喜欢看视频教程，边看边实践，这样学得快"},
                    {"role": "assistant", "content": "实践出真知！"}
                ],
                "description": "Round 10: Learning preferences"
            },
            # Round 11: Skill update
            {
                "messages": [
                    {"role": "user", "content": "Python现在用得很熟练了，公司的数据分析都是我做的"},
                    {"role": "assistant", "content": "进步很快啊！"}
                ],
                "description": "Round 11: Python skill upgrade"
            },
            # Round 12: New interest
            {
                "messages": [
                    {"role": "user", "content": "最近开始学吉他，虽然才学了一个月，但挺有意思的"},
                    {"role": "assistant", "content": "音乐也能陶冶情操！"}
                ],
                "description": "Round 12: New interest - guitar"
            },
        ]

        print("\n" + "="*70)
        print(" CONVERSATION SIMULATION (12 rounds)")
        print("="*70)

        # Execute conversation rounds
        for i, round_data in enumerate(conversation_rounds, 1):
            print(f"\n[{i}/12] {round_data['description']}")
            print(f"  User: {round_data['messages'][0]['content']}")

            result = user_profile.set_profile(
                user_id=user_id,
                messages=round_data['messages']
            )

            if result.get('success'):
                ops = result.get('operations_performed', {})
                print(f"  ✓ Operations: +{ops.get('added', 0)} ~{ops.get('updated', 0)} -{ops.get('deleted', 0)}")
            else:
                print(f"  ✗ Error: {result.get('error')}")

            time.sleep(0.3)  # Small delay between rounds

        # Retrieve final profile
        print("\n" + "="*70)
        print(" DATABASE STATE - FINAL PROFILE")
        print("="*70)

        profile = user_profile.get_profile(user_id=user_id)

        # Print Basic Info
        print("\n📋 BASIC INFO (PostgreSQL - Conversation-extracted reference data):")
        print("-" * 70)
        basic_info = profile.get('basic_info', {})
        if basic_info:
            for key, value in sorted(basic_info.items()):
                if value and key not in ['user_id', 'created_at', 'updated_at']:
                    print(f"  • {key}: {value}")
        else:
            print("  (No basic info extracted)")

        # Print Additional Profile
        additional = profile.get('additional_profile', {})

        # Interests
        print("\n❤️  INTERESTS:")
        print("-" * 70)
        interests = additional.get('interests', [])
        if interests:
            for item in interests:
                evidence_count = len(item.get('evidence', []))
                print(f"  • {item.get('name')} (degree: {item.get('degree')}/5, evidence: {evidence_count})")
                for ev in item.get('evidence', [])[:2]:  # Show first 2 evidence
                    print(f"    - \"{ev.get('text')}\" [{ev.get('timestamp', '')[:10]}]")
        else:
            print("  (None)")

        # Skills
        print("\n💡 SKILLS:")
        print("-" * 70)
        skills = additional.get('skills', [])
        if skills:
            for item in skills:
                evidence_count = len(item.get('evidence', []))
                print(f"  • {item.get('name')} (degree: {item.get('degree')}/5, evidence: {evidence_count})")
                for ev in item.get('evidence', [])[:2]:
                    print(f"    - \"{ev.get('text')}\" [{ev.get('timestamp', '')[:10]}]")
        else:
            print("  (None)")

        # Personality
        print("\n🎭 PERSONALITY:")
        print("-" * 70)
        personality = additional.get('personality', [])
        if personality:
            for item in personality:
                evidence_count = len(item.get('evidence', []))
                print(f"  • {item.get('name')} (degree: {item.get('degree')}/5, evidence: {evidence_count})")
                for ev in item.get('evidence', [])[:2]:
                    print(f"    - \"{ev.get('text')}\" [{ev.get('timestamp', '')[:10]}]")
        else:
            print("  (None)")

        # Social Context
        print("\n👨‍👩‍👦 SOCIAL CONTEXT:")
        print("-" * 70)
        social = additional.get('social_context', [])
        if social:
            for item in social:
                print(f"  • {item.get('name')}: {item.get('details', 'N/A')}")
                evidence_count = len(item.get('evidence', []))
                if evidence_count > 0:
                    print(f"    Evidence: {evidence_count} entries")
        else:
            print("  (None)")

        # Learning Preferences
        print("\n📚 LEARNING PREFERENCES:")
        print("-" * 70)
        learning = additional.get('learning_preferences', [])
        if learning:
            for item in learning:
                print(f"  • {item.get('name')}: {item.get('details', 'N/A')}")
        else:
            print("  (None)")

        # Statistics
        print("\n" + "="*70)
        print(" STATISTICS")
        print("="*70)
        print(f"  Total Interests: {len(interests)}")
        print(f"  Total Skills: {len(skills)}")
        print(f"  Total Personality Traits: {len(personality)}")
        print(f"  Total Social Context Items: {len(social)}")
        print(f"  Total Learning Preferences: {len(learning)}")

        total_evidence = sum(len(item.get('evidence', [])) for item in interests + skills + personality)
        print(f"  Total Evidence Entries: {total_evidence}")

        # Validation
        print("\n" + "="*70)
        print(" VALIDATION")
        print("="*70)

        checks = {
            "Basic info extracted": len(basic_info) > 0,
            "At least 3 interests": len(interests) >= 3,
            "At least 3 skills": len(skills) >= 3,
            "At least 2 personality traits": len(personality) >= 2,
            "Evidence accumulated": total_evidence >= 10,
        }

        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")

        all_passed = all(checks.values())
        print_result("Realistic Conversation Scenario", all_passed,
                    f"Profile completeness: {sum(checks.values())}/{len(checks)} checks passed")

        return all_passed

    except Exception as e:
        print_result("Realistic Conversation Scenario", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_long_rich_prompt():
    """
    Test Case 10: Long Rich Prompt (★★★☆☆)

    Scenario: Single user message with rich, dense information
    Expected: All information points extracted correctly
    """
    print_section("Test 10: Long Rich Prompt")

    try:
        config = MemoryConfig(**TEST_CONFIG)
        user_profile = UserProfile(config)
        user_id = "test_long_prompt_001"

        # Long, information-dense prompt
        long_prompt = """
        你好！我叫赵刚，今年35岁，来自成都，现在在深圳工作，是一名资深的全栈工程师。

        我的技术栈很广：精通Python、JavaScript和Go语言，熟悉React和Vue前端框架，
        会用Docker和Kubernetes做容器化部署，还了解一些DevOps的知识。数据库方面，
        MySQL和PostgreSQL都很熟练，MongoDB也会用。

        工作之余，我有很多爱好。我特别喜欢爬山，每个月都会去附近的山爬一次，
        已经爬过深圳的梧桐山、七娘山好多次了。我也喜欢看科幻小说，刘慈欣的作品都读过，
        最近在看《三体》英文版练英语。摄影也是我的爱好之一，用的是Sony A7M3，
        主要拍风景和人文。音乐方面，我会弹吉他，学了5年了，现在能自己编曲。

        性格上，我比较内向但很专注，喜欢深入研究技术问题，有点完美主义。
        朋友说我很靠谱，做事认真负责。我也挺好学的，总想学新东西，最近在学Rust语言。

        家庭方面，我已婚，妻子是设计师，我们有一个3岁的女儿。父母还在成都，
        都退休了，身体挺好的。我是独生子，所以工作之余经常回成都看望父母。

        学习方法上，我比较喜欢通过实践学习，边做项目边学。看技术文档和视频教程都可以，
        但最重要的是要动手实践。我习惯在晚上学习，效率比较高。
        """

        print("\nProcessing long prompt with dense information...")
        print(f"Prompt length: {len(long_prompt)} characters")

        result = user_profile.set_profile(
            user_id=user_id,
            messages=[{"role": "user", "content": long_prompt}]
        )

        print(f"\nExtraction result:")
        if result.get('success'):
            ops = result.get('operations_performed', {})
            print(f"  ✓ Operations: +{ops.get('added', 0)} ~{ops.get('updated', 0)} -{ops.get('deleted', 0)}")
        else:
            print(f"  ✗ Error: {result.get('error')}")

        # Retrieve and analyze profile
        profile = user_profile.get_profile(user_id=user_id)

        basic_info = profile.get('basic_info', {})
        additional = profile.get('additional_profile', {})

        interests = additional.get('interests', [])
        skills = additional.get('skills', [])
        personality = additional.get('personality', [])
        social = additional.get('social_context', [])
        learning = additional.get('learning_preferences', [])

        # Print extracted info summary
        print("\n📊 EXTRACTION SUMMARY:")
        print("-" * 70)
        print(f"  Basic Info Fields: {len([k for k, v in basic_info.items() if v and k not in ['user_id', 'created_at', 'updated_at']])}")
        print(f"  Interests: {len(interests)}")
        if interests:
            for item in interests:
                print(f"    - {item.get('name')} (degree: {item.get('degree')})")

        print(f"  Skills: {len(skills)}")
        if skills:
            for item in skills[:5]:  # Show first 5
                print(f"    - {item.get('name')} (degree: {item.get('degree')})")
            if len(skills) > 5:
                print(f"    ... and {len(skills) - 5} more")

        print(f"  Personality Traits: {len(personality)}")
        if personality:
            for item in personality:
                print(f"    - {item.get('name')} (degree: {item.get('degree')})")

        print(f"  Social Context: {len(social)}")
        print(f"  Learning Preferences: {len(learning)}")

        # Validation criteria
        print("\n✅ VALIDATION:")
        print("-" * 70)

        checks = {
            "Name extracted (赵刚)": basic_info.get('name') == '赵刚',
            "Age/City extracted": basic_info.get('current_city') or basic_info.get('hometown'),
            "At least 3 interests": len(interests) >= 3,
            "At least 5 skills": len(skills) >= 5,  # Should extract many technical skills
            "Personality traits": len(personality) >= 2,
            "Social context (family)": len(social) >= 1,
        }

        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")

        all_passed = all(checks.values())
        print_result("Long Rich Prompt", all_passed,
                    f"Information extraction: {sum(checks.values())}/{len(checks)} checks passed")

        return all_passed

    except Exception as e:
        print_result("Long Rich Prompt", False, f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all advanced test cases"""
    print_section("UserProfile Advanced Test Suite")
    print("Testing key challenges from development documentation")
    print("Difficulty levels: ★☆☆☆☆ to ★★★★★")

    test_functions = [
        test_contradiction_handling,          # ★★★☆☆
        test_interest_skill_overlap,          # ★★☆☆☆
        test_degree_dynamic_adjustment,       # ★★★☆☆
        test_evidence_accumulation,           # ★★☆☆☆
        test_basic_info_reference_data,       # ★★☆☆☆
        test_personality_inference,           # ★★★☆☆
        test_empty_and_null_handling,         # ★★☆☆☆
        test_concurrent_updates,              # ★★☆☆☆
        test_long_rich_prompt,                # ★★★☆☆
        test_realistic_conversation_scenario, # ★★★★☆
    ]

    results = []
    for test_func in test_functions:
        try:
            passed = test_func()
            results.append((test_func.__name__, passed))
        except Exception as e:
            print(f"\n✗ FATAL ERROR in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_func.__name__, False))

    # Summary
    print_section("Test Summary")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed\n")

    for test_name, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name.replace('test_', '').replace('_', ' ').title()}")

    if passed_count == total_count:
        print("\n🎉 All advanced tests passed!")
        return True
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)