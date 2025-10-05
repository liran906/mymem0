# Family Schema 设计方案讨论

**日期**：2025-10-05
**关联讨论**：discuss/26-social_context_overwrite_issue.md, discuss/27-respond.md
**状态**：讨论中

---

## 用户确认的问题一解决方案

✅ **确认采用代码层面合并方案**：

- LLM 只负责**提取增量信息**
- 如果涉及已有数据的更新：返回 `UPDATE` action + `id` + 新内容
- 如果是新增数据：返回 `ADD` action + 新内容
- **后端代码根据 action 执行合并逻辑**

这个方案我同意，符合职责分离原则：
- LLM：智能提取和决策
- 代码：可靠的数据合并和一致性保证

---

## 新问题：family 字段设计

### 问题描述

1. **关系类型的归属问题**：
   - 妻子/丈夫、儿女、兄弟姐妹应该放在 `family` 还是 `others`？
   - 祖父母、外祖父母应该如何处理？

2. **用户人设差异**：
   - 当前项目人设：用户是小孩，只有 father/mother（可能有 sibling/grandparent）
   - 通用场景：用户可能是成人，有 spouse/child

3. **Schema 灵活性 vs 一致性**：
   - 如何平衡"预定义字段"和"动态扩展"？

### 用户提出的两个方案

#### 方案1：预定义所有可能的家庭关系

```yaml
family:
  father: {}          # 必有（除非已故）
  mother: {}          # 必有（除非已故）
  brother: []         # 可选，可能没有
  sister: []          # 可选，可能没有
  grandmother: {}     # 可选
  grandfather: {}     # 可选
  wife: {}            # 可选（如果是成人）
  husband: {}         # 可选（如果是成人）
  daughter: []        # 可选（如果是成人）
  son: []             # 可选（如果是成人）
```

**优点**：
- ✅ 结构清晰，字段名一致
- ✅ 便于查询和展示（知道所有可能的字段）
- ✅ 防止 LLM typo（只能填预定义字段）

**缺点**：
- ❌ 字段冗余（大部分用户很多字段都是空的）
- ❌ 不够灵活（如果有特殊关系，如养父/继母/监护人，需要修改 schema）
- ❌ 维护成本高（新增关系类型需要改代码）

---

#### 方案2：固定核心字段 + 动态扩展

```yaml
family:
  father: {}          # 固定字段
  mother: {}          # 固定字段
  # 其他关系动态添加，如：
  # brother: []
  # wife: {}
  # ...
```

LLM prompt 中说明：
> "family 必须包含 father 和 mother（如无则为 null），其他直系亲属（如 sibling/spouse/child/grandparent）可以动态添加到 family"

**优点**：
- ✅ 灵活性高（可以处理各种家庭结构）
- ✅ 无冗余字段（按需添加）
- ✅ 可扩展性好（不需要修改代码即可支持新关系）

**缺点**：
- ❌ 字段名可能不一致（LLM 可能用 brother 也可能用 sibling）
- ❌ 可能有 typo（如 daugther 而不是 daughter）
- ❌ 查询时不确定性（不知道有哪些字段）

---

## Claude 的建议：混合方案

我建议采用 **方案1的思想 + 方案2的实现** = **建议字段 + 灵活扩展**

### 具体设计

#### 1. 在 `extraction_rules.yaml` 中定义"建议字段"

```yaml
social_context:
  description: "用户的社交关系网络"

  structure:
    family:
      description: "家庭成员"
      suggested_relations:
        # 核心字段（一般都会有）
        - father: "父亲"
        - mother: "母亲"

        # 常见字段（可能有）
        - brother: "兄弟（数组，可多个）"
        - sister: "姐妹（数组，可多个）"
        - grandfather_paternal: "爷爷"
        - grandmother_paternal: "奶奶"
        - grandfather_maternal: "外公"
        - grandmother_maternal: "外婆"

        # 成人场景字段
        - spouse: "配偶（丈夫/妻子）"
        - son: "儿子（数组，可多个）"
        - daughter: "女儿（数组，可多个）"

      rules:
        - "优先使用 suggested_relations 中定义的字段名"
        - "如果用户提到配偶，使用 spouse 而不是 wife/husband"
        - "如果用户提到兄弟姐妹但性别不明，使用 sibling"
        - "允许添加 suggested_relations 之外的关系（如 stepfather/guardian）"

    friends:
      description: "朋友关系（好友列表，数组）"

    colleagues:
      description: "同事关系（同事列表，数组）"
```

#### 2. 在代码层增加"建议字段"验证

```python
# mem0/user_profile/user_profile_schema.py

FAMILY_SUGGESTED_RELATIONS = {
    # 核心关系（高优先级）
    "core": ["father", "mother"],

    # 常见关系（建议使用）
    "common": [
        "brother", "sister", "sibling",
        "grandfather_paternal", "grandmother_paternal",
        "grandfather_maternal", "grandmother_maternal",
        "spouse", "son", "daughter"
    ],

    # 允许的扩展关系（不在列表中也可以，但会警告）
    "allowed_extensions": True
}

def validate_family_relation(relation_key: str) -> dict:
    """
    验证 family 关系字段名

    返回：
    {
        "valid": True/False,
        "suggestion": "建议使用的字段名",
        "warning": "警告信息"
    }
    """
    if relation_key in FAMILY_SUGGESTED_RELATIONS["core"]:
        return {"valid": True, "suggestion": None, "warning": None}

    if relation_key in FAMILY_SUGGESTED_RELATIONS["common"]:
        return {"valid": True, "suggestion": None, "warning": None}

    # 常见 typo 检测
    suggestions = {
        "daugther": "daughter",
        "gramdfather": "grandfather",
        "sisiter": "sister",
        # ... 更多常见 typo
    }

    if relation_key in suggestions:
        return {
            "valid": False,
            "suggestion": suggestions[relation_key],
            "warning": f"Possible typo: '{relation_key}' → '{suggestions[relation_key]}'"
        }

    # 不在建议列表中，但允许扩展
    if FAMILY_SUGGESTED_RELATIONS["allowed_extensions"]:
        return {
            "valid": True,
            "suggestion": None,
            "warning": f"Non-standard family relation: '{relation_key}'"
        }

    return {
        "valid": False,
        "suggestion": None,
        "warning": f"Invalid family relation: '{relation_key}'"
    }
```

#### 3. 在 `user_profile_manager.py` 中调用验证

```python
def _apply_decisions(self, existing_profile, decisions):
    """应用 LLM 决策到现有档案"""

    for decision in decisions:
        field = decision["field"]

        # 验证 family 关系字段
        if field.startswith("social_context.family."):
            relation = field.split(".")[-1]
            validation = validate_family_relation(relation)

            if not validation["valid"]:
                logger.warning(f"Family relation validation failed: {validation['warning']}")
                if validation["suggestion"]:
                    logger.warning(f"Using suggested field: {validation['suggestion']}")
                    # 自动修正为建议字段
                    field = field.replace(relation, validation["suggestion"])
            elif validation["warning"]:
                logger.info(f"Family relation: {validation['warning']}")

        # 继续处理决策
        ...
```

---

### 方案优势

这个混合方案的优势：

1. ✅ **一致性**：通过"建议字段"保证常见关系的字段名一致
2. ✅ **灵活性**：允许扩展字段，不限制特殊家庭结构
3. ✅ **容错性**：自动检测和修正常见 typo
4. ✅ **可维护性**：新增建议字段只需修改配置，不影响核心逻辑
5. ✅ **无冗余**：不会有大量空字段

---

## 新问题：name 字段填充错误

### 问题描述

当前测试结果：
```json
{
  "name": "妻子",       // ❌ 错误：应该为 null
  "relation": "妻子",   // ✅ 正确
  "info": ["设计师"]
}
```

**应该是**：
```json
{
  "name": null,         // ✅ 名字未提供
  "relation": "妻子",   // ✅ 关系类型
  "info": ["设计师"]
}
```

### 解决方案

修改 `extraction_rules.yaml` 和 extraction prompt，明确说明：

```yaml
social_context:
  structure:
    family:
      relation_schema:
        name: "具体名字（如果未提及则为 null，❗不要用关系词填充）"
        relation: "关系类型（如 father/mother/spouse）"
        info: "相关信息列表"

      rules:
        - "❗CRITICAL: name 字段只填具体名字（如'小芳'），如果对话中没有提到名字，则为 null"
        - "❌ 错误示例：name='妻子'（这是关系，不是名字）"
        - "✅ 正确示例：name='小芳' 或 name=null"
```

在 extraction prompt 中增加明确示例：

```python
example = """
示例1：有名字
输入："我妻子叫小芳"
输出：
{
  "name": "小芳",
  "relation": "spouse",
  "info": []
}

示例2：无名字
输入："我妻子是设计师"
输出：
{
  "name": null,           # ❗不是 "妻子"
  "relation": "spouse",
  "info": ["设计师"]
}
"""
```

---

## 待用户确认

1. ✅ 是否采用"建议字段 + 灵活扩展"的混合方案？
2. ✅ 建议字段列表是否需要调整？（如 spouse vs wife/husband）
3. ✅ 是否需要实现 typo 自动修正？
4. ✅ name 字段填充规则是否清晰？

---

## 实施计划（待确认后执行）

### Phase 1: Schema 定义和验证

- [ ] 创建 `mem0/user_profile/user_profile_schema.py`
  - 定义 `FAMILY_SUGGESTED_RELATIONS`
  - 实现 `validate_family_relation()`
  - 实现常见 typo 检测

- [ ] 修改 `extraction_rules.yaml`
  - 增加 suggested_relations
  - 明确 name/relation/info 填充规则

- [ ] 修改 `prompts.py`
  - 在 extraction prompt 中增加 family 关系示例
  - 强调 name 字段填充规则

### Phase 2: 合并逻辑实现

- [ ] 修改 `user_profile_manager.py`
  - 实现 `_deep_merge_social_context()`
  - 集成 `validate_family_relation()`
  - 处理 UPDATE action 的 id 匹配逻辑

### Phase 3: 测试和文档

- [ ] 编写测试用例
  - 测试 social_context 合并（不覆盖）
  - 测试 name 字段正确填充
  - 测试 typo 自动修正

- [ ] 更新文档
  - 更新 `DEV_GUIDE_UserProfile.md`
  - 更新 `TODO.md`

### Phase 4: 提交

- [ ] git commit 提交所有修改

---

**Claude 注**：等待用户确认方案后再开始实施。特别需要确认：
1. 建议的 family 关系字段列表是否符合需求
2. 是否使用 spouse 统一配偶，还是分别使用 wife/husband