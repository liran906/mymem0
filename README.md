# My Mem0 Service

基于Mem0的独立记忆服务，使用Qdrant + DeepSeek + OpenAI Embedding

## 配置说明

### 1. 编辑 .env 文件
```bash
# DeepSeek API Configuration (for LLM)
DEEPSEEK_API_KEY=sk-xxxxxxxxx  # 替换为你的DeepSeek API Key

# OpenAI API Configuration (for embeddings only)
OPENAI_API_KEY=sk-xxxxxxxxx   # 替换为你的OpenAI API Key
```

### 2. 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 验证服务
- **API文档**: http://localhost:18088/docs
- **Qdrant Web UI**: http://localhost:6334/dashboard
- **SQLite数据库查看**: http://localhost:18089 (历史记录)

## API 使用示例

### 添加记忆
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

### 搜索记忆
```bash
curl -X POST "http://localhost:18088/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "用户喜欢什么菜",
    "user_id": "user_123"
  }'
```

### 获取所有记忆
```bash
curl "http://localhost:18088/memories?user_id=user_123"
```

## 技术架构

- **向量数据库**: Qdrant (本地Docker)
- **LLM**: DeepSeek Chat (API) - 成本极低
- **嵌入模型**: OpenAI text-embedding-3-small - 质量优秀
- **Web框架**: FastAPI
- **无图数据库**: 简化部署

## 端口说明

- `18088`: Mem0 API服务
- `6333`: Qdrant API
- `6334`: Qdrant Web UI
- `18089`: SQLite 数据库查看器 (历史记录)

## 故障排除

1. **DeepSeek API调用失败**: 检查API Key是否正确
2. **OpenAI embedding失败**: 检查网络连接和API Key
3. **Qdrant连接失败**: 确保Qdrant容器正常启动
4. **Container构建失败**: 检查Docker和网络连接

## 扩展配置

如需修改配置，编辑 `server/main.py` 中的 `DEFAULT_CONFIG`。