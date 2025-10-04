# 架构决策：basic_info 定位与职责

**日期**: 2025-10-04
**决策**: 采用混合方案（方案1的增强版）

## 问题背景

主服务已经维护了用户基本信息（姓名、性别、年龄等），且 LLM 的 context 中会包含主服务提供的用户基本信息。需要明确 UserProfile 服务中 `basic_info` 的定位和职责。

## 候选方案

### 方案1：主服务维护，我们删除基本信息
- **优点**: 避免数据冗余和不一致，职责分离清晰
- **缺点**: 失去从对话中发现信息变更的能力

### 方案2：从主服务同步，存入我们的数据库
- **优点**: 可提供完整用户画像，独立查询
- **缺点**: 数据同步复杂性，存储冗余

### 方案3：我们也维护，但不保持一致
- **优点**: LLM 可自由提取和更新
- **缺点**: 数据不一致导致混乱

## 最终决策：混合方案（方案1的增强版）

### 核心设计思路

**basic_info 定位：对话中提取的基本信息（非权威数据，仅供参考）**

1. **数据性质**
   - 从用户对话中 LLM 提取的基本信息
   - 明确标注为"非权威数据"
   - 主服务的用户基本信息是唯一权威数据源

2. **使用场景**
   - **发现信息变更**: 与主服务数据对比，发现用户信息变化（如改名、搬家）
   - **对话个性化**: 记录用户在对话中的称呼偏好（如"叫我小李"）
   - **数据质量监控**: 检测主服务数据缺失或过期
   - **参考性补充**: 当主服务某些字段为空时，可参考对话提取的信息

3. **职责划分**
   - **主服务**: 权威的用户基本信息（姓名、性别、年龄、手机号、地址等）
   - **UserProfile 服务**:
     - `basic_info`: 从对话中提取的基本信息（参考性、辅助性）
     - `additional_profile`: 兴趣、技能、性格等深度特征（**核心价值**）

### API 数据结构

```python
# GET /profile 返回结构
{
    "basic_info": {
        # 从对话中提取的基本信息（非权威，仅供参考）
        "name": "李明",              # LLM 从对话中提取
        "current_city": "杭州",       # LLM 从对话中提取
        "nickname": "小李",          # 用户希望被称呼的名字
        # ... 其他对话中提到的信息
    },
    "additional_profile": {
        # 核心数据：用户深度特征
        "interests": [...],
        "skills": [...],
        "personality": [...],
        "social_context": [...],
        "learning_preferences": [...]
    }
}
```

### 实际使用指南

#### 前端/主服务调用

1. **常规场景**: 只获取 `additional_profile`
   ```python
   GET /profile?user_id=xxx&type=additional
   ```

2. **数据对比场景**: 获取 `basic_info` 用于发现变更
   ```python
   GET /profile?user_id=xxx&type=all
   # 对比 basic_info 和主服务数据，发现不一致则提示用户确认
   ```

3. **LLM Context**: 用户基本信息来自主服务（权威数据）
   ```python
   # 主服务构建 LLM context 时
   context = {
       "user_info": main_service.get_user_info(user_id),  # 来自主服务
       "user_profile": userprofile_service.get_profile(user_id, type="additional")  # 只要深度特征
   }
   ```

#### manual_data 参数说明

- **不需要 manual_data 参数**: 因为 `basic_info` 本身就是"对话提取的参考数据"，不需要主服务覆盖
- **如果需要纠正**: 主服务应该更新自己的权威数据，而不是覆盖 UserProfile 的提取数据
- **前端表单**: 用户手动填写的信息应该提交到主服务，而非 UserProfile

### 数据库架构

- **PostgreSQL (user_profile schema)**: 存储 `basic_info`（对话提取的参考信息）
- **MongoDB (user_additional_profile collection)**: 存储 `additional_profile`（核心特征数据）

### 注意事项

1. **避免混淆**: 文档和代码注释中明确标注 `basic_info` 是"对话提取的非权威数据"
2. **权威数据源**: 始终以主服务的用户信息为准
3. **用途限制**: `basic_info` 仅用于参考、对比、个性化，不用于业务决策
4. **数据同步**: 不需要主动同步主服务数据到 UserProfile

## 实施检查清单

- [x] 更新项目文档（CLAUDE.md, DEV_GUIDE_UserProfile.md 等）
- [x] 更新代码注释和 docstrings
- [x] 调整测试用例说明
- [x] 移除 manual_data 相关测试

## 参考

- 讨论来源: `discuss/18-manual_data.md`
- 相关文档: `DEV_GUIDE_UserProfile.md`, `docs/mem0_integration_analysis.md`