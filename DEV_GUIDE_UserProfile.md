# UserProfile 功能开发指南

> 本文档是 UserProfile 模块的完整开发指南，可直接指导开发工作。

**版本**: 1.0
**创建日期**: 2025-10-04
**适用阶段**: MVP (Minimum Viable Product)

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [数据模型](#3-数据模型)
4. [核心 Pipeline](#4-核心-pipeline)
5. [Prompt 设计](#5-prompt-设计)
6. [API 设计](#6-api-设计)
7. [错误处理](#7-错误处理)
8. [实施步骤](#8-实施步骤)
9. [测试用例](#9-测试用例)
10. [部署配置](#10-部署配置)

---

## 1. 项目概述

### 1.1 功能描述

开发一个**用户画像系统**，从对话中自动提取和管理用户的：
- 基本信息（姓名、生日、地理位置等）
- 兴趣爱好
- 技能
- 性格特征
- 社交关系
- 学习偏好

为 AI 对话提供丰富的用户上下文。

### 1.2 核心设计理念

**Evidence-Based（基于证据）**：
- 每个判断都有证据支撑
- 证据包含文本描述和时间戳
- LLM 可综合分析证据做出智能决策

### 1.3 暂不实现的功能

- **词汇管理**（vocab）：归档到 `archived/vocab_design.md`
- 理由：逻辑需要与产品进一步讨论
- 处理：预留接口，返回 501 Not Implemented

---

## 2. 架构设计

### 2.1 模块结构

```
mem0/
├── memory/                 # 现有：记忆模块
│   └── ...
├── user_profile/           # 新增：用户画像模块
│   ├── __init__.py         # 暴露 UserProfile 类
│   ├── main.py             # UserProfile 主类
│   ├── profile_manager.py  # Profile 业务逻辑
│   ├── vocab_manager.py    # Vocab 业务逻辑（预留，返回 Not Implemented）
│   ├── prompts.py          # Prompt 模板
│   ├── models.py           # Pydantic 数据模型
│   ├── database/
│   │   ├── __init__.py
│   │   ├── postgres.py     # PostgreSQL 操作封装
│   │   └── mongodb.py      # MongoDB 操作封装
│   └── utils.py            # 工具函数
├── llms/                   # 现有：LLM 提供商
├── embeddings/             # 现有：Embedding 提供商
└── ...

server/
├── main.py                 # FastAPI 服务（修改）
└── ...
```

### 2.2 组件关系

```
┌─────────────────────────────────────────────────┐
│            FastAPI Server (server/main.py)      │
│  - USER_PROFILE_INSTANCE = UserProfile(config)  │
│  - POST /profile → set_profile()                │
│  - GET /profile → get_profile()                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│      UserProfile (mem0/user_profile/main.py)    │
│  - __init__(config)                             │
│  - set_profile(user_id, messages, ...)          │
│  - get_profile(user_id, type, field, ...)       │
└─────────┬───────────────────────────────────────┘
          │
          ├──────────────────┬──────────────────┐
          ▼                  ▼                  ▼
┌──────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  ProfileManager  │ │ PostgresManager │ │ MongoDBManager  │
│  (业务逻辑)       │ │ (数据访问)       │ │ (数据访问)       │
└──────────────────┘ └─────────────────┘ └─────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────┐
│             LLM (复用 mem0 的 LLM)                │
│  - DeepSeek (provider: deepseek)                 │
└──────────────────────────────────────────────────┘
```

### 2.3 数据流

```
1. 用户对话 (messages)
   ↓
2. FastAPI 接收 POST /profile
   ↓
3. UserProfile.set_profile()
   ↓
4. ProfileManager.set_profile()
   ├─ 阶段 1: LLM 提取信息 + evidence
   ├─ 查询现有数据 (PostgreSQL + MongoDB)
   ├─ 阶段 2: LLM 判断更新操作 (ADD/UPDATE/DELETE)
   └─ 执行数据库操作
   ↓
5. 返回结果给 FastAPI
   ↓
6. 返回 JSON 响应给客户端
```

---

## 3. 数据模型

### 3.1 PostgreSQL: user_profile 表

**用途**：存储用户基本信息（结构化、稳定）

```sql
CREATE SCHEMA IF NOT EXISTS user_profile;

CREATE TABLE user_profile.user_profile (
    user_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 基本信息
    name VARCHAR(100),
    nickname VARCHAR(100),
    english_name VARCHAR(100),
    birthday DATE,
    gender VARCHAR(10),

    -- 地理和文化
    nationality VARCHAR(50),
    hometown VARCHAR(100),
    current_city VARCHAR(100),
    timezone VARCHAR(50),
    language VARCHAR(50),

    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

-- 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profile_updated_at
    BEFORE UPDATE ON user_profile.user_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| user_id | VARCHAR(50) | 用户唯一标识 | "u123" |
| name | VARCHAR(100) | 真实姓名 | "爱丽丝" |
| nickname | VARCHAR(100) | 昵称 | "小艾" |
| english_name | VARCHAR(100) | 英文名 | "Alice" |
| birthday | DATE | 生日 | "2018-07-15" |
| gender | VARCHAR(10) | 性别 | "F" / "M" / "Other" |
| nationality | VARCHAR(50) | 国籍 | "China" |
| hometown | VARCHAR(100) | 家乡 | "Nanjing" |
| current_city | VARCHAR(100) | 当前城市 | "Beijing" |
| timezone | VARCHAR(50) | 时区 | "Asia/Shanghai" |
| language | VARCHAR(50) | 主要语言 | "Chinese" |

---

### 3.2 MongoDB: user_additional_profile 集合

**用途**：存储用户扩展信息（灵活、可扩展）

```javascript
{
    "_id": ObjectId("..."),
    "user_id": "u123",

    // 兴趣（允许与 skills 重叠）
    "interests": [
        {
            "id": "0",
            "name": "足球",
            "degree": 4,  // 1-5: 喜好程度
            "evidence": [
                {
                    "text": "和朋友踢足球很开心",
                    "timestamp": "2025-10-01T10:30:00"
                },
                {
                    "text": "周末又赢了一场",
                    "timestamp": "2025-10-08T15:20:00"
                }
            ]
        }
    ],

    // 技能（允许与 interests 重叠）
    "skills": [
        {
            "id": "0",
            "name": "python",
            "degree": 2,  // 1-5: 掌握程度
            "evidence": [
                {
                    "text": "学了 Python 的 for 循环",
                    "timestamp": "2025-09-20T14:00:00"
                }
            ]
        }
    ],

    // 性格
    "personality": [
        {
            "id": "0",
            "name": "好奇",
            "degree": 4,  // 1-5: 明显程度
            "evidence": [
                {
                    "text": "主动问了很多问题",
                    "timestamp": "2025-10-01T10:00:00"
                }
            ]
        }
    ],

    // 社交关系
    "social_context": {
        "family": {
            "father": {
                "name": "John",
                "career": "doctor",
                "info": ["kind and loving", "plays football"]
            },
            "mother": {
                "name": "Mary",
                "career": "teacher",
                "info": ["strict", "cooks delicious meals"]
            },
            "siblings": ["younger brother"]
        },
        "friends": [
            {"name": "Tom", "relation": "classmate"},
            {"name": "Jerry", "relation": "neighbor"}
        ]
    },

    // 学习偏好
    "learning_preferences": {
        "preferred_time": "evening",      // "morning" / "afternoon" / "evening"
        "preferred_style": "visual",      // "visual" / "auditory" / "kinesthetic"
        "difficulty_level": "intermediate" // "beginner" / "intermediate" / "advanced"
    },

    // 系统元数据
    "system_metadata": {
        "created_at": "2025-10-01T00:00:00",
        "updated_at": "2025-10-03T12:30:00",
        "version": 1
    }
}
```

**MongoDB 索引**：
```javascript
db.user_additional_profile.createIndex({ "user_id": 1 }, { unique: true });
db.user_additional_profile.createIndex({ "interests.name": 1 });
db.user_additional_profile.createIndex({ "skills.name": 1 });
db.user_additional_profile.createIndex({ "personality.name": 1 });
```

**统一字段结构** (interests / skills / personality)：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识（整数字符串，如 "0", "1"） |
| name | string | 名称（中文） |
| degree | int (1-5) | 程度（兴趣=喜好程度，技能=掌握程度，性格=明显程度） |
| evidence | array | 证据列表 |
| evidence[].text | string | 证据描述（简短，1-2句话） |
| evidence[].timestamp | ISO8601 | 时间戳 |

---

## 4. 核心 Pipeline

### 4.1 set_profile 完整流程

```
┌─────────────────────────────────────────────────┐
│  Input: user_id, messages, manual_data, options │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Step 1: 合并前端数据和 LLM 提取（basic_info）   │
│  - 如果 manual_data 有值，优先使用              │
│  - 否则调用 LLM 提取 basic_info                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Step 2: LLM 提取扩展信息（阶段 1）              │
│  - 提取 interests, skills, personality          │
│  - 每项包含 name 和 evidence                    │
│  - 返回 JSON 格式                               │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Step 3: 查询现有数据                           │
│  - PostgreSQL: user_profile (basic_info)        │
│  - MongoDB: user_additional_profile (全部)      │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Step 4: basic_info 直接 UPSERT                 │
│  - 不需要 LLM 判断                              │
│  - 有值就更新，无值就保持                       │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Step 5: LLM 判断扩展信息更新（阶段 2）          │
│  - Input: 现有数据 + 新提取数据                 │
│  - Output: ADD / UPDATE / DELETE 决策           │
│  - 包含新的 degree 和 evidence                  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Step 6: 执行数据库操作                         │
│  - 逐字段容错处理                               │
│  - 记录日志                                     │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Output: 返回更新结果                           │
│  - basic_info: 更新了哪些字段                   │
│  - interests/skills/personality: 各项的操作     │
└─────────────────────────────────────────────────┘
```

### 4.2 get_profile 查询流程

```
┌─────────────────────────────────────────────────┐
│  Input: user_id, type, field, query_all         │
└─────────────────┬───────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
    type="basic"      type="additional"
         │                 │
         ▼                 ▼
  查询 PostgreSQL    查询 MongoDB
         │                 │
         │                 ├─ field="" → 返回全部
         │                 ├─ field="interests" → 返回 interests
         │                 └─ field="social_context.father.name" → 点语法查询
         │                 │
         └────────┬────────┘
                  ▼
         合并结果 (如果 type="all")
                  │
                  ▼
         返回 JSON 响应
```

---

## 5. Prompt 设计

### 5.1 阶段 1：提取信息和 evidence

**Prompt 模板** (`mem0/user_profile/prompts.py`):

```python
PROFILE_EXTRACTION_PROMPT = """你是一个用户画像专家，擅长从对话中提取用户的特征信息。

**任务**：从对话中提取用户的兴趣、技能和性格特征，并记录相关证据。

**对话内容**：
{messages}

**请返回 JSON 格式**（严格遵守格式）：
{{
    "basic_info": {{
        "current_city": "Beijing",
        "hometown": "Nanjing"
    }},
    "interests": [
        {{
            "name": "足球",
            "evidence": "和朋友踢足球很开心"
        }}
    ],
    "skills": [
        {{
            "name": "python",
            "evidence": "学了 Python 的 for 循环"
        }}
    ],
    "personality": [
        {{
            "name": "好奇",
            "evidence": "主动问了很多问题"
        }}
    ]
}}

**提取规则**：
1. **basic_info**：只提取对话中明确提到的基本信息字段
   - 可用字段：current_city, hometown, nationality, timezone, language
   - 如果没有提及，返回空对象 {{}}

2. **interests**：用户喜欢、感兴趣的活动或事物
   - name：兴趣名称（中文）
   - evidence：具体的事实描述（1-2句话，从对话中提取）

3. **skills**：用户掌握、会做的技能或能力
   - name：技能名称（中文）
   - evidence：具体的事实描述

4. **personality**：从对话中推断的性格特征
   - name：性格特征（中文，如"好奇"、"外向"、"耐心"）
   - evidence：支持这个特征的行为描述

**注意事项**：
- 只提取对话中明确提到或明显体现的内容
- 不要过度推断
- evidence 必须是具体的事实，不要是模糊的总结
- 如果某一类信息不存在，返回空列表 []
- 严格按照 JSON 格式返回，不要添加额外的文字
- 保持中文输出
"""

def get_profile_extraction_prompt(messages: List[Dict[str, str]]) -> str:
    """生成阶段 1 的提取 Prompt"""
    # 格式化 messages
    formatted_messages = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    ])

    return PROFILE_EXTRACTION_PROMPT.format(messages=formatted_messages)
```

---

### 5.2 阶段 2：判断更新操作

**Prompt 模板**：

```python
PROFILE_UPDATE_DECISION_PROMPT = """你是一个用户画像管理专家，负责判断如何更新用户画像。

**当前用户画像**：
{current_profile}

**从最新对话提取的信息**：
{extracted_info}

**任务**：判断如何更新用户画像，返回 ADD / UPDATE / DELETE 决策。

**返回 JSON 格式**（严格遵守）：
{{
    "interests": [
        {{
            "id": "0",
            "name": "足球",
            "event": "UPDATE",
            "new_degree": 4,
            "new_evidence": {{
                "text": "和朋友踢足球很开心",
                "timestamp": "{current_time}"
            }},
            "reason": "新增了积极的证据"
        }},
        {{
            "name": "北京烤鸭",
            "event": "ADD",
            "new_degree": 3,
            "new_evidence": {{
                "text": "吃了北京烤鸭，很好吃",
                "timestamp": "{current_time}"
            }},
            "reason": "新发现的兴趣"
        }}
    ],
    "skills": [...],
    "personality": [...]
}}

**判断规则**：

1. **ADD（新增）**：
   - 名称在当前画像中不存在
   - 生成新 ID（由程序处理，不需要返回）
   - 初始 degree：根据 evidence 质量判断（通常 2-3）

2. **UPDATE（更新）**：
   - 名称已存在
   - 必须使用原 ID
   - 添加新 evidence
   - 重新评估 degree（综合考虑所有 evidence）

3. **DELETE（删除）**：
   - 新对话明确表示不再喜欢/不会/不具备该特征
   - 综合考虑：
     * 旧 evidence 数量：多 → 谨慎删除
     * 旧 evidence 时间：近期 → 可能是临时情绪，降 degree 而不删除
     * 旧 evidence 时间：久远 → 可能真的改变了，可以删除

4. **degree 评估**（1-5）：
   - 兴趣：1=不太喜欢, 2=一般, 3=喜欢, 4=很喜欢, 5=最爱
   - 技能：1=初学, 2=入门, 3=中级, 4=高级, 5=专家
   - 性格：1=不明显, 2=偶尔, 3=一般, 4=明显, 5=非常明显
   - 判断依据：evidence 数量 + 质量 + 时间分布

**矛盾处理示例**：

- 场景1：旧 evidence 多(6+)且时间近(3个月内)，用户说"不喜欢了"
  → 判断：可能是临时情绪
  → 操作：UPDATE, new_degree = max(1, old_degree - 2)

- 场景2：旧 evidence 多但时间久远(1年前)，用户说"不喜欢了"
  → 判断：兴趣可能真的改变了
  → 操作：DELETE

- 场景3：旧 evidence 少(1-2)，用户说"不喜欢了"
  → 判断：之前判断可能不准确
  → 操作：DELETE

**证据时间分析**（已提供）：
{evidence_analysis}

**当前时间**：{current_time}

**注意事项**：
- ID 必须来自当前画像，不要生成新的 ID
- degree 必须是 1-5 的整数
- reason 字段简短说明判断理由
- 严格按照 JSON 格式返回
"""

def get_profile_update_decision_prompt(
    current_profile: Dict[str, Any],
    extracted_info: Dict[str, Any],
    evidence_analysis: Optional[Dict[str, Any]] = None
) -> str:
    """生成阶段 2 的更新决策 Prompt"""
    import json
    from datetime import datetime

    current_time = datetime.now().isoformat()

    # 格式化当前画像（简化显示）
    formatted_current = format_profile_for_prompt(current_profile)

    # 格式化提取的信息
    formatted_extracted = json.dumps(extracted_info, ensure_ascii=False, indent=2)

    # 格式化证据分析（如果提供）
    formatted_analysis = ""
    if evidence_analysis:
        formatted_analysis = json.dumps(evidence_analysis, ensure_ascii=False, indent=2)

    return PROFILE_UPDATE_DECISION_PROMPT.format(
        current_profile=formatted_current,
        extracted_info=formatted_extracted,
        evidence_analysis=formatted_analysis,
        current_time=current_time
    )

def format_profile_for_prompt(profile: Dict[str, Any]) -> str:
    """格式化画像数据，便于 LLM 理解"""
    lines = []

    for category in ["interests", "skills", "personality"]:
        items = profile.get(category, [])
        if items:
            lines.append(f"\n{category}:")
            for item in items:
                evidence_summary = f"{len(item.get('evidence', []))} 条证据"
                lines.append(f"  - {item['name']} (degree={item['degree']}, {evidence_summary})")
                # 可选：显示最近 2 条 evidence
                for ev in item.get('evidence', [])[:2]:
                    lines.append(f"    * \"{ev['text']}\" ({ev['timestamp'][:10]})")

    return "\n".join(lines)
```

---

## 6. API 设计

### 6.1 POST /profile（更新用户画像）

**请求**：

```http
POST /profile HTTP/1.1
Content-Type: application/json

{
    "user_id": "u123",
    "messages": [
        {
            "role": "user",
            "content": "我昨天搬家了，新家在北京"
        },
        {
            "role": "assistant",
            "content": "恭喜你搬新家！"
        },
        {
            "role": "user",
            "content": "是的，而且北京的烤鸭很好吃"
        }
    ],
    "manual_data": {
        "name": "Alice",
        "birthday": "2018-07-15"
    },
    "options": {
        "update_basic": true,
        "update_interests": true,
        "update_skills": true,
        "update_personality": true,
        "query_all": true
    }
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户ID |
| messages | array | 是 | 对话消息列表 |
| messages[].role | string | 是 | "user" / "assistant" |
| messages[].content | string | 是 | 消息内容 |
| manual_data | object | 否 | 前端手动输入的数据（优先级最高） |
| options | object | 否 | 控制选项 |
| options.update_basic | bool | 否 | 是否更新基本信息（默认 true） |
| options.update_interests | bool | 否 | 是否更新兴趣（默认 true） |
| options.update_skills | bool | 否 | 是否更新技能（默认 true） |
| options.update_personality | bool | 否 | 是否更新性格（默认 true） |
| options.query_all | bool | 否 | 是否查询全部数据（默认 true，false 时需提供查询字段） |

**响应**：

```json
{
    "results": {
        "basic_info": {
            "updated_fields": ["current_city"],
            "values": {
                "current_city": "Beijing",
                "name": "Alice",
                "birthday": "2018-07-15"
            }
        },
        "interests": [
            {
                "name": "北京烤鸭",
                "event": "ADD",
                "degree": 3
            }
        ],
        "skills": [],
        "personality": []
    }
}
```

---

### 6.2 GET /profile（获取用户画像）

**请求示例**：

```http
# 获取全部
GET /profile?user_id=u123&type=all

# 只获取基本信息
GET /profile?user_id=u123&type=basic

# 只获取兴趣
GET /profile?user_id=u123&type=additional&field=interests

# 获取嵌套字段（点语法）
GET /profile?user_id=u123&type=additional&field=social_context.father.name
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户ID |
| type | string | 否 | "basic" / "additional" / "all"（默认 "all"） |
| field | string | 否 | 字段名（支持点语法），仅在 type="additional" 时有效 |

**响应示例**：

```json
// type=all
{
    "user_id": "u123",
    "basic_info": {
        "name": "Alice",
        "birthday": "2018-07-15",
        "current_city": "Beijing",
        ...
    },
    "additional_profile": {
        "interests": [...],
        "skills": [...],
        "personality": [...],
        ...
    }
}

// type=additional&field=interests
{
    "user_id": "u123",
    "interests": [
        {
            "id": "0",
            "name": "足球",
            "degree": 4,
            "evidence": [...]
        }
    ]
}

// type=additional&field=social_context.father.name
{
    "user_id": "u123",
    "field": "social_context.father.name",
    "value": "John"
}
```

---

### 6.3 POST /vocab 和 GET /vocab（预留）

**实现**：返回 501 Not Implemented

```python
@app.post("/vocab", summary="Update user vocabulary (Not Implemented)")
def set_vocab():
    raise HTTPException(
        status_code=501,
        detail="Vocabulary management feature is not implemented in this version. See archived/vocab_design.md for future plans."
    )

@app.get("/vocab", summary="Get user vocabulary (Not Implemented)")
def get_vocab():
    raise HTTPException(
        status_code=501,
        detail="Vocabulary management feature is not implemented in this version."
    )
```

---

## 7. 错误处理

### 7.1 四层容错机制

#### 第 1 层：LLM 调用容错

```python
def call_llm_with_retry(self, prompt: str, max_retries: int = 2) -> str:
    """带重试的 LLM 调用"""
    for attempt in range(max_retries + 1):
        try:
            response = self.llm.generate_response(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt == max_retries:
                raise Exception(f"LLM service unavailable after {max_retries + 1} attempts")
            time.sleep(1)  # 等待 1 秒后重试
```

#### 第 2 层：JSON 解析容错

```python
from mem0.memory.utils import remove_code_blocks

def parse_llm_response(response: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON，带容错"""
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed, attempting to clean: {e}")

        # 尝试去除 markdown 代码块
        cleaned = remove_code_blocks(response)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error(f"JSON parse failed after cleaning. Response: {response}")
            return {}  # 返回空字典，而不是崩溃
```

#### 第 3 层：逐字段容错

```python
def update_additional_profile(self, user_id: str, decisions: Dict[str, Any]) -> Dict[str, Any]:
    """更新扩展画像，逐字段容错"""
    results = {}

    for field in ["interests", "skills", "personality"]:
        try:
            field_decisions = decisions.get(field, [])
            field_results = self._update_field(user_id, field, field_decisions)
            results[field] = field_results
        except Exception as e:
            logger.error(f"Failed to update {field} for user {user_id}: {e}")
            results[field] = {"error": str(e), "updated": []}

    return results
```

#### 第 4 层：数据库事务（PostgreSQL，可选）

```python
def update_basic_info_transactional(self, user_id: str, data: Dict[str, Any]):
    """使用事务更新基本信息"""
    conn = self.pool.getconn()
    try:
        conn.autocommit = False
        cursor = conn.cursor()

        # 执行多个 SQL 操作
        cursor.execute(...)
        cursor.execute(...)

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed, rolled back: {e}")
        raise
    finally:
        cursor.close()
        self.pool.putconn(conn)
```

---

### 7.2 错误码设计

| HTTP 状态码 | 场景 | 返回示例 |
|------------|------|---------|
| 200 OK | 成功 | `{"results": {...}}` |
| 400 Bad Request | 参数错误 | `{"detail": "user_id is required"}` |
| 404 Not Found | 用户不存在 | `{"detail": "User u123 not found"}` |
| 500 Internal Server Error | 服务器错误 | `{"detail": "LLM service unavailable"}` |
| 501 Not Implemented | 功能未实现 | `{"detail": "Vocabulary feature not implemented"}` |

---

## 8. 实施步骤

### Phase 1: 基础架构（2-3 天）

**目标**：搭建基本框架和数据库连接

#### 1.1 创建目录结构
```bash
mkdir -p mem0/user_profile/database
touch mem0/user_profile/__init__.py
touch mem0/user_profile/main.py
touch mem0/user_profile/profile_manager.py
touch mem0/user_profile/vocab_manager.py
touch mem0/user_profile/prompts.py
touch mem0/user_profile/models.py
touch mem0/user_profile/utils.py
touch mem0/user_profile/database/__init__.py
touch mem0/user_profile/database/postgres.py
touch mem0/user_profile/database/mongodb.py
```

#### 1.2 实现数据库管理器

**postgres.py** (核心方法)：
```python
import psycopg2
from psycopg2 import pool
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PostgresManager:
    def __init__(self, config: Dict[str, Any]):
        """初始化 PostgreSQL 连接池"""
        self.pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )

    def upsert_basic_info(self, user_id: str, data: Dict[str, Any]) -> None:
        """插入或更新基本信息"""
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # 构建 UPSERT SQL
            fields = list(data.keys())
            placeholders = ["%s"] * len(fields)

            sql = f"""
                INSERT INTO user_profile.user_profile (user_id, {', '.join(fields)})
                VALUES (%s, {', '.join(placeholders)})
                ON CONFLICT (user_id)
                DO UPDATE SET
                    {', '.join([f"{f} = EXCLUDED.{f}" for f in fields])},
                    updated_at = CURRENT_TIMESTAMP
            """

            values = [user_id] + [data[f] for f in fields]
            cursor.execute(sql, values)
            conn.commit()

            logger.info(f"Upserted basic_info for user {user_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert basic_info for user {user_id}: {e}")
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_basic_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取基本信息"""
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_profile.user_profile WHERE user_id = %s",
                (user_id,)
            )
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            cursor.close()
            self.pool.putconn(conn)
```

**mongodb.py** (核心方法)：
```python
from pymongo import MongoClient
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self, config: Dict[str, Any]):
        """初始化 MongoDB 连接"""
        self.client = MongoClient(
            config["uri"],
            maxPoolSize=10
        )
        self.db = self.client[config["database"]]
        self.collection = self.db["user_additional_profile"]

    def get_additional_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取扩展画像"""
        doc = self.collection.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)  # 移除 MongoDB 的 _id
        return doc

    def update_field(self, user_id: str, field: str, items: List[Dict[str, Any]]) -> None:
        """更新指定字段（interests / skills / personality）"""
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {
                field: items,
                "system_metadata.updated_at": datetime.now().isoformat()
            }},
            upsert=True
        )
        logger.info(f"Updated {field} for user {user_id}")

    def add_item_to_field(self, user_id: str, field: str, item: Dict[str, Any]) -> None:
        """向字段添加新项"""
        self.collection.update_one(
            {"user_id": user_id},
            {"$push": {field: item}},
            upsert=True
        )
```

#### 1.3 配置集成

**server/main.py**（修改）：
```python
# 新增环境变量
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://mongodb:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "mem0_profile")

# 扩展 DEFAULT_CONFIG
DEFAULT_CONFIG = {
    # ... 现有配置 ...

    "user_profile": {
        "postgres": {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "database": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "schema": "user_profile"
        },
        "mongodb": {
            "uri": MONGODB_URI,
            "database": MONGODB_DATABASE
        }
    }
}
```

**验收标准**：
- ✅ 目录结构创建完成
- ✅ PostgreSQL 连接成功，可以 UPSERT 和查询
- ✅ MongoDB 连接成功，可以读写
- ✅ 配置正确加载

---

### Phase 2: Profile 功能（3-4 天）

**目标**：实现 set_profile 和 get_profile 的完整功能

#### 2.1 实现 ProfileManager

**profile_manager.py**：
```python
class ProfileManager:
    def __init__(self, llm, postgres, mongodb):
        self.llm = llm
        self.postgres = postgres
        self.mongodb = mongodb

    def set_profile(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        manual_data: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """完整的 set_profile 流程"""
        options = options or {}
        results = {}

        # Step 1: 提取信息（阶段 1 LLM）
        extracted = self._extract_profile(messages)

        # Step 2: 更新 basic_info
        if options.get("update_basic", True):
            basic_info = self._merge_basic_info(
                extracted.get("basic_info", {}),
                manual_data
            )
            if basic_info:
                self.postgres.upsert_basic_info(user_id, basic_info)
                results["basic_info"] = basic_info

        # Step 3: 查询现有扩展画像
        current_additional = self.mongodb.get_additional_profile(user_id) or {}

        # Step 4: LLM 判断更新（阶段 2 LLM）
        decisions = self._decide_profile_updates(current_additional, extracted)

        # Step 5: 执行更新
        if options.get("update_interests", True):
            results["interests"] = self._update_interests(user_id, decisions.get("interests", []))
        # ... skills, personality 类似 ...

        return {"results": results}

    def _extract_profile(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """阶段 1：LLM 提取"""
        from mem0.user_profile.prompts import get_profile_extraction_prompt

        prompt = get_profile_extraction_prompt(messages)
        response = self.llm.generate_response(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return parse_llm_response(response)

    def _decide_profile_updates(
        self,
        current: Dict[str, Any],
        extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        """阶段 2：LLM 判断"""
        from mem0.user_profile.prompts import get_profile_update_decision_prompt

        prompt = get_profile_update_decision_prompt(current, extracted)
        response = self.llm.generate_response(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return parse_llm_response(response)
```

#### 2.2 实现 UserProfile 主类

**main.py**：
```python
from mem0.configs.base import MemoryConfig
from mem0.utils.factory import LlmFactory
from mem0.user_profile.database.postgres import PostgresManager
from mem0.user_profile.database.mongodb import MongoDBManager
from mem0.user_profile.profile_manager import ProfileManager

class UserProfile:
    def __init__(self, config: MemoryConfig):
        self.config = config

        # 复用 LLM
        self.llm = LlmFactory.create(
            config.llm.provider,
            config.llm.config
        )

        # 初始化数据库
        self.postgres = PostgresManager(config.user_profile["postgres"])
        self.mongodb = MongoDBManager(config.user_profile["mongodb"])

        # 初始化业务逻辑
        self.profile_manager = ProfileManager(
            llm=self.llm,
            postgres=self.postgres,
            mongodb=self.mongodb
        )

    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]):
        """从字典配置创建实例"""
        from mem0.configs.base import MemoryConfig
        config = MemoryConfig(**config_dict)
        return cls(config)

    def set_profile(self, user_id: str, messages: List[Dict[str, str]], **kwargs):
        """对外接口"""
        return self.profile_manager.set_profile(user_id, messages, **kwargs)

    def get_profile(self, user_id: str, type: str = "all", field: Optional[str] = None):
        """对外接口"""
        return self.profile_manager.get_profile(user_id, type, field)
```

#### 2.3 集成到 FastAPI

**server/main.py**（修改）：
```python
from mem0.user_profile import UserProfile

# 创建实例
USER_PROFILE_INSTANCE = UserProfile.from_config(DEFAULT_CONFIG)

# 新增路由
@app.post("/profile", summary="Update user profile")
def set_profile(
    user_id: str,
    messages: List[Message],
    manual_data: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, bool]] = None
):
    try:
        result = USER_PROFILE_INSTANCE.set_profile(
            user_id=user_id,
            messages=[m.model_dump() for m in messages],
            manual_data=manual_data,
            options=options
        )
        return JSONResponse(content=result)
    except Exception as e:
        logging.exception("Error in set_profile:")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile", summary="Get user profile")
def get_profile(
    user_id: str,
    type: str = "all",
    field: Optional[str] = None
):
    try:
        result = USER_PROFILE_INSTANCE.get_profile(
            user_id=user_id,
            type=type,
            field=field
        )
        return JSONResponse(content=result)
    except Exception as e:
        logging.exception("Error in get_profile:")
        raise HTTPException(status_code=500, detail=str(e))
```

**验收标准**：
- ✅ 可以调用 POST /profile 成功更新
- ✅ 可以调用 GET /profile 成功查询
- ✅ LLM 提取信息正确
- ✅ LLM 判断更新正确
- ✅ 数据正确存储到 PostgreSQL 和 MongoDB

---

### Phase 3: 测试和优化（1-2 天）

详见第 9 节测试用例。

---

### Phase 4: 文档和部署（1 天）

- 更新 CLAUDE.md
- 更新 TODO.md
- 创建数据库初始化脚本
- 更新 docker-compose.yaml
- 更新 .env.example

---

## 9. 测试用例

### 9.1 基础功能测试

```python
# test/test_user_profile.py

def test_set_profile_basic():
    """测试基本信息更新"""
    response = client.post("/profile", json={
        "user_id": "test_user_1",
        "messages": [
            {"role": "user", "content": "我叫Alice，今年7岁，住在北京"}
        ]
    })

    assert response.status_code == 200
    data = response.json()

    assert "basic_info" in data["results"]
    assert data["results"]["basic_info"]["values"]["name"] == "Alice"
    assert data["results"]["basic_info"]["values"]["current_city"] == "北京"

def test_set_profile_interests():
    """测试兴趣更新"""
    response = client.post("/profile", json={
        "user_id": "test_user_2",
        "messages": [
            {"role": "user", "content": "我喜欢踢足球，每周都和朋友踢"}
        ]
    })

    assert response.status_code == 200
    data = response.json()

    assert "interests" in data["results"]
    assert len(data["results"]["interests"]) > 0
    assert any(item["name"] == "足球" for item in data["results"]["interests"])

def test_get_profile():
    """测试获取画像"""
    # 先设置
    client.post("/profile", json={
        "user_id": "test_user_3",
        "messages": [{"role": "user", "content": "我喜欢编程"}]
    })

    # 再获取
    response = client.get("/profile?user_id=test_user_3&type=all")
    assert response.status_code == 200

    data = response.json()
    assert "basic_info" in data or "additional_profile" in data
```

### 9.2 边界情况测试

```python
def test_empty_messages():
    """测试空消息"""
    response = client.post("/profile", json={
        "user_id": "test_user_4",
        "messages": []
    })
    # 应该正常处理，返回空结果
    assert response.status_code == 200

def test_invalid_json_from_llm():
    """测试 LLM 返回无效 JSON（需要 mock）"""
    # 使用 mock 让 LLM 返回无效 JSON
    # 应该被第 2 层容错捕获，返回空结果而不是崩溃
    pass

def test_conflict_resolution():
    """测试矛盾处理"""
    # 先建立兴趣
    client.post("/profile", json={
        "user_id": "test_user_5",
        "messages": [{"role": "user", "content": "我喜欢足球"}] * 5
    })

    # 再说不喜欢
    response = client.post("/profile", json={
        "user_id": "test_user_5",
        "messages": [{"role": "user", "content": "我不喜欢足球了"}]
    })

    # 检查是降低 degree 还是删除
    # （具体行为取决于 LLM 判断）
```

---

## 10. 部署配置

### 10.1 数据库初始化脚本

**scripts/init_user_profile_postgres.sql**：
```sql
-- 创建 schema
CREATE SCHEMA IF NOT EXISTS user_profile;

-- 创建表
CREATE TABLE IF NOT EXISTS user_profile.user_profile (
    -- ... 见第 3.1 节 ...
);

-- 创建触发器
-- ... 见第 3.1 节 ...
```

**scripts/init_user_profile_mongodb.js**：
```javascript
// 连接到数据库
db = db.getSiblingDB('mem0_profile');

// 创建集合（如果不存在）
db.createCollection('user_additional_profile');

// 创建索引
db.user_additional_profile.createIndex({ "user_id": 1 }, { unique: true });
db.user_additional_profile.createIndex({ "interests.name": 1 });
db.user_additional_profile.createIndex({ "skills.name": 1 });
db.user_additional_profile.createIndex({ "personality.name": 1 });

print("MongoDB initialization completed");
```

### 10.2 docker-compose.yaml 更新

```yaml
version: '3.8'

services:
  postgres:
    # ... 现有配置 ...

  mongodb:  # 新增
    image: mongo:7.0
    container_name: mem0-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
      - ./scripts/init_user_profile_mongodb.js:/docker-entrypoint-initdb.d/init.js
    networks:
      - mem0_network

  mem0-service:
    # ... 现有配置 ...
    environment:
      # ... 现有环境变量 ...
      - MONGODB_URI=mongodb://mongodb:27017
      - MONGODB_DATABASE=mem0_profile
    depends_on:
      - postgres
      - mongodb  # 新增依赖

volumes:
  postgres_db:
  mongodb_data:  # 新增
  neo4j_data:

networks:
  mem0_network:
    driver: bridge
```

### 10.3 .env.example 更新

```bash
# ... 现有配置 ...

# MongoDB Configuration (for UserProfile)
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=mem0_profile
```

---

## 附录 A：完整代码示例

由于篇幅限制，完整代码见各模块的实现文件。

---

## 附录 B：常见问题 FAQ

**Q1: 为什么 basic_info 不需要两阶段 LLM？**
A: 因为 basic_info 的字段值是唯一的（如 current_city 只有一个值），提取到新值就直接覆盖，无需复杂的合并判断。

**Q2: 如果 LLM 返回的 JSON 格式错误怎么办？**
A: 有四层容错机制保护，见第 7 节。

**Q3: 兴趣和技能可以重叠吗？**
A: 可以。同一事物（如"足球"）可以同时出现在 interests 和 skills 中。

**Q4: degree 如何动态调整？**
A: 由阶段 2 的 LLM 综合 evidence 数量、质量和时间判断。

**Q5: 词汇功能什么时候开发？**
A: 下一阶段，详见 `archived/vocab_design.md`。

---

**文档结束** 🎉

**下一步**：开始 Phase 1 的开发工作！