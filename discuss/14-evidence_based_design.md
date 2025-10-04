# Evidence-Based 设计方案

## 1. 兴趣 vs 技能的边界问题

### 1.1 你提出的问题

**场景分析**：
- "我喜欢踢足球" → 兴趣？技能？
- "我会踢足球" → 技能？兴趣？

**现实情况**：确实有重叠和模糊！

### 1.2 三种处理方案

#### 方案 A：明确区分（严格边界）

**定义**：
- **兴趣（interests）**：喜欢、感兴趣的活动/事物（情感导向）
- **技能（skills）**：会做、掌握的能力（能力导向）

**示例**：
| 用户表述 | 分类 | 理由 |
|---------|------|------|
| "我喜欢踢足球" | 兴趣 | 强调"喜欢" |
| "我会踢足球" | 技能 | 强调"会" |
| "我喜欢踢足球，而且踢得很好" | 兴趣 + 技能 | 两者都有 |

**问题**：
- LLM 需要精确判断（prompt 复杂）
- 用户表述模糊时难以分类

---

#### 方案 B：允许重叠（灵活边界）

**定义**：
- **兴趣**：倾向于娱乐、爱好类
- **技能**：倾向于能力、专业类
- **允许同一事物同时出现在两个列表中**

**示例**：
```javascript
{
    "interests": [
        {"name": "足球", "degree": "like", "evidence": [...]}
    ],
    "skills": [
        {"name": "足球", "level": "intermediate", "evidence": [...]}
    ]
}
```

**优点**：
- 符合现实（喜欢且擅长）
- LLM 判断压力小

**问题**：
- 数据冗余
- 查询时需要合并展示

---

#### 方案 C：统一为"能力项"（推荐）⭐

**思路**：不严格区分兴趣和技能，统一为"用户的能力/爱好项"

**数据结构**：
```javascript
{
    "capabilities": [  // 或者叫 "attributes"
        {
            "id": "0",
            "name": "足球",
            "type": "hobby",  // hobby / skill / both
            "degree": 3,  // 1-5 的喜欢/擅长程度
            "evidence": [
                {
                    "text": "和朋友踢足球很开心",
                    "timestamp": "2025-10-01",
                    "aspect": "interest"  // interest / skill
                },
                {
                    "text": "踢进了关键一球",
                    "timestamp": "2025-10-05",
                    "aspect": "skill"
                }
            ]
        }
    ]
}
```

**优点**：
- 避免边界问题
- evidence 中区分了 aspect（兴趣/技能维度）
- 可以通过 type 和 aspect 灵活查询

**问题**：
- 概念上的抽象（但更接近现实）

---

### 1.3 我的建议

**MVP 阶段：方案 B（允许重叠）**

理由：
1. **最简单**：不需要创造新概念（capabilities）
2. **符合直觉**：用户和 LLM 都容易理解"兴趣"和"技能"
3. **灵活**：允许重叠，避免强制分类的困扰

**实施细节**：
- LLM Prompt 中说明：同一事物可以同时是兴趣和技能
- 查询时可以合并展示（前端逻辑）

**你觉得方案 B 可行吗？还是更倾向于方案 C？**

---

## 2. Evidence-Based 设计（核心）

### 2.1 你的建议分析

**你的想法**：
> 与其统计 count，是否可以直接统计事实（evidence）？
> evidence 是一个 list，里面是相关的所有事件以及时间。
> 兴趣、技能和性格都可以这么记录。

**我的评价**：✅ **非常好的想法！这比 count 更好！**

---

### 2.2 统一的数据结构

#### 方案：interests、skills、personality 都用同样的结构

```javascript
{
    "user_id": "u123",

    // 兴趣
    "interests": [
        {
            "id": "0",
            "name": "足球",
            "degree": 4,  // 见下文 degree 的讨论
            "evidence": [
                {
                    "text": "和朋友踢足球很开心",
                    "timestamp": "2025-10-01T10:30:00"
                },
                {
                    "text": "周末又去踢了一场，赢了！",
                    "timestamp": "2025-10-08T15:20:00"
                }
            ]
        },
        {
            "id": "1",
            "name": "北京烤鸭",
            "degree": 3,
            "evidence": [
                {
                    "text": "吃了北京烤鸭，很好吃",
                    "timestamp": "2025-10-01T18:00:00"
                }
            ]
        }
    ],

    // 技能
    "skills": [
        {
            "id": "0",
            "name": "python",
            "degree": 2,  // 程度：初级
            "evidence": [
                {
                    "text": "今天学了 Python 的 for 循环",
                    "timestamp": "2025-09-20T14:00:00"
                },
                {
                    "text": "用 Python 写了一个计算器",
                    "timestamp": "2025-09-25T16:30:00"
                }
            ]
        }
    ],

    // 性格
    "personality": [
        {
            "id": "0",
            "name": "好奇",
            "degree": 4,
            "evidence": [
                {
                    "text": "主动问了很多问题",
                    "timestamp": "2025-10-01T10:00:00"
                },
                {
                    "text": "对新话题表现出浓厚兴趣",
                    "timestamp": "2025-10-05T11:00:00"
                }
            ]
        }
    ],

    // 其他字段...
}
```

---

### 2.3 关于 degree 字段的统一

**你的问题**：
> "现在的 level、count 都是想表达 degree，那么干脆统一？
> 统一之后应该用什么呢？是个 int？还是 enum？还是别的？"

#### 选项对比

##### 选项 1：整数（1-5）⭐ 推荐

```javascript
{
    "name": "足球",
    "degree": 4  // 1=很低, 2=低, 3=中, 4=高, 5=很高
}
```

**优点**：
- 简单直观
- LLM 容易生成（数字比枚举字符串稳定）
- 可以做数值运算（如平均值、排序）
- 统一适用于兴趣、技能、性格

**degree 的语义**（根据类型不同）：
- **兴趣**：1=不太喜欢, 2=一般, 3=喜欢, 4=很喜欢, 5=最爱
- **技能**：1=初学, 2=入门, 3=中级, 4=高级, 5=专家
- **性格**：1=不明显, 2=偶尔, 3=一般, 4=明显, 5=非常明显

**LLM 判断依据**：evidence 的数量和质量
- evidence 少（1-2条）→ degree 较低（1-2）
- evidence 多（3-5条）→ degree 中等（3）
- evidence 很多（6+条）且质量高 → degree 高（4-5）

---

##### 选项 2：枚举字符串

```javascript
// 兴趣
{"name": "足球", "degree": "like"}  // dislike / neutral / like / love

// 技能
{"name": "python", "degree": "intermediate"}  // beginner / intermediate / advanced

// 性格
{"name": "好奇", "degree": "strong"}  // weak / moderate / strong
```

**问题**：
- 不同类型需要不同的枚举值（不统一）
- LLM 容易拼写错误（如 "intermidiate"）
- 难以排序和比较

---

##### 选项 3：浮点数（0.0-1.0）

```javascript
{"name": "足球", "degree": 0.85}
```

**问题**：
- 过于精确，LLM 难以判断（0.85 vs 0.87？）
- 语义不清晰

---

#### 我的建议：**选项 1（整数 1-5）**

**理由**：
1. ✅ 统一：所有类型都用 1-5
2. ✅ 简单：LLM 判断容易，用户理解直观
3. ✅ 灵活：可以根据 evidence 动态调整

**程序逻辑**（可选，辅助 LLM）：
```python
def calculate_degree_from_evidence(evidence_list):
    """根据 evidence 数量和时间，辅助计算 degree"""
    count = len(evidence_list)

    # 简单规则（LLM 为主，这只是兜底）
    if count >= 6:
        return 5
    elif count >= 4:
        return 4
    elif count >= 2:
        return 3
    elif count == 1:
        return 2
    else:
        return 1
```

**你同意用整数 1-5 吗？**

---

## 3. Evidence-Based 的完整 Pipeline

### 3.1 set_profile 流程

#### 阶段 1：提取信息和 evidence

**Prompt**：
```
从对话中提取用户的兴趣、技能和性格特征，并记录相关证据。

对话内容：
User: 我昨天和朋友踢足球，赢了！
Assistant: 太棒了！你很喜欢足球吗？
User: 是的，我每周都踢，而且越来越厉害了。

请返回 JSON：
{
    "interests": [
        {
            "name": "足球",
            "evidence": "和朋友踢足球，赢了"
        }
    ],
    "skills": [
        {
            "name": "足球",
            "evidence": "每周都踢，越来越厉害了"
        }
    ],
    "personality": [
        {
            "name": "社交",
            "evidence": "喜欢和朋友一起活动"
        }
    ]
}

注意：
- evidence 字段记录具体的事实描述（简短，1-2 句话）
- 只提取对话中明确提到的内容
- 如果某类信息不存在，返回空列表
```

---

#### 阶段 2：查询现有数据并合并

**查询现有数据**：
```python
current_profile = get_additional_profile(user_id)
# 返回：
{
    "interests": [
        {
            "id": "0",
            "name": "足球",
            "degree": 3,
            "evidence": [
                {"text": "喜欢踢足球", "timestamp": "2025-09-20T10:00:00"}
            ]
        }
    ],
    "skills": [],
    "personality": []
}
```

---

#### 阶段 2.5：LLM 判断更新策略

**Prompt**：
```
当前用户画像：
兴趣：
- 足球 (degree=3)
  - 证据1: "喜欢踢足球" (2025-09-20)

从最新对话提取的信息：
兴趣：
- 足球
  - 新证据: "和朋友踢足球，赢了" (2025-10-01)

技能：
- 足球
  - 新证据: "每周都踢，越来越厉害了" (2025-10-01)

请判断如何更新用户画像：
{
    "interests": [
        {
            "id": "0",  // 已存在，使用原ID
            "name": "足球",
            "event": "UPDATE",
            "new_degree": 4,  // 根据新证据，从 3 提升到 4
            "new_evidence": {
                "text": "和朋友踢足球，赢了",
                "timestamp": "2025-10-01T14:00:00"
            },
            "reason": "新增了积极的证据，提升程度"
        }
    ],
    "skills": [
        {
            "name": "足球",
            "event": "ADD",
            "new_degree": 2,  // 新技能，初级
            "new_evidence": {
                "text": "每周都踢，越来越厉害了",
                "timestamp": "2025-10-01T14:00:00"
            },
            "reason": "新发现的技能"
        }
    ],
    "personality": [...]
}

判断原则：
1. 如果名称已存在：
   - event = "UPDATE"
   - 使用原 ID
   - 添加新 evidence
   - 根据所有 evidence（旧的+新的）重新评估 degree

2. 如果名称不存在：
   - event = "ADD"
   - 生成新 ID（由程序处理）
   - 添加 evidence
   - 根据 evidence 判断初始 degree

3. 如果发现矛盾（如"我不喜欢足球了"）：
   - event = "DELETE" 或 "UPDATE" (降低 degree)
   - 综合考虑旧 evidence 的数量和时间
   - 如果旧证据很多且时间久远，可能确实改变了
   - 如果旧证据很多且时间很近，可能是一时的情绪
```

---

### 3.2 处理矛盾的智能判断

**你提到的场景**：
> "之前有10个evidence，现在用户却说不喜欢了，那么有可能是一时的气话？
> 又比如10个evidence都是几年前的了，那可能确实不喜欢了。"

**LLM Prompt 指引**：
```
矛盾处理原则：

场景1：旧证据很多（6+条）且时间很近（3个月内）
- 用户说"不喜欢了"
- 判断：可能是临时情绪，degree 降低但不删除
- 操作：UPDATE, new_degree = max(1, old_degree - 2)

场景2：旧证据很多但时间久远（1年前）
- 用户说"不喜欢了"
- 判断：兴趣可能真的改变了
- 操作：DELETE 或 UPDATE degree=1（标记为"曾经喜欢"）

场景3：旧证据很少（1-2条）
- 用户说"不喜欢了"
- 判断：之前判断可能不准确
- 操作：DELETE

场景4：明确的转变
- 用户说"我以前喜欢X，现在更喜欢Y"
- 操作：X 的 degree 降低，Y 新增或提升
```

**程序辅助**（可选）：
```python
def analyze_evidence_time_distribution(evidence_list):
    """分析 evidence 的时间分布"""
    now = datetime.now()
    recent_count = 0  # 3个月内
    old_count = 0     # 1年前

    for ev in evidence_list:
        ev_time = datetime.fromisoformat(ev["timestamp"])
        days_ago = (now - ev_time).days

        if days_ago <= 90:
            recent_count += 1
        elif days_ago >= 365:
            old_count += 1

    return {
        "total": len(evidence_list),
        "recent": recent_count,
        "old": old_count
    }

# 在 Prompt 中提供这个分析结果
time_analysis = analyze_evidence_time_distribution(current_evidence)
prompt += f"\n证据时间分析：总数={time_analysis['total']}, 近期={time_analysis['recent']}, 久远={time_analysis['old']}"
```

**你觉得这个矛盾处理逻辑如何？**

---

## 4. 统一后的数据结构总结

### 4.1 最终方案

```javascript
{
    "user_id": "u123",

    // 兴趣
    "interests": [
        {
            "id": "0",
            "name": "足球",
            "degree": 4,  // 1-5 整数
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

    // 技能
    "skills": [
        {
            "id": "0",
            "name": "python",
            "degree": 2,
            "evidence": [
                {
                    "text": "学了 for 循环",
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
            "degree": 4,
            "evidence": [
                {
                    "text": "主动问了很多问题",
                    "timestamp": "2025-10-01T10:00:00"
                }
            ]
        }
    ],

    // 社交关系（保持不变）
    "social_context": {...},

    // 学习偏好（保持不变）
    "learning_preferences": {...},

    // 元数据
    "system_metadata": {
        "created_at": "2025-10-01",
        "updated_at": "2025-10-03",
        "version": 1
    }
}
```

### 4.2 统一的字段说明

| 字段 | 类型 | 说明 | 适用于 |
|------|------|------|--------|
| `id` | string | 唯一标识符 | 所有 |
| `name` | string | 名称（中文） | 所有 |
| `degree` | int (1-5) | 程度/等级 | 所有 |
| `evidence` | array | 证据列表 | 所有 |
| `evidence[].text` | string | 证据描述 | 所有 |
| `evidence[].timestamp` | ISO8601 | 时间戳 | 所有 |

**语义统一**：
- interests: degree = 喜好程度
- skills: degree = 掌握程度
- personality: degree = 明显程度

---

## 5. 最终确认清单

| 问题 | 建议方案 | 状态 |
|------|---------|------|
| **兴趣 vs 技能边界** | 允许重叠（方案 B） | ❓ 待确认 |
| **统一数据结构** | id + name + degree + evidence | ❓ 待确认 |
| **degree 类型** | 整数 1-5 | ❓ 待确认 |
| **evidence 结构** | text + timestamp | ❓ 待确认 |
| **矛盾处理** | LLM 综合判断（考虑数量和时间） | ❓ 待确认 |
| **冲突规则** | 基于 evidence 的智能判断 | ❓ 待确认 |
| **容错机制** | 前三层（LLM/JSON/字段） | ✅ 已确认 |

---

## 6. 下一步

如果你确认以上方案，我会立即起草**最终的详尽开发文档**，包括：

1. **完整的数据结构** - Evidence-based 设计
2. **详细的 Pipeline** - 两阶段流程和 Prompt
3. **矛盾处理逻辑** - 智能判断规则
4. **API 设计** - 统一接口
5. **实施计划** - 分阶段开发步骤
6. **测试用例** - 覆盖各种场景

**你是否同意这个 Evidence-based 的设计？还有其他需要调整的吗？**