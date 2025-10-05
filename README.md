# My Mem0 Service

_[English Version](#english-version)_

---

## 简体中文说明

### 项目概览
本仓库基于开源项目 [mem0](https://github.com/mem0ai/mem0) 进行深度定制：
- 保留 mem0 的长期记忆能力（事实抽取、向量化存储、检索、历史追踪）。
- 增加一个可直接部署的 FastAPI 服务层，提供 `/memories`、`/profile` 等 REST 接口，并集成请求日志、健康检查等中间件。
- 新增 **UserProfile** 模块，采用“证据驱动 + 双阶段 LLM Pipeline”，将基础信息写入 PostgreSQL（仅作参考）并把兴趣/技能/性格等核心画像写入 MongoDB。

> 📌 当前版本的画像设计优先适配 **3-9 岁儿童用户**（业务约束），因此数据库字段、Prompt 示例、冲突处理策略会优先保留与儿童相关的特征（如 school_name、grade、学习偏好等）。若要支持成年人，只需在 Prompt、schema 与校验规则中调整字段列表和示例，该架构仍然适用。

### 核心组件
- **FastAPI 服务**（`server/main.py`）：包装 `mem0.Memory` 与 `mem0.user_profile.UserProfile`，提供配置、CRUD、检索和画像接口，并添加请求日志中间件。
- **定制 mem0 库**（`mem0/`）：在保留原有模块的基础上，新增 UserProfile 业务逻辑、Postgres/Mongo 管理器、Prompt 模板、性能采集等。
- **数据库脚本**（`scripts/`）：包含 `user_profile` schema 初始化 SQL、增量迁移、Mongo 初始化脚本。
- **性能监控**（`performance_monitoring/`）：可选的性能分析工具，可在 `mem0/memory/main.py` 中启用。
- **文档体系**：`DEV_GUIDE_UserProfile.md`（开发指南）、`docs/`（设计决策）、`CLAUDE.md`（协作约定）。

### 配置与可扩展性
- `server/main.py` 中的 `DEFAULT_CONFIG` 与 `mem0.configs.base.MemoryConfig` 保持一致，可通过 `.env` 或 Docker 环境变量覆盖任何 LLM、Embedding、Vector Store、历史库等设置。
- 运行时可使用 `POST /configure` 直接替换整个配置对象。
- 如果在其他项目中集成，可用 `UserProfile(Memory.from_config(custom_config).config)` 直接复用现有逻辑。
- 默认镜像内安装了 DeepSeek + Qwen 所需依赖，但这些只是“样例配置”，可以按需改为 OpenAI、Claude、不同的向量库等。

常用环境变量示例：

| 变量 | 用途 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | LLM 调用密钥 | 无 | 若自定义 `llm` 配置，可留空。 |
| `DASHSCOPE_API_KEY` | Qwen Embedding 密钥 | 无 | 自定义 embedder 后同样可留空。 |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | pgvector 连接 | `postgres/5432/postgres/postgres/postgres` | 同时用于记忆与 basic_info。 |
| `POSTGRES_COLLECTION` | 向量集合名 | `memories` | 可改为自定义表名。 |
| `EMBEDDING_MODEL_DIMS` | 向量维度 | `1536` | 与所选 embedder 保持一致。 |
| `MONGODB_URI` / `MONGODB_DATABASE` | 画像扩展信息库 | `mongodb://mongo:mongo@mongodb:27017/` / `mem0` | 生产环境请改为真实连接串。 |
| `HISTORY_DB_PATH` | SQLite 历史库路径 | `/app/history/history.db` | 可挂载到宿主机目录。 |
| `LOG_LEVEL` | 日志级别 | `INFO` | 影响 FastAPI 与 mem0 模块。 |

### 用户画像业务说明（儿童优先）
- PostgreSQL 表结构包含 `school_name`、`grade`、`class_name` 等字段，用于追踪 3-9 岁儿童的教育信息。
- Prompt 需要 LLM 在判断兴趣/技能/性格时考虑儿童语境（例如兴趣“画画”、技能“识字”等）。
- `DEV_GUIDE_UserProfile.md` 和 `scripts/migrations/` 里的注释均标记了儿童优先的设计点；若要适配成年人，需要调整这些定义以及冲突处理规则。
- MongoDB `social_context` 结构将“family 核心关系”与“其他关系”分开，默认假设当前用户是孩子（父母信息优先）。

### 快速部署指南（Docker Compose）
> 依赖：Docker 24+、Compose Plugin 2.20+。

1. **克隆并配置环境变量**
   ```bash
   git clone <repo>
   cd my_mem0
   cp .env.example .env  # 如果存在模板
   # 编辑 .env，填入所需密钥与数据库信息
   ```

2. **初始化数据库** —— `docker compose up` 不会自动创建 `user_profile` schema 和 Mongo 索引，需手动执行：
   ```bash
   # 启动数据库容器
   docker compose up -d postgres mongodb

   # 在容器内创建 PostgreSQL schema / 表
   docker compose exec -T postgres \
     psql -U postgres -d postgres -f /app/scripts/init_userprofile_db.sql

   # 依次执行增量迁移（如有）
   for file in scripts/migrations/*.sql; do
     docker compose exec -T postgres \
       psql -U postgres -d postgres -f "/app/$file"
   done

   # 初始化 Mongo 集合与索引（在宿主机执行，可修改为真实连接串）
   MONGODB_URI="mongodb://mongo:mongo@localhost:27017/" \
   MONGODB_DATABASE=mem0 \
   python scripts/init_mongodb.py
   ```

   已有 pgvector 数据时（命名卷如 `my_mem0_postgres_db` 已存在），上述 SQL 不会自动触发，请务必手动跑完再启动 API。也可以编写维护脚本调用 `UserProfile.initialize_databases()` 执行同样逻辑。

3. **启动服务**
   ```bash
   docker compose up -d
   docker compose ps
   docker compose logs -f mem0-service
   ```

   端口映射：`18088` → FastAPI、`8432` → PostgreSQL、`27017` → MongoDB、`18089` → SQLite 历史库浏览器。数据持久化通过 Docker 命名卷完成，如需绑定宿主机目录，可修改 `docker-compose.yaml` 并提前迁移数据。

4. **验收**
   - 打开 Swagger：<http://localhost:18088/docs>
   - 写入记忆：
     ```bash
     curl -X POST http://localhost:18088/memories \
       -H 'Content-Type: application/json' \
       -d '{"messages":[{"role":"user","content":"我喜欢恐龙"}],"user_id":"demo"}'
     ```
   - 更新画像：
     ```bash
     curl -X POST http://localhost:18088/profile \
       -H 'Content-Type: application/json' \
       -d '{"user_id":"demo","messages":[{"role":"user","content":"我叫乐乐，在北京上小学"}]}'
     ```

### 非容器化运行
1. 安装依赖：`pip install -r server/requirements.txt`（排除 `mem0ai`），随后 `pip install -e .` 使本地 `mem0/` 可被引用。
2. 提供 PostgreSQL（含 pgvector 扩展）、MongoDB 和 SQLite 路径。
3. 运行 FastAPI：
   ```bash
   cd server
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. 使用同样的 SQL / Python 脚本或 `UserProfile.initialize_databases()` 初始化 Schema。

### API 摘要
| 接口 | 说明 |
| --- | --- |
| `POST /configure` | 运行时替换完整的 `MemoryConfig` 配置。 |
| `POST /memories` | 写入记忆，需至少包含 `user_id` / `agent_id` / `run_id`。 |
| `GET /memories` / `GET /memories/{id}` | 获取指定范围或单条记忆。 |
| `POST /search` | 向量检索，支持过滤、阈值、条数限制。 |
| `PUT /memories/{id}` / `DELETE /memories/{id}` / `DELETE /memories` | 修改或删除记忆。 |
| `GET /memories/{id}/history` | 查看记忆的历史演变（来自 SQLite）。 |
| `POST /profile` | 执行两阶段画像更新，可附带 `manual_data`（人工校验信息）。 |
| `GET /profile` | 查询画像数据，支持字段过滤与 `evidence_limit`。 |
| `GET /profile/missing-fields` | 返回缺失字段列表，便于后续对话补全。 |
| `DELETE /profile` | 删除 PostgreSQL + MongoDB 中的画像数据。 |
| `POST/GET /vocab` | 预留接口，当前返回 501。 |

### 运维与排障
- **日志**：通过 `LOG_LEVEL` 控制；请求/响应日志由 `middleware/RequestLoggingMiddleware` 提供。
- **性能监控**：可在 `mem0/memory/main.py` 中启用 `PERFORMANCE_MONITORING_ENABLED`。
- **JSON 健壮性**：画像 Pipeline 含多重容错（重试、JSON 清洗、逐字段回退），详见 `profile_manager.py`。
- **Schema 版本管理**：所有迁移脚本位于 `scripts/migrations/`，均具备 `IF NOT EXISTS` 保护。
- **更换供应商**：更新 `.env` 或调用 `POST /configure`，同时确保 Docker 镜像已安装所需 SDK。

### 更多文档
- [DEV_GUIDE_UserProfile.md](DEV_GUIDE_UserProfile.md)：UserProfile 全流程、Prompt、测试方案。
- [docs/summary_and_challenges.md](docs/summary_and_challenges.md)：设计总结与风险列表。
- [docs/mem0_integration_analysis.md](docs/mem0_integration_analysis.md)：mem0 集成分析。
- [CLAUDE.md](CLAUDE.md)：协作规范与更新要求。

---

## English Version

### Overview
This repository delivers a production-friendly deployment of [mem0](https://github.com/mem0ai/mem0):
- It preserves **all** upstream long-term memory capabilities (fact extraction, vector storage/search, history tracking).
- A FastAPI layer exposes REST endpoints (`/memories`, `/profile`, etc.), adds logging middleware, and makes the service easy to run inside Docker.
- An evidence-based **UserProfile** module augments the system, persisting conversation-derived basic info in PostgreSQL (non-authoritative reference) and richer attributes in MongoDB.

> 📌 The current profile design is tuned for **children aged 3–9**—a product decision. Schema fields (e.g., school info), prompt examples, and conflict rules prioritise child-centric traits. With light prompt/schema adjustments, the same architecture can serve adult personas.

### Key Components
- **FastAPI server** (`server/main.py`): wraps `mem0.Memory` and `mem0.user_profile.UserProfile`, exposes configuration & CRUD/search endpoints, and wires in request logging middleware.
- **Custom mem0 fork** (`mem0/`): keeps upstream modules while adding user-profile logic, Postgres/Mongo managers, prompt templates, and optional performance hooks.
- **Database tooling** (`scripts/`): SQL bootstrap for the `user_profile` schema, incremental migrations, and a MongoDB initialiser creating collections/indexes.
- **Performance monitoring** (`performance_monitoring/`): opt-in instrumentation controlled from `mem0/memory/main.py`.
- **Documentation**: `DEV_GUIDE_UserProfile.md`, `docs/`, and `CLAUDE.md` capture design choices, requirements, and collaboration rules.

### Configurability Highlights
- `DEFAULT_CONFIG` mirrors `mem0.configs.base.MemoryConfig`. Environment variables feed the structure but you can:
  - Override any provider/model/connection via `.env`/Docker vars.
  - Replace the active config at runtime with `POST /configure`.
  - Embed the library elsewhere with `UserProfile(Memory.from_config(custom_config).config)`.
- DeepSeek + Qwen are default dependencies inside the reference image; swap them freely for other LLM/embedding/vector backends.
- SQLite history storage (`HISTORY_DB_PATH`) can point to any accessible location.

### Child-Focused Profile Design
- PostgreSQL schema ships with `school_name`, `grade`, `class_name`, etc., to capture primary-school context.
- Prompts instruct the LLM to reason about child interests/skills (drawing, reading, etc.).
- Mongo `social_context` assumes the persona is the child, elevating parents/guardians as core relations.
- See `DEV_GUIDE_UserProfile.md` and `scripts/migrations/` for the exact field lists and guidance on adapting them for adult users.

### Quick Deploy (Docker Compose)
Prerequisites: Docker 24+, Compose Plugin 2.20+.

1. **Clone & configure**
   ```bash
   git clone <repo>
   cd my_mem0
   cp .env.example .env
   # edit .env with API keys and DB credentials
   ```

2. **Bootstrap databases** – `docker compose up` will *not* auto-create schemas/indexes:
   ```bash
   docker compose up -d postgres mongodb

   docker compose exec -T postgres \
     psql -U postgres -d postgres -f /app/scripts/init_userprofile_db.sql

   for file in scripts/migrations/*.sql; do
     docker compose exec -T postgres \
       psql -U postgres -d postgres -f "/app/$file"
   done

   MONGODB_URI="mongodb://mongo:mongo@localhost:27017/" \
   MONGODB_DATABASE=mem0 \
   python scripts/init_mongodb.py
   ```

   Existing pgvector volumes (`my_mem0_postgres_db`, etc.) will skip entrypoint scripts—run the SQL manually before starting the API. `UserProfile.initialize_databases()` offers the same logic programmatically.

3. **Launch services**
   ```bash
   docker compose up -d
   docker compose ps
   docker compose logs -f mem0-service
   ```

   Port map: `18088` (API), `8432` (Postgres), `27017` (Mongo), `18089` (SQLite viewer). Data persists in Docker named volumes; swap to bind mounts if you need host-level paths.

4. **Smoke test**
   - Swagger: <http://localhost:18088/docs>
   - Add a memory:
     ```bash
     curl -X POST http://localhost:18088/memories \
       -H 'Content-Type: application/json' \
       -d '{"messages":[{"role":"user","content":"I love dinosaurs"}],"user_id":"demo"}'
     ```
   - Update profile:
     ```bash
     curl -X POST http://localhost:18088/profile \
       -H 'Content-Type: application/json' \
       -d '{"user_id":"demo","messages":[{"role":"user","content":"My name is Lily and I go to school in Beijing"}]}'
     ```

### Running Without Docker
- Install dependencies: `pip install -r server/requirements.txt` (strip `mem0ai`), then `pip install -e .` to expose the local `mem0/` package.
- Provide Postgres + pgvector, MongoDB, and an SQLite path via environment variables.
- Launch FastAPI from `server/`: `uvicorn main:app --host 0.0.0.0 --port 8000`.
- Use the same SQL/Python scripts (or `UserProfile.initialize_databases()`) to create schemas before accepting traffic.

### API Surface
| Endpoint | Description |
| --- | --- |
| `POST /configure` | Swap the active `MemoryConfig` at runtime. |
| `POST /memories` | Add memories; requires one of `user_id`/`agent_id`/`run_id`. |
| `GET /memories`, `GET /memories/{id}` | Retrieve scoped or single memories. |
| `POST /search` | Vector search with filters/threshold/limit. |
| `PUT /memories/{id}`, `DELETE /memories/{id}`, `DELETE /memories` | Update/delete memories. |
| `GET /memories/{id}/history` | Inspect memory history (SQLite). |
| `POST /profile` | Two-stage profile update with optional `manual_data`. |
| `GET /profile` | Query profile data with field filters and `evidence_limit`. |
| `GET /profile/missing-fields` | Suggest missing fields (Postgres/Mongo/both). |
| `DELETE /profile` | Remove profile records from both stores. |
| `POST/GET /vocab` | Reserved (returns HTTP 501). |

### Operations & Troubleshooting
- **Logging**: controlled via `LOG_LEVEL`; request/response logging is provided by `RequestLoggingMiddleware`.
- **Performance monitoring**: toggle `PERFORMANCE_MONITORING_ENABLED` in `mem0/memory/main.py`.
- **JSON safeguards**: the profile pipeline handles retries, JSON cleaning, and per-field fallbacks (`profile_manager.py`).
- **Schema management**: migrations live under `scripts/migrations/`, all idempotent (`IF NOT EXISTS`).
- **Provider changes**: update `.env` or call `POST /configure`; ensure Docker images include the necessary SDKs.

### Further Reading
- [DEV_GUIDE_UserProfile.md](DEV_GUIDE_UserProfile.md) – implementation, prompts, and test strategy.
- [docs/summary_and_challenges.md](docs/summary_and_challenges.md) – design summary & risk log.
- [docs/mem0_integration_analysis.md](docs/mem0_integration_analysis.md) – integration analysis.
- [CLAUDE.md](CLAUDE.md) – collaboration norms.

Use this README for deployment/operations. For code-level changes or schema adjustments, consult the detailed documents before editing.
