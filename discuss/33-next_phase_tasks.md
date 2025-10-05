# 下一阶段任务规划

**日期**：2025-10-05
**状态**：待开始
**前置任务**：social_context 覆盖问题已修复 (commit: 8fd3600, dab1f7f)

---

## 当前已完成工作总结

### ✅ 已修复问题

1. **social_context 覆盖问题** (commit: 8fd3600)
   - 问题：添加 spouse/daughter 时，father/mother 数据丢失
   - 解决：实现深度合并逻辑 `_deep_merge_social_context()`
   - 创建 `user_profile_schema.py` 进行字段验证
   - 测试通过：✅ 所有关系保留，正确合并

2. **name 字段错误填充问题** (commit: 8fd3600)
   - 问题：name 字段被填充为关系词（如"妻子"）而不是具体名字
   - 解决：在 prompt 中明确规则和示例
   - 测试通过：✅ name 正确填充为 "小芳"、"小静静"

3. **语言一致性问题** (commit: dab1f7f)
   - 问题：LLM 将中文翻译成英文（"退休了" → "retired"）
   - 解决：强化语言一致性规则，所有示例改为中文
   - 状态：已提交，待用户测试验证

### ✅ 新增功能

- **family Schema 约束**：
  - 定义 FAMILY_RELATIONS（core/common/extended）
  - 只允许直系亲属，旁系亲属放到 others
  - Typo 自动修正功能
  - 字段验证（validate_family_relation, validate_relation_structure）

- **用户画像调整指南**：
  - 文档说明如何从"小孩"调整到"成年人"画像
  - 需要修改的文件清单（schema.py, prompts.py, DEV_GUIDE）

---

## 下一阶段任务

### 优先级 P1：Personality 冲突检测

**问题描述** (来自 discuss/25-problem.md):

用户说："我今天被领导批评了，说我粗枝大叶"

现有 personality：
```json
[
  {"name": "认真负责", "degree": 4},
  {"name": "专注", "degree": 4}
]
```

LLM 输出：
```json
{"name": "粗枝大叶", "degree": 4}  // ❌ 直接新增，没有检测到冲突
```

**期望行为**：
- 检测到 "粗枝大叶" 与 "认真负责" 冲突
- 触发冲突解决逻辑（evidence 分析）
- degree=4 不合理（仅一次批评不应该是高 degree）

**解决方案（待讨论）**：

方案 A：在 decision prompt 中增加"反义词冲突检测"

```yaml
personality_conflict_rules:
  - "检测语义冲突（如：细心 vs 粗心，内向 vs 外向）"
  - "如果新 personality 与现有 personality 冲突："
  - "  - 如果新 evidence 只有1-2条 → 不添加或 degree=2"
  - "  - 如果新 evidence 多且recent → 触发冲突解决（可能是真的改变）"
  - "  - 如果现有 evidence 多且old → DELETE 旧的，ADD 新的"
```

方案 B：维护反义词对列表

```python
# mem0/user_profile/user_profile_schema.py
PERSONALITY_CONFLICTS = {
    "细心": ["粗心", "粗枝大叶"],
    "认真负责": ["粗枝大叶", "马虎"],
    "内向": ["外向"],
    "乐观": ["悲观"],
    # ... 更多
}
```

在代码层检测冲突，然后在 prompt 中提示 LLM 处理。

方案 C：让 LLM 自己判断语义冲突

在 decision prompt 中：
```
Before adding a new personality trait:
1. Check if it conflicts with existing traits semantically
2. Examples of conflicts:
   - "粗枝大叶" conflicts with "细心", "认真负责"
   - "内向" conflicts with "外向"
3. If conflict detected:
   - Analyze evidence count and timestamps
   - Decide: UPDATE existing (reduce degree), DELETE old + ADD new, or SKIP new
```

**建议采用方案 C**：
- 优点：灵活，不需要维护词表
- 缺点：依赖 LLM 判断准确性
- 可以后续结合方案 B 作为兜底

**实施步骤**：

1. [ ] 更新 `UPDATE_PROFILE_PROMPT`
   - 添加 personality 冲突检测规则
   - 添加冲突处理示例

2. [ ] 测试验证
   - 测试用例："粗枝大叶" vs "认真负责"
   - 测试用例："外向" vs "内向"
   - 验证 degree 合理性

3. [ ] 如果效果不好，考虑方案 B
   - 在 `user_profile_schema.py` 中维护 PERSONALITY_CONFLICTS
   - 在 `profile_manager.py` 中预检测
   - 在 decision prompt 中提示冲突

---

### 优先级 P2：Prompt 整体优化

**问题** (来自 discuss/31-respond.md):

用户观察到：**当前 prompt 有点长**

**要求**：
- 综合考虑准确性与长度
- **准确性优先**
- 在完成 personality 冲突检测后再进行

**优化方向**（待实施）：

1. **合并重复规则**：
   - extraction_rules.yaml 和 prompt 中有重复
   - 考虑在 yaml 中定义，prompt 中引用

2. **精简示例**：
   - 保留最具代表性的示例
   - 合并相似场景

3. **使用更简洁的表达**：
   - 去掉冗余的强调（多个 ❗CRITICAL）
   - 使用更紧凑的格式

4. **分层次的规则**：
   - 核心规则（必须遵守）
   - 边界情况（可选参考）

**实施步骤**：

1. [ ] 分析当前 prompt 长度和结构
   - EXTRACT_PROFILE_PROMPT 行数
   - UPDATE_PROFILE_PROMPT 行数
   - 识别重复内容

2. [ ] 制定优化方案
   - 哪些规则可以合并
   - 哪些示例可以删除
   - 如何保持准确性

3. [ ] 实施优化
   - 对比优化前后效果
   - A/B 测试验证准确性

4. [ ] 文档更新

---

### 优先级 P3：其他待优化问题

**来自 discuss/26-32 讨论**：

1. **Schema 约束问题**：
   - MongoDB 无 schema，可能导致 LLM 返回错误字段
   - 考虑在代码层增加更严格的验证
   - 或使用 MongoDB Schema Validation

2. **Evidence limit 优化**：
   - 当前在应用层处理（全量取回后截取）
   - 优化为数据库层处理（MongoDB aggregation $slice）
   - 减少网络传输和内存占用

3. **并发处理**：
   - Profile 更新的并发冲突处理
   - 考虑乐观锁或悲观锁

---

## 推荐的实施顺序

1. **P1: Personality 冲突检测** (高优先级)
   - 这是功能性 bug，影响用户体验
   - 实施方案 C（LLM 语义判断）
   - 如果效果不好再考虑方案 B

2. **P2: Prompt 整体优化** (中优先级)
   - 在 P1 完成后进行
   - 可以一起优化 personality 冲突检测的 prompt

3. **P3: 其他优化** (低优先级)
   - 根据实际使用情况决定

---

## 相关文件

**需要修改的文件**：

1. `mem0/user_profile/prompts.py`
   - UPDATE_PROFILE_PROMPT 中添加 personality 冲突检测

2. `mem0/user_profile/user_profile_schema.py`
   - (可选) 添加 PERSONALITY_CONFLICTS 词表

3. `mem0/user_profile/profile_manager.py`
   - (可选) 在 _apply_decisions() 中预检测冲突

**测试文件**：

- 创建 `test_personality_conflict.py` 测试冲突检测

**文档**：

- 更新 `DEV_GUIDE_UserProfile.md` 说明冲突检测机制
- 更新 `TODO.md` 记录任务完成情况

---

## 注意事项

1. **语言一致性修复验证**：
   - 下一个实例首先应该验证用户测试 commit dab1f7f 的结果
   - 如果仍有问题，可能需要进一步强化 prompt

2. **测试驱动**：
   - 每个功能先写测试用例
   - 验证通过后再提交

3. **讨论优先**：
   - 重大设计决策先在 discuss 中讨论
   - 获得用户确认后再实施

4. **文档同步**：
   - 代码修改后立即更新文档
   - 保持 DEV_GUIDE 和 TODO.md 的一致性

---

**Claude 注**：
- 本文档为下一个实例准备，记录了当前状态和下一步任务
- 建议优先处理 P1 (Personality 冲突检测)
- 等待用户确认语言一致性修复效果