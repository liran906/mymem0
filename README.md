# My Mem0 Service

基于Mem0的独立记忆服务，支持：
- **Memory Management**: 使用 PGVector + DeepSeek + Qwen Embedding 进行记忆管理
- **UserProfile**: 基于证据的用户画像提取和管理 (PostgreSQL + MongoDB)

## 配置说明

### 1. 编辑 .env 文件
```bash
# API Keys
DEEPSEEK_API_KEY=sk-xxxxxxxxx  # DeepSeek API Key (for LLM)
DASHSCOPE_API_KEY=sk-xxxxxxxxx # Qwen API Key (for embeddings)

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# MongoDB Configuration (for UserProfile)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=mem0
```

### 2. 初始化数据库
```bash
# 初始化 PostgreSQL 表
psql -h localhost -p 8432 -U postgres -d postgres -f scripts/init_userprofile_db.sql

# 初始化 MongoDB 集合和索引
python scripts/init_mongodb.py
```

### 3. 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 验证服务
- **API文档**: http://localhost:18088/docs
- **SQLite数据库查看**: http://localhost:18089 (历史记录)
- **PostgreSQL**: localhost:8432
- **MongoDB**: localhost:27017

## API 使用示例

### Memory 相关

#### 添加记忆
```bash
curl -X POST "http://localhost:18088/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "我喜欢吃川菜"},
      {"role": "assistant", "content": "好的，我记住了您喜欢川菜"}
    ],
    "user_id": "user_123"
  }'
```

#### 搜索记忆
```bash
curl -X POST "http://localhost:18088/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "用户喜欢什么菜",
    "user_id": "user_123"
  }'
```

#### 获取所有记忆
```bash
curl "http://localhost:18088/memories?user_id=user_123"
```

### UserProfile 相关

#### 创建/更新用户画像
```bash
curl -X POST "http://localhost:18088/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "messages": [
      {"role": "user", "content": "我叫张三，住在北京，今年30岁"},
      {"role": "assistant", "content": "你好张三！"},
      {"role": "user", "content": "我很喜欢踢足球，每周末都和朋友一起踢"}
    ]
  }'
```

#### 获取用户画像
```bash
# 获取完整画像
curl "http://localhost:18088/profile?user_id=user_123"

# 只获取特定字段
curl "http://localhost:18088/profile?user_id=user_123&fields=interests,skills"
```

#### 删除用户画像
```bash
curl -X DELETE "http://localhost:18088/profile?user_id=user_123"
```

## 技术架构

### Memory 模块
- **向量数据库**: PGVector (PostgreSQL + pgvector扩展)
- **LLM**: DeepSeek Chat (API) - 成本极低
- **嵌入模型**: Qwen text-embedding-v4 (1536维) - 质量优秀
- **历史记录**: SQLite

### UserProfile 模块
- **基础信息存储**: PostgreSQL (user_profile schema)
- **附加信息存储**: MongoDB (evidence-based structure)
- **LLM Pipeline**: 两阶段提取 + 决策
- **特性**:
  - 基于证据的画像更新
  - UUID→int映射防止幻觉
  - 智能冲突处理
  - Degree系统 (1-5评分)

### 通用
- **Web框架**: FastAPI
- **容器化**: Docker + docker-compose

## 端口说明

- `18088`: Mem0 API服务
- `8432`: PostgreSQL (PGVector + UserProfile)
- `27017`: MongoDB (UserProfile additional_profile)
- `18089`: SQLite 数据库查看器 (历史记录)

## 故障排除

1. **DeepSeek API调用失败**: 检查API Key是否正确
2. **Qwen embedding失败**: 检查DASHSCOPE_API_KEY和网络连接
3. **PostgreSQL连接失败**: 确保PostgreSQL容器正常启动
4. **MongoDB连接失败**: 确保MongoDB容器正常启动
5. **Container构建失败**: 检查Docker和网络连接

## 文档

- **开发指南**: [DEV_GUIDE_UserProfile.md](DEV_GUIDE_UserProfile.md) - UserProfile模块完整开发指南
- **设计文档**: [docs/summary_and_challenges.md](docs/summary_and_challenges.md) - 设计总结和重难点
- **集成分析**: [docs/mem0_integration_analysis.md](docs/mem0_integration_analysis.md) - mem0框架集成分析
- **项目说明**: [CLAUDE.md](CLAUDE.md) - 项目结构和核心组件说明

## 扩展配置

如需修改配置，编辑 `server/main.py` 中的 `DEFAULT_CONFIG`。