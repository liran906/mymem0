# TODO List

## 当前开发任务

### UserProfile 功能开发

> **详细开发指南**: 参见 `DEV_GUIDE_UserProfile.md`
> **设计文档**: 参见 `docs/mem0_integration_analysis.md` 和 `docs/summary_and_challenges.md`

#### Phase 1: 基础架构 ✅ (已完成 - 2025-10-04)
- [x] 创建目录结构
  - [x] `mem0/user_profile/` 目录
  - [x] `__init__.py`, `main.py`, `profile_manager.py`
  - [x] `database/postgres_manager.py`, `database/mongodb_manager.py`
  - [x] `prompts.py`, `utils.py`

- [x] 数据库管理器
  - [x] 实现 `PostgresManager`（基础信息 CRUD）
  - [x] 实现 `MongoDBManager`（附加信息 CRUD）
  - [x] 编写数据库初始化脚本（`scripts/init_userprofile_db.sql`）
  - [x] 更新 `docker-compose.yaml`（MongoDB 服务）

- [x] 配置扩展
  - [x] 扩展 `DEFAULT_CONFIG`（user_profile 部分）
  - [x] 更新 `.env.example`（MONGODB_URI, MONGODB_DATABASE）
  - [x] 实现配置验证和加载

**提交**: `12c86a0` - feat: Add UserProfile module Phase 1 - Infrastructure

#### Phase 2: Profile 功能 ✅ (已完成 - 2025-10-04)
- [x] ProfileManager 实现
  - [x] **阶段 1**：LLM 提取基础信息 + 附加信息
  - [x] **阶段 2**：查询现有数据 + UUID 映射
  - [x] **阶段 3**：LLM 决策 ADD/UPDATE/DELETE
  - [x] **阶段 4**：执行数据库操作（事务）

- [x] Prompt 开发
  - [x] `EXTRACT_PROFILE_PROMPT`（阶段 1）
  - [x] `UPDATE_PROFILE_PROMPT`（阶段 3）
  - [x] Few-shot 示例完善
  - [x] 输出格式严格化（JSON schema）

- [x] UserProfile 主类
  - [x] `set_profile()` - 完整 Pipeline
  - [x] `get_profile()` - 支持 options 参数
  - [x] 四层错误处理（LLM → JSON → 字段 → DB）

- [x] FastAPI 集成
  - [x] 实现 `/profile` 路由（POST, GET, DELETE）
  - [x] 请求验证和响应格式化
  - [x] 错误处理中间件

**提交**: `410aa2b` - feat: Add UserProfile module Phase 2 - Core functionality

#### Phase 3: 测试和优化 ⏳ (部分完成 - 2025-10-04)
- [x] 集成测试脚本
  - [x] 编写 `test/test_user_profile.py` - 完整 Pipeline 端到端测试
  - [x] 编写 `test/test_user_profile_advanced.py` - 高级场景测试（10个测试用例）
  - [x] 测试数据库初始化
  - [x] 测试 Profile CRUD 操作
  - [x] 测试 field filtering
  - [x] 测试冲突处理、degree调整、evidence积累等场景

- [ ] 单元测试（待完善）
  - [ ] PostgresManager 单元测试
  - [ ] MongoDBManager 单元测试
  - [ ] ProfileManager 各阶段单元测试
  - [ ] LLM 输出解析测试

- [ ] 场景测试（待完善）
  - [x] 冲突处理场景测试（evidence 分析）✅
  - [x] 边界情况测试（空输入、格式错误等）✅
  - [ ] 并发场景测试

- [x] 错误处理
  - [x] 四层错误处理实现（LLM → JSON → 字段 → DB）
  - [x] 日志记录（已优化Docker日志输出）
  - [ ] 异常场景 fallback 机制（待完善）
  - [ ] 数据一致性保证（待完善）

**备注**: 基础集成测试已完成，10个高级场景测试已完成，单元测试待后续完善

#### Phase 3.5: API增强 ✅ (已完成 - 2025-10-04)
- [x] evidence_limit 参数实现
  - [x] MongoDBManager 添加 `_limit_evidence()` 方法
  - [x] UserProfile.get_profile() 支持 evidence_limit 参数
  - [x] FastAPI GET /profile 添加 evidence_limit 参数（默认5，-1表示全部）
  - [x] 按时间倒序返回最新的N条evidence

- [x] missing-fields 接口实现
  - [x] PostgresManager 添加 `get_missing_fields()` 方法
  - [x] MongoDBManager 添加 `get_missing_fields()` 方法
  - [x] UserProfile 添加 `get_missing_fields()` 方法
  - [x] FastAPI 添加 GET /profile/missing-fields 接口
  - [x] 支持 source 参数（pg/mongo/both）

- [x] social_context schema 扩展
  - [x] 添加 teachers 字段（name, subject, info）
  - [x] 添加 others 字段（name, relation, info）
  - [x] 更新 prompts.py 示例

- [x] 鉴权TODO标记
  - [x] 在所有profile endpoints添加TODO注释（POST/GET/DELETE/missing-fields）

**提交**: 待提交 - feat: Add UserProfile API enhancements (evidence_limit, missing-fields, auth TODOs)

#### Phase 4: 文档和部署 ✅ (已完成 - 2025-10-04)
- [x] 文档更新
  - [x] README.md - API 使用示例、架构说明
  - [x] 部署指南 - 数据库初始化步骤
  - [x] 技术架构文档更新

- [x] 部署准备
  - [x] 环境变量配置（.env.example）
  - [x] 数据库初始化脚本（SQL + Python）
  - [x] Docker 配置更新（docker-compose.yaml）
  - [x] 依赖管理（添加 pymongo）

**提交**: `ca75965` - docs: Add documentation and test script

---

### Vocabulary 功能（归档 - Phase 2 开发）
> **归档文档**: 参见 `archived/vocab_design.md`
> **归档原因**: 需要产品讨论 count 语义、level 升级规则、是否降级等细节
> **当前状态**: API 预留（返回 501 Not Implemented）

---

## 未来需要实现的功能

### 隐私和安全（高优先级）⚠️
> **重要提醒**：这些功能目前未实现，但对生产环境至关重要！

- [ ] **访问控制**
  - [ ] user_id 权限校验（防止跨用户访问）
  - [ ] API 层添加认证机制
  - [ ] 操作审计日志（谁在什么时候访问了哪些数据）

- [ ] **数据保护**
  - [ ] 敏感字段加密存储（如家庭成员详细信息）
  - [ ] 数据导出功能（GDPR 合规 - 用户数据可导出）
  - [ ] 数据删除功能（GDPR 合规 - 用户注销/被遗忘权）
  - [ ] PII（个人身份信息）识别和标记

- [ ] **安全加固**
  - [ ] SQL 注入防护检查
  - [ ] MongoDB 注入防护检查
  - [ ] 输入验证和清洗
  - [ ] 速率限制（Rate Limiting）

### 性能优化（中优先级）
- [ ] **数据库优化**
  - [ ] 词汇表分页性能优化（大量词汇时）
  - [ ] MongoDB 索引优化和查询性能测试
  - [ ] PostgreSQL 查询计划分析
  - [ ] 数据库连接池调优

- [ ] **并发处理**
  - [ ] 词汇 count 的原子更新（防止并发丢失）
  - [ ] Profile 更新的并发冲突处理
  - [ ] 乐观锁或悲观锁机制

- [ ] **缓存策略**
  - [ ] Profile 数据缓存（Redis）
  - [ ] 常用词汇查询缓存
  - [ ] LLM 响应缓存（相同输入）

### 功能增强（低优先级）
- [ ] **Profile 和 Memories 联动**
  - [ ] 从历史 memories 批量提取并生成 profile
  - [ ] 自动从 memories 更新 profile（定期任务）
  - [ ] Profile 信息辅助 memories 搜索

- [ ] **词汇学习增强**
  - [ ] 词汇学习进度可视化 API
  - [ ] 词汇复习提醒（基于遗忘曲线）
  - [ ] 词汇学习报告（周报、月报）
  - [ ] 词汇分类和标签

- [ ] **数据分析**
  - [ ] 用户画像统计和聚合
  - [ ] 词汇学习趋势分析
  - [ ] 兴趣变化追踪

### 运维和监控（中优先级）
- [ ] **监控和告警**
  - [ ] LLM 调用失败监控
  - [ ] 数据库连接健康检查
  - [ ] API 响应时间监控
  - [ ] 错误率告警

- [ ] **数据管理**
  - [ ] 数据库迁移脚本管理（版本化）
  - [ ] 数据备份和恢复策略
  - [ ] 数据清理策略（过期数据）

- [ ] **文档和工具**
  - [ ] API 文档完善（OpenAPI/Swagger）
  - [ ] 数据库 Schema 文档
  - [ ] 运维手册

### 技术债务
- [ ] 代码重构
  - [ ] 提取公共的 LLM 调用逻辑
  - [ ] 统一错误处理机制
  - [ ] 单元测试覆盖率提升到 80%+

- [ ] 依赖管理
  - [ ] 依赖版本更新和安全扫描
  - [ ] Docker 镜像优化（减小体积）

---

## 已完成的任务 ✅

### 设计和规划阶段（2025-10-04）
- [x] 用户画像功能设计和讨论（discuss/01-17）
- [x] mem0 核心实现研究和集成分析
- [x] 数据库 Schema 设计（PostgreSQL + MongoDB）
- [x] API 接口设计（基于证据的架构）
- [x] 实施计划确认

### 文档编写（2025-10-04）
- [x] 编写 `docs/mem0_integration_analysis.md` - mem0 集成分析
- [x] 编写 `docs/summary_and_challenges.md` - 设计总结和重难点
- [x] 编写 `DEV_GUIDE_UserProfile.md` - 完整开发指南
- [x] 编写 `archived/vocab_design.md` - 词汇功能归档设计
- [x] 更新 `CLAUDE.md` - 新增 UserProfile 模块说明
- [x] 更新 `TODO.md` - 细化开发任务

### UserProfile 开发（2025-10-04）
- [x] Phase 1: 基础架构 - 提交 `12c86a0`
- [x] Phase 2: 核心功能 - 提交 `410aa2b`
- [x] Phase 3: 测试和优化 - 部分完成
- [x] Phase 4: 文档和部署 - 提交 `ca75965`
- [x] 创建 11 个新文件，修改 6 个文件
- [x] 实现完整的两阶段 LLM Pipeline
- [x] 基于证据的画像更新机制
- [x] FastAPI 路由集成

---

## 备注

- 优先级标记：⚠️ 高优先级 / 📌 中优先级 / 💡 低优先级
- 安全和隐私相关的功能在生产环境上线前**必须**实现
- 性能优化可以根据实际使用情况逐步优化
- 功能增强根据用户反馈和需求优先级调整

---

---

## 开发进度总结

### 🎯 UserProfile 模块 - 已完成核心功能

#### ✅ 已完成（2025-10-04）
- **Phase 1**: 基础架构 - 数据库管理器、配置扩展、Docker 集成
- **Phase 2**: 核心功能 - ProfileManager Pipeline、UserProfile 主类、API 路由
- **Phase 3**: 部分测试 - 集成测试脚本、错误处理机制
- **Phase 4**: 文档部署 - README、初始化脚本、依赖管理

#### ⏳ 待完善
- Phase 3 的单元测试（PostgresManager, MongoDBManager, ProfileManager）
- 高级场景测试（冲突处理、边界情况、并发）
- 性能优化和安全加固

#### 📊 开发成果
- **3 次提交**:
  - `12c86a0` - Phase 1: Infrastructure
  - `410aa2b` - Phase 2: Core functionality
  - `ca75965` - Documentation and testing
- **11 个新文件** + **6 个修改文件**
- **完整 Pipeline**: 提取 → 决策 → 执行
- **REST API**: POST/GET/DELETE `/profile`

---

最后更新：2025-10-04