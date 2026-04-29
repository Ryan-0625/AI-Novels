# AI-Novels 重构计划 vs 现有项目 — 差距分析报告

> 版本: 1.0
> 日期: 2026-04-29
> 范围: Step1-15 全部重构计划 vs 现有代码库
> 代码统计: Python 47,385行 / 前端 5,930行 / 测试 8,185行 / 文档 63,766行

---

## 执行摘要

| 维度 | 现有状态 | 目标状态 (Step1-15) | 差距等级 |
|-----|---------|-------------------|---------|
| 架构模式 | 单体FastAPI，24+Agent内联 | NestJS BFF + Python AI引擎微服务 | 🔴 极大 |
| 数据库 | MySQL + MongoDB + Neo4j + ChromaDB | PostgreSQL + Qdrant + (Neo4j可选) | 🔴 极大 |
| 前端体验 | 6个基础页面，3秒轮询 | 10+沉浸式工作空间，WebSocket实时 | 🔴 极大 |
| 容器化 | 无Dockerfile，仅基础设施Compose | 3个多阶段Dockerfile + 完整编排 | 🔴 极大 |
| CI/CD | 无流水线，全手动部署 | GitHub Actions六阶段自动流水线 | 🔴 极大 |
| 可观测性 | 无监控、文本日志、无追踪 | PLG + OpenTelemetry全链路 | 🔴 极大 |
| 通信协议 | REST轮询 | REST + GraphQL + WebSocket + SSE + gRPC | 🔴 极大 |
| 消息队列 | RocketMQ | Redis Streams + Celery | 🟡 中等 |
| ORM | 自定义ORM (SQLite风格) | SQLModel (Python) + Prisma (BFF) | 🔴 极大 |
| 实体模型 | dataclass + to_dict() | SQLModel + Pydantic v2 | 🔴 极大 |
| 配置管理 | 多文件JSON + 环境变量 | AppConfig (Step10) 统一配置中心 | 🟡 中等 |
| 事件总线 | 内存EventBus | Redis Streams持久化事件总线 | 🟡 中等 |
| 日志系统 | 文本print风格 | Structlog结构化JSON + OTel集成 | 🟡 中等 |
| 安全 | CORS allow_origins=["*"] | Traefik网关 + Rate Limit + WAF + Trivy扫描 | 🟡 中等 |
| API文档 | FastAPI自动Swagger | Swagger + GraphQL Playground + 协议文档 | 🟢 小 |

**总体评估**: 15个重构步骤涉及 **141个文件变更**（新建/修改/废弃），当前代码库与目标架构存在根本性架构差异，属于**重写级重构**而非渐进式升级。

---

## 1. 架构层面对比

### 1.1 当前架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (Vue3 SPA)                          │
│            6页面 · Axios轮询 · Element Plus                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST (port 8004)
┌───────────────────────────▼─────────────────────────────────┐
│              单体 FastAPI 应用 (src/deepnovel/)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ API Routes   │  │ 24+ Agents   │  │ LLM Router       │  │
│  │ (4 controllers)│  (coordinator等) │  (OpenAI/Gemini等) │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ ConfigManager│  │ 内存EventBus │  │ 自定义ORM        │  │
│  │ (JSON多文件)  │  │ (asyncio)    │  │ (SQLite风格)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ MySQL Client │  │ MongoDB      │  │ Neo4j            │  │
│  │ (pymysql)    │  │ (pymongo)    │  │ (neo4j driver)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ ChromaDB     │  │ RocketMQ     │                        │
│  │ (向量存储)    │  │ (消息队列)    │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 目标架构 (Step14)

```
┌─────────────────────────────────────────────────────────────┐
│              前端 (Vue3 + TypeScript 沉浸式平台)               │
│    10+工作空间 · WebSocket/SSE · TipTap · Vue Flow · GSAP    │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST / GraphQL / WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│           BFF API Gateway (NestJS + TypeScript)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ REST Controller│ │ GraphQL      │  │ WebSocket        │  │
│  │              │  │ Resolver     │  │ Gateway          │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth/JWT     │  │ Rate Limit   │  │ Pino结构化日志   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ gRPC / HTTP / Redis Pub/Sub
┌───────────────────────────▼─────────────────────────────────┐
│              Python AI Engine (FastAPI 微服务)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Agent编排器   │  │ LLM Router   │  │ RAG Engine       │  │
│  │ (简化Agent)  │  │ (Tier支持)   │  │ (Qdrant)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Celery Worker│  │ Redis Streams│  │ SQLModel ORM     │  │
│  │ (异步任务)   │  │ (事件总线)   │  │ (Repository模式) │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 架构差距分析

| 差距项 | 当前实现 | 目标实现 | 影响 | 涉及Step |
|-------|---------|---------|------|---------|
| **服务拆分** | 单体FastAPI，Agent/Config/RAG/LLM全部内联 | NestJS BFF + Python AI引擎两个独立服务 | 需要完全重写API层和通信层 | Step14 |
| **BFF模式** | 无，前端直连Python后端 | NestJS BFF统一网关，聚合Python服务 | 需要全新Node.js项目 | Step14 |
| **协议丰富度** | 仅有REST | REST + GraphQL + WebSocket + SSE + gRPC | API层重写，前端通信层重写 | Step11, Step13, Step14 |
| **gRPC通信** | 无 | BFF ↔ Python引擎间高性能gRPC | 需要定义proto，双端实现 | Step14 |
| **微服务边界** | 无边界，直接函数调用 | 清晰的Service/Repository/Domain分层 | 需要重构Python项目结构 | Step14 |

---

## 2. 数据库层对比 (Step1)

### 2.1 当前数据库方案

```yaml
# config/docker-compose.yaml 中的数据库服务

MySQL 8.0:
  用途: 任务状态、日志、配置存储
  驱动: pymysql 1.1.0
  ORM: 自定义ORM (sqlite3风格)
  问题: 无连接池优化，无迁移工具

MongoDB (latest):
  用途: 世界圣经、角色档案、大纲、手稿
  驱动: pymongo 4.6.1
  问题: latest标签不可复现，无Schema验证

Neo4j (latest):
  用途: 角色关系图谱、世界知识图谱
  驱动: neo4j 5.18.0
  问题: latest标签，APOC插件配置有误（"serveredbms_default" 拼写错误）

ChromaDB (latest):
  用途: 章节全文向量、钩子向量、角色记忆
  驱动: chromadb 0.4.24
  问题: latest标签，无持久化备份策略
```

### 2.2 目标数据库方案 (Step1, Step14)

```yaml
PostgreSQL 16:
  用途: 统一主数据库（替换MySQL+MongoDB）
  扩展: pgvector（向量存储）、JSONB（文档存储）
  ORM: SQLModel (Python) + Prisma (BFF)
  优势: 单一数据库，ACID事务，全文搜索

Qdrant:
  用途: 专用向量数据库（替换ChromaDB）
  优势: REST API、gRPC、分布式集群、更好的性能

Redis 7:
  用途: 缓存、会话、消息队列、事件总线（替换RocketMQ）
  扩展: Redis Streams（事件总线）、RedisJSON
  优势: 统一中间件，减少运维复杂度

Neo4j (可选保留):
  用途: 图数据库（角色关系、知识图谱）
  变更: 固定版本标签，修正配置
```

### 2.3 数据库差距矩阵

| 组件 | 现状 | 目标 | 工作量 | 风险 |
|-----|------|------|--------|------|
| MySQL → PostgreSQL | pymysql + 自定义ORM | asyncpg + SQLModel | 🔴 高 | 数据迁移 |
| MongoDB → PostgreSQL JSONB | pymongo无Schema | SQLModel模型 + JSONB字段 | 🔴 高 | 查询兼容性 |
| ChromaDB → Qdrant | chromadb 0.4.24 | qdrant-client + REST API | 🟡 中 | 向量索引重建 |
| Neo4j | 配置有拼写错误 | 修正配置，固定版本 | 🟢 低 | 无 |
| RocketMQ → Redis Streams | rocketmq-client-python 2.0.0 | redis-py Streams API | 🟡 中 | 消息格式变更 |
| ORM | 自定义ORM (sqlite3风格) | SQLModel + Repository模式 | 🔴 高 | 全量查询重写 |

### 2.4 数据迁移路径

```
MySQL (tasks, logs, config)
    ├──→ PostgreSQL (relational tables)
    │      ├── novels
    │      ├── tasks
    │      ├── chapters
    │      └── system_logs
    │
MongoDB (world_bible, characters, outlines)
    ├──→ PostgreSQL JSONB columns
    │      ├── world_entities (JSONB)
    │      ├── characters (JSONB)
    │      └── outlines (JSONB)
    │
ChromaDB (vectors)
    ├──→ Qdrant Collections
           ├── chapter_embeddings
           ├── hook_embeddings
           └── character_memories
```

---

## 3. 实体模型对比 (Step1)

### 3.1 当前模型 (dataclass)

```python
# src/deepnovel/model/entities.py — 当前实现

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Character:
    char_id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    age_visual: int = 0
    age_real: Optional[int] = None
    gender: str = ""
    archetype: str = ""
    core_drive: str = ""
    core_wound: str = ""
    voice_style: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    profile: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return { ... }  # 手动序列化

@dataclass
class WorldEntity:
    world_id: str
    name: str
    category: str
    public_description: str = ""
    secret_truth: str = ""
    unspoken_tension: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return { ... }
```

**当前问题:**
- 纯 dataclass，无数据库映射能力
- `to_dict()` 手动编写，维护成本高
- 无类型验证（仅靠Python类型提示）
- `created_at` 为字符串，非 datetime 对象
- 无关系映射（Character → WorldEntity）

### 3.2 目标模型 (SQLModel)

```python
# Step1 计划中的模型

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.dialects.postgresql import JSONB
import uuid

class Character(SQLModel, table=True):
    """角色模型 — 世界仿真核心"""
    __tablename__ = "characters"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    novel_id: str = Field(foreign_key="novels.id", index=True)
    name: str = Field(index=True)
    aliases: List[str] = Field(default=[], sa_column=Column(JSONB))
    age_visual: int = Field(default=0)
    age_real: Optional[int] = Field(default=None)
    gender: str = Field(default="")
    archetype: str = Field(default="", index=True)
    core_drive: str = Field(default="")
    core_wound: str = Field(default="")
    voice_style: str = Field(default="")
    profile: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))

    # 关系
    novel: "Novel" = Relationship(back_populates="characters")
    mind: Optional["CharacterMind"] = Relationship(back_populates="character")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CharacterMind(SQLModel, table=True):
    """角色心智模型"""
    __tablename__ = "character_minds"

    character_id: str = Field(foreign_key="characters.id", primary_key=True)
    emotional_state: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    relationships: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    beliefs: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))

    character: Character = Relationship(back_populates="mind")
```

**目标优势:**
- SQLModel = SQLAlchemy ORM + Pydantic v2 验证
- 自动 `created_at`/`updated_at` 管理
- JSONB 原生支持（PostgreSQL）
- 关系映射（Relationship）
- 自动生成迁移脚本（Alembic）

### 3.3 模型差距

| 差距 | 当前 | 目标 | 影响文件 |
|-----|------|------|---------|
| 基类 | dataclass | SQLModel | `model/entities.py` 全量重写 |
| 数据库映射 | 无 (仅内存对象) | SQLAlchemy table=True | 新增 migration/alembic |
| 序列化 | 手动 to_dict() | Pydantic model_dump() | 所有使用to_dict的地方 |
| 关系 | 无 | Relationship | Agent逻辑需重写 |
| 验证 | 类型提示 (运行时无验证) | Pydantic v2 严格验证 | API层受益 |
| 时间类型 | str (ISO格式字符串) | datetime (UTC) | 所有时间字段 |

---

## 4. API层对比 (Step11, Step14)

### 4.1 当前API (FastAPI单体)

```python
# src/deepnovel/api/main.py — 当前

app = FastAPI(
    title="AI-Novels API",
    description="AI小说生成系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS: 生产环境安全隐患
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入的控制器
from .controllers import (
    task_controller,      # 任务管理
    status_controller,    # 状态查询
    config_controller,    # 配置管理
    health_controller     # 健康检查
)

# 路由
from .routes import router
app.include_router(router)
```

```python
# src/deepnovel/api/routes.py — 当前路由
# 从 api.ts 推断的端点:
# POST   /tasks              创建任务
# GET    /tasks/{id}         获取任务
# GET    /tasks/{id}/health  任务健康
# GET    /tasks/{id}/logs    任务日志
# POST   /tasks/{id}/cancel  取消任务
# GET    /tasks              列表查询
# GET    /tasks/{id}/chapters      章节列表
# GET    /tasks/{id}/chapters/{n}  章节内容
# GET    /config/{key}       获取配置
# POST   /config/update      更新配置
# GET    /stats              统计数据
# GET    /agents             Agent列表
# GET    /health             健康检查
# GET    /health/component/{name} 组件健康
```

### 4.2 目标API (NestJS BFF + Python引擎)

```typescript
// Step14 计划的 BFF API

// GraphQL Schema (Step14)
type Novel {
  id: ID!
  title: String!
  characters: [Character!]!
  world: World
  outline: Outline
  chapters: [Chapter!]!
}

type Query {
  novels: [Novel!]!
  novel(id: ID!): Novel
  characters(novelId: ID!): [Character!]!
  tasks(status: TaskStatus): [Task!]!
}

type Mutation {
  createNovel(input: CreateNovelInput!): Novel!
  generateChapter(input: GenerateChapterInput!): Task!
  updateCharacter(id: ID!, input: UpdateCharacterInput!): Character!
}

type Subscription {
  taskProgress(taskId: ID!): TaskProgress!
  agentThinking(taskId: ID!): AgentThinking!
  systemLog(level: LogLevel): SystemLog!
}

// REST端点补充:
// WebSocket: /ws (NestJS Gateway)
// SSE: /events (Server-Sent Events)
// gRPC: 内部BFF ↔ Python通信
```

### 4.3 API差距

| 能力 | 当前 | 目标 | 影响 |
|-----|------|------|------|
| **协议** | 仅REST | REST + GraphQL + WebSocket + SSE + gRPC | 前端100%重写通信层 |
| **CORS** | `allow_origins=["*"]` | Traefik网关层控制 | 安全修复 |
| **认证** | 无JWT | NestJS Passport JWT | 新增登录/授权流程 |
| **限流** | 无 | Traefik Rate Limit + NestJS Throttler | 防滥用 |
| **版本管理** | v1硬编码 | URL版本 + Header版本协商 | API兼容性 |
| **文档** | Swagger UI | Swagger + GraphQL Playground | 双份文档 |
| **实时通信** | 3秒轮询 | WebSocket + SSE推送 | 前端状态管理重写 |
| **请求追踪** | 无 | OpenTelemetry Trace ID | 全链路追踪 |
| **错误格式** | 不一致 | RFC 7807 Problem Details | 统一错误处理 |

---

## 5. 前端层对比 (Step13)

### 5.1 当前前端

```
frontend/
├── src/
│   ├── views/ (6个页面)
│   │   ├── TaskCreationView.vue      # 963行 — 创建任务表单
│   │   ├── TaskMonitorView.vue       # 817行 — 任务列表/状态
│   │   ├── SystemHealthView.vue      # 1024行 — 系统监控面板
│   │   ├── NovelPreviewView.vue      # 413行 — 小说预览
│   │   └── AboutView.vue             # 744行 — 关于页面
│   ├── components/
│   │   └── SystemHealthPanel.vue     # 839行 — 健康状态组件
│   ├── layouts/
│   │   └── MainLayout.vue            # 474行 — 主布局
│   ├── router/index.ts               # 5个路由
│   ├── services/api.ts               # 79行 — Axios简单封装
│   ├── utils/logger.ts               # 95行 — 前端日志
│   ├── main.ts                       # 25行
│   └── App.vue                       # 316行
├── package.json — 14个依赖
└── vite.config.ts — 基础配置
```

**当前前端特征:**
- Vue 3.4 + Composition API
- Element Plus UI组件库
- Tailwind CSS
- Axios HTTP客户端（3秒轮询刷新任务状态）
- 无状态管理（无Pinia store使用，仅创建了实例）
- 无WebSocket/SSE
- 无GraphQL
- 6个基础页面，功能导向

### 5.2 目标前端 (Step13)

```
frontend/ (Step13计划)
├── src/
│   ├── views/ (10+沉浸式工作空间)
│   │   ├── NovelStudio.vue           # 小说总览仪表盘
│   │   ├── WorldBuilder.vue          # 世界构建器（可视化）
│   │   ├── CharacterStudio.vue       # 角色工作室（卡片/图谱）
│   │   ├── OutlineEditor.vue         # 大纲编辑器（块级/TipTap）
│   │   ├── WritingStudio.vue         # 写作工作室（AI辅助编辑器）
│   │   ├── WorkflowCanvas.vue        # Agent工作流DAG编排
│   │   ├── AgentCommand.vue          # Agent命令面板
│   │   ├── ReviewCenter.vue          # 审阅中心（版本对比）
│   │   ├── KnowledgeExplorer.vue     # 知识探索（图谱/搜索）
│   │   ├── LogCenter.vue             # 日志中心（结构化查询）
│   │   └── SystemOps.vue             # 系统运维面板
│   ├── stores/ (Pinia)
│   │   ├── novelStore.ts             # 小说状态
│   │   ├── taskStore.ts              # 任务状态（WebSocket驱动）
│   │   ├── worldStore.ts             # 世界状态
│   │   ├── characterStore.ts         # 角色状态
│   │   ├── logStore.ts               # 日志状态
│   │   └── uiStore.ts                # UI状态
│   ├── composables/
│   │   ├── useWebSocket.ts           # WebSocket封装
│   │   ├── useSSE.ts                 # SSE封装
│   │   ├── useGraphQL.ts             # GraphQL客户端
│   │   └── useCommandPalette.ts      # 命令面板
│   ├── components/
│   │   ├── editor/ (TipTap块编辑器)
│   │   ├── graph/ (Vue Flow DAG)
│   │   ├── visualization/ (ECharts/D3)
│   │   ├── ai/ (AI辅助组件)
│   │   └── common/ (设计系统)
│   ├── design-system/
│   ├── graphql/
│   └── main.ts
```

**目标前端新增依赖 (Step13):**
```json
{
  "@tiptap/vue-3": "^2.x",
  "@vue-flow/core": "^1.x",
  "gsap": "^3.x",
  "@apollo/client": "^3.x",
  "zod": "^3.x",
  "date-fns": "^3.x",
  "fuse.js": "^7.x"
}
```

### 5.3 前端差距

| 维度 | 当前 | 目标 | 工作量 |
|-----|------|------|--------|
| 页面数量 | 6个功能页 | 10+工作空间 | 🔴 极大 |
| 设计理念 | 功能映射 | 用户旅程驱动 | 🔴 极大 |
| 状态管理 | 未使用Pinia | 6+个Pinia Store | 🟡 中 |
| 实时通信 | 3秒轮询 | WebSocket + SSE + 乐观更新 | 🔴 极大 |
| 编辑器 | Element Plus表单 | TipTap块级编辑器 | 🔴 极大 |
| 可视化 | ECharts基础图表 | Vue Flow DAG + D3图谱 + GSAP动画 | 🔴 极大 |
| 数据获取 | REST Axios | GraphQL + Zod验证 | 🟡 中 |
| 命令面板 | 无 | ⌘K全局命令面板 | 🟡 中 |
| 键盘导航 | 无 | 全键盘支持 | 🟡 中 |
| 设计系统 | Element Plus主题覆盖 | 自研设计系统 | 🟡 中 |
| 类型共享 | 无 | shared/types/ 前后端共享 | 🟡 中 |

---

## 6. 事件总线对比 (Step14)

### 6.1 当前事件总线

```python
# src/deepnovel/core/event_bus.py — 当前

class EventBus:
    """内存事件总线 — asyncio实现"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def publish(self, event: Event):
        """发布事件到内存队列"""
        await self._event_queue.put(event)

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件 — 内存引用"""
        self._subscribers[event_type].append(handler)
```

**当前问题:**
- 纯内存实现，进程重启事件丢失
- 无持久化，无法重放
- 无消费组，无法水平扩展
- 订阅者为函数引用，生命周期难管理

### 6.2 目标事件总线 (Redis Streams)

```python
# Step14 计划的 Redis Streams 事件总线

import redis.asyncio as redis
from redis.streams import StreamEntry

class RedisEventBus:
    """Redis Streams持久化事件总线"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stream_key = "deepnovel:events"
        self.consumer_group = "deepnovel-consumers"

    async def publish(self, event: Event) -> str:
        """发布事件到Redis Stream"""
        event_id = await self.redis.xadd(
            self.stream_key,
            fields={"data": event.model_dump_json()},
            maxlen=100000,  # 保留最近10万条
            approximate=True
        )
        return event_id

    async def subscribe(
        self,
        consumer_name: str,
        event_types: List[str],
        handler: Callable
    ):
        """消费组订阅 — 支持多个消费者"""
        await self.redis.xgroup_create(
            self.stream_key,
            self.consumer_group,
            id="0",  # 从开头消费
            mkstream=True
        )
        # 读取未确认消息...
```

### 6.3 事件总线差距

| 特性 | 当前 | 目标 | 影响 |
|-----|------|------|------|
| 持久化 | ❌ 内存，重启丢失 | ✅ Redis Streams持久化 | 任务状态可靠性 |
| 消费组 | ❌ 无 | ✅ 多消费者竞争消费 | 水平扩展 |
| 重放能力 | ❌ 无 | ✅ 可重放历史事件 | 调试/审计 |
| 跨服务 | ❌ 单进程内 | ✅ BFF + Python共享 | 微服务通信 |
| 积压处理 | ❌ 无限增长 | ✅ maxlen限制 + 死信队列 | 内存保护 |

---

## 7. Agent架构对比

### 7.1 当前Agent架构

```
src/deepnovel/agents/ (24个文件)
├── coordinator.py           # 1,294行 — 主协调器
├── content_generator.py     # 1,256行 — 内容生成
├── quality_checker.py       # 1,004行 — 质量检查
├── workflow_orchestrator.py # 工作流编排
├── enhanced_workflow_orchestrator.py # 增强编排
├── character_generator.py   # 角色生成
├── world_builder.py         # 世界构建
├── outline_planner.py       # 大纲规划
├── conflict_generator.py    # 冲突生成
├── hook_generator.py        # 钩子生成
├── chapter_summary.py       # 章节摘要
├── enhanced_communicator.py # 增强通信
├── agent_communicator.py    # Agent通信
├── agent_handlers.py        # 处理器
├── base.py                  # 基础类
├── implementations.py       # 实现
├── constants.py             # 常量
├── health_checker.py        # 健康检查
├── task_manager.py          # 任务管理
├── config_enhancer.py       # 配置增强
└── ... (其他)
```

**当前问题:**
- Agent之间直接函数调用，紧耦合
- 无Agent生命周期管理
- 无Agent状态持久化
- Coordinator 1,294行，职责过重
- 两个workflow_orchestrator（重复/冲突）

### 7.2 目标Agent架构 (Step14)

```
Python AI Engine:
├── agents/
│   ├── orchestrator.py      # Agent编排器（简化，Step5 TaskOrchestrator）
│   └── tools/               # @tool装饰器函数
│       ├── generate_content.py
│       ├── check_quality.py
│       └── research_facts.py
├── services/
│   ├── agent_service.py     # Agent业务逻辑
│   ├── llm_service.py       # LLM调用
│   └── rag_service.py       # RAG检索
└── domain/
    └── agents/              # Agent领域模型
```

**目标特征:**
- Agent作为Tool注册到Registry（Step8）
- 通过PromptComposer动态组装Prompt（Step9）
- TaskOrchestrator管理任务状态（Step5）
- 状态持久化到PostgreSQL

---

## 8. 基础设施对比 (Step15)

### 8.1 当前基础设施

| 项目 | 当前状态 | 问题 |
|-----|---------|------|
| Dockerfile | ❌ 不存在 | 无法容器化部署 |
| docker-compose | ✅ 仅基础设施服务 | 无应用服务编排 |
| CI/CD | ❌ 无 | 全手动部署 |
| 监控 | ❌ 无 | 无可见性 |
| 日志 | ❌ 文本文件 | 无结构化、无聚合 |
| 备份 | ❌ 无策略 | 数据风险 |
| 安全扫描 | ❌ 无 | CVE风险 |
| 部署脚本 | ⚠️ 碎片化 | .bat/.sh/.ps1互不兼容 |
| K8s | ❌ 无 | 无法扩展 |

### 8.2 目标基础设施 (Step15)

| 项目 | 目标状态 |
|-----|---------|
| Dockerfile | ✅ 3个多阶段Dockerfile（ai/bff/frontend）|
| docker-compose | ✅ Profile分层（dev/test/monitoring/full）|
| CI/CD | ✅ GitHub Actions六阶段流水线 |
| 监控 | ✅ Prometheus + Grafana + AlertManager |
| 日志 | ✅ Loki聚合 + OpenTelemetry Trace |
| 备份 | ✅ Restic自动化 + S3归档 |
| 安全扫描 | ✅ Trivy镜像扫描 + Falco运行时 |
| 部署脚本 | ✅ Taskfile跨平台统一 |
| K8s | ✅ Helm Chart + ArgoCD GitOps |

---

## 9. 技术栈版本对比

### 9.1 Python依赖

| 包 | 当前版本 | 目标版本 | 变更原因 |
|---|---------|---------|---------|
| fastapi | 0.109.0 | 0.115.x | 目标版有更好性能 |
| uvicorn | 0.27.0 | 0.30.x | 保持最新 |
| pydantic | 2.5.0 | 2.9.x | 目标版性能优化 |
| sqlalchemy | 2.0.25 | 2.0.x + sqlmodel | 新增ORM层 |
| chromadb | 0.4.24 | ❌ 移除 | 替换为Qdrant |
| qdrant-client | ❌ 未安装 | 1.x | 新增向量DB客户端 |
| redis | ❌ 未安装 | 5.x | 新增缓存/队列/事件总线 |
| celery | ❌ 未安装 | 5.4.x | 新增异步任务队列 |
| structlog | ❌ 未安装 | 24.x | 新增结构化日志 |
| opentelemetry | ❌ 未安装 | 1.25.x | 新增链路追踪 |
| gunicorn | ❌ 未安装 | 22.x | 生产WSGI服务器 |
| asyncpg | ❌ 未安装 | 0.29.x | PostgreSQL异步驱动 |
| pymysql | 1.1.0 | ❌ 移除 | MySQL替换为PostgreSQL |
| pymongo | 4.6.1 | ❌ 移除 | MongoDB替换为PostgreSQL JSONB |
| rocketmq-client-python | 2.0.0 | ❌ 移除 | 替换为Redis Streams |

### 9.2 Node.js依赖 (新增)

| 包 | 版本 | 用途 |
|---|------|------|
| @nestjs/core | 10.x | BFF框架 |
| @nestjs/graphql | 12.x | GraphQL支持 |
| @nestjs/websockets | 10.x | WebSocket网关 |
| @nestjs/platform-fastify | 10.x | HTTP服务器 |
| @prisma/client | 5.x | ORM |
| pino | 9.x | 结构化日志 |
| @opentelemetry/sdk-node | 1.x | 链路追踪 |

### 9.3 前端依赖变化

| 包 | 当前 | 目标 | 变更 |
|---|------|------|------|
| vue | 3.4.31 | 3.5.x | 升级 |
| @tiptap/vue-3 | ❌ | 2.x | 新增块编辑器 |
| @vue-flow/core | ❌ | 1.x | 新增DAG编排 |
| gsap | ❌ | 3.x | 新增动画 |
| @apollo/client | ❌ | 3.x | 新增GraphQL |
| zod | ❌ | 3.x | 新增类型验证 |
| pinia | 2.1.7 (未使用) | 2.2.x (实际使用) | 启用状态管理 |

---

## 10. 文件级变更清单

### 10.1 需要新建的文件 (>50个)

#### Docker/基础设施 (Step15)
```
Dockerfile.ai                              [NEW] — Python AI引擎容器
Dockerfile.bff                             [NEW] — NestJS BFF容器
Dockerfile.frontend                        [NEW] — Vue3前端容器
.dockerignore                              [NEW]
docker-bake.hcl                            [NEW] — BuildKit配置
docker-compose.yml                         [NEW] — 核心编排
docker-compose.override.yml                [NEW] — 开发覆盖
docker-compose.security.yml                [NEW] — 安全配置
docker-compose.backup.yml                  [NEW] — 备份编排
config/otel/otel-collector-config.yaml     [NEW]
config/prometheus/prometheus.yml           [NEW]
config/prometheus/alertmanager.yml         [NEW]
config/prometheus/rules/*.yml              [NEW] × 2
config/grafana/provisioning/               [NEW] — 自动化配置
config/grafana/dashboards/*.json           [NEW] × 4
config/loki/loki-config.yaml               [NEW]
config/falco/falco.yaml                    [NEW]
config/security/seccomp-*.json             [NEW] × 2
config/init/postgres/001_schema.sql        [NEW]
frontend/nginx.conf                        [NEW]
taskfile.yml                               [NEW]
scripts/validate-env.sh                    [NEW]
scripts/backup.sh                          [NEW]
scripts/restore.sh                         [NEW]
scripts/install.sh                         [NEW]
scripts/health-check.sh                    [NEW]
.github/workflows/ci-cd.yml                [NEW]
.github/workflows/security.yml             [NEW]
.github/dependabot.yml                     [NEW]
.releaserc.json                            [NEW]
k8s/                                       [NEW] — 完整K8s目录
```

#### NestJS BFF (Step14)
```
bff/                                       [NEW] — 完整NestJS项目
  ├── src/
  │   ├── main.ts
  │   ├── app.module.ts
  │   ├── auth/
  │   ├── common/
  │   ├── config/
  │   ├── core/
  │   │   ├── telemetry/
  │   │   ├── logger/
  │   │   └── exceptions/
  │   ├── modules/
  │   │   ├── novels/
  │   │   ├── tasks/
  │   │   ├── agents/
  │   │   ├── characters/
  │   │   ├── worlds/
  │   │   └── logs/
  │   └── gateways/
  │       ├── websocket.gateway.ts
  │       └── sse.gateway.ts
  ├── prisma/
  │   └── schema.prisma
  └── proto/
      └── ai_engine.proto
```

#### Python引擎重构 (Step1, Step14)
```
src/deepnovel/core/telemetry.py            [NEW] — OTel初始化
src/deepnovel/core/llm_router.py           [NEW] — 统一LLM路由（Step3）
src/deepnovel/prompts/composer.py          [NEW] — PromptComposer（Step9）
src/deepnovel/tools/registry.py            [NEW] — ToolRegistry（Step8）
src/deepnovel/tasks/orchestrator.py        [NEW] — TaskOrchestrator（Step5）
src/deepnovel/tasks/checkpoint.py          [NEW] — CheckpointManager
src/deepnovel/rag/engine.py                [NEW] — RAG引擎（Step6）
src/deepnovel/memory/manager.py            [NEW] — MemoryManager（Step2）
src/deepnovel/facts/manager.py             [NEW] — FactManager（Step4）
src/deepnovel/database/postgres_client.py  [NEW] — PostgreSQL客户端
src/deepnovel/database/qdrant_client.py    [NEW] — Qdrant客户端
alembic/                                   [NEW] — 数据库迁移
```

#### 前端重构 (Step13)
```
frontend/src/views/*.vue                   [NEW/重写] × 10+
frontend/src/stores/*.ts                   [NEW] × 6
frontend/src/composables/*.ts              [NEW] × 4
frontend/src/components/editor/            [NEW] — TipTap编辑器
frontend/src/components/graph/             [NEW] — Vue Flow
frontend/src/components/visualization/     [NEW] — 可视化
frontend/src/components/ai/                [NEW] — AI辅助
frontend/src/design-system/                [NEW]
frontend/src/graphql/                      [NEW]
```

### 10.2 需要修改的文件

```
src/deepnovel/model/entities.py            [MODIFY] — dataclass → SQLModel
src/deepnovel/database/orm.py              [MODIFY] — 自定义ORM → SQLModel适配层
src/deepnovel/database/mysql_client.py     [MODIFY] → 废弃标记
src/deepnovel/database/mongodb_client.py   [MODIFY] → 废弃标记
src/deepnovel/database/chromadb_client.py  [MODIFY] → 废弃标记
src/deepnovel/core/event_bus.py            [MODIFY] — 内存 → Redis Streams适配
src/deepnovel/utils/logger.py              [MODIFY] — 文本日志 → Structlog JSON
src/deepnovel/api/main.py                  [MODIFY] — 增加OTel、健康检查、指标端点
src/deepnovel/config/settings.py           [MODIFY] — 整合Step10 AppConfig
src/deepnovel/agents/coordinator.py        [MODIFY] — 简化，调用TaskOrchestrator
src/deepnovel/llm/router.py                [MODIFY] — 增加Tier路由（Step3）

config/.env.example                        [MODIFY] — 增加新环境变量
config/docker-compose.yaml                 [MODIFY] — 标记deprecated

docs/DEPLOYMENT.md                         [MODIFY] — 更新容器化部署指南
doc/06-部署流程文档.md                       [MODIFY] — 更新中文部署文档
```

### 10.3 需要废弃的文件

```
scripts/manage-server.sh                   [DEPRECATED] → Taskfile替代
scripts/restart-server.bat                 [DEPRECATED] → Taskfile替代
scripts/server-manager.ps1                 [DEPRECATED] → Taskfile替代
scripts/start_server_simple.py             [DEPRECATED] → docker compose up
scripts/run_server.py                      [DEPRECATED] → docker compose up

docker-images/*.tar                        [DEPRECATED] → 镜像仓库替代

src/deepnovel/database/mysql_client.py     [REMOVE after migration]
src/deepnovel/database/mongodb_client.py   [REMOVE after migration]
src/deepnovel/database/chromadb_client.py  [REMOVE after migration]
src/deepnovel/messaging/rocketmq_*.py      [REMOVE] — Redis Streams替代
```

---

## 11. 关键冲突与风险

### 11.1 技术风险

| 风险 | 等级 | 描述 | 缓解措施 |
|-----|------|------|---------|
| **数据库迁移** | 🔴 高 | MySQL+MongoDB → PostgreSQL JSONB，数据量未知 | 编写专用迁移脚本，双写验证 |
| **向量索引重建** | 🔴 高 | ChromaDB → Qdrant，所有向量需重新嵌入 | 保留ChromaDB运行，逐步迁移 |
| **前端重写** | 🔴 高 | 6页 → 10+工作空间，完全重写 | 分页面逐步替换，保留旧路由 |
| **NestJS学习曲线** | 🟡 中 | 团队需要TypeScript/NestJS技能 | 预留2周培训时间 |
| **消息队列替换** | 🟡 中 | RocketMQ → Redis Streams | 验证消息语义兼容性 |
| **性能回归** | 🟡 中 | 新增BFF层可能增加延迟 | gRPC + 缓存优化 |
| **依赖冲突** | 🟢 低 | 35+Python包升级 | 使用虚拟环境隔离测试 |

### 11.2 已发现的现有代码问题

```
1. config/docker-compose.yaml:84 — Neo4j配置拼写错误:
   "NEO4J_serveredbms_default listening address" → 应为 "NEO4J_dbms_default__listen__address"

2. src/deepnovel/api/main.py:77 — CORS安全隐患:
   allow_origins=["*"] → 生产环境必须限制域名

3. config/docker-compose.yaml — 多个服务使用 latest 标签:
   neo4j:latest, mongo:latest, chromadb/chroma:latest → 不可复现构建

4. src/deepnovel/database/orm.py — 自定义ORM基于sqlite3:
   计划使用PostgreSQL但ORM使用sqlite3 API → 不兼容

5. docker-compose.yaml volumes — 使用 bind mount:
   driver_opts: {type: none, device: ./data/...} → 不适合跨平台

6. requirements.txt — 无版本锁定文件:
   无 requirements.lock 或 poetry.lock → 构建不可复现
```

---

## 12. 实施优先级建议

### 12.1 分阶段实施路线图

基于差距分析，建议按以下优先级实施：

```
Phase 0: 准备工作 (1周)
├── 冻结现有功能开发
├── 创建 feature/refactor-2026 分支
├── 建立CI/CD基础流水线（仅lint + test）
└── 编写数据迁移脚本

Phase 1: 基础设施 (2-3周) — Step15
├── Dockerfile × 3 + docker-compose.yml
├── PostgreSQL + Qdrant + Redis 基础设施
├── Taskfile + 环境验证脚本
└── 保留MySQL/MongoDB/ChromaDB并行运行

Phase 2: 数据层迁移 (3-4周) — Step1
├── SQLModel模型定义
├── Alembic迁移脚本
├── 双写模式（旧系统写MySQL+MongoDB，新系统写PostgreSQL）
├── 数据一致性校验
└── 切换读流量到新数据库

Phase 3: Python后端重构 (4-5周) — Step2-10
├── 核心模块重构（EventBus → Redis Streams, Logger → Structlog）
├── Agent简化（24个 → 核心编排器 + Tool Registry）
├── LLM Router升级（Tier支持）
└── RAG引擎（Qdrant集成）

Phase 4: NestJS BFF (3-4周) — Step14
├── BFF项目初始化
├── Prisma Schema定义
├── gRPC proto定义
├── REST/GraphQL/WebSocket实现
└── Python引擎gRPC服务

Phase 5: 前端重构 (4-5周) — Step13
├── 设计系统搭建
├── Pinia Store实现
├── 页面逐个替换
├── WebSocket/SSE接入
└── GraphQL集成

Phase 6: 可观测性与安全 (2周) — Step15
├── OpenTelemetry全链路接入
├── Grafana面板部署
├── 告警规则配置
├── Trivy扫描集成
└── 安全加固

Phase 7: 生产部署 (2周)
├── K8s部署
├── 数据备份策略
├── 性能压测
├── 灰度发布
└── 旧系统下线

总工期: 约 21-25 周 (5-6个月)
```

### 12.2 建议的MVP路径

如果无法承受全量重构，建议MVP路径：

```
MVP目标: 最小可用升级，保留现有架构，提升关键能力

1. Week 1-2: 容器化
   - Dockerfile.ai + docker-compose.yml（仅现有服务）
   - 无NestJS BFF，前端直连Python

2. Week 3-4: 数据库渐进迁移
   - PostgreSQL新增，MySQL保留
   - 新功能使用PostgreSQL

3. Week 5-6: 前端体验提升
   - 保留6个页面，增加WebSocket实时推送
   - Pinia状态管理

4. Week 7-8: 可观测性
   - OpenTelemetry + Grafana
   - 结构化日志

MVP后评估是否继续全量重构
```

---

## 13. 总结

### 13.1 统计摘要

| 指标 | 数值 |
|-----|------|
| 现有Python代码行数 | 47,385 |
| 现有前端代码行数 | 5,930 |
| 现有测试代码行数 | 8,185 |
| 计划新增文件数 | 80+ |
| 计划修改文件数 | 15+ |
| 计划废弃文件数 | 10+ |
| 重构步骤数 | 15个Step |
| 涉及技术栈变更 | Python/Node/Vue/Docker/K8s |
| 预估总工期 | 21-25周 |

### 13.2 核心结论

1. **架构代差巨大**: 当前单体FastAPI与目标微服务架构存在根本性差异，不是渐进式优化，而是**平台级重写**

2. **数据迁移是最大风险**: 4个数据库(MySQL+MongoDB+Neo4j+ChromaDB)的迁移涉及数据一致性、向量索引重建、查询语法转换

3. **前端完全重写**: 当前6个基础页面与目标10+沉浸式工作空间的差距无法通过增量修改弥补

4. **团队技能要求**: 需要TypeScript/NestJS/GraphQL/Prisma/SQLModel等新技能栈

5. **价值与成本权衡**: 全量重构5-6个月 vs MVP升级2个月，建议根据业务紧迫度选择路径

6. **文档资产丰厚**: Step1-15提供了极其详细的实施指南，这是重大优势，可降低实施风险
