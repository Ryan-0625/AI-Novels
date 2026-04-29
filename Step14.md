# Step 14: 后端API全面重构 — NestJS BFF网关 + Python AI引擎微服务架构

> 版本: 1.0
> 日期: 2026-04-29
> 依赖: Step1-13 (全栈)
> 目标: 从单体FastAPI升级为现代化微服务架构，匹配前端Step13的实时通信与类型安全需求
> 核心转变: 单体Python后端 → NestJS BFF网关 + Python AI引擎微服务

---

## 1. 设计哲学

### 1.1 为什么必须重构

```
当前后端状态诊断:

❌ 单体架构                    → API/Agent/Config/RAG全部耦合在一个进程中
❌ 无实时通信                  → 前端3秒轮询，WebSocket/SSE完全缺失
❌ 内存状态管理                → 任务状态存在Dict中，重启丢失，无法水平扩展
❌ 文本日志                    → 前端LogCenter需要结构化JSON日志，当前是文本
❌ 无链路追踪                  → 一个请求经过Agent→LLM→DB，无法追踪全链路
❌ 无类型共享                  → 前端Zod + 后端Pydantic，各自维护，不同步
❌ 无消息队列                  → 长任务阻塞API线程，无异步处理
❌ 数据库访问混乱              → 5种数据库各自为政，无统一ORM/Repository层
❌ 无缓存层                    → LLM调用、RAG检索、配置读取均无缓存
❌ 无GraphQL                   → 前端需要灵活查询（如"同时获取小说+角色+世界"），REST需多次请求
```

### 1.2 核心架构决策

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          前端 (Step13)                                       │
│              Vue3 + TypeScript + WebSocket + GraphQL/REST                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     BFF API Gateway (NestJS + TypeScript)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ REST API     │  │ GraphQL      │  │ WebSocket    │  │ SSE Event Stream │  │
│  │ Controller   │  │ Resolver     │  │ Gateway      │  │ Endpoint         │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth/JWT     │  │ Rate Limit   │  │ Cache        │  │ Structured Logs  │  │
│  │ Service      │  │ Service      │  │ Service      │  │ (Pino)           │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Service Layer (聚合多个Python微服务的API调用)                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │ gRPC/HTTP     │ Redis Pub/Sub │ Message Queue
                    ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Python AI Engine (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Agent        │  │ LLM Router   │  │ RAG Engine   │  │ World Simulation │  │
│  │ Orchestrator │  │ Service      │  │ Service      │  │ Service          │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Task         │  │ Memory       │  │ Fact         │  │ Prompt           │  │
│  │ Scheduler    │  │ Manager      │  │ Manager      │  │ Composer         │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐
│ PostgreSQL  │  │ Redis    │  │ Qdrant       │  │ Neo4j       │  │ MinIO    │
│ (主数据库)   │  │ (缓存/队列)│  │ (向量数据库)  │  │ (图数据库)   │  │ (文件存储) │
└─────────────┘  └──────────┘  └──────────────┘  └─────────────┘  └──────────┘
```

### 1.3 行业前沿参考

| 架构模式 | 参考来源 | 在本项目中的应用 |
|---------|---------|---------------|
| **BFF (Backend for Frontend)** | Netflix, SoundCloud | NestJS网关聚合多个Python服务，为前端提供统一API |
| **CQRS + Event Sourcing** | EventStoreDB, Axon | 任务状态变更通过事件驱动，支持回放和审计 |
| **GraphQL Federation** | Apollo, Netflix | 单一GraphQL端点聚合多个服务的Schema |
| **gRPC + Protocol Buffers** | Google, Kubernetes | BFF与Python引擎间高性能通信 |
| **Structured Logging + OTel** | Grafana, Datadog | Pino结构化日志 + OpenTelemetry链路追踪 |
| **Async Task Queue** | Celery, RQ, Bull | 长任务（小说生成）放入队列异步执行 |
| **WebSocket Gateway** | Socket.io, ws | NestJS Gateway管理所有前端实时连接 |
| **Redis Streams** | Redis 5.0+ | 事件总线替代内存EventBus，支持持久化和消费组 |

---

## 2. 技术栈选型决策

### 2.1 为什么不是"纯Python升级"

考虑过在Python生态内升级（FastAPI + Celery + Socket.IO + Structlog），但最终选择引入NestJS BFF：

| 对比维度 | 纯Python升级 | NestJS BFF + Python引擎 |
|---------|-----------|------------------------|
| 开发语言 | Python单一 | TypeScript(BFF) + Python(引擎) |
| 前后端类型共享 | ❌ 各自维护 | ✅ `shared/`目录共享DTS/Protobuf |
| WebSocket体验 | socket.io-py一般 | NestJS @Gateway极致 |
| GraphQL生态 | Strawberry较小 | NestJS @nestjs/graphql成熟 |
| 微服务治理 | 无成熟方案 | NestJS微服务模块完善 |
| 社区活跃度 | FastAPI活跃 | NestJS + TypeScript更活跃 |
| 招聘/协作 | Python后端 | TypeScript全栈更通用 |
| 核心逻辑重写 | 不需要 | 不需要（Python保留） |
| 部署复杂度 | 低（单一进程） | 中（两个服务） |
| AI生态 | Python最佳 | Python保留，不受影响 |

**关键决策**: Python AI核心（约80%代码）保留，仅将API层（约20%代码）迁移到NestJS。

### 2.2 BFF层技术栈 (NestJS)

```typescript
// package.json (backend/bff/)
{
  "name": "ai-novels-bff",
  "version": "2.0.0",
  "dependencies": {
    // NestJS核心
    "@nestjs/common": "^10.3.0",
    "@nestjs/core": "^10.3.0",
    "@nestjs/platform-express": "^10.3.0",
    "@nestjs/platform-socket.io": "^10.3.0",
    "@nestjs/platform-fastify": "^10.3.0",
    "@nestjs/websockets": "^10.3.0",
    "@nestjs/graphql": "^12.1.0",
    "@nestjs/apollo": "^12.1.0",
    "@nestjs/microservices": "^10.3.0",
    "@nestjs/config": "^3.1.0",
    "@nestjs/swagger": "^7.3.0",
    "@nestjs/terminus": "^10.2.0",
    "@nestjs/throttler": "^5.1.0",
    "@nestjs/cache-manager": "^2.2.0",
    "@nestjs/jwt": "^10.2.0",
    "@nestjs/passport": "^10.0.0",
    
    // GraphQL
    "apollo-server-express": "^3.13.0",
    "graphql": "^16.8.0",
    "graphql-subscriptions": "^2.0.0",
    "class-validator": "^0.14.1",
    "class-transformer": "^0.5.1",
    
    // gRPC通信
    "@grpc/grpc-js": "^1.10.0",
    "@grpc/proto-loader": "^0.7.10",
    
    // 数据库/缓存
    "@prisma/client": "^5.10.0",
    "prisma": "^5.10.0",
    "redis": "^4.6.0",
    "ioredis": "^5.3.0",
    "cache-manager": "^5.4.0",
    "cache-manager-redis-store": "^3.0.0",
    
    // 消息队列
    "bullmq": "^5.4.0",
    
    // 日志/可观测性
    "pino": "^8.19.0",
    "pino-pretty": "^10.3.0",
    "nestjs-pino": "^4.0.0",
    "@opentelemetry/api": "^1.8.0",
    "@opentelemetry/sdk-node": "^0.48.0",
    "@opentelemetry/auto-instrumentations-node": "^0.41.0",
    
    // 工具
    "reflect-metadata": "^0.2.1",
    "rxjs": "^7.8.1",
    "zod": "^3.22.4",
    "uuid": "^9.0.1",
    "luxon": "^3.4.4",
    "nanoid": "^5.0.6"
  }
}
```

### 2.3 Python AI引擎升级技术栈

```python
# pyproject.toml (backend/engine/)
[project]
name = "ai-novels-engine"
version = "2.0.0"
dependencies = [
    # FastAPI + ASGI
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "python-socketio>=5.11.0",
    "python-multipart>=0.0.9",
    
    # Pydantic + Settings
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "email-validator>=2.1.0",
    
    # ORM + Database
    "sqlmodel>=0.0.16",
    "asyncpg>=0.29.0",
    "aiomysql>=0.2.0",
    "motor>=3.3.0",
    "neo4j>=5.18.0",
    
    # Vector DB
    "qdrant-client>=1.7.0",
    
    # Cache
    "redis>=5.0.0",
    "cachetools>=5.3.0",
    
    # Message Queue
    "celery>=5.3.0",
    "kombu>=5.3.0",
    
    # gRPC
    "grpcio>=1.60.0",
    "grpcio-tools>=1.60.0",
    
    # Structured Logging
    "structlog>=24.1.0",
    "python-json-logger>=2.0.7",
    
    # Observability
    "opentelemetry-api>=1.22.0",
    "opentelemetry-sdk>=1.22.0",
    "opentelemetry-instrumentation-fastapi>=0.43b0",
    "opentelemetry-instrumentation-redis>=0.43b0",
    "opentelemetry-exporter-otlp>=1.22.0",
    
    # LLM
    "openai>=1.12.0",
    "ollama>=0.1.6",
    "google-generativeai>=0.3.2",
    "httpx>=0.27.0",
    "aiohttp>=3.9.0",
    
    # Utils
    "python-dotenv>=1.0.0",
    "tenacity>=8.2.0",
    "orjson>=3.9.0",
    "ujson>=5.9.0",
]
```

### 2.4 共享类型定义 (`shared/`)

```
shared/
├── types/
│   ├── novel.ts           # 前端 + BFF + Python（通过codegen）
│   ├── world.ts
│   ├── character.ts
│   ├── task.ts
│   ├── agent.ts
│   ├── log.ts
│   ├── config.ts
│   └── index.ts
├── schema/
│   ├── novel.proto        # gRPC Proto定义
│   ├── task.proto
│   └── agent.proto
├── codegen/
│   └── python/            # 从TS类型生成Python Pydantic模型
└── package.json
```

**类型共享策略**:
- **TS端**: Zod schema作为单一真相源，从Zod infer类型
- **Python端**: 使用 `zod-to-pydantic` 或手动同步，或从Protobuf生成
- **gRPC**: Proto文件作为跨语言契约

---

## 3. 现状深度诊断

### 3.1 当前后端架构问题

```
当前架构层级评估:

API Layer (api/)
├── main.py          ⚠️  全局异常处理缺失traceId注入
├── routes.py        ⚠️  所有路由平铺，无版本控制，无模块划分
├── controllers.py   ⚠️  业务逻辑与数据访问耦合，无Service层
└── middleware.py    ✅  相对完善（RequestID/Timing/Logging/RateLimit）

Problem: API层缺乏模块化、版本控制、GraphQL、WebSocket

Business Layer (agents/)
├── coordinator.py        ⚠️  1280行单体，内存状态，无持久化
├── task_manager.py       ⚠️  内存任务队列，重启丢失
├── base.py               ⚠️  硬编码8个工具，无动态工具注册
├── *_generator.py        ⚠️  各Agent各自为政，无统一编排接口
└── workflow_orchestrator.py ⚠️  未使用，与coordinator重叠

Problem: 业务层无Service/Repository分层，状态管理混乱

Data Layer (database/)
├── mysql_client.py       ⚠️  同步驱动，无连接池优化
├── mongodb_client.py     ⚠️  基础封装，无ORM
├── neo4j_client.py       ⚠️  基础封装
├── chromadb_client.py    ❌  MD5假Embedding + reset()删数据
└── base.py               ⚠️  无统一接口

Problem: 5种数据库无统一抽象，无ORM，异步支持不足

Config Layer (config/)
├── manager.py            ⚠️  配置加载分散，无类型安全
├── settings.py           ⚠️  懒加载逻辑重复3次
├── validator.py          ⚠️  JSON Schema手动维护
└── loader.py             ⚠️  与utils/config_loader.py重复

Problem: 无Pydantic v2统一配置，无环境变量映射
```

### 3.2 前端需求与后端能力缺口

| 前端Step13需求 | 当前后端能力 | 缺口 |
|--------------|-----------|------|
| WebSocket实时推送 | ❌ 完全缺失 | 需要NestJS Gateway + Redis Pub/Sub |
| SSE备用通道 | ❌ 完全缺失 | 需要FastAPI/NestJS SSE端点 |
| GraphQL灵活查询 | ❌ 完全缺失 | 需要Apollo/Strawberry |
| 结构化JSON日志 | ❌ 文本日志 | 需要Pino/Structlog + traceId/spanId |
| 链路追踪 | ❌ 完全缺失 | 需要OpenTelemetry |
| 任务队列持久化 | ❌ 内存Dict | 需要Redis + Bullmq/Celery |
| API版本控制 | ❌ 无版本 | 需要 `/v1/` `/v2/` 或GraphQL |
| 类型共享 | ❌ 各自维护 | 需要 `shared/` + Zod/Protobuf |
| 缓存层 | ❌ 完全缺失 | 需要Redis Cache |
| 统一ORM | ❌ 无ORM | 需要Prisma/SQLModel |

---

## 4. BFF层架构设计 (NestJS)

### 4.1 项目结构

```
backend/bff/
├── src/
│   ├── main.ts                          # 应用入口
│   ├── app.module.ts                    # 根模块
│   ├── config/
│   │   ├── app.config.ts               # 应用配置
│   │   ├── database.config.ts          # 数据库配置
│   │   ├── redis.config.ts             # Redis配置
│   │   └── grpc.config.ts              # gRPC配置
│   ├── modules/
│   │   ├── auth/                        # 认证模块
│   │   │   ├── auth.module.ts
│   │   │   ├── auth.controller.ts
│   │   │   ├── auth.service.ts
│   │   │   ├── auth.guard.ts
│   │   │   ├── auth.strategy.ts
│   │   │   └── dto/
│   │   ├── novel/                       # 小说模块
│   │   │   ├── novel.module.ts
│   │   │   ├── novel.controller.ts      # REST API
│   │   │   ├── novel.resolver.ts        # GraphQL
│   │   │   ├── novel.service.ts
│   │   │   ├── novel.gateway.ts         # WebSocket
│   │   │   └── dto/
│   │   ├── world/                       # 世界模块
│   │   ├── character/                   # 角色模块
│   │   ├── outline/                     # 大纲模块
│   │   ├── chapter/                     # 章节模块
│   │   ├── task/                        # 任务模块
│   │   ├── agent/                       # Agent模块
│   │   ├── workflow/                    # 工作流模块
│   │   ├── knowledge/                   # 知识库模块
│   │   ├── log/                         # 日志模块
│   │   ├── config/                      # 配置模块
│   │   └── system/                      # 系统模块
│   ├── gateway/
│   │   ├── app.gateway.ts               # 根WebSocket网关
│   │   ├── task.gateway.ts              # 任务实时推送
│   │   ├── agent.gateway.ts             # Agent对话推送
│   │   ├── log.gateway.ts               # 日志实时流
│   │   └── system.gateway.ts            # 系统健康推送
│   ├── graphql/
│   │   ├── schema.gql                   # 自动生成的Schema
│   │   ├── scalars/
│   │   │   ├── date.scalar.ts
│   │   │   └── json.scalar.ts
│   │   └── directives/
│   ├── grpc/
│   │   ├── client/
│   │   │   ├── engine.client.ts         # Python引擎gRPC客户端
│   │   │   └── health.client.ts
│   │   └── proto/
│   │       ├── novel.proto
│   │       ├── task.proto
│   │       └── agent.proto
│   ├── services/
│   │   ├── engine.service.ts            # Python引擎HTTP调用封装
│   │   ├── cache.service.ts             # Redis缓存封装
│   │   ├── event-bus.service.ts         # Redis Streams事件总线
│   │   ├── logger.service.ts            # Pino日志封装
│   │   └── tracer.service.ts            # OpenTelemetry封装
│   ├── interceptors/
│   │   ├── logging.interceptor.ts       # 请求日志拦截
│   │   ├── timing.interceptor.ts        # 耗时监控拦截
│   │   ├── transform.interceptor.ts     # 响应标准化拦截
│   │   └── tracing.interceptor.ts       # 链路追踪拦截
│   ├── filters/
│   │   ├── http-exception.filter.ts     # HTTP异常过滤器
│   │   ├── ws-exception.filter.ts       # WebSocket异常过滤器
│   │   └── graphql-exception.filter.ts  # GraphQL异常过滤器
│   ├── pipes/
│   │   ├── validation.pipe.ts           # Zod验证管道
│   │   └── transform.pipe.ts            # 数据转换管道
│   ├── decorators/
│   │   ├── current-user.decorator.ts
│   │   ├── roles.decorator.ts
│   │   └── public.decorator.ts
│   ├── common/
│   │   ├── dto/
│   │   │   ├── pagination.dto.ts
│   │   │   ├── sort.dto.ts
│   │   │   └── api-response.dto.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   └── utils/
│   │       └── index.ts
│   └── prisma/
│       ├── schema.prisma                # 数据库Schema
│       └── seed.ts                      # 种子数据
├── shared/
│   └── types/                           # 与前端共享的类型
│       ├── novel.ts
│       ├── world.ts
│       └── index.ts
├── proto/                               # gRPC Proto文件
│   ├── novel.proto
│   ├── task.proto
│   └── agent.proto
├── test/
├── prisma/
│   └── schema.prisma
├── Dockerfile
├── docker-compose.yml
├── nest-cli.json
├── tsconfig.json
└── package.json
```

### 4.2 核心模块实现

#### 4.2.1 根模块与配置

```typescript
// src/app.module.ts
import { Module } from '@nestjs/common'
import { ConfigModule } from '@nestjs/config'
import { GraphQLModule } from '@nestjs/graphql'
import { ApolloDriver, ApolloDriverConfig } from '@nestjs/apollo'
import { BullModule } from '@nestjs/bullmq'
import { CacheModule } from '@nestjs/cache-manager'
import { redisStore } from 'cache-manager-redis-yet'
import { LoggerModule } from 'nestjs-pino'

import { appConfig, databaseConfig, redisConfig } from './config'

// 业务模块
import { AuthModule } from './modules/auth/auth.module'
import { NovelModule } from './modules/novel/novel.module'
import { WorldModule } from './modules/world/world.module'
import { CharacterModule } from './modules/character/character.module'
import { TaskModule } from './modules/task/task.module'
import { AgentModule } from './modules/agent/agent.module'
import { WorkflowModule } from './modules/workflow/workflow.module'
import { LogModule } from './modules/log/log.module'
import { KnowledgeModule } from './modules/knowledge/knowledge.module'
import { SystemModule } from './modules/system/system.module'

// 网关
import { AppGateway } from './gateway/app.gateway'

// 服务
import { EngineService } from './services/engine.service'
import { EventBusService } from './services/event-bus.service'
import { TracerService } from './services/tracer.service'

@Module({
  imports: [
    // 配置
    ConfigModule.forRoot({
      isGlobal: true,
      load: [appConfig, databaseConfig, redisConfig],
    }),
    
    // GraphQL
    GraphQLModule.forRoot<ApolloDriverConfig>({
      driver: ApolloDriver,
      autoSchemaFile: 'src/graphql/schema.gql',
      sortSchema: true,
      subscriptions: {
        'graphql-ws': true,
        'subscriptions-transport-ws': true,
      },
      context: ({ req, connection }) => {
        return { req, connection }
      },
      formatError: (error) => {
        return {
          message: error.message,
          code: error.extensions?.code || 'INTERNAL_SERVER_ERROR',
          requestId: error.extensions?.requestId,
        }
      },
    }),
    
    // 消息队列
    BullModule.forRootAsync({
      useFactory: (configService: ConfigService) => ({
        connection: {
          host: configService.get('redis.host'),
          port: configService.get('redis.port'),
        },
        defaultJobOptions: {
          removeOnComplete: 100,
          removeOnFail: 50,
          attempts: 3,
          backoff: { type: 'exponential', delay: 5000 },
        },
      }),
      inject: [ConfigService],
    }),
    
    // 缓存
    CacheModule.registerAsync({
      isGlobal: true,
      useFactory: async (configService: ConfigService) => ({
        store: await redisStore({
          socket: {
            host: configService.get('redis.host'),
            port: configService.get('redis.port'),
          },
          ttl: 60 * 5, // 5分钟默认TTL
        }),
      }),
      inject: [ConfigService],
    }),
    
    // 结构化日志
    LoggerModule.forRoot({
      pinoHttp: {
        level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
        transport: process.env.NODE_ENV !== 'production'
          ? { target: 'pino-pretty', options: { colorize: true } }
          : undefined,
        serializers: {
          req: (req) => ({
            id: req.id,
            method: req.method,
            url: req.url,
          }),
        },
      },
    }),
    
    // 业务模块
    AuthModule,
    NovelModule,
    WorldModule,
    CharacterModule,
    TaskModule,
    AgentModule,
    WorkflowModule,
    LogModule,
    KnowledgeModule,
    SystemModule,
  ],
  providers: [AppGateway, EngineService, EventBusService, TracerService],
})
export class AppModule {}
```

#### 4.2.2 WebSocket Gateway

```typescript
// src/gateway/app.gateway.ts
import {
  WebSocketGateway,
  WebSocketServer,
  OnGatewayConnection,
  OnGatewayDisconnect,
  SubscribeMessage,
} from '@nestjs/websockets'
import { Server, Socket } from 'socket.io'
import { Logger } from '@nestjs/common'
import { InjectPinoLogger, PinoLogger } from 'nestjs-pino'

@WebSocketGateway({
  namespace: '/',
  cors: { origin: '*' }, // 生产环境限制具体域名
  transports: ['websocket', 'polling'],
})
export class AppGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server

  private readonly logger = new Logger(AppGateway.name)

  constructor(
    @InjectPinoLogger(AppGateway.name) private readonly pinoLogger: PinoLogger,
  ) {}

  handleConnection(client: Socket) {
    this.pinoLogger.info({ socketId: client.id }, 'Client connected')
  }

  handleDisconnect(client: Socket) {
    this.pinoLogger.info({ socketId: client.id }, 'Client disconnected')
  }

  // 广播事件到所有客户端
  broadcast(event: string, data: unknown) {
    this.server.emit(event, data)
  }

  // 发送到特定房间
  emitToRoom(room: string, event: string, data: unknown) {
    this.server.to(room).emit(event, data)
  }

  // 发送到特定客户端
  emitToClient(clientId: string, event: string, data: unknown) {
    this.server.to(clientId).emit(event, data)
  }
}
```

```typescript
// src/gateway/task.gateway.ts
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  MessageBody,
  ConnectedSocket,
} from '@nestjs/websockets'
import { Server, Socket } from 'socket.io'
import { UseGuards } from '@nestjs/common'
import { WsJwtGuard } from '../modules/auth/guards/ws-jwt.guard'
import { EventBusService } from '../services/event-bus.service'

@WebSocketGateway({ namespace: '/tasks' })
@UseGuards(WsJwtGuard)
export class TaskGateway {
  @WebSocketServer()
  server: Server

  constructor(private readonly eventBus: EventBusService) {
    // 订阅Redis事件，转发到WebSocket
    this.eventBus.subscribe('task:*', (channel, message) => {
      const event = channel.replace('task:', '')
      const data = JSON.parse(message)
      // 发送到该任务的房间
      this.server.to(`task:${data.taskId}`).emit(event, data)
    })
  }

  @SubscribeMessage('task:subscribe')
  handleSubscribe(
    @MessageBody() data: { taskId: string },
    @ConnectedSocket() client: Socket,
  ) {
    client.join(`task:${data.taskId}`)
    return { success: true, taskId: data.taskId }
  }

  @SubscribeMessage('task:unsubscribe')
  handleUnsubscribe(
    @MessageBody() data: { taskId: string },
    @ConnectedSocket() client: Socket,
  ) {
    client.leave(`task:${data.taskId}`)
    return { success: true }
  }
}
```

#### 4.2.3 GraphQL Resolver

```typescript
// src/modules/novel/novel.resolver.ts
import { Resolver, Query, Mutation, Subscription, Args } from '@nestjs/graphql'
import { PubSub } from 'graphql-subscriptions'
import { NovelService } from './novel.service'
import { Novel } from './entities/novel.entity'
import { CreateNovelInput } from './dto/create-novel.input'
import { UpdateNovelInput } from './dto/update-novel.input'

const pubSub = new PubSub()

@Resolver(() => Novel)
export class NovelResolver {
  constructor(private readonly novelService: NovelService) {}

  @Query(() => [Novel], { name: 'novels' })
  async findAll(
    @Args('pagination', { nullable: true }) pagination?: PaginationInput,
    @Args('filter', { nullable: true }) filter?: NovelFilterInput,
  ) {
    return this.novelService.findAll(pagination, filter)
  }

  @Query(() => Novel, { name: 'novel' })
  async findOne(@Args('id') id: string) {
    return this.novelService.findOne(id)
  }

  @Mutation(() => Novel)
  async createNovel(@Args('input') input: CreateNovelInput) {
    const novel = await this.novelService.create(input)
    pubSub.publish('novelCreated', { novelCreated: novel })
    return novel
  }

  @Mutation(() => Novel)
  async updateNovel(
    @Args('id') id: string,
    @Args('input') input: UpdateNovelInput,
  ) {
    const novel = await this.novelService.update(id, input)
    pubSub.publish('novelUpdated', { novelUpdated: novel })
    return novel
  }

  @Subscription(() => Novel, { name: 'novelCreated' })
  novelCreated() {
    return pubSub.asyncIterator('novelCreated')
  }

  @Subscription(() => Novel, { name: 'novelUpdated' })
  novelUpdated() {
    return pubSub.asyncIterator('novelUpdated')
  }
}
```

#### 4.2.4 与Python引擎通信 (gRPC)

```typescript
// src/grpc/client/engine.client.ts
import { Injectable, OnModuleInit } from '@nestjs/common'
import { ClientGrpc } from '@nestjs/microservices'
import { Inject } from '@nestjs/common'
import { lastValueFrom } from 'rxjs'
import { NovelService as NovelGrpcService } from '../proto/novel'

@Injectable()
export class EngineClient implements OnModuleInit {
  private novelService: NovelGrpcService

  constructor(
    @Inject('ENGINE_PACKAGE') private readonly client: ClientGrpc,
  ) {}

  onModuleInit() {
    this.novelService = this.client.getService<NovelGrpcService>('NovelService')
  }

  async generateChapter(data: {
    novelId: string
    chapterNumber: number
    config: Record<string, unknown>
  }) {
    const response = await lastValueFrom(
      this.novelService.generateChapter(data),
    )
    return response
  }

  async getWorldGraph(worldId: string) {
    const response = await lastValueFrom(
      this.novelService.getWorldGraph({ worldId }),
    )
    return response
  }
}
```

### 4.3 中间件与拦截器

```typescript
// src/interceptors/tracing.interceptor.ts
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common'
import { Observable } from 'rxjs'
import { tap } from 'rxjs/operators'
import { trace, context } from '@opentelemetry/api'
import { v4 as uuidv4 } from 'uuid'

@Injectable()
export class TracingInterceptor implements NestInterceptor {
  intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown> {
    const request = ctx.switchToHttp().getRequest()
    const requestId = request.headers['x-request-id'] || uuidv4()
    
    // 创建OpenTelemetry span
    const tracer = trace.getTracer('ai-novels-bff')
    const span = tracer.startSpan(`${request.method} ${request.url}`)
    span.setAttribute('http.method', request.method)
    span.setAttribute('http.url', request.url)
    span.setAttribute('http.request_id', requestId)

    // 注入trace context到请求头（传递给Python引擎）
    const carrier = {}
    trace.getSpanContext(context.active())
    // ... propagation

    return next.handle().pipe(
      tap({
        next: () => {
          span.setAttribute('http.status_code', 200)
          span.end()
        },
        error: (error) => {
          span.setAttribute('error', true)
          span.setAttribute('error.message', error.message)
          span.end()
        },
      }),
    )
  }
}
```

---

## 5. Python AI引擎重构

### 5.1 项目结构

```
backend/engine/
├── src/
│   ├── main.py                          # FastAPI应用入口
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                      # 依赖注入
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py               # API路由聚合
│   │   │   ├── endpoints/
│   │   │   │   ├── novel.py
│   │   │   │   ├── world.py
│   │   │   │   ├── character.py
│   │   │   │   ├── task.py
│   │   │   │   ├── agent.py
│   │   │   │   ├── rag.py
│   │   │   │   └── health.py
│   │   │   └── websocket/
│   │   │       ├── task_ws.py
│   │   │       └── agent_ws.py
│   │   └── grpc/
│   │       ├── server.py               # gRPC服务
│   │       └── services/
│   │           ├── novel_service.py
│   │           ├── task_service.py
│   │           └── agent_service.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Pydantic Settings
│   │   ├── events.py                    # 事件总线（Redis Streams）
│   │   ├── exceptions.py                # 自定义异常
│   │   ├── logging.py                   # Structlog配置
│   │   ├── tracing.py                   # OpenTelemetry配置
│   │   └── security.py                  # 安全工具
│   ├── services/                        # 业务服务层
│   │   ├── __init__.py
│   │   ├── novel_service.py
│   │   ├── world_service.py
│   │   ├── character_service.py
│   │   ├── task_service.py
│   │   ├── agent_orchestrator.py        # 重构后的编排器
│   │   ├── llm_service.py
│   │   ├── rag_service.py
│   │   ├── memory_service.py
│   │   └── fact_service.py
│   ├── repositories/                    # 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py                      # 抽象基类
│   │   ├── novel_repo.py
│   │   ├── world_repo.py
│   │   ├── character_repo.py
│   │   ├── task_repo.py
│   │   ├── memory_repo.py
│   │   └── fact_repo.py
│   ├── models/                          # Pydantic v2模型
│   │   ├── __init__.py
│   │   ├── novel.py
│   │   ├── world.py
│   │   ├── character.py
│   │   ├── task.py
│   │   ├── agent.py
│   │   ├── config.py
│   │   └── log.py
│   ├── domain/                          # 领域模型（DDD）
│   │   ├── __init__.py
│   │   ├── novel/
│   │   │   ├── __init__.py
│   │   │   ├── entity.py
│   │   │   ├── value_objects.py
│   │   │   └── events.py
│   │   ├── world/
│   │   │   ├── entity.py
│   │   │   ├── value_objects.py
│   │   │   └── events.py
│   │   └── task/
│   │       ├── entity.py
│   │       ├── value_objects.py
│   │       └── events.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py           # 统一连接管理
│   │   │   ├── postgres.py            # PostgreSQL
│   │   │   ├── mongodb.py             # MongoDB
│   │   │   ├── neo4j.py               # Neo4j
│   │   │   └── qdrant.py              # Qdrant向量数据库
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── redis_cache.py
│   │   ├── queue/
│   │   │   ├── __init__.py
│   │   │   └── celery_app.py
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── adapters/
│   │           ├── openai.py
│   │           ├── ollama.py
│   │           ├── gemini.py
│   │           └── qwen.py
│   ├── agents/                          # 保留原有Agent逻辑，重构为Service调用
│   │   ├── __init__.py
│   │   ├── base.py                      # 新的BaseAgent（对接Service层）
│   │   ├── director.py
│   │   ├── world_builder.py
│   │   ├── character_generator.py
│   │   ├── content_generator.py
│   │   ├── quality_checker.py
│   │   └── tools/                       # 动态工具注册
│   │       ├── __init__.py
│   │       ├── registry.py
│   │       └── definitions.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── proto/                               # gRPC Proto文件（与BFF共享）
│   ├── novel.proto
│   ├── task.proto
│   └── agent.proto
├── alembic/                             # 数据库迁移
│   ├── versions/
│   └── env.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

### 5.2 核心重构点

#### 5.2.1 结构化日志 (Structlog)

```python
# src/core/logging.py
import structlog
import logging
import sys
from typing import Any


def configure_logging():
    """配置结构化JSON日志"""
    
    # 标准库日志桥接
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Structlog配置
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ExtraAdder(),
            structlog.stdlib.filter_by_level,
            # 如果trace_id存在，添加到日志
            add_trace_info,
            # JSON格式化（生产环境）
            structlog.processors.JSONRenderer()
            if sys.env.get("ENV") == "production"
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_trace_info(logger, method_name, event_dict):
    """添加链路追踪信息到日志"""
    from opentelemetry import trace
    
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    
    return event_dict


# 使用示例
logger = structlog.get_logger()

logger.info(
    "task_started",
    task_id="task_123",
    agent="outline_generator",
    novel_id="novel_456",
)

# 输出（生产环境）:
# {"event": "task_started", "level": "info", "timestamp": "2026-04-29T10:30:00Z", "task_id": "task_123", "agent": "outline_generator", "novel_id": "novel_456", "trace_id": "abc123...", "span_id": "def456..."}
```

#### 5.2.2 OpenTelemetry链路追踪

```python
# src/core/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


def setup_tracing(app, service_name: str = "ai-novels-engine"):
    """配置分布式链路追踪"""
    
    # 设置TracerProvider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # OTLP导出器（发送到Jaeger/Tempo）
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # 自动埋点
    FastAPIInstrumentor.instrument_app(app)
    RedisInstrumentor().instrument()
    # SQLAlchemyInstrumentor().instrument()
    
    return provider


# 在Service层手动创建span
class TaskService:
    def __init__(self):
        self.tracer = trace.get_tracer("task.service")
    
    async def generate_novel(self, novel_id: str, config: dict):
        with self.tracer.start_as_current_span("generate_novel") as span:
            span.set_attribute("novel.id", novel_id)
            span.set_attribute("novel.config", str(config))
            
            # 步骤1: 构建世界
            with self.tracer.start_as_current_span("build_world"):
                world = await self.world_service.build(config["world"])
            
            # 步骤2: 设计角色
            with self.tracer.start_as_current_span("design_characters"):
                characters = await self.character_service.design(config["characters"])
            
            # 步骤3: 生成大纲
            with self.tracer.start_as_current_span("generate_outline"):
                outline = await self.outline_service.generate(world, characters)
            
            # 步骤4: 生成章节
            with self.tracer.start_as_current_span("generate_chapters"):
                for chapter in outline.chapters:
                    await self.chapter_service.generate(chapter)
            
            span.set_attribute("task.status", "completed")
            return {"novel_id": novel_id, "status": "completed"}
```

#### 5.2.3 Redis Streams事件总线

```python
# src/core/events.py
import json
import asyncio
from typing import Callable, Dict, Set
from redis.asyncio import Redis


class EventBus:
    """
    Redis Streams事件总线
    
    替代内存EventBus，支持:
    - 持久化事件（不丢失）
    - 多消费者组（BFF和多个引擎实例）
    - 事件回放
    """
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self._local_handlers: Dict[str, Set[Callable]] = {}
        self._running = False
        self._consumer_group = "engine"
    
    async def publish(self, stream: str, event: dict):
        """发布事件到Stream"""
        await self.redis.xadd(
            stream,
            {"data": json.dumps(event)},
            maxlen=10000,  # 保留最近10000条
        )
    
    async def subscribe(self, stream: str, handler: Callable, consumer_name: str):
        """订阅Stream事件"""
        # 创建消费者组（如果不存在）
        try:
            await self.redis.xgroup_create(stream, self._consumer_group, id="0", mkstream=True)
        except Exception:
            pass  # 已存在
        
        while self._running:
            try:
                messages = await self.redis.xreadgroup(
                    groupname=self._consumer_group,
                    consumername=consumer_name,
                    streams={stream: ">"},
                    count=10,
                    block=5000,
                )
                
                for stream_name, msgs in messages:
                    for msg_id, fields in msgs:
                        data = json.loads(fields[b"data"])
                        await handler(data)
                        # ACK确认
                        await self.redis.xack(stream, self._consumer_group, msg_id)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("EventBus error", error=str(e))
    
    async def start(self):
        self._running = True
    
    async def stop(self):
        self._running = False


# 使用示例
event_bus = EventBus(redis_client)

# 任务服务发布事件
await event_bus.publish("task:events", {
    "type": "task.updated",
    "task_id": task_id,
    "status": "running",
    "progress": 50,
    "timestamp": datetime.utcnow().isoformat(),
})

# BFF层订阅事件并转发到WebSocket
async def handle_task_event(event: dict):
    # 通过gRPC或HTTP回调通知BFF
    await bff_client.notify(f"task:{event['task_id']}", event)

asyncio.create_task(event_bus.subscribe("task:events", handle_task_event, "bff-consumer"))
```

#### 5.2.4 异步任务队列 (Celery)

```python
# src/infrastructure/queue/celery_app.py
from celery import Celery
from celery.signals import task_prerun, task_postrun
from opentelemetry import trace


celery_app = Celery(
    "ai_novels",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=[
        "src.tasks.novel_generation",
        "src.tasks.world_building",
        "src.tasks.character_design",
        "src.tasks.chapter_generation",
        "src.tasks.quality_review",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


@task_prerun.connect
def on_task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **extras):
    """任务开始前的链路追踪"""
    tracer = trace.get_tracer("celery")
    span = tracer.start_span(f"celery.task.{task.name}")
    span.set_attribute("celery.task_id", task_id)
    span.set_attribute("celery.task_name", task.name)
    task._otel_span = span


@task_postrun.connect
def on_task_postrun(sender=None, task_id=None, task=None, retval=None, state=None, **extras):
    """任务结束后的链路追踪"""
    if hasattr(task, "_otel_span"):
        span = task._otel_span
        span.set_attribute("celery.task_state", state)
        span.end()


# 任务定义
@celery_app.task(bind=True, max_retries=3)
def generate_chapter_task(self, novel_id: str, chapter_number: int, config: dict):
    """生成章节异步任务"""
    from src.services.chapter_service import ChapterService
    
    service = ChapterService()
    try:
        result = service.generate(novel_id, chapter_number, config)
        return {"status": "completed", "result": result}
    except Exception as exc:
        # 重试
        raise self.retry(exc=exc, countdown=60)
```

---

## 6. API设计规范

### 6.1 REST API规范

```typescript
// 统一的API响应格式
interface ApiResponse<T> {
  success: boolean
  code: string
  message: string
  data: T
  requestId: string
  timestamp: string
  meta?: {
    pagination?: {
      page: number
      pageSize: number
      total: number
      totalPages: number
    }
    sort?: {
      field: string
      order: 'asc' | 'desc'
    }
  }
}

// 错误响应格式
interface ApiError {
  success: false
  code: string        // 业务错误码: TASK_NOT_FOUND, AGENT_TIMEOUT, etc.
  message: string
  requestId: string
  timestamp: string
  details?: Record<string, unknown>
}
```

### 6.2 路由设计

```
REST API Routes (BFF Layer):

Authentication:
  POST /api/v1/auth/login
  POST /api/v1/auth/register
  POST /api/v1/auth/refresh
  POST /api/v1/auth/logout
  GET  /api/v1/auth/me

Novels:
  GET    /api/v1/novels                  # 列表 + 分页 + 过滤
  POST   /api/v1/novels                  # 创建（触发AI补全）
  GET    /api/v1/novels/:id
  PATCH  /api/v1/novels/:id
  DELETE /api/v1/novels/:id
  POST   /api/v1/novels/:id/generate     # 触发生成任务
  GET    /api/v1/novels/:id/progress     # 获取生成进度

Worlds:
  GET    /api/v1/novels/:novelId/world
  POST   /api/v1/novels/:novelId/world/entities
  GET    /api/v1/novels/:novelId/world/entities
  GET    /api/v1/novels/:novelId/world/graph          # 关系图谱数据
  GET    /api/v1/novels/:novelId/world/timeline       # 时间线数据

Characters:
  GET    /api/v1/novels/:novelId/characters
  POST   /api/v1/novels/:novelId/characters
  GET    /api/v1/novels/:novelId/characters/:id
  GET    /api/v1/novels/:novelId/characters/:id/relations
  GET    /api/v1/novels/:novelId/characters/:id/consistency  # 一致性分析

Outlines:
  GET    /api/v1/novels/:novelId/outline
  POST   /api/v1/novels/:novelId/outline/chapters
  PATCH  /api/v1/novels/:novelId/outline/chapters/:id
  DELETE /api/v1/novels/:novelId/outline/chapters/:id
  POST   /api/v1/novels/:novelId/outline/reorder       # 拖拽重排

Chapters:
  GET    /api/v1/novels/:novelId/chapters
  GET    /api/v1/novels/:novelId/chapters/:number
  POST   /api/v1/novels/:novelId/chapters/:number/generate
  GET    /api/v1/novels/:novelId/chapters/:number/versions  # 版本历史
  POST   /api/v1/novels/:novelId/chapters/:number/versions/:versionId/rollback

Tasks:
  GET    /api/v1/tasks
  GET    /api/v1/tasks/:id
  GET    /api/v1/tasks/:id/status
  GET    /api/v1/tasks/:id/logs
  POST   /api/v1/tasks/:id/cancel
  POST   /api/v1/tasks/:id/pause
  POST   /api/v1/tasks/:id/resume
  GET    /api/v1/tasks/:id/workflow                    # DAG节点状态

Agents:
  GET    /api/v1/agents                                 # Agent列表
  GET    /api/v1/agents/:name                           # Agent详情
  POST   /api/v1/agents/:name/chat                      # 对话
  GET    /api/v1/agents/:name/history                   # 对话历史
  GET    /api/v1/agents/:name/thinking/:messageId       # 思考过程
  GET    /api/v1/agents/:name/tools                     # 可用工具

Workflows:
  GET    /api/v1/workflows
  GET    /api/v1/workflows/:id
  GET    /api/v1/workflows/:id/nodes
  POST   /api/v1/workflows/:id/execute
  POST   /api/v1/workflows/:id/nodes/:nodeId/execute

Knowledge:
  GET    /api/v1/knowledge/search                       # 全文+语义检索
  GET    /api/v1/knowledge/graph                        # 知识图谱
  GET    /api/v1/knowledge/timeline                     # 时间线
  GET    /api/v1/knowledge/vector-space                 # 向量空间数据

Logs:
  GET    /api/v1/logs                                   # 查询日志
  GET    /api/v1/logs/streams                           # SSE端点
  GET    /api/v1/logs/stats                             # 日志统计
  GET    /api/v1/logs/traces/:traceId                   # 链路详情

System:
  GET    /api/v1/system/health                          # 健康检查
  GET    /api/v1/system/metrics                         # 系统指标
  GET    /api/v1/system/config                          # 运行时配置
  POST   /api/v1/system/config/reload                   # 热加载配置
  GET    /api/v1/system/agents                          # Agent状态
  GET    /api/v1/system/llm/providers                   # LLM提供商状态
```

### 6.3 GraphQL Schema设计

```graphql
# src/graphql/schema.gql (自动生成)

type Novel {
  id: ID!
  title: String!
  subtitle: String
  genre: Genre!
  status: NovelStatus!
  progress: Float!
  wordCount: Int!
  chapterCount: Int!
  config: NovelConfig!
  world: World
  characters: [Character!]!
  outline: Outline
  chapters: [Chapter!]!
  tasks: [Task!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type World {
  id: ID!
  name: String!
  description: String
  entities: [WorldEntity!]!
  relations: [EntityRelation!]!
  graph: GraphData!
  timeline: [TimelineEvent!]!
}

type Task {
  id: ID!
  type: TaskType!
  status: TaskStatus!
  progress: Float!
  currentStage: String
  workflow: Workflow
  logs: [LogEntry!]!
  createdAt: DateTime!
  startedAt: DateTime
  completedAt: DateTime
}

type Workflow {
  id: ID!
  nodes: [WorkflowNode!]!
  edges: [WorkflowEdge!]!
  status: WorkflowStatus!
}

type Query {
  # Novel queries
  novels(pagination: PaginationInput, filter: NovelFilterInput): NovelConnection!
  novel(id: ID!): Novel
  
  # World queries
  world(novelId: ID!): World
  worldGraph(novelId: ID!, filter: GraphFilterInput): GraphData!
  
  # Task queries
  tasks(pagination: PaginationInput, filter: TaskFilterInput): TaskConnection!
  task(id: ID!): Task
  
  # Knowledge queries
  searchKnowledge(query: String!, strategy: SearchStrategy): [KnowledgeResult!]!
}

type Mutation {
  # Novel mutations
  createNovel(input: CreateNovelInput!): Novel!
  updateNovel(id: ID!, input: UpdateNovelInput!): Novel!
  deleteNovel(id: ID!): Boolean!
  generateNovel(id: ID!, config: GenerationConfigInput): Task!
  
  # Task mutations
  cancelTask(id: ID!): Task!
  pauseTask(id: ID!): Task!
  resumeTask(id: ID!): Task!
  
  # Agent mutations
  sendAgentMessage(agentName: String!, message: String!): AgentMessage!
}

type Subscription {
  # Real-time subscriptions
  taskUpdated(taskId: ID!): Task!
  taskLogAdded(taskId: ID!): LogEntry!
  agentMessageAdded(agentName: String!): AgentMessage!
  agentThinkingUpdated(agentName: String!, messageId: ID!): AgentThinking!
  systemHealthUpdated: SystemHealth!
  novelProgressUpdated(novelId: ID!): NovelProgress!
}
```

### 6.4 WebSocket事件协议

```typescript
// 前端与BFF Gateway之间的WebSocket事件协议

// Client → Server
interface ClientEvents {
  // 任务订阅
  'task:subscribe': { taskId: string }
  'task:unsubscribe': { taskId: string }
  
  // Agent订阅
  'agent:subscribe': { agentName: string }
  'agent:unsubscribe': { agentName: string }
  'agent:sendMessage': { agentName: string; message: string; context?: Record<string, unknown> }
  
  // 日志订阅
  'log:subscribe': { filter?: LogFilter }
  'log:unsubscribe': {}
  
  // 系统订阅
  'system:subscribe': {}
  'system:unsubscribe': {}
}

// Server → Client
interface ServerEvents {
  // 任务事件
  'task:created': Task
  'task:updated': Task
  'task:completed': Task
  'task:failed': { taskId: string; error: string }
  'task:progress': { taskId: string; progress: number; stage: string }
  'task:log': { taskId: string; log: LogEntry }
  
  // 工作流节点事件
  'workflow:node:started': { workflowId: string; nodeId: string; nodeName: string }
  'workflow:node:completed': { workflowId: string; nodeId: string; result: unknown }
  'workflow:node:failed': { workflowId: string; nodeId: string; error: string }
  
  // Agent事件
  'agent:message': { agentName: string; message: AgentMessage }
  'agent:thinking': { agentName: string; messageId: string; thinking: string }
  'agent:toolCall': { agentName: string; messageId: string; tool: string; params: Record<string, unknown> }
  
  // 日志事件
  'log:new': LogEntry
  'log:stats': LogStats
  
  // 系统事件
  'system:health': SystemHealth
  'system:alert': { level: 'warning' | 'critical'; message: string; component: string }
  'system:configChanged': { key: string; oldValue: unknown; newValue: unknown }
}
```

---

## 7. 数据库层重构

### 7.1 数据库选型调整

| 数据库 | 当前用途 | Step14调整后 | 理由 |
|--------|---------|------------|------|
| **PostgreSQL** | 新增 | 主数据库（替代MySQL） | ACID事务、JSONB、全文检索、向量扩展(pgvector) |
| **Redis** | 新增 | 缓存 + 消息队列 + 会话 | 统一缓存层，替代内存状态 |
| **Qdrant** | 新增 | 向量数据库（替代ChromaDB） | 高性能、分布式、REST API |
| **Neo4j** | 保留 | 图数据库（关系网络） | 角色关系、世界关系 |
| **MongoDB** | 保留 | 日志存储（可选） | 非结构化日志归档 |
| **MySQL** | 移除 | 迁移到PostgreSQL | 统一SQL数据库，减少运维 |
| **ChromaDB** | 移除 | 迁移到Qdrant | ChromaDB有假Embedding问题 |

### 7.2 Prisma Schema设计 (BFF层)

```prisma
// backend/bff/prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// 小说
model Novel {
  id            String   @id @default(uuid())
  title         String
  subtitle      String?
  genre         Genre
  status        NovelStatus @default(DRAFT)
  progress      Float    @default(0)
  wordCount     Int      @default(0)
  chapterCount  Int      @default(0)
  config        Json     // NovelConfig JSON
  
  worldId       String?
  world         World?   @relation(fields: [worldId], references: [id])
  
  characters    Character[]
  chapters      Chapter[]
  outline       Outline?
  tasks         Task[]
  
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  
  @@index([status])
  @@index([genre])
  @@index([createdAt])
}

// 世界
model World {
  id          String   @id @default(uuid())
  name        String
  description String?
  rules       Json     // WorldRules JSON
  
  novels      Novel[]
  entities    WorldEntity[]
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

// 世界实体
model WorldEntity {
  id          String     @id @default(uuid())
  name        String
  type        EntityType
  description String?
  properties  Json
  position    Json?      // {x, y} for map view
  
  worldId     String
  world       World      @relation(fields: [worldId], references: [id], onDelete: Cascade)
  
  fromRelations EntityRelation[] @relation("FromEntity")
  toRelations   EntityRelation[] @relation("ToEntity")
  
  @@index([worldId])
  @@index([type])
}

// 实体关系
model EntityRelation {
  id          String       @id @default(uuid())
  type        RelationType
  strength    Float        @default(1)
  description String?
  
  fromId      String
  from        WorldEntity  @relation("FromEntity", fields: [fromId], references: [id], onDelete: Cascade)
  toId        String
  to          WorldEntity  @relation("ToEntity", fields: [toId], references: [id], onDelete: Cascade)
  
  @@index([fromId])
  @@index([toId])
}

// 角色
model Character {
  id          String   @id @default(uuid())
  name        String
  role        CharacterRole @default(SUPPORTING)
  archetype   String?
  personality Json     // Big Five / MBTI etc.
  backstory   String?
  appearance  String?
  abilities   Json?
  
  novelId     String
  novel       Novel    @relation(fields: [novelId], references: [id], onDelete: Cascade)
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  @@index([novelId])
}

// 章节
model Chapter {
  id            String   @id @default(uuid())
  number        Int
  title         String
  content       String?  @db.Text
  summary       String?
  wordCount     Int      @default(0)
  status        ChapterStatus @default(PLANNED)
  
  novelId       String
  novel         Novel    @relation(fields: [novelId], references: [id], onDelete: Cascade)
  
  versions      ChapterVersion[]
  
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  
  @@unique([novelId, number])
  @@index([novelId])
}

// 章节版本（用于版本历史）
model ChapterVersion {
  id        String   @id @default(uuid())
  number    Int      // 版本号
  content   String   @db.Text
  wordCount Int
  changeDescription String?
  
  chapterId String
  chapter   Chapter  @relation(fields: [chapterId], references: [id], onDelete: Cascade)
  
  createdAt DateTime @default(now())
  
  @@index([chapterId])
}

// 任务
model Task {
  id            String     @id @default(uuid())
  type          TaskType
  status        TaskStatus @default(PENDING)
  progress      Float      @default(0)
  currentStage  String?
  error         String?
  
  novelId       String?
  novel         Novel?     @relation(fields: [novelId], references: [id])
  
  workflow      Workflow?
  
  createdAt     DateTime   @default(now())
  startedAt     DateTime?
  completedAt   DateTime?
  
  @@index([status])
  @@index([novelId])
  @@index([createdAt])
}

// 工作流
model Workflow {
  id      String   @id @default(uuid())
  status  WorkflowStatus @default(CREATED)
  graph   Json     // DAG graph JSON
  
  taskId  String   @unique
  task    Task     @relation(fields: [taskId], references: [id], onDelete: Cascade)
  
  nodes   WorkflowNode[]
}

// 工作流节点
model WorkflowNode {
  id        String     @id @default(uuid())
  nodeId    String     // 业务节点ID
  agentName String?
  status    NodeStatus @default(PENDING)
  result    Json?
  error     String?
  startedAt DateTime?
  endedAt   DateTime?
  
  workflowId String
  workflow   Workflow   @relation(fields: [workflowId], references: [id], onDelete: Cascade)
  
  @@index([workflowId])
  @@index([status])
}

// 枚举定义
enum Genre {
  XIANXIA
  WUXIA
  SCI_FI
  FANTASY
  MODERN
  HORROR
  HISTORY
  OTHER
}

enum NovelStatus {
  DRAFT
  WRITING
  REVIEWING
  COMPLETED
}

enum EntityType {
  WORLD
  REGION
  FACTION
  CITY
  LANDMARK
  RULE
  EVENT
  ITEM
}

enum RelationType {
  CONTAINS
  CONNECTS
  OPPOSES
  ALLIES
  CAUSES
  REFERENCES
}

enum CharacterRole {
  PROTAGONIST
  DEUTERAGONIST
  ANTAGONIST
  SUPPORTING
  NPC
}

enum ChapterStatus {
  PLANNED
  GENERATING
  COMPLETED
  REVIEWED
}

enum TaskType {
  NOVEL_GENERATION
  WORLD_BUILDING
  CHARACTER_DESIGN
  OUTLINE_GENERATION
  CHAPTER_GENERATION
  QUALITY_REVIEW
}

enum TaskStatus {
  PENDING
  RUNNING
  PAUSED
  COMPLETED
  FAILED
  CANCELLED
}

enum WorkflowStatus {
  CREATED
  RUNNING
  PAUSED
  COMPLETED
  FAILED
}

enum NodeStatus {
  PENDING
  SCHEDULED
  RUNNING
  COMPLETED
  FAILED
  SKIPPED
  CANCELLED
}
```

---

## 8. 安全与认证

### 8.1 认证体系

```typescript
// JWT + Refresh Token 双令牌

interface AuthToken {
  accessToken: string   // JWT, 15分钟过期
  refreshToken: string  // JWT, 7天过期
  expiresIn: number     // 900 (15分钟)
}

// 认证流程
1. POST /api/v1/auth/login
   Body: { username: string; password: string }
   → 验证密码 → 生成双令牌 → 返回

2. 前端存储accessToken（内存）和refreshToken（httpOnly cookie）

3. 每次请求携带: Authorization: Bearer <accessToken>

4. AccessToken过期 → 自动调用POST /api/v1/auth/refresh
   → 验证refreshToken → 生成新的双令牌

5. RefreshToken过期 → 强制重新登录
```

### 8.2 权限模型 (RBAC)

```typescript
enum Role {
  ADMIN = 'admin',         // 全部权限
  CREATOR = 'creator',     // 创建/编辑小说
  READER = 'reader',       // 只读
  SYSTEM = 'system',       // 系统服务间调用
}

enum Permission {
  NOVEL_CREATE = 'novel:create',
  NOVEL_READ = 'novel:read',
  NOVEL_UPDATE = 'novel:update',
  NOVEL_DELETE = 'novel:delete',
  TASK_CREATE = 'task:create',
  TASK_CANCEL = 'task:cancel',
  AGENT_CHAT = 'agent:chat',
  CONFIG_READ = 'config:read',
  CONFIG_WRITE = 'config:write',
  SYSTEM_MONITOR = 'system:monitor',
}

// NestJS装饰器
@Roles(Role.CREATOR)
@Permissions(Permission.NOVEL_CREATE)
@Controller('novels')
```

### 8.3 API安全策略

| 策略 | 实现 | 说明 |
|------|------|------|
| HTTPS | 强制TLS 1.3 | 生产环境 |
| CORS | 白名单 | 只允许前端域名 |
| Rate Limit | @nestjs/throttler | 60 req/min, burst 10 |
| Input Validation | Zod/Pydantic | 请求体严格验证 |
| SQL Injection | Prisma/SQLModel | ORM参数化查询 |
| XSS | 输出编码 | GraphQL/REST响应编码 |
| CSRF | SameSite Cookie | 启用SameSite=Strict |
| Secrets | Vault/Env | API密钥加密存储 |

---

## 9. 性能优化策略

### 9.1 多层缓存架构

```
Cache Hierarchy:

L1: In-Memory (Node.js/Python进程内)
  - 热数据: 系统配置、Agent元数据
  - TTL: 60s
  - 库: node-cache / cachetools

L2: Redis (分布式)
  - API响应缓存: GET /api/v1/novels/:id
  - Session存储
  - Rate Limit计数器
  - TTL: 5min ~ 1hour

L3: Database Query Cache
  - Prisma查询缓存
  - 复杂GraphQL查询结果缓存
  - TTL: 10min
```

### 9.2 数据库优化

```typescript
// Prisma查询优化示例
@Injectable()
export class NovelService {
  async findById(id: string) {
    return this.prisma.novel.findUnique({
      where: { id },
      include: {
        world: {
          include: {
            entities: {
              take: 100,  // 限制关联查询数量
            },
          },
        },
        characters: true,
        chapters: {
          orderBy: { number: 'asc' },
          select: {  // 只选择需要的字段
            id: true,
            number: true,
            title: true,
            status: true,
            wordCount: true,
          },
        },
      },
    })
  }
}
```

### 9.3 连接池与并发

```typescript
// BFF: 连接池配置
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL,
    },
  },
  connectionLimit: 20,
})

// Python引擎: 异步连接池
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=30)
```

---

## 10. 与前端Step13对接

### 10.1 API端点映射

| 前端页面 | 所需API | 协议 |
|---------|--------|------|
| NovelStudio | REST: `POST /novels`, `GET /novels` | REST |
| WorldBuilder | GraphQL: `world`, `worldGraph` + WS: `entity:updated` | GraphQL + WebSocket |
| CharacterStudio | REST: `/characters` + GraphQL: `character.relations` | REST + GraphQL |
| OutlineEditor | REST: `/outline` + WS: `chapter:updated` | REST + WebSocket |
| WritingStudio | REST: `/chapters/:id` + WS: `chapter:generating` | REST + WebSocket |
| WorkflowCanvas | WS: `workflow:*` events | WebSocket |
| AgentCommand | WS: `agent:*` + REST: `/agents/:name/chat` | WebSocket + REST |
| ReviewCenter | REST: `/novels/:id/review` | REST |
| KnowledgeExplorer | GraphQL: `searchKnowledge` + REST: `/knowledge/graph` | GraphQL + REST |
| LogCenter | WS: `log:new` + SSE: `/logs/streams` | WebSocket + SSE |
| SystemOps | REST: `/system/*` + WS: `system:health` | REST + WebSocket |

### 10.2 共享类型目录

```typescript
// shared/types/novel.ts (前后端共享)
import { z } from 'zod'

export const NovelSchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1).max(200),
  subtitle: z.string().max(500).optional(),
  genre: z.enum(['xianxia', 'wuxia', 'sci-fi', 'fantasy', 'modern', 'horror', 'history']),
  status: z.enum(['draft', 'writing', 'reviewing', 'completed']),
  progress: z.number().min(0).max(100).default(0),
  wordCount: z.number().default(0),
  chapterCount: z.number().default(0),
  config: z.record(z.unknown()).optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})

export type Novel = z.infer<typeof NovelSchema>

// Python端生成Pydantic模型（通过codegen或手动同步）
// from pydantic import BaseModel
// class Novel(BaseModel):
//     id: UUID
//     title: str
//     ...
```

---

## 11. 部署与运维

### 11.1 Docker Compose 开发环境

```yaml
# docker-compose.yml
version: '3.8'

services:
  # BFF API Gateway
  bff:
    build: ./backend/bff
    ports:
      - "8004:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ainovels
      - REDIS_URL=redis://redis:6379
      - ENGINE_GRPC_URL=engine:50051
      - JWT_SECRET=dev-secret
    depends_on:
      - postgres
      - redis
      - engine
    volumes:
      - ./shared:/app/shared:ro

  # Python AI Engine
  engine:
    build: ./backend/engine
    ports:
      - "8005:8000"
      - "50051:50051"
    environment:
      - ENV=development
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ainovels
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URL=bolt://neo4j:7687
    depends_on:
      - postgres
      - redis
      - qdrant
      - neo4j

  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ainovels
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Qdrant (向量数据库)
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  # Neo4j
  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/password
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  # Jaeger (链路追踪)
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "4317:4317"

  # Grafana (监控)
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  neo4j_data:
  grafana_data:
```

### 11.2 生产部署架构

```
Production Architecture:

┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                         │
│                        (Nginx/Traefik)                       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   BFF Instance 1         │    │   BFF Instance 2         │
│   (NestJS + PM2)         │    │   (NestJS + PM2)         │
└──────────────────────────┘    └──────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Redis Cluster                           │
│              (Session + Cache + Pub/Sub)                     │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   Engine Instance 1      │    │   Engine Instance 2      │
│   (Python + Gunicorn)    │    │   (Python + Gunicorn)    │
└──────────────────────────┘    └──────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Primary + Replica                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. 实施计划

### 12.1 文件变更清单

**新增文件 (约80个)**:
```
backend/
├── bff/                                 # NestJS BFF (约50个文件)
│   ├── src/
│   │   ├── main.ts
│   │   ├── app.module.ts
│   │   ├── config/
│   │   ├── modules/*/(*.module.ts, *.controller.ts, *.service.ts, *.resolver.ts, *.gateway.ts, dto/)
│   │   ├── gateway/
│   │   ├── graphql/
│   │   ├── grpc/
│   │   ├── services/
│   │   ├── interceptors/
│   │   ├── filters/
│   │   └── prisma/
│   ├── shared/types/
│   ├── proto/
│   └── Dockerfile
│
└── engine/                              # Python引擎重构 (约30个文件)
    ├── src/
    │   ├── main.py (重构)
    │   ├── api/
    │   │   ├── deps.py
    │   │   ├── v1/endpoints/*.py
    │   │   ├── websocket/*.py
    │   │   └── grpc/server.py
    │   ├── core/
    │   │   ├── logging.py
    │   │   ├── tracing.py
    │   │   └── events.py
    │   ├── services/
    │   ├── repositories/
    │   ├── models/
    │   ├── domain/
    │   └── infrastructure/
    │       ├── database/
    │       ├── cache/
    │       └── queue/
    ├── proto/
    ├── alembic/
    └── Dockerfile
```

**修改文件 (约15个)**:
```
src/deepnovel/api/main.py         # 改为Python引擎入口
src/deepnovel/api/routes.py       # 精简为内部gRPC服务
src/deepnovel/api/middleware.py   # 部分迁移到BFF
src/deepnovel/agents/base.py      # 重构为Service调用模式
src/deepnovel/agents/coordinator.py # 保留核心逻辑，增加事件发布
src/deepnovel/config/manager.py   # 适配新配置系统
src/deepnovel/utils/logger.py     # 接入Structlog
```

**删除文件 (约10个)**:
```
src/deepnovel/agents/task_manager.py          # 功能由Celery替代
src/deepnovel/agents/workflow_orchestrator.py # 功能由TaskOrchestrator替代
src/deepnovel/agents/enhanced_*.py            # 未使用的增强版
src/deepnovel/database/chromadb_client.py     # 迁移到Qdrant
src/deepnovel/vector_store/chroma_store.py    # 迁移到Qdrant
src/deepnovel/messaging/rocketmq_*.py         # 迁移到Redis Streams
src/deepnovel/config/validator.py (旧)       # 由Pydantic替代
```

### 12.2 实施阶段 (6周)

#### Phase 1: 基础设施搭建 (Week 1)

**Day 1-2: 项目初始化**
- [ ] 创建 `backend/bff/` NestJS项目（nest new）
- [ ] 创建 `backend/engine/` Python项目（poetry init）
- [ ] 创建 `shared/types/` 共享类型目录
- [ ] 配置 Docker Compose 开发环境

**Day 3-4: 数据库与缓存**
- [ ] PostgreSQL迁移脚本（从MySQL）
- [ ] Prisma Schema定义
- [ ] Redis连接配置
- [ ] Qdrant向量数据库配置

**Day 5-7: gRPC通信**
- [ ] 定义Proto文件（Novel/Task/Agent）
- [ ] Python gRPC Server实现
- [ ] NestJS gRPC Client实现
- [ ] 通信测试

**验收标准**:
- [ ] `docker-compose up` 启动所有服务
- [ ] NestJS能成功调用Python gRPC服务
- [ ] PostgreSQL数据迁移成功

#### Phase 2: BFF核心开发 (Week 2-3)

**Day 8-10: 核心模块**
- [ ] Auth模块（JWT + Guard）
- [ ] Novel模块（REST + GraphQL）
- [ ] Task模块（REST + GraphQL）

**Day 11-14: 实时通信**
- [ ] WebSocket Gateway框架
- [ ] Redis Pub/Sub集成
- [ ] 事件转发机制（Python → Redis → NestJS → WebSocket）
- [ ] SSE端点实现

**Day 15-17: 中间件**
- [ ] Pino结构化日志
- [ ] OpenTelemetry链路追踪
- [ ] 请求耗时监控
- [ ] 响应标准化

**Day 18-21: 其他模块**
- [ ] World/Character/Outline/Chapter模块
- [ ] Agent模块
- [ ] Log模块
- [ ] System模块

**验收标准**:
- [ ] GraphQL Playground可查询Novel/World/Character
- [ ] WebSocket连接成功，能接收模拟事件
- [ ] 结构化日志输出JSON格式
- [ ] 链路追踪在Jaeger可见

#### Phase 3: Python引擎重构 (Week 4-5)

**Day 22-24: 核心升级**
- [ ] Structlog配置
- [ ] OpenTelemetry配置
- [ ] Redis Streams事件总线
- [ ] Celery任务队列

**Day 25-28: 服务层重构**
- [ ] Repository模式实现
- [ ] Service层重构（从Controller分离业务逻辑）
- [ ] Agent Base类重构（对接Service层）
- [ ] Coordinator重构（发布事件到Redis Streams）

**Day 29-32: API层重构**
- [ ] FastAPI依赖注入（deps.py）
- [ ] gRPC服务实现
- [ ] WebSocket端点（SSE备用）
- [ ] 健康检查端点

**Day 33-35: 数据库迁移**
- [ ] MySQL → PostgreSQL数据迁移
- [ ] ChromaDB → Qdrant数据迁移
- [ ] Alembic迁移脚本
- [ ] 数据验证

**验收标准**:
- [ ] Python引擎能处理长任务（小说生成）并发布事件
- [ ] Celery Worker正常运行
- [ ] gRPC接口测试通过
- [ ] 数据库迁移无数据丢失

#### Phase 4: 集成测试 (Week 6)

**Day 36-38: 端到端测试**
- [ ] 前端 → BFF → Python引擎 → 数据库 全链路测试
- [ ] WebSocket实时推送测试
- [ ] GraphQL查询测试
- [ ] 并发请求测试

**Day 39-40: 性能优化**
- [ ] 数据库查询优化（慢查询分析）
- [ ] 缓存命中率监控
- [ ] 内存泄漏检查
- [ ] 负载测试（100并发）

**Day 41-42: 部署准备**
- [ ] Docker镜像构建
- [ ] Kubernetes配置（可选）
- [ ] 监控告警配置
- [ ] 文档更新

**验收标准**:
- [ ] 完整端到端流程：创建小说 → 生成 → 写作 → 审校
- [ ] WebSocket延迟 < 500ms
- [ ] API P95响应 < 500ms
- [ ] 系统稳定运行24小时无内存泄漏

---

## 13. 量化验收标准

### 13.1 功能验收

| # | 验收项 | 验收标准 |
|---|--------|---------|
| F1 | gRPC通信 | BFF ↔ Python引擎 gRPC调用 P99 < 50ms |
| F2 | WebSocket推送 | 事件从Python产生到前端接收 < 500ms |
| F3 | GraphQL查询 | 复杂查询（Novel + World + Characters）< 300ms |
| F4 | 任务队列 | Celery处理10个并发生成任务无丢失 |
| F5 | 结构化日志 | 所有日志输出JSON，包含trace_id/span_id |
| F6 | 链路追踪 | 一个请求的全链路在Jaeger完整可见 |
| F7 | 数据库事务 | 小说创建（Novel + World + Config）原子性 |
| F8 | 缓存生效 | 热点数据缓存命中率 > 80% |
| F9 | 类型共享 | 前后端使用同一套Zod Schema，无类型不一致 |
| F10 | 认证授权 | JWT双令牌正常工作，权限控制生效 |

### 13.2 性能验收

| # | 指标 | 目标 |
|---|------|------|
| P1 | API响应P95 | < 500ms |
| P2 | GraphQL查询P95 | < 500ms |
| P3 | gRPC调用P99 | < 50ms |
| P4 | WebSocket延迟 | < 500ms |
| P5 | 数据库查询 | < 100ms（单表） |
| P6 | 并发请求 | 支持100并发无错误 |
| P7 | 内存使用 | BFF < 200MB, Engine < 500MB |
| P8 | 日志吞吐量 | > 1000条/秒 |

### 13.3 兼容性验收

| # | 指标 | 目标 |
|---|------|------|
| C1 | 前端兼容 | Step13前端能正常调用所有新API |
| C2 | 数据兼容 | 旧数据完整迁移，无丢失 |
| C3 | 配置兼容 | 旧配置文件能导入新系统 |
| C4 | API兼容 | 保留 `/api/v1/` 兼容层（1个版本） |

---

## 14. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| gRPC性能不达预期 | BFF与引擎通信延迟高 | 降级为HTTP/REST，gRPC作为可选优化 |
| PostgreSQL迁移失败 | 数据丢失 | 保留MySQL只读副本，回滚机制 |
| NestJS学习曲线 | 开发延期 | 核心开发者先学习1周，文档齐全 |
| WebSocket连接不稳定 | 实时功能不可用 | SSE作为降级方案，双重保障 |
| Celery任务丢失 | 生成任务丢失 | Redis持久化 + 任务结果存储 |
| 微服务调试复杂 | 开发效率降低 | 本地Docker Compose一体化开发 |
| 类型同步滞后 | 前后端类型不一致 | CI检查 + 代码生成工具 |

---

## 15. 附录

### 15.1 与Step1-13的整合矩阵

| Step | 后端变更 | 整合方式 |
|------|---------|---------|
| Step1 (数据层) | World/Fact Repository | Python引擎Repository层对接 |
| Step2 (记忆层) | Memory Service | Python引擎Memory Service |
| Step3 (LLM层) | LLM Router Service | Python引擎LLM Service |
| Step4 (Agent层) | Agent Orchestrator | Python引擎Agent Service + 事件发布 |
| Step5 (调度层) | TaskOrchestrator + Celery | 任务队列持久化，事件驱动 |
| Step6 (RAG层) | RAG Service | Python引擎RAG Service，Qdrant |
| Step7 (配置层) | NovelConfig Pydantic模型 | 共享类型 + API验证 |
| Step8 (工具层) | Tool Registry | Agent Service内部调用 |
| Step9 (Prompt层) | Prompt Composer | Agent Service内部使用 |
| Step10 (配置层) | AppConfig → NestJS Config | BFF统一配置管理 |
| Step11 (API层) | REST + GraphQL + WebSocket | BFF实现 |
| Step12/13 (前端) | 所有API | BFF + Python引擎对接 |

### 15.2 技术选型决策记录

| 决策 | 选项A | 选项B | 选择 | 理由 |
|------|-------|-------|------|------|
| BFF语言 | NestJS (TS) | FastAPI升级 | NestJS | 类型共享、WebSocket生态 |
| 通信协议 | gRPC | HTTP REST | gRPC + HTTP | gRPC高性能，HTTP兼容 |
| 消息队列 | Bullmq (Redis) | RabbitMQ | Bullmq | Redis已用，无需新组件 |
| 主数据库 | PostgreSQL | 保留MySQL | PostgreSQL | JSONB、向量扩展 |
| 向量数据库 | Qdrant | 保留Chroma | Qdrant | 性能、分布式、REST API |
| 日志 | Pino (TS) + Structlog (Py) | Winston + logging | Pino + Structlog | 结构化JSON、OTel兼容 |
| ORM | Prisma (TS) + SQLModel (Py) | TypeORM + SQLAlchemy | Prisma + SQLModel | 类型安全、异步支持 |

---

*文档版本: 1.0*
*创建日期: 2026-04-29*
*关联文档: Step13.md (前端需求), OPTIMIZED_ROADMAP.md (全局路线图), INTEGRATION_SPEC.md (模块集成规范)*
