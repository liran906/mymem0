# 词汇管理功能设计（归档）

> 本功能暂不实现，归档设计方案供下一阶段开发参考。

**归档日期**: 2025-10-04
**预计开发**: Phase 2

---

## 1. 功能概述

追踪用户的英语词汇掌握情况，包括：
- 词汇列表管理
- 掌握程度评估（learned / practicing / mastered）
- 练习次数统计
- 学习进度追踪

---

## 2. 数据模型（PostgreSQL）

```sql
CREATE TABLE user_profile.user_vocabulary (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    word VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,  -- learned, practicing, mastered
    count INT DEFAULT 1,  -- 练习次数
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context TEXT,  -- 最近一次使用的上下文

    UNIQUE(user_id, word),
    INDEX idx_user_id (user_id),
    INDEX idx_word (word),
    INDEX idx_level (level),
    INDEX idx_last_seen (last_seen)
);
```

---

## 3. Pipeline 设计

### 方案 A：两阶段（参考 Profile）

**阶段 1**：LLM 提取词汇 + 使用情况
**阶段 2**：LLM 判断 level
**阶段 3**：程序执行数据库操作

### 方案 B：一阶段 + 程序逻辑（推荐）

**阶段 1**：LLM 提取词汇 + 判断使用质量
```json
{
    "vocab": [
        {
            "word": "apple",
            "usage_quality": "correct",
            "usage_count": 2,
            "context": "I ate an apple"
        }
    ]
}
```

**程序逻辑**：根据规则升级 level
```python
def calculate_new_level(current_level, current_count, usage_quality):
    if current_level == "learned":
        if current_count >= 2 and usage_quality == "correct":
            return "practicing"
    elif current_level == "practicing":
        if current_count >= 4 and usage_quality == "correct":
            return "mastered"
    return current_level
```

---

## 4. API 设计（预留）

```python
# POST /vocab - 更新词汇
{
    "user_id": "u123",
    "messages": [...]
}

# GET /vocab - 获取词汇
/vocab?user_id=u123&limit=10&offset=0
/vocab?user_id=u123&word=apple
/vocab?user_id=u123&level=mastered
```

**当前实现**：返回 501 Not Implemented

---

## 5. 未来增强

### 5.1 智能 count 加权

**想法**：用户使用得很好，一次可以 count +10
- LLM 判断使用质量（excellent / good / fair / poor）
- excellent → count +10
- good → count +5
- fair → count +2
- poor → count +1

### 5.2 遗忘曲线

根据艾宾浩斯遗忘曲线，提醒用户复习：
- 1天后、3天后、7天后、30天后

### 5.3 词汇统计

- 总词汇量
- 各 level 的词汇量
- 学习进度（本周新增 X 个词）

---

## 6. 实施建议

1. **先实现 Profile 功能**，验证架构设计
2. **复用 Profile 的经验**（Pipeline、Prompt、容错）
3. **与产品讨论**：
   - count 的语义（出现次数 vs 练习次数）
   - level 升级规则
   - 是否需要降级（遗忘）

---

## 7. 参考讨论

- `discuss/10-vocab_and_personality.md` - 词汇评估方案讨论
- `discuss/11-respond.md` - 决定归档的理由

---

**备注**：本功能的接口已在 `server/main.py` 中预留（返回 501），数据库表结构已设计完成。