# 实施方案确认文档

基于对 mem0 核心实现的研究和你在 05 中的反馈，我整理了完整的实施方案。

---

## 1. mem0 的核心 Pipeline 分析

### 1.1 mem0.add() 的完整流程

我研究了 `mem0/memory/main.py` (203-473行) 和 `mem0/configs/prompts.py`，总结如下：

**两阶段 LLM 调用**：

#### 阶段 1：事实提取（Fact Extraction）
```python
# 位置：main.py 347-360
# 使用 FACT_RETRIEVAL_PROMPT
response = llm.generate_response(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": parsed_messages}
    ],
    response_format={"type": "json_object"}
)

# 输出格式：
{
    "facts": ["Name is John", "Loves pizza", ...]
}
```

#### 阶段 2：内存更新决策（Memory Update Decision）
```python
# 位置：main.py 392-414
# 使用 DEFAULT_UPDATE_MEMORY_PROMPT
# 输入：retrieved_old_memory（现有记忆）+ new_retrieved_facts（新事实）
response = llm.generate_response(
    messages=[{"role": "user", "content": function_calling_prompt}],
    response_format={"type": "json_object"}
)

# 输出格式：
{
    "memory": [
        {
            "id": "0",
            "text": "User is a software engineer",
            "event": "NONE"
        },
        {
            "id": "1",
            "text": "Name is John",
            "event": "ADD"
        },
        {
            "id": "2",
            "text": "Loves cheese and chicken pizza",
            "event": "UPDATE",
            "old_memory": "Loves cheese pizza"
        }
    ]
}
```

#### 阶段 3：执行操作
```python
# 位置：main.py 419-473
# 根据 event 类型执行：
- ADD: 创建新记忆（_create_memory）
- UPDATE: 更新现有记忆（_update_memory）
- DELETE: 删除记忆（_delete_memory）
- NONE: 不操作
```

### 1.2 关键设计点

1. **UUID 映射防幻觉**（385-389行）：
   ```python
   # 将真实的 UUID 映射为简单的整数 ID，防止 LLM 生成错误的 UUID
   temp_uuid_mapping = {}
   for idx, item in enumerate(retrieved_old_memory):
       temp_uuid_mapping[str(idx)] = item["id"]
       retrieved_old_memory[idx]["id"] = str(idx)
   ```

2. **错误处理**（401-414行）：
   ```python
   try:
       response = llm.generate_response(...)
   except Exception as e:
       logger.error(f"Error in new memory actions response: {e}")
       response = ""

   # 如果 response 为空或无效 JSON，返回空字典而不是崩溃
   if not response or not response.strip():
       new_memories_with_actions = {}
   ```

3. **向量搜索限制**（370-377行）：
   ```python
   # 每个新事实只搜索前 5 条最相关的旧记忆
   existing_memories = vector_store.search(
       query=new_mem,
       vectors=messages_embeddings,
       limit=5,
       filters=filters
   )
   ```

---

## 2. 针对你的问题的回答

### 2.1 关于基本信息采集策略（你的第2点）

你说的对，**第2层和第3层本质上是一个过程**，都是 LLM 提取和判断。

**简化后的策略**：

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 前端手动输入（manual_data）                        │
│  - 如果前端有值 → 直接使用，不可被 LLM 覆盖                  │
│  - 如果前端无值 → 进入 Layer 2                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: LLM 提取和更新决策（参考 mem0 的两阶段 pipeline）  │
│  1. 提取事实（新的基本信息 + 扩展信息）                      │
│  2. 查询现有信息                                             │
│  3. 判断操作（ADD / UPDATE / DELETE / NONE）                │
│  4. 执行操作                                                 │
└─────────────────────────────────────────────────────────────┘
```

**关于置信度**：你的疑问很对，LLM 的置信度确实不可靠。

**建议**：MVP 阶段**不使用置信度**，直接信任 LLM 的判断。如果未来需要人工审核，可以：
- 方案 A：记录所有变更到历史表，允许用户回滚
- 方案 B：重要字段（如生日、性别）的变更需要前端确认

---

### 2.2 关于 LLM 输出结构和幻觉问题（你的第3点）

**你的担心非常合理！** mem0 也遇到同样的问题。

#### mem0 的解决方案：

1. **两阶段调用**：降低单次输出的复杂度
   - 第一次只提取事实（简单 JSON）
   - 第二次才做决策（相对复杂的 JSON）

2. **UUID 映射**：防止 UUID 幻觉

3. **逐条容错**：
   ```python
   # main.py 419-465
   for resp in new_memories_with_actions.get("memory", []):
       try:
           # 处理单条记录
       except Exception as e:
           logger.error(f"Error processing memory action: {resp}, Error: {e}")
           # 跳过这条，继续处理下一条
   ```

4. **字段验证**：
   ```python
   action_text = resp.get("text")
   if not action_text:
       logger.info("Skipping memory entry because of empty `text` field.")
       continue
   ```

#### 针对 UserProfile 的建议：

**采用 mem0 的设计，但针对我们的场景优化**：

```json
// 第一阶段：提取事实（简化）
{
    "basic_info": {
        "hometown": "Nanjing",
        "timezone": "Asia/Shanghai"
    },
    "interests": ["football", "lego"],
    "skills": ["python"],
    "personality": ["curious"],
    "social_context": {
        "father.name": "John",
        "father.career": "doctor"
    }
}

// 第二阶段：更新决策（参考 mem0）
{
    "basic_info": [
        {
            "field": "hometown",
            "value": "Nanjing",
            "event": "ADD"  // 或 UPDATE
        }
    ],
    "additional_profile": {
        "interests": [
            {
                "id": "0",
                "text": "football",
                "event": "NONE"
            },
            {
                "id": "1",
                "text": "lego",
                "event": "ADD"
            }
        ],
        "skills": [...]
    }
}
```

**容错策略**：
1. 每个顶级字段（basic_info, interests, skills 等）独立处理
2. 如果某个字段的 JSON 解析失败，跳过该字段，继续处理其他字段
3. 记录错误日志但不中断整个流程

---

### 2.3 关于 dislike 字段（你的第4点）

**不建议增加 dislike**，理由：

1. **逻辑复杂**：需要维护 interests 和 dislikes 两个列表，容易冲突
2. **语义模糊**："不喜欢了"可以直接从 interests 删除，无需额外存储
3. **查询困惑**：搜索时是否要同时考虑 dislikes？

**推荐的保守策略**：
- "我喜欢足球" → ADD to interests
- "我不喜欢足球了" → DELETE from interests
- "我讨厌足球" → DELETE from interests（如果存在）
- 不主动维护 dislikes 列表

如果未来确实需要，可以在 MongoDB 的 additional_profile 中新增字段，不影响现有逻辑。

---

### 2.4 关于词汇的历史数据查询（你的第5点）

**你说的对**，词汇的 level 判断需要历史数据。

**流程设计**：

```python
def set_vocab(user_id: str, messages: List[dict]):
    # 1. LLM 提取本次涉及的词汇
    extracted = llm_extract_vocab(messages)
    # 输出：[{"word": "apple", "usage_quality": "correct"}, ...]

    # 2. 查询这些词汇的历史记录
    words = [item["word"] for item in extracted]
    history = get_vocab(user_id, words=words)
    # 返回：{"apple": {"level": "learned", "count": 3, ...}, ...}

    # 3. LLM 判断新的 level（带历史上下文）
    new_levels = llm_decide_vocab_level(extracted, history)
    # 输出：[{"word": "apple", "new_level": "practicing"}, ...]

    # 4. 程序逻辑更新数据库
    for item in new_levels:
        upsert_vocab(
            user_id=user_id,
            word=item["word"],
            level=item["new_level"],
            count=history.get(item["word"], {}).get("count", 0) + 1,
            last_seen=datetime.now()
        )
```

**Prompt 示例**：
```
当前词汇历史：
- apple: level=learned, count=3
- banana: 无历史记录（新词汇）

本次对话中的使用情况：
- apple: 用户正确使用了2次
- banana: 用户第一次使用，有拼写错误

请判断新的 level：
- learned: 第一次正确使用
- practicing: 多次使用，仍有错误或需要帮助
- mastered: 连续正确使用，无需提示

返回 JSON 格式：
{
    "vocab": [
        {"word": "apple", "new_level": "practicing"},
        {"word": "banana", "new_level": "learned"}
    ]
}
```

---

## 3. 表结构优化建议（你的第7点）

基于你说的"尽量全面，减少后续新增"，我建议：

### 3.1 user_profile（PostgreSQL）

```sql
CREATE TABLE user_profile (
    user_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 基本信息
    name VARCHAR(100),
    nickname VARCHAR(100),
    english_name VARCHAR(100),
    birthday DATE,
    gender VARCHAR(10),  -- 改为 VARCHAR 而不是 ENUM，更灵活

    -- 地理和文化
    nationality VARCHAR(50),
    hometown VARCHAR(100),
    current_city VARCHAR(100),  -- 新增：当前居住城市（可能与 hometown 不同）
    timezone VARCHAR(50),
    language VARCHAR(50),  -- 新增：主要使用语言

    -- 扩展字段（预留）
    avatar_url TEXT,  -- 新增：头像 URL
    bio TEXT,  -- 新增：简短自我介绍

    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```

**变更说明**：
1. `gender` 改为 VARCHAR：支持 "M", "F", "Other", "Prefer not to say" 等
2. 移除 `age`，只保留 `birthday`（你已确认）
3. 新增 `current_city`：处理"搬家"场景
4. 新增 `language`：多语言用户场景
5. 新增 `avatar_url` 和 `bio`：常见的用户信息

### 3.2 user_vocabulary（PostgreSQL）

```sql
CREATE TABLE user_vocabulary (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    word VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,  -- learned, practicing, mastered
    count INT DEFAULT 1,  -- 练习次数（默认值改为1）
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 新增：首次学习时间

    -- 扩展字段
    context TEXT,  -- 新增：最近一次使用的上下文（可选）
    notes TEXT,  -- 新增：备注（可选）

    -- 唯一约束和索引
    UNIQUE(user_id, word),
    INDEX idx_user_id (user_id),
    INDEX idx_word (word),
    INDEX idx_level (level),
    INDEX idx_last_seen (last_seen)
);
```

**变更说明**：
1. `level` 改为 VARCHAR：未来可能增加状态，不用修改表结构
2. `count` 默认值改为 1：第一次出现就是 count=1
3. 新增 `first_seen`：统计学习周期（例如"7天掌握10个词"）
4. 新增 `context`：记录最近一次使用场景，帮助复习
5. 新增 `notes`：用户手动添加的笔记

### 3.3 user_additional_profile（MongoDB）

```javascript
{
    "user_id": "u123",

    // 兴趣爱好（数组）
    "interests": [
        {
            "id": "0",
            "name": "football",
            "added_at": "2025-10-01"
        }
    ],

    // 技能（数组）
    "skills": [
        {
            "id": "0",
            "name": "python",
            "level": "beginner",  // 可选
            "added_at": "2025-10-01"
        }
    ],

    // 性格特征（数组）
    "personality": ["curious", "extroverted"],

    // 社交关系（嵌套对象）
    "social_context": {
        "family": {
            "father": {
                "name": "John",
                "career": "doctor",
                "info": ["kind and loving"]
            },
            "mother": {...},
            "siblings": [...]
        },
        "friends": [
            {"name": "Tom", "relation": "classmate"},
            {"name": "Jerry", "relation": "neighbor"}
        ]
    },

    // 学习偏好（新增）
    "learning_preferences": {
        "preferred_time": "evening",
        "preferred_style": "visual",
        "difficulty_level": "intermediate"
    },

    // 系统元数据
    "system_metadata": {
        "created_at": "2025-10-01",
        "updated_at": "2025-10-03",
        "version": 1  // 预留版本号
    }
}
```

**变更说明**：
1. `interests` 和 `skills` 改为对象数组（而不是字符串数组），包含 id 和时间戳
2. `social_context` 结构优化：family 和 friends 分开
3. 新增 `learning_preferences`：个性化学习场景
4. 新增 `version`：方便未来数据迁移

**索引**：
```javascript
db.user_additional_profile.createIndex({ "user_id": 1 }, { unique: true })
db.user_additional_profile.createIndex({ "interests.name": 1 })
db.user_additional_profile.createIndex({ "skills.name": 1 })
db.user_additional_profile.createIndex({ "social_context.family.father.name": 1 })
```

---

## 4. API 接口设计（你的第8点）

参考 mem0 的接口风格：

### 4.1 Profile 接口

```python
# server/main.py 新增路由

# 1. 更新 profile（类似 /memories）
POST /profile
{
    "user_id": "u123",
    "messages": [...],
    "manual_data": {  // 可选
        "name": "Alice",
        "birthday": "2018-07-15"
    }
}
Response: {"results": [...]}  // 类似 mem0 的返回格式

# 2. 获取 profile（类似 /memories?user_id=xxx）
GET /profile?user_id=u123&type=basic
GET /profile?user_id=u123&type=additional&field=interests

# 3. 搜索 profile（新增，可选）
POST /profile/search
{
    "user_id": "u123",
    "query": "兴趣爱好",
    "fields": ["interests", "skills"]
}
```

### 4.2 Vocab 接口

```python
# 1. 更新词汇
POST /vocab
{
    "user_id": "u123",
    "messages": [...]
}
Response: {"results": [...]}

# 2. 获取词汇
GET /vocab?user_id=u123&limit=10&offset=0
GET /vocab?user_id=u123&word=apple
GET /vocab?user_id=u123&level=mastered&limit=50

# 3. 词汇统计（新增）
GET /vocab/stats?user_id=u123
Response: {
    "total": 150,
    "learned": 50,
    "practicing": 70,
    "mastered": 30
}
```

---

## 5. 测试策略（你的第9点）

你说的对，**测试不会影响开发设计**。

**建议**：
- **现在**：我提供一个测试模板和几个基础测试用例（10-20个），保证核心功能可测
- **实现后**：你人工测试，发现问题我再补充边界用例

这样既不阻塞开发，又保证基本质量。

---

## 6. TODO 文件（你的第11点）

我会创建，见后续文件。

---

## 7. 最终确认清单

| 项目 | 方案 | 状态 |
|------|------|------|
| **架构** | 集成在 mem0 中，独立 UserProfile 类 | ✅ 确认 |
| **数据库** | PostgreSQL + MongoDB | ✅ 确认 |
| **基本信息策略** | 前端优先 + LLM 提取（两层） | ✅ 确认 |
| **LLM 调用** | 参考 mem0 的两阶段 pipeline | ✅ 确认 |
| **容错策略** | 逐字段容错，记录日志不崩溃 | ✅ 确认 |
| **兴趣变化** | 保守策略，不增加 dislike | ✅ 确认 |
| **词汇判断** | 带历史上下文的 LLM 判断 | ✅ 确认 |
| **表结构** | 如第 3 节优化后的设计 | ❓ 待你确认 |
| **API 设计** | 如第 4 节 | ❓ 待你确认 |
| **测试** | 现在提供模板，实现后人工测 | ✅ 确认 |

---

## 8. 实施步骤（供参考）

### Phase 1: 基础架构（1-2天）
1. 创建 `mem0/user_profile/` 目录
2. 实现 `UserProfile` 类骨架
3. 配置 PostgreSQL 和 MongoDB 连接
4. 创建数据库表和集合

### Phase 2: Profile 功能（2-3天）
1. 实现 `set_profile()`（参考 mem0.add()）
2. 实现 `get_profile()`
3. 编写 Profile 的 Prompt
4. FastAPI 接口集成

### Phase 3: Vocab 功能（1-2天）
1. 实现 `set_vocab()`
2. 实现 `get_vocab()`
3. 编写 Vocab 的 Prompt
4. FastAPI 接口集成

### Phase 4: 测试和优化（1-2天）
1. 基础功能测试
2. 错误处理完善
3. 日志和监控
4. 文档更新

**总计：5-9 天**

---

## 9. 你需要确认的问题

1. **表结构**（第 3 节）：是否同意新增的字段？有没有遗漏的场景？
2. **API 接口**（第 4 节）：是否符合预期？
3. **实施步骤**：是否认可这个顺序？有没有优先级调整？

确认后我们就可以开始实施了！