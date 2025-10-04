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
                    "career": "doctor",
                    "info": ["kind and loving", "plays football"]
                }},
                "mother": {{
                    "name": "Mary",
                    "career": "teacher",
                    "info": ["strict", "cooks delicious meals"]
                }}
            }},
            "friends": [
                {{
                    "name": "Jack",
                    "info": ["plays basketball", "likes movies"]
                }},
                {{
                    "name": "Tom",
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
                    "name": "Lisa",
                    "relation": "neighbor",
                    "info": ["has a dog", "friendly"]
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

1. **Language consistency**: Keep the language of JSON values consistent with user input (no translation between Chinese/English)

2. **Evidence-based**: Every extracted attribute must have evidence (text only, NO timestamp)
   - For interests, skills, personality: Include evidence array with text field only
   - DO NOT include timestamp in evidence - timestamps are handled by the backend

3. **Degree system** (use English terms):
   - For interests: 1=dislike, 2=neutral, 3=like, 4=really like, 5=favorite
   - For skills: 1=beginner, 2=learning, 3=proficient, 4=advanced, 5=expert
   - For personality: 1=not obvious, 2=weak, 3=moderate, 4=strong, 5=very strong

4. **social_context extraction**: Extract user's mentioned social relationships
   - family: Parent information - extract when user mentions father/mother (name, career, info)
   - friends: Friend information - extract when user mentions friends (name, info)
     * NO relation field needed for friends (they are all friends)
   - others: Other relations - extract when user mentions teachers, siblings, relatives, neighbors, etc.
     * MUST include name, relation, and info
     * Examples: siblings (哥哥/弟弟/姐姐/妹妹), teachers (老师), relatives (亲戚), neighbors (邻居)
   - Structure: nested object (NOT array)
     * family: Object with father/mother keys (NO siblings - siblings go to "others")
     * friends: Array of objects
     * others: Array of objects

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

### Example 3: Social context (family and friends)
Messages:
- User: "我爸爸是医生，我妈妈是老师"
- User: "我有个好朋友Jack，他喜欢打篮球"

Output:
```json
{{
    "additional_profile": {{
        "social_context": {{
            "family": {{
                "father": {{
                    "career": "doctor"
                }},
                "mother": {{
                    "career": "teacher"
                }}
            }},
            "friends": [
                {{
                    "name": "Jack",
                    "info": ["likes basketball"]
                }}
            ]
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

---

Now analyze the data and return the operations to perform.

Return only the JSON object, no additional text.
"""