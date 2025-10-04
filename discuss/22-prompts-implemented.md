# Prompts 修复实施完成

**日期**: 2025-10-04
**任务来源**: discuss/21-prompts.md

## 已完成的修改

### 1. 时间戳处理 ✅

**修改内容**:
- ✅ 移除了 LLM 生成时间戳的所有指示
- ✅ EXTRACT_PROFILE_PROMPT: 移除 `{current_time}` 参数和时间戳相关规则
- ✅ UPDATE_PROFILE_PROMPT: 明确说明 "DO NOT return timestamps in your output"
- ✅ 后端 profile_manager.py 添加 `_add_timestamps_to_evidence()` 方法
- ✅ 在 Stage 1 (extract) 和 Stage 3 (decide) 自动添加时间戳

**技术实现**:
```python
# profile_manager.py
def _add_timestamps_to_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Add timestamps to evidence entries (backend-generated)"""
    current_time = get_current_timestamp()
    # 递归处理所有evidence字段，添加timestamp
    ...
```

### 2. 语言一致性 ✅

**新增规则**:
> **Language consistency**: Keep the language of JSON values consistent with user input (no translation between Chinese/English)

- LLM 不再翻译中英文
- 保持用户输入的原始语言

### 3. Degree 描述统一为英文 ✅

**修改前**: 1=不太喜欢, 2=一般, 3=喜欢...
**修改后**:
- For interests: 1=dislike, 2=neutral, 3=like, 4=really like, 5=favorite
- For skills: 1=beginner, 2=learning, 3=proficient, 4=advanced, 5=expert
- For personality: 1=not obvious, 2=weak, 3=moderate, 4=strong, 5=very strong

### 4. social_context 结构调整 ✅

**修改**: teachers → friends

**新结构**:
```json
{
  "social_context": {
    "family": {
      "father": { "name": "...", "career": "...", "info": [...] },
      "mother": { "name": "...", "career": "...", "info": [...] }
    },
    "friends": [
      { "name": "Jack", "info": ["plays basketball", "likes movies"] }
    ],
    "others": [
      { "name": "Amy", "relation": "teacher", "info": ["teaches math", "very patient"] },
      { "name": "Tom", "relation": "sibling", "info": [...] }
    ]
  }
}
```

**规则说明**:
- `family`: 对象，只包含 father/mother（siblings 放到 others）
- `friends`: 数组，包含 name 和 info（不需要 relation 字段）
- `others`: 数组，包含 teachers、siblings、relatives、neighbors 等，需要 name、relation 和 info

### 5. 缺失字段处理明确化 ✅

**新增规则**:
> **Omit missing fields**: If no information found for a field, DO NOT include that field in the JSON (both key and value should be omitted)

- 不返回 null 或空对象
- 直接省略整个字段（key 和 value）

### 6. 新增 API 端点 ✅

#### GET /profile/missing-fields
```python
@app.get("/profile/missing-fields")
def get_missing_fields(user_id: str, source: str = "both"):
    """
    返回缺失的字段列表

    source: "pg" | "mongo" | "both"

    返回:
    {
      "user_id": "user123",
      "missing_fields": {
        "basic_info": ["hometown", "gender"],
        "additional_profile": ["personality"]
      }
    }
    """
```

#### GET /profile - evidence_limit 参数
```python
@app.get("/profile")
def get_profile(user_id: str, fields: str = None, evidence_limit: int = 5):
    """
    evidence_limit:
    - 0: 移除所有 evidence（返回空数组）
    - N (正数): 返回最新的 N 条 evidence
    - -1: 返回所有 evidence
    - 默认: 5
    """
```

### 7. 示例更新 ✅

- ✅ Example 1: 基本对话
- ✅ Example 2: 兴趣提取
- ✅ Example 3: 社交关系（family + friends）

## 文件修改清单

### 代码文件
- ✅ `mem0/user_profile/prompts.py` - 完全重写两个 prompt
- ✅ `mem0/user_profile/profile_manager.py` - 添加时间戳生成逻辑
- ✅ `server/main.py` - 已有新 API 端点（无需修改）
- ✅ `mem0/user_profile/database/mongodb_manager.py` - 已实现 evidence_limit
- ✅ `mem0/user_profile/database/postgres_manager.py` - 已实现 get_missing_fields
- ✅ `mem0/user_profile/main.py` - 已实现 get_missing_fields 和 evidence_limit

### 测试文件
- ✅ `test/test_user_profile_quick.py` - 无需修改（已正确测试 friends 结构）

### 文档文件（待更新）
- ⏳ `CLAUDE.md`
- ⏳ `DEV_GUIDE_UserProfile.md`
- ⏳ `discuss/20-new endpoint.md` - 标记已完成

## 技术要点

### 时间戳生成流程
1. LLM 返回: `{"text": "..."}`
2. 后端添加: `{"text": "...", "timestamp": "2025-10-04T22:10:00"}`
3. 递归处理所有嵌套结构（interests, skills, personality, social_context 等）

### Evidence 限制优化
- MongoDB 端实现排序和限制
- 按 timestamp 降序排列（最新的优先）
- 支持 0（移除）、N（限制）、-1（全部）三种模式

### Missing Fields 逻辑
- PostgreSQL: 检查 NULL 或空字符串
- MongoDB: 检查不存在或空数组/空对象
- 支持分别查询或合并查询

## 下一步

- [ ] 更新 CLAUDE.md
- [ ] 更新 DEV_GUIDE_UserProfile.md
- [ ] 运行完整测试验证所有修改
- [ ] Git commit 记录所有更改