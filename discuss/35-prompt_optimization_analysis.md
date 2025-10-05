# Prompt 整体优化分析和方案（P2）

**日期**：2025-10-05
**状态**：方案设计中
**优先级**：P2（中优先级）
**前置任务**：P1 Personality冲突检测完成

---

## 当前状态分析

### Prompt 长度统计

**文件**: `mem0/user_profile/prompts.py` - 总计 678 行

1. **EXTRACT_PROFILE_PROMPT**: 307 行（第5-312行）
   - 规则部分：约 170 行
   - 示例部分：约 137 行（5个示例）

2. **UPDATE_PROFILE_PROMPT**: 365 行（第314-679行）
   - 规则部分：约 140 行
   - 示例部分：约 225 行（8个示例）

**总计**: 672 行 prompt 内容

### 工业最佳实践参考

根据LLM prompt工程最佳实践：

1. **COSTAR框架**：Context, Objective, Style, Tone, Audience, Response
2. **精简原则**：
   - 移除冗余信息
   - 合并相似规则
   - 使用清晰的层级结构
   - 示例要具有代表性，避免重复

3. **长度建议**：
   - 关键规则 < 1000 tokens
   - 示例 2-3 个最具代表性的即可
   - 总长度控制在 2000-3000 tokens 为佳

4. **准确性保证**：
   - 保留所有关键约束（CRITICAL rules）
   - 保留边界情况处理
   - 保留冲突检测逻辑

---

## 识别的优化机会

### 1. 重复规则（跨prompt）

#### Language Consistency
- **EXTRACT**: Rule 1（14行）
- **UPDATE**: Rule 1（1行简述）
- **优化**: 在EXTRACT中详细说明，UPDATE中简化引用

#### Evidence 格式
- **EXTRACT**: Rule 2（3行）
- **UPDATE**: Rule 2, 7（共6行）
- **优化**: 统一说明，避免重复

#### Social Context
- **EXTRACT**: Rule 4（60行详细）
- **UPDATE**: Rule 8（29行详细）
- **优化**: EXTRACT中详细说明schema，UPDATE中简化为"遵循extraction规则"

### 2. 冗余示例

#### EXTRACT_PROFILE_PROMPT 示例分析

| 示例 | 主题 | 行数 | 保留建议 |
|------|------|------|----------|
| Example 1 | basic_info | 12 | ✅ 保留 - 基础格式 |
| Example 2 | interests | 14 | ✅ 保留 - degree示例 |
| Example 3 | social_context - 基础 | 24 | ✅ 保留 - name规则 |
| Example 4 | social_context - collateral | 31 | ❓ 合并到Example 3 |
| Example 5 | social_context - spouse | 23 | ❓ 合并到Example 3 |

**优化**: 将Example 3, 4, 5合并为一个完整的social_context示例

#### UPDATE_PROFILE_PROMPT 示例分析

| 示例 | 主题 | 行数 | 保留建议 |
|------|------|------|----------|
| Example 1 | ADD interest | 18 | ✅ 保留 - 基础ADD |
| Example 2 | UPDATE degree | 16 | ✅ 保留 - 基础UPDATE |
| Example 3 | DELETE (contradiction) | 15 | ✅ 保留 - 基础DELETE |
| Example 4 | social_context ADD | 29 | ❓ 与Rule 8重复 |
| Example 5 | social_context UPDATE | 28 | ❓ 与Rule 8重复 |
| Example 6 | Personality SKIP | 28 | ✅ 保留 - 冲突检测核心 |
| Example 7 | Personality DELETE+ADD | 45 | ✅ 保留 - 冲突检测核心 |
| Example 8 | Personality COEXIST | 29 | ❓ 简化或合并到Rule 9 |

**优化**:
- Example 4, 5 简化为Rule 8的内联示例
- Example 8 简化（RARE情况，在Rule 9中已说明）

### 3. 冗余强调

#### ❗标记使用
- EXTRACT: 5个 ❗CRITICAL
- UPDATE: 2个 ❗CRITICAL
- **优化**: 只在最关键的规则使用，减少到每个prompt 2-3个

#### 重复注意事项
- "NO translation" 在多处重复
- "Keep exact language" 在多处重复
- **优化**: 合并到统一的语言一致性规则

### 4. 格式优化

#### JSON示例
- 当前：完整的多层级JSON
- **优化**: 使用紧凑格式或省略号表示

#### 列表格式
- 当前：冗长的bullet points
- **优化**: 使用表格或更紧凑的格式

---

## 优化方案

### 方案目标

- ✅ **准确性优先**：保留所有关键约束和规则
- ✅ **精简冗余**：移除重复内容
- ✅ **提升可读性**：更清晰的结构
- 🎯 **目标长度**：减少 30-40% （从 672行 → 400-470行）

### 具体优化策略

#### A. EXTRACT_PROFILE_PROMPT 优化

**优化前**: 307 行
**优化目标**: 200-220 行（减少 30%）

1. **规则部分** (170行 → 110行):
   - 保留 7 条核心规则
   - Rule 1 (Language): 简化为核心要点 + 示例
   - Rule 4 (Social Context): 精简为表格 + 核心规则
   - 移除冗余的"注意事项"重复

2. **示例部分** (137行 → 90行):
   - 保留 3 个示例：
     * Example 1: basic_info（简化）
     * Example 2: interests + personality（合并，展示degree）
     * Example 3: social_context（合并3个示例，展示所有场景）

#### B. UPDATE_PROFILE_PROMPT 优化

**优化前**: 365 行
**优化目标**: 220-250 行（减少 30-35%）

1. **规则部分** (140行 → 90行):
   - 保留 9 条核心规则
   - Rule 8 (Social Context): 简化，引用EXTRACT中的详细说明
   - Rule 9 (Personality Conflict): 保持详细但紧凑

2. **示例部分** (225行 → 130行):
   - 保留 5 个示例：
     * Example 1: ADD（简化）
     * Example 2: UPDATE（简化）
     * Example 3: DELETE（简化）
     * Example 4: Personality SKIP（合并Example 6, 8的要点）
     * Example 5: Personality DELETE+ADD（简化Example 7）

---

## 优化细节

### 1. Language Consistency 简化

**优化前**:
```
1. **❗CRITICAL - Language consistency**: Keep the EXACT language of user input in ALL fields
   - ❌ WRONG: User says "退休了" → You output "retired"
   - ✅ CORRECT: User says "退休了" → You output "退休了"
   - ❌ WRONG: User says "designer" → You output "设计师"
   - ✅ CORRECT: User says "designer" → You output "designer"
   - **NO translation between Chinese/English/any languages**
   - **Copy the EXACT words from user's message**
```

**优化后**:
```
1. **❗Language Consistency**: Preserve user's EXACT language - NO translation
   - 中文 input → 中文 output | English input → English output
   - ❌ "退休了" → "retired" | ✅ "退休了" → "退休了"
```

**节省**: ~8行

### 2. Social Context Schema 简化

**优化前**: 60行详细规则

**优化后**: 使用表格 + 核心规则，约30行

```
**social_context Schema**:

| Field | Type | Examples | Rules |
|-------|------|----------|-------|
| family | object | father, mother, spouse, brother[], daughter[] | Direct relatives only. name=actual name or null |
| friends | array | {name, info} | NO relation field |
| others | array | {name, relation, info} | Collateral relatives, teachers, etc. |

**Core Rules**:
- family: ONLY direct relatives (see allowed list)
- name: Actual name or null (NOT relation word like "妻子")
- Collateral relatives (uncle/aunt/cousin) → others
```

**节省**: ~30行

### 3. 示例合并

**EXTRACT Example 3 (优化前 - 分散在3个示例中)**:

Example 3: 24行 (father/mother)
Example 4: 31行 (brother/uncle)
Example 5: 23行 (spouse/daughter)
总计: 78行

**EXTRACT Example 3 (优化后 - 合并)**:

```markdown
### Example 3: Social context - Complete scenarios

Messages:
- "我爸爸叫李明，是医生。我妈妈是老师"
- "我有两个哥哥，大哥叫小明。我舅舅是工程师"
- "我老婆叫小芳，是设计师。女儿小静静三岁"

Output:
{
  "additional_profile": {
    "social_context": {
      "family": {
        "father": {"name": "李明", "info": ["医生"]},
        "mother": {"name": null, "info": ["老师"]},
        "brother": [
          {"name": "小明", "info": ["大哥"]},
          {"name": null, "info": ["哥哥"]}
        ],
        "spouse": {"name": "小芳", "info": ["设计师"]},
        "daughter": [{"name": "小静静", "info": ["三岁"]}]
      },
      "others": [
        {"name": null, "relation": "舅舅", "info": ["工程师"]}
      ]
    }
  }
}
```

**节省**: ~35行

### 4. UPDATE示例简化

**优化前**: Example 4, 5各约28行，展示social_context的ADD/UPDATE

**优化后**: 在Rule 8中添加简短示例

```
8. **social_context**: Uses DEEP MERGE - preserve unmentioned relationships
   - ADD spouse: {"spouse": {"event": "ADD", "name": "小芳", "info": [...]}}
   - Backend merges with existing father/mother
```

**节省**: ~40行

---

## 风险评估

### 高风险（需要保留）

1. **Personality 冲突检测** (Rule 9 + Examples 6, 7)
   - 这是P1刚实现的核心功能
   - **保留**: 完整规则 + 2个示例

2. **Social Context 深度合并** (Rule 8)
   - 这是P0修复的关键bug
   - **保留**: 核心规则 + 简短示例

3. **Language Consistency** (Rule 1)
   - 这是P0修复的语言问题
   - **保留**: 核心规则 + 明确示例

### 低风险（可以简化）

1. 重复的注意事项
2. 冗长的JSON格式示例
3. 相似场景的多个示例

---

## 实施计划

### Phase 1: 分析和验证（当前阶段）
- [x] 统计当前长度
- [x] 识别重复内容
- [x] 制定优化方案
- [ ] **等待用户确认方案**

### Phase 2: 实施优化
1. 创建备份（prompts_backup.py）
2. 优化 EXTRACT_PROFILE_PROMPT
3. 优化 UPDATE_PROFILE_PROMPT
4. 代码审查

### Phase 3: 测试验证
1. 运行现有测试套件
   - test_user_profile.py
   - test_user_profile_advanced.py
   - test_social_context_merge.py
   - test_personality_conflict.py
2. 比对优化前后的LLM输出
3. 确保准确性不降低

### Phase 4: 文档更新
1. 更新 DEV_GUIDE
2. 更新 TODO.md
3. 创建 discuss/36-prompt_optimization_implemented.md

---

## 优化效果预测

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total lines | 672 | ~450 | -33% |
| EXTRACT lines | 307 | ~220 | -28% |
| UPDATE lines | 365 | ~230 | -37% |
| Examples (EXTRACT) | 5 | 3 | -40% |
| Examples (UPDATE) | 8 | 5 | -38% |
| ❗CRITICAL markers | 7 | 4 | -43% |

**预计Token减少**: 约 30-35%

---

## 用户确认点

请确认以下优化方向：

1. ✅ **合并social_context示例**（3个→1个）是否可接受？
2. ✅ **简化Rule 8 (social_context)**，在UPDATE中引用EXTRACT的详细规则？
3. ✅ **保留Personality冲突检测的2个完整示例**（SKIP + DELETE/ADD）？
4. ✅ **使用表格代替部分冗长的列表**？
5. ✅ **目标减少30-35%长度**是否合适，还是需要更激进？

---

**Claude 注**：
- 本方案遵循工业最佳实践（COSTAR框架，精简原则）
- 优先保证准确性，所有CRITICAL规则保留
- 通过合并重复内容和优化格式实现精简
- 等待用户确认后开始实施