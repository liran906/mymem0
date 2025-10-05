"""
Prompts for UserProfile LLM calls
"""

EXTRACT_PROFILE_PROMPT = """You are a profile extraction assistant. Your task is to extract user profile information from conversation messages.

Extract the following information:
1. **basic_info**: Basic personal information (name, birthday, location, etc.) - **Non-authoritative, conversation-extracted reference data only**
2. **additional_profile**: Extended information (interests, skills, personality, social_context, learning_preferences)

## Output Format

Return a JSON object with this structure:

```json
{{
    "basic_info": {{
        "name": "张三",
        "nickname": "小张",
        "english_name": "John",
        "birthday": "1990-01-15",
        "gender": "male",
        "nationality": "中国",
        "hometown": "北京",
        "current_city": "上海",
        "timezone": "Asia/Shanghai",
        "language": "zh-CN"
    }},
    "additional_profile": {{
        "interests": [
            {{
                "name": "足球",
                "degree": 4,
                "evidence": [
                    {{"text": "周末和朋友踢足球很开心"}}
                ]
            }}
        ],
        "skills": [
            {{
                "name": "Python编程",
                "degree": 3,
                "evidence": [
                    {{"text": "用Python写了一个数据分析工具"}}
                ]
            }}
        ],
        "personality": [
            {{
                "name": "外向",
                "degree": 4,
                "evidence": [
                    {{"text": "喜欢参加各种社交活动"}}
                ]
            }}
        ],
        "social_context": {{
            "family": {{
                "father": {{
                    "name": "John",
                    "info": ["doctor", "kind and loving", "plays football"]
                }},
                "mother": {{
                    "name": "Mary",
                    "info": ["teacher", "strict", "cooks delicious meals"]
                }},
                "brother": [
                    {{
                        "name": "Tom",
                        "info": ["older brother", "engineer"]
                    }}
                ]
            }},
            "friends": [
                {{
                    "name": "Jack",
                    "info": ["plays basketball", "likes movies"]
                }},
                {{
                    "name": null,
                    "info": ["classmate", "studies together"]
                }}
            ],
            "others": [
                {{
                    "name": "Amy",
                    "relation": "teacher",
                    "info": ["teaches math", "very patient"]
                }},
                {{
                    "name": null,
                    "relation": "uncle",
                    "info": ["lives in Beijing", "very humorous"]
                }}
            ]
        }},
        "learning_preferences": {{
            "preferred_time": "evening",
            "preferred_style": "visual",
            "difficulty_level": "intermediate"
        }}
    }}
}}
```

## Important Rules

1. **❗CRITICAL - Language consistency**: Keep the EXACT language of user input in ALL fields
   - ❌ WRONG: User says "退休了" → You output "retired"
   - ✅ CORRECT: User says "退休了" → You output "退休了"
   - ❌ WRONG: User says "designer" → You output "设计师"
   - ✅ CORRECT: User says "designer" → You output "designer"
   - **NO translation between Chinese/English/any languages**
   - **Copy the EXACT words from user's message**

2. **Evidence-based**: Every extracted attribute must have evidence (text only, NO timestamp)
   - For interests, skills, personality: Include evidence array with text field only
   - DO NOT include timestamp in evidence - timestamps are handled by the backend

3. **Degree system** (use English terms):
   - For interests: 1=dislike, 2=neutral, 3=like, 4=really like, 5=favorite
   - For skills: 1=beginner, 2=learning, 3=proficient, 4=advanced, 5=expert
   - For personality: 1=not obvious, 2=weak, 3=moderate, 4=strong, 5=very strong

4. **social_context extraction**: Extract user's mentioned social relationships

   **Field Structure**:
   - family: Direct family members ONLY (immediate relatives)
     * Fields: {{ "name": str|null, "info": [str] }}
     * Single members: father, mother, spouse, grandfather_*, grandmother_*
     * Multiple members (arrays): brother, sister, son, daughter, grandson, granddaughter

   - friends: Friend information
     * Fields: {{ "name": str|null, "info": [str] }}
     * Array of objects
     * NO relation field needed (they are all friends)

   - others: Other social relations (collateral relatives, teachers, colleagues, neighbors, etc.)
     * Fields: {{ "name": str|null, "relation": str (required), "info": [str] }}
     * Array of objects
     * Examples: uncle (叔叔/舅舅/姑父), aunt (姑姑/阿姨/舅妈), cousin (表哥/堂妹), teacher (老师), colleague (同事), neighbor (邻居)

   **Allowed family relations** (ONLY use these, DO NOT create new relations):
   - Core: father, mother
   - Common: brother, sister, grandfather_paternal, grandmother_paternal, grandfather_maternal, grandmother_maternal
   - Extended: spouse, son, daughter, grandson, granddaughter

   **CRITICAL Rules**:
   - ❗ name field: ONLY fill with actual name (e.g., "小芳"). If name not mentioned, set to null
     * ❌ WRONG: {{"name": "妻子"}} (this is relation, not name)
     * ✅ CORRECT: {{"name": "小芳"}} or {{"name": null}}

   - ❗ Collateral relatives (uncle/aunt/cousin) → Put in "others", NOT in "family"
     * Reason: Need "relation" field to distinguish (e.g., "姑姑" vs "阿姨")

   - ❗ Unified field format:
     * family members: ONLY {{ "name", "info" }} - NO career or other fields
     * friends: ONLY {{ "name", "info" }}
     * others: {{ "name", "relation", "info" }}

   - ❗ Use standardized relation names:
     * Spouse: Use "spouse" (NOT "wife" or "husband")
     * Siblings: Use "brother" or "sister" (NOT "sibling")

5. **learning_preferences extraction**: Extract learning preferences when mentioned
   - preferred_time: When user prefers to study - extract from mentions like "晚上学习", "早上效率高" → "morning" / "afternoon" / "evening"
   - preferred_style: How user likes to learn - extract from mentions like "看视频", "听讲座", "动手实践" → "visual" / "auditory" / "kinesthetic"
   - difficulty_level: Current learning level - extract from mentions like "初学者", "中级", "高级" → "beginner" / "intermediate" / "advanced"
   - Structure: object (NOT array)

6. **Only extract explicit information**: Don't infer or guess

7. **Omit missing fields**: If no information found for a field, DO NOT include that field in the JSON (both key and value should be omitted)
   - Return only the fields that have data from the conversation
   - Example: If no interests mentioned, don't include "interests" key at all

## Examples

### Example 1: Basic conversation
Messages:
- User: "我叫李明，今年30岁，住在杭州"

Output:
```json
{{
    "basic_info": {{
        "name": "李明",
        "current_city": "杭州"
    }}
}}
```

### Example 2: Interest extraction
Messages:
- User: "我最近迷上了摄影，每个周末都出去拍照"

Output:
```json
{{
    "additional_profile": {{
        "interests": [
            {{
                "name": "摄影",
                "degree": 4,
                "evidence": [
                    {{"text": "最近迷上了摄影，每个周末都出去拍照"}}
                ]
            }}
        ]
    }}
}}
```

### Example 3: Social context - name field rules (❗Language consistency)
Messages:
- User: "我爸爸叫李明，是医生。我妈妈是老师"
- User: "我有个好朋友Jack，他喜欢打篮球"

Output:
```json
{{
    "additional_profile": {{
        "social_context": {{
            "family": {{
                "father": {{
                    "name": "李明",
                    "info": ["医生"]
                }},
                "mother": {{
                    "name": null,
                    "info": ["老师"]
                }}
            }},
            "friends": [
                {{
                    "name": "Jack",
                    "info": ["喜欢打篮球"]
                }}
            ]
        }}
    }}
}}
```

### Example 4: Social context - collateral relatives go to others (❗Language consistency)
Messages:
- User: "我有两个哥哥，大哥叫小明，在北京工作"
- User: "我舅舅是工程师，对我很好"

Output:
```json
{{
    "additional_profile": {{
        "social_context": {{
            "family": {{
                "brother": [
                    {{
                        "name": "小明",
                        "info": ["大哥", "在北京工作"]
                    }},
                    {{
                        "name": null,
                        "info": ["哥哥"]
                    }}
                ]
            }},
            "others": [
                {{
                    "name": null,
                    "relation": "舅舅",
                    "info": ["工程师", "对我很好"]
                }}
            ]
        }}
    }}
}}
```

### Example 5: Social context - spouse and children (❗Language consistency)
Messages:
- User: "我老婆叫小芳，是设计师。我们有个女儿叫小静静，今年三岁"

Output:
```json
{{
    "additional_profile": {{
        "social_context": {{
            "family": {{
                "spouse": {{
                    "name": "小芳",
                    "info": ["设计师"]
                }},
                "daughter": [
                    {{
                        "name": "小静静",
                        "info": ["三岁"]
                    }}
                ]
            }}
        }}
    }}
}}
```

---

Now extract profile information from the following messages:

{messages}

Return only the JSON object, no additional text.
"""

UPDATE_PROFILE_PROMPT = """You are a profile update assistant. Your task is to analyze extracted profile information and existing data, then decide what operations to perform.

## Input Data

### Extracted Information (from messages)
{extracted_info}

### Existing Profile (from database, with timestamps for reference)
{existing_profile}

## Your Task

For each item in the extracted information, decide one of the following operations:
- **ADD**: Add new information (item doesn't exist)
- **UPDATE**: Update existing information (evidence supports change)
- **DELETE**: Remove information (evidence supports removal, e.g., "我不再喜欢足球了")
- **SKIP**: No action needed (information is the same)

## Output Format

```json
{{
    "basic_info": {{
        "name": "张三",
        "current_city": "上海"
    }},
    "additional_profile": {{
        "interests": [
            {{
                "id": "1",
                "event": "UPDATE",
                "name": "足球",
                "degree": 5,
                "evidence": [
                    {{"text": "周末又赢了一场比赛"}}
                ]
            }},
            {{
                "id": null,
                "event": "ADD",
                "name": "摄影",
                "degree": 3,
                "evidence": [
                    {{"text": "买了新相机，开始学摄影"}}
                ]
            }}
        ],
        "skills": [
            {{
                "id": "2",
                "event": "DELETE",
                "name": "Java"
            }}
        ]
    }}
}}
```

## Important Rules

1. **Language consistency**: Keep the language of JSON values consistent with user input (no translation between Chinese/English)

2. **NO timestamps in output**: DO NOT include timestamp in evidence - timestamps are handled by the backend
   - You can USE the timestamps from existing profile to understand how old the data is
   - But DO NOT return timestamps in your output

3. **ID mapping**: Use the ID from existing profile. For ADD operations, set id=null

4. **Evidence analysis for contradictions**:
   - If user says "不喜欢了" but has 10 recent evidence entries showing they like it → reduce degree (temporary mood)
   - If user says "不喜欢了" and has only 2 old evidence entries → DELETE (previous judgment may be wrong)
   - If user says "不喜欢了" and has 10 old evidence entries (6+ months ago) → DELETE (real change)

5. **Degree updates**: When updating, combine new evidence with existing evidence to determine new degree

6. **basic_info**: Always use direct UPSERT (no ADD/UPDATE/DELETE events)

7. **Evidence consolidation**: Return only NEW evidence to add - the backend will merge with existing evidence

8. **social_context special handling** - CRITICAL for preserving existing relationships:
   - ❗ social_context uses **DEEP MERGE**, NOT overwrite
   - When adding/updating a relationship, preserve ALL other existing relationships
   - Example: If existing has father/mother, and new info mentions spouse → ADD spouse, KEEP father/mother
   - ❌ WRONG: Return only spouse (will lose father/mother)
   - ✅ CORRECT: Return ADD operation for spouse only, backend will merge

   **For social_context operations**:
   - Return only the relationships that are mentioned in new messages
   - Use ADD/UPDATE/DELETE events for individual relationships
   - Backend will merge with existing data, preserving unmentioned relationships

   **social_context event types**:
   - ADD: Add new relationship (e.g., add spouse when only father/mother exist)
   - UPDATE: Update existing relationship info (e.g., add new info about existing father)
   - DELETE: Remove relationship (only when explicitly stated)

## Examples

### Example 1: Add new interest
Extracted: User says "我开始喜欢爬山了"
Existing: No "爬山" in interests
Output:
```json
{{
    "additional_profile": {{
        "interests": [
            {{
                "id": null,
                "event": "ADD",
                "name": "爬山",
                "degree": 3,
                "evidence": [{{"text": "我开始喜欢爬山了"}}]
            }}
        ]
    }}
}}
```

### Example 2: Update degree
Extracted: User says "我现在是Python专家了"
Existing: {{"id": "5", "name": "Python", "degree": 3, "evidence": [...]}}
Output:
```json
{{
    "additional_profile": {{
        "skills": [
            {{
                "id": "5",
                "event": "UPDATE",
                "name": "Python",
                "degree": 5,
                "evidence": [{{"text": "我现在是Python专家了"}}]
            }}
        ]
    }}
}}
```

### Example 3: Handle contradiction
Extracted: User says "我不喜欢足球了"
Existing: {{"id": "1", "name": "足球", "degree": 4, "evidence": [10 entries with timestamps 8 months ago]}}
Analysis: Many old evidence, real change → DELETE
Output:
```json
{{
    "additional_profile": {{
        "interests": [
            {{
                "id": "1",
                "event": "DELETE",
                "name": "足球"
            }}
        ]
    }}
}}
```

### Example 4: social_context deep merge - ADD new relationship (❗Language consistency)
Extracted: User says "我老婆叫小芳，是设计师"
Existing: {{
    "social_context": {{
        "family": {{
            "father": {{"name": null, "info": ["退休了"]}},
            "mother": {{"name": null, "info": ["退休了"]}}
        }}
    }}
}}
Analysis: New spouse info, existing father/mother should be preserved
Output:
```json
{{
    "additional_profile": {{
        "social_context": {{
            "family": {{
                "spouse": {{
                    "event": "ADD",
                    "name": "小芳",
                    "info": ["设计师"]
                }}
            }}
        }}
    }}
}}
```
Note: Backend will merge this with existing father/mother. Do NOT return father/mother here.

### Example 5: social_context deep merge - UPDATE existing relationship (❗Language consistency)
Extracted: User says "我爸爸身体很好"
Existing: {{
    "social_context": {{
        "family": {{
            "father": {{"name": "李明", "info": ["退休了"]}},
            "mother": {{"name": null, "info": ["退休了"]}}
        }}
    }}
}}
Analysis: Update father's info, preserve mother
Output:
```json
{{
    "additional_profile": {{
        "social_context": {{
            "family": {{
                "father": {{
                    "event": "UPDATE",
                    "name": "李明",
                    "info": ["退休了", "身体很好"]
                }}
            }}
        }}
    }}
}}
```
Note: Backend will preserve mother. Do NOT return mother here.

---

Now analyze the data and return the operations to perform.

Return only the JSON object, no additional text.
"""