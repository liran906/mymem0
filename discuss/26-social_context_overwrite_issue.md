# Social Context 覆盖问题及 Schema 设计讨论

**日期**：2025-10-05
**问题来源**：discuss/25-problem.md
**状态**：讨论中

---

## 问题描述

在测试 UserProfile 功能时发现以下问题：

### 问题1：social_context 数据丢失（🔥严重）

**复现步骤**：

1. 第一次输入：
   > "我已婚，妻子是设计师，我们有一个3岁的女儿。父母还在成都，都退休了，身体挺好的。我是独生子..."

   **存储结果**：
   ```json
   "social_context": {
     "family": {
       "father": { "info": ["退休了", "身体挺好的"] },
       "mother": { "info": ["退休了", "身体挺好的"] }
     },
     "others": [
       { "name": "妻子", "relation": "妻子", "info": ["设计师"] },
       { "name": "女儿", "relation": "女儿", "info": ["3岁"] }
     ]
   }
   ```

2. 第二次输入：
   > "我的老婆叫小芳，我和她七年前就结婚了。我女儿叫小静静，她今年三岁，十分可爱"

   **存储结果**：
   ```json
   "social_context": {
     "family": {
       "wife": { "name": "小芳", "info": ["七年前结婚"] },
       "daughter": { "name": "小静静", "info": ["三岁", "十分可爱"] }
     }
   }
   ```

**问题**：原有的 `father` 和 `mother` 数据**完全丢失**！

---

### 问题2：personality 冲突检测失效（⚠️中等）

**复现步骤**：

已有 personality：
```json
[
  { "name": "认真负责", "degree": 4, ... },
  { "name": "专注", "degree": 4, ... }
]
```

新输入：
> "我今天被领导批评了，说我粗枝大叶"

**存储结果**：
```json
{ "name": "粗枝大叶", "degree": 4, "evidence": [...] }
```

**问题**：
- "粗枝大叶" 与 "认真负责" 明显冲突，但 LLM 没有检测到
- 直接新增而不是触发冲突解决逻辑
- degree=4 也不合理（仅一次领导批评不应该是高 degree）

---

### 问题3-4：Schema 设计问题（💭设计层面）

**问题3**：family 字段应该固定还是动态？

当前问题：
- 第一次 LLM 生成了 `father/mother` + `others`
- 第二次 LLM 生成了 `wife/daughter`（直接在 family 下）

疑问：
- 是否应该预定义 family 的可选字段（如 father/mother/sibling/spouse/child）？
- 还是完全由 LLM 自由决定？

**问题4**：如何约束 MongoDB 字段？

MongoDB 无 schema，可能导致：
- LLM 返回错误的字段名（typo）→ 直接写入错误数据
- LLM 返回不一致的结构（如 father vs parent）→ 数据混乱
- 无法区分"必需字段"和"可选字段"

需求：
- 某些字段应该**严格约束**（如 interests/skills/personality 必须有 name/degree/evidence）
- 某些字段应该**灵活扩展**（如 social_context 允许新的关系类型）
- 如何在代码层面实现这种"部分约束"？

---

## Claude 的分析和建议

### 优先级划分

**🔥 P0（立即修复）**：问题1 - social_context 覆盖

- 这是**数据丢失 bug**，影响功能正确性
- 用户的家庭关系数据不应该因为新信息而丢失旧信息

**⏳ P1（下一步优化）**：问题2 - personality 冲突检测

- 这是**智能优化**问题，需要更复杂的 prompt 工程
- 可能需要引入"反义词检测"或"语义冲突分析"

**💭 P2（架构设计讨论）**：问题3-4 - Schema 约束

- 这是**架构设计**问题，需要更多讨论和权衡
- 涉及灵活性 vs 一致性的 trade-off

---

## 问题1 解决方案（待确认）

### 根本原因

当前 `extraction_rules.yaml` 和 decision prompt 中，social_context 的更新逻辑是：
- LLM 提取到新的 social_context → **整体替换**现有数据
- 没有"合并"逻辑

### 解决方案 A：修改 Prompt 强调合并逻辑

**修改位置**：`mem0/user_profile/extraction_rules.yaml`

```yaml
social_context:
  description: "用户的社交关系网络"
  structure:
    family: "家庭成员（如 father, mother, sibling, spouse, child 等）"
    friends: "朋友关系"
    colleagues: "同事关系"

  update_rules:
    - "❗CRITICAL: 对 social_context 执行**合并更新**，不是覆盖"
    - "保留所有现有关系，只添加或更新被明确提及的关系"
    - "示例：如果现有 father/mother，新信息提到 wife，应该保留 father/mother 并添加 wife"
    - "对于 family 字段，执行**深度合并**：合并所有关系人，不删除未提及的关系"
    - "只有在明确说明某关系不再存在时才执行 DELETE 操作"
```

**修改位置**：`mem0/user_profile/prompts.py` 中的 decision prompt

在 decision prompt 中增加示例：

```python
# 在 DECISION_PROMPT 中增加 social_context 更新示例
example = """
示例：social_context 合并更新

现有数据：
{
  "family": {
    "father": {"info": ["退休"]},
    "mother": {"info": ["退休"]}
  }
}

新信息："我老婆叫小芳"

正确决策：
{
  "field": "social_context.family.wife",
  "action": "ADD",
  "value": {"name": "小芳"},
  "reason": "新增妻子信息，保留现有的 father/mother"
}

❌ 错误决策（会导致数据丢失）：
{
  "field": "social_context.family",
  "action": "UPDATE",
  "value": {"wife": {"name": "小芳"}},  # 这会覆盖 father/mother！
}
"""
```

### 解决方案 B：修改代码层合并逻辑

**修改位置**：`mem0/user_profile/user_profile_manager.py`

在 `_apply_decisions()` 方法中，针对 `social_context` 字段做特殊处理：

```python
def _apply_decisions(self, existing_profile, decisions):
    """应用 LLM 决策到现有档案"""

    for decision in decisions:
        field = decision["field"]
        action = decision["action"]
        value = decision["value"]

        # 特殊处理：social_context 必须合并，不能覆盖
        if field.startswith("social_context"):
            if action == "UPDATE":
                # 强制使用深度合并而不是覆盖
                self._deep_merge_social_context(existing_profile, field, value)
                continue

        # 其他字段按原逻辑处理
        if action == "ADD":
            ...
        elif action == "UPDATE":
            ...
        elif action == "DELETE":
            ...

def _deep_merge_social_context(self, profile, field, new_value):
    """深度合并 social_context，保留现有关系"""
    # 实现深度合并逻辑
    # 例如：合并 family 时，保留现有的 father/mother，添加新的 wife
    ...
```

### 我的建议

**采用方案 A + B 组合**：

1. **方案 A（Prompt 层面）**：让 LLM 更明确地理解"合并"而非"覆盖"
2. **方案 B（代码层面）**：增加保护机制，即使 LLM 理解错误，代码也能正确合并

理由：
- Prompt 层面的修改是主要解决方式（让 LLM 做对）
- 代码层面的保护是兜底机制（防止 LLM 出错导致数据丢失）

---

## 问题2-4 初步思路（暂不实施）

### 问题2：personality 冲突检测

**可能方案**：

1. 在 decision prompt 中增加"语义冲突检测"指令
2. 维护一个常见反义词对列表（细心↔粗心，内向↔外向）
3. 或者让 LLM 自己判断语义冲突

**建议**：下一步再讨论，当前先修复数据丢失问题。

### 问题3-4：Schema 约束

**可能方案**：

**阶段1（Python 代码层验证）**：
```python
# 定义 user_profile_schema.py
STRICT_FIELDS = {
    "interests": ["name", "degree", "evidence"],
    "skills": ["name", "degree", "evidence"],
    "personality": ["name", "degree", "evidence"],
}

FLEXIBLE_FIELDS = ["social_context"]  # 允许任意子字段

FAMILY_SUGGESTED_RELATIONS = [
    "father", "mother", "sibling", "spouse", "child", "grandparent"
]
```

**阶段2（MongoDB Schema Validation）**：
使用 MongoDB 3.2+ 的 JSON Schema 验证功能。

**建议**：需要更多讨论，涉及架构设计权衡。

---

## 待用户确认

1. ✅ 是否同意优先级划分（P0 > P1 > P2）？
2. ✅ 是否采用方案 A + B 组合修复问题1？
3. ✅ 问题2-4 是否暂缓到下一步讨论？

---

## 后续 TODO

**如果方案获得确认**：

- [ ] 修改 `extraction_rules.yaml` 中 social_context 的更新规则
- [ ] 修改 `prompts.py` 中 decision prompt，增加合并示例
- [ ] 在 `user_profile_manager.py` 中实现 `_deep_merge_social_context()` 方法
- [ ] 编写测试用例验证修复效果
- [ ] 更新 `DEV_GUIDE_UserProfile.md` 文档
- [ ] git commit 提交修复

---

**Claude 注**：等待用户确认方案后再开始实施。