#!/usr/bin/env python3
"""
Test social_context deep merge functionality

This test verifies that adding new family relationships (spouse, daughter)
does not overwrite existing relationships (father, mother).
"""

import requests
import json
import time

BASE_URL = "http://localhost:18088"
USER_ID = "test_user_merge_001"

def delete_profile():
    """Delete existing profile to start fresh"""
    print(f"\n1. Deleting existing profile for {USER_ID}...")
    response = requests.delete(f"{BASE_URL}/profile", params={"user_id": USER_ID})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")

def send_message(messages):
    """Send messages to update profile"""
    data = {
        "user_id": USER_ID,
        "messages": [{"role": "user", "content": msg} for msg in messages]
    }
    response = requests.post(f"{BASE_URL}/profile", json=data)
    return response

def get_profile():
    """Get current profile"""
    response = requests.get(f"{BASE_URL}/profile", params={"user_id": USER_ID, "evidence_limit": -1})
    return response

def main():
    print("=" * 80)
    print("Testing social_context Deep Merge")
    print("=" * 80)

    # Step 1: Delete existing profile
    delete_profile()
    time.sleep(1)

    # Step 2: First message - father and mother
    print("\n2. Sending first message (father and mother)...")
    msg1 = "我已婚，妻子是设计师，我们有一个3岁的女儿。父母还在成都，都退休了，身体挺好的。我是独生子"
    response = send_message([msg1])
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Operations: {result.get('operations_performed')}")
    else:
        print(f"   Error: {response.text}")
        return

    time.sleep(1)

    # Step 3: Get profile after first message
    print("\n3. Getting profile after first message...")
    response = get_profile()
    if response.status_code == 200:
        profile1 = response.json()
        social_context1 = profile1.get("additional_profile", {}).get("social_context", {})
        family1 = social_context1.get("family", {})
        print(f"   Family members: {list(family1.keys())}")
        print(f"   Father: {family1.get('father')}")
        print(f"   Mother: {family1.get('mother')}")
        others1 = social_context1.get("others", [])
        print(f"   Others count: {len(others1)}")
        if others1:
            print(f"   Others: {[o.get('relation') for o in others1]}")
    else:
        print(f"   Error: {response.text}")
        return

    # Step 4: Second message - spouse and daughter names
    print("\n4. Sending second message (spouse and daughter names)...")
    msg2 = "我的老婆叫小芳，我和她七年前就结婚了。我女儿叫小静静，她今年三岁，十分可爱"
    response = send_message([msg2])
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Operations: {result.get('operations_performed')}")
    else:
        print(f"   Error: {response.text}")
        return

    time.sleep(1)

    # Step 5: Get profile after second message
    print("\n5. Getting profile after second message...")
    response = get_profile()
    if response.status_code == 200:
        profile2 = response.json()
        social_context2 = profile2.get("additional_profile", {}).get("social_context", {})
        family2 = social_context2.get("family", {})
        print(f"   Family members: {list(family2.keys())}")

        print("\n   Family details:")
        for relation, data in family2.items():
            if isinstance(data, dict):
                print(f"   - {relation}: name={data.get('name')}, info={data.get('info')}")
            elif isinstance(data, list):
                print(f"   - {relation}: {[{'name': d.get('name'), 'info': d.get('info')} for d in data]}")

        # Verify father and mother still exist
        print("\n6. Verification:")
        if "father" in family2:
            print(f"   ✅ father preserved: {family2['father']}")
        else:
            print("   ❌ father lost!")

        if "mother" in family2:
            print(f"   ✅ mother preserved: {family2['mother']}")
        else:
            print("   ❌ mother lost!")

        if "spouse" in family2:
            print(f"   ✅ spouse added: {family2['spouse']}")
        else:
            print("   ⚠️  spouse not found")

        if "daughter" in family2:
            print(f"   ✅ daughter added: {family2['daughter']}")
        else:
            print("   ⚠️  daughter not found")

        # Check name field
        print("\n7. Name field validation:")
        for relation, data in family2.items():
            if isinstance(data, dict):
                name = data.get("name")
                if relation in ["spouse", "daughter"] and name and name not in ["spouse", "daughter", "妻子", "女儿"]:
                    print(f"   ✅ {relation}.name correctly set: {name}")
                elif relation in ["spouse", "daughter"] and name in ["spouse", "daughter", "妻子", "女儿"]:
                    print(f"   ❌ {relation}.name incorrectly filled with relation word: {name}")
            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    name = item.get("name")
                    if relation in ["daughter"] and name and name not in ["daughter", "女儿"]:
                        print(f"   ✅ {relation}[{idx}].name correctly set: {name}")
                    elif relation in ["daughter"] and name in ["daughter", "女儿"]:
                        print(f"   ❌ {relation}[{idx}].name incorrectly filled: {name}")

    else:
        print(f"   Error: {response.text}")

    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)

if __name__ == "__main__":
    main()
