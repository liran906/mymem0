# Social Context 最终 Schema 设计方案

**日期**：2025-10-05
**关联讨论**：discuss/28-family_schema_design.md, discuss/29-respond.md
**状态**：已确认，待实施

---

## 用户确认的设计方案

### 1. Social Context 结构

```yaml
social_context:
  family:         # 家庭成员（直系亲属）
    father:       # { name, info }
    mother:       # { name, info }
    brother:      # [ { name, info }, ... ]  可多个
    sister:       # [ { name, info }, ... ]  可多个
    spouse:       # { name, info }
    son:          # [ { name, info }, ... ]  可多个
    daughter:     # [ { name, info }, ... ]  可多个
    grandfather_paternal:   # { name, info }
    grandmother_paternal:   # { name, info }
    grandfather_maternal:   # { name, info }
    grandmother_maternal:   # { name, info }
    # ... 其他建议字段

  friends:        # 朋友关系
    # [ { name, info }, ... ]

  others:         # 其他社交关系（同事、远房亲戚等）
    # [ { name, relation, info }, ... ]
```

### 2. 关键设计决策

#### ✅ 确认的决策

1. **去掉 sibling**：
   - 原因：维护复杂度高（sibling → brother/sister 需要迁移数据）
   - 改为：直接使用 brother/sister

2. **统一字段格式**：
   - family 成员：`{ name, info }`
   - friends 成员：`{ name, info }`
   - others 成员：`{ name, relation, info }`（多一个 relation 字段）
   - **不给父母单独增加 career 等特殊字段**（避免两套规则）

3. **去掉 colleagues**：
   - 同事关系放到 `others` 中
   - 最终只有三个顶级字段：family, friends, others

4. **建议字段约束**：
   - 给 LLM 提示词中列出核心字段和常见字段
   - **LLM 不要原创词汇**（使用建议字段列表）
   - 不属于 family 建议字段且不是朋友的 → 放到 others

5. **name 字段填充规则**：
   - 通过加强 prompt 解决
   - name 只填具体名字，没有则为 null

---

## Schema 定义

### family 建议字段列表

```python
# mem0/user_profile/user_profile_schema.py

FAMILY_RELATIONS = {
    # 核心关系（一般都会有）
    "core": ["father", "mother"],

    # 常见关系（可能有）
    "common": [
        "brother",                    # 兄弟（可多个，数组）
        "sister",                     # 姐妹（可多个，数组）
        "spouse",                     # 配偶
        "son",                        # 儿子（可多个，数组）
        "daughter",                   # 女儿（可多个，数组）
    ],

    # 扩展关系（祖辈等）
    "extended": [
        "grandfather_paternal",       # 爷爷
        "grandmother_paternal",       # 奶奶
        "grandfather_maternal",       # 外公
        "grandmother_maternal",       # 外婆
        "uncle",                      # 叔叔/舅舅（可多个，数组）
        "aunt",                       # 阿姨/姑姑（可多个，数组）
    ]
}

# 所有允许的 family 关系（扁平化列表）
ALL_FAMILY_RELATIONS = (
    FAMILY_RELATIONS["core"] +
    FAMILY_RELATIONS["common"] +
    FAMILY_RELATIONS["extended"]
)

# 可多个的关系（数组类型）
ARRAY_RELATIONS = ["brother", "sister", "son", "daughter", "uncle", "aunt"]

# 单个的关系（对象类型）
SINGLE_RELATIONS = ["father", "mother", "spouse",
                    "grandfather_paternal", "grandmother_paternal",
                    "grandfather_maternal", "grandmother_maternal"]
```

### 数据结构规范

```python
# 每个关系的字段格式

# family 成员（单个）
{
    "name": str | None,      # 具体名字，如"小芳"；未提及则为 null
    "info": [str]            # 相关信息列表，如 ["设计师", "35岁"]
}

# family 成员（数组）
[
    {
        "name": str | None,
        "info": [str]
    },
    ...
]

# friends 成员
[
    {
        "name": str | None,
        "info": [str]
    },
    ...
]

# others 成员
[
    {
        "name": str | None,
        "relation": str,       # 关系描述，如 "同事"、"表哥"
        "info": [str]
    },
    ...
]
```

---

## Extraction Rules 更新

### extraction_rules.yaml

```yaml
social_context:
  description: "用户的社交关系网络，包括家庭、朋友和其他社交关系"

  structure:
    family:
      description: "家庭成员（直系亲属）"

      allowed_relations:
        core:
          - father: "父亲"
          - mother: "母亲"

        common:
          - brother: "兄弟（可多个）"
          - sister: "姐妹（可多个）"
          - spouse: "配偶（丈夫/妻子）"
          - son: "儿子（可多个）"
          - daughter: "女儿（可多个）"

        extended:
          - grandfather_paternal: "爷爷"
          - grandmother_paternal: "奶奶"
          - grandfather_maternal: "外公"
          - grandmother_maternal: "外婆"
          - uncle: "叔叔/舅舅（可多个）"
          - aunt: "阿姨/姑姑（可多个）"

      field_schema:
        name: "具体名字（如'李明'），未提及则为 null"
        info: "相关信息列表（如 ['退休', '身体健康']）"

      rules:
        - "❗CRITICAL: 只使用 allowed_relations 中列出的关系，不要原创新的关系词"
        - "❗CRITICAL: name 字段只填具体名字，如果对话中没有提到名字，则设为 null"
        - "❌ 错误：name='父亲'（这是关系，不是名字）"
        - "✅ 正确：name='李明' 或 name=null"
        - "info 字段存储关于该关系人的所有信息（职业、年龄、健康状况等）"
        - "配偶统一使用 spouse，不要使用 wife/husband"
        - "兄弟姐妹使用 brother/sister，不要使用 sibling"
        - "远房亲戚（如表哥、堂妹）不属于 family，应放到 others"

    friends:
      description: "朋友关系（好友列表）"

      field_schema:
        name: "朋友的名字（未提及则为 null）"
        info: "关于该朋友的信息列表"

      rules:
        - "只存储明确提到的朋友"
        - "如果只提到'朋友'但没有具体名字，name 设为 null"

    others:
      description: "其他社交关系（同事、远房亲戚、邻居等）"

      field_schema:
        name: "名字（未提及则为 null）"
        relation: "关系描述（如 '同事'、'表哥'、'邻居'）"
        info: "相关信息列表"

      rules:
        - "不属于 family allowed_relations 的亲戚（如表哥、堂妹）放到 others"
        - "同事、邻居、导师等非亲友关系都放到 others"
        - "relation 字段必须明确描述关系类型"

  update_rules:
    - "❗CRITICAL: 对 social_context 执行**深度合并**，不是覆盖"
    - "保留所有现有关系，只添加或更新被明确提及的关系"
    - "如果新信息提到某个关系（如 spouse），只更新该关系，不影响其他关系（如 father/mother）"
    - "只有在明确说明某关系不再存在时才执行 DELETE 操作"
```

---

## Prompt 更新

### Extraction Prompt 增加示例

```python
# mem0/user_profile/prompts.py

EXTRACTION_EXAMPLES = """
## social_context 提取示例

### 示例1：正确填充 name 字段

输入："我父亲叫李明，是工程师；我母亲叫王芳，是老师"

输出：
```json
{
  "social_context": {
    "family": {
      "father": {
        "name": "李明",
        "info": ["工程师"]
      },
      "mother": {
        "name": "王芳",
        "info": ["老师"]
      }
    }
  }
}
```

### 示例2：name 未提及时设为 null

输入："我父母都退休了，身体很好"

输出：
```json
{
  "social_context": {
    "family": {
      "father": {
        "name": null,           # ❗不是 "父亲"
        "info": ["退休", "身体很好"]
      },
      "mother": {
        "name": null,           # ❗不是 "母亲"
        "info": ["退休", "身体很好"]
      }
    }
  }
}
```

### 示例3：配偶使用 spouse

输入："我老婆叫小芳，是设计师，我们结婚7年了"

输出：
```json
{
  "social_context": {
    "family": {
      "spouse": {
        "name": "小芳",
        "info": ["设计师", "结婚7年"]
      }
    }
  }
}
```

### 示例4：兄弟姐妹（数组）

输入："我有两个哥哥，大哥叫李伟，在北京工作；二哥叫李强"

输出：
```json
{
  "social_context": {
    "family": {
      "brother": [
        {
          "name": "李伟",
          "info": ["大哥", "在北京工作"]
        },
        {
          "name": "李强",
          "info": ["二哥"]
        }
      ]
    }
  }
}
```

### 示例5：远房亲戚放到 others

输入："我表哥是医生，我们关系很好"

输出：
```json
{
  "social_context": {
    "others": [
      {
        "name": null,
        "relation": "表哥",
        "info": ["医生", "关系很好"]
      }
    ]
  }
}
```

### 示例6：同事放到 others

输入："我同事小张是前端工程师，技术很强"

输出：
```json
{
  "social_context": {
    "others": [
      {
        "name": "小张",
        "relation": "同事",
        "info": ["前端工程师", "技术很强"]
      }
    ]
  }
}
```

### 示例7：朋友

输入："我有个好朋友叫阿明，我们从小一起长大"

输出：
```json
{
  "social_context": {
    "friends": [
      {
        "name": "阿明",
        "info": ["好朋友", "从小一起长大"]
      }
    ]
  }
}
```
"""
```

---

## 验证逻辑

### 字段验证函数

```python
# mem0/user_profile/user_profile_schema.py

def validate_family_relation(relation_key: str) -> dict:
    """
    验证 family 关系字段名

    Returns:
        {
            "valid": bool,
            "suggestion": str | None,
            "warning": str | None
        }
    """
    if relation_key in ALL_FAMILY_RELATIONS:
        return {"valid": True, "suggestion": None, "warning": None}

    # 检测常见错误用法
    common_mistakes = {
        "wife": "spouse",
        "husband": "spouse",
        "sibling": "brother or sister",
        "parent": "father or mother",
        "child": "son or daughter",
        "grandparent": "grandfather_* or grandmother_*",
    }

    if relation_key in common_mistakes:
        return {
            "valid": False,
            "suggestion": common_mistakes[relation_key],
            "warning": f"Invalid relation '{relation_key}', use '{common_mistakes[relation_key]}' instead"
        }

    # 检测 typo
    typo_suggestions = {
        "fatehr": "father",
        "motehr": "mother",
        "borther": "brother",
        "sisiter": "sister",
        "daugther": "daughter",
        "spose": "spouse",
    }

    if relation_key in typo_suggestions:
        return {
            "valid": False,
            "suggestion": typo_suggestions[relation_key],
            "warning": f"Possible typo: '{relation_key}' → '{typo_suggestions[relation_key]}'"
        }

    # 不在允许列表中
    return {
        "valid": False,
        "suggestion": None,
        "warning": f"Unknown family relation: '{relation_key}'. Should use allowed_relations or put in 'others'."
    }


def validate_relation_structure(relation_key: str, value: dict | list) -> dict:
    """
    验证关系的数据结构是否正确

    Returns:
        {
            "valid": bool,
            "errors": [str]
        }
    """
    errors = []

    # 检查是否应该是数组
    if relation_key in ARRAY_RELATIONS:
        if not isinstance(value, list):
            errors.append(f"'{relation_key}' should be an array, got {type(value)}")
        else:
            for idx, item in enumerate(value):
                errors.extend(_validate_relation_item(relation_key, item, idx))
    else:
        if isinstance(value, list):
            errors.append(f"'{relation_key}' should be an object, got array")
        else:
            errors.extend(_validate_relation_item(relation_key, value))

    return {"valid": len(errors) == 0, "errors": errors}


def _validate_relation_item(relation_key: str, item: dict, index: int = None) -> list:
    """验证单个关系项的字段"""
    errors = []
    prefix = f"{relation_key}[{index}]" if index is not None else relation_key

    # 检查必需字段
    if "name" not in item:
        errors.append(f"{prefix}: missing 'name' field")
    if "info" not in item:
        errors.append(f"{prefix}: missing 'info' field")

    # 检查字段类型
    if "name" in item and item["name"] is not None and not isinstance(item["name"], str):
        errors.append(f"{prefix}.name: should be string or null, got {type(item['name'])}")

    if "info" in item and not isinstance(item["info"], list):
        errors.append(f"{prefix}.info: should be array, got {type(item['info'])}")

    # 检查是否有多余字段
    allowed_fields = {"name", "info"}
    extra_fields = set(item.keys()) - allowed_fields
    if extra_fields:
        errors.append(f"{prefix}: unexpected fields {extra_fields}")

    return errors
```

---

## 实施计划

### Phase 1: Schema 和验证 (✅ 已设计完成)

- [x] 确定 social_context 结构（family, friends, others）
- [x] 定义 family 允许的关系列表
- [x] 定义字段格式规范（name, info, relation）
- [x] 设计验证函数

### Phase 2: 代码实现（待开始）

- [ ] 创建 `mem0/user_profile/user_profile_schema.py`
  - 实现 `FAMILY_RELATIONS`, `ALL_FAMILY_RELATIONS`
  - 实现 `ARRAY_RELATIONS`, `SINGLE_RELATIONS`
  - 实现 `validate_family_relation()`
  - 实现 `validate_relation_structure()`

- [ ] 更新 `mem0/user_profile/extraction_rules.yaml`
  - 添加完整的 social_context 规则
  - 添加 allowed_relations 列表
  - 添加 field_schema 定义

- [ ] 更新 `mem0/user_profile/prompts.py`
  - 在 extraction prompt 中添加示例
  - 在 decision prompt 中强调合并逻辑

- [ ] 修改 `mem0/user_profile/user_profile_manager.py`
  - 实现 `_deep_merge_social_context()` 方法
  - 集成字段验证逻辑
  - 在 `_apply_decisions()` 中调用验证

### Phase 3: 测试（待开始）

- [ ] 编写测试用例
  - 测试 family 关系合并（不覆盖）
  - 测试 name=null 场景
  - 测试数组关系（brother/sister）
  - 测试字段验证和错误提示
  - 测试 typo 检测

- [ ] 手动测试
  - 使用 discuss/25 中的测试数据
  - 验证 father/mother 不会丢失
  - 验证 name 字段正确填充

### Phase 4: 文档更新（待开始）

- [ ] 更新 `DEV_GUIDE_UserProfile.md`
  - 添加 social_context schema 说明
  - 添加字段验证说明

- [ ] 更新 `TODO.md`

### Phase 5: 提交（待开始）

- [ ] git commit 提交所有修改

---

## 后续优化方向（暂不实施）

1. **personality 冲突检测**：
   - "粗枝大叶" vs "认真负责" 的语义冲突
   - 需要更复杂的 prompt 工程或反义词库

2. **MongoDB Schema Validation**：
   - 在数据库层面增加约束
   - 需要评估性能影响

---

**Claude 注**：方案已确认，可以开始实施。是否现在开始 Phase 2 的代码实现？