# Step 15: 企业级基础设施重构 — 容器化编排、可观测性与一键部署体系

> 版本: 1.0
> 日期: 2026-04-29
> 依赖: Step1-14 (全栈)
> 目标: 从"无容器化、无CI/CD、手动部署"升级为面向用户的企业级DevOps体系
> 核心转变: 零基础设施自动化 → 一键启动、全自动CI/CD、全链路可观测

---

## 1. 设计哲学

### 1.1 为什么必须重构

```
当前基础设施状态诊断:

❌ 无Dockerfile                      → 部署文档引用的Dockerfile不存在，仅docker-compose.yaml运行基础设施
❌ 无应用容器化                      → Python后端和前端均为裸进程部署，环境不一致
❌ 无CI/CD流水线                     → 全手动部署，无自动化测试、构建、发布
❌ 无可观测性                        → 无监控、无告警、无链路追踪、无结构化日志聚合
❌ 无环境隔离                        → 开发/测试/生产环境混杂，配置管理混乱
❌ 无数据备份策略                    → 无自动化备份、无灾难恢复方案
❌ 无安全扫描                        → 容器镜像无CVE扫描、运行时无安全监控
❌ 无反向代理/网关                   → 无HTTPS、无Rate Limit、无WAF
❌ 部署脚本碎片化                    → 多个start_server.py、restart-server.bat、manage-server.sh互不兼容
❌ 无Kubernetes方案                  → 无法水平扩展、无自愈能力、无滚动更新
```

### 1.2 核心架构决策

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户 / 互联网                                       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Traefik v3         │  ← Auto HTTPS, Rate Limit, WAF
                    │  (反向代理 + 网关)      │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼────┐           ┌──────▼──────┐         ┌──────▼──────┐
   │ Vue3    │           │  NestJS BFF │         │ Python AI   │
   │Frontend │           │  (Node.js)  │         │ Engine      │
   │(Nginx)  │           │             │         │ (FastAPI)   │
   └─────────┘           └──────┬──────┘         └──────┬──────┘
                                │                       │
                    ┌───────────┴───────────┐           │
                    │      Redis Cluster    │◄──────────┘
                    │   (缓存/队列/事件总线)  │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼─────┐          ┌──────▼──────┐         ┌──────▼──────┐
   │PostgreSQL│          │   Qdrant    │         │    MinIO    │
   │  (HA)    │          │ (向量数据库)  │         │  (对象存储)  │
   └──────────┘          └─────────────┘         └─────────────┘

可观测性层:
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │ Prometheus  │  │    Loki     │  │   Jaeger    │  │   Grafana   │
  │  (指标)      │  │  (日志聚合)   │  │  (链路追踪)   │  │  (可视化)    │
  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
        ▲                ▲                ▲
        └────────────────┴────────────────┘
                         │
              ┌──────────▼──────────┐
              │ OpenTelemetry       │
              │ Collector           │
              │ (统一采集)            │
              └─────────────────────┘

安全层:
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   Trivy     │  │   Vault     │  │    Falco    │
  │(镜像扫描)    │  │(密钥管理)    │  │(运行时安全)   │
  └─────────────┘  └─────────────┘  └─────────────┘
```

### 1.3 行业前沿参考

| 技术/模式 | 参考来源 | 在本项目中的应用 |
|---------|---------|---------------|
| **Multi-Stage Docker Build** | Google, Shopify | Python/Node多阶段构建，distroless运行时镜像 |
| **Docker Compose Profiles** | Docker官方最佳实践 | 开发/测试/监控通过profile隔离，按需启动 |
| **Traefik v3** | HashiCorp, Docker | 自动HTTPS、Docker标签服务发现、内置Rate Limit |
| **OpenTelemetry Collector** | CNCF, Grafana | 统一采集 traces/metrics/logs，替代多个Agent |
| **PLG Stack** | Grafana Labs | Prometheus + Loki + Grafana 全链路可观测 |
| **GitHub Actions + OIDC** | GitHub, AWS | SHA-pinning actions、无长期密钥、多层缓存 |
| **Semantic Release** | Conventional Commits | 自动化版本管理与Changelog生成 |
| **Taskfile** | Modern DevOps | 跨平台一键命令替代Makefile |
| **Chainguard Images** | Chainguard | 零CVE基础镜像替代Alpine/Debian |
| **K3s / CloudNativePG** | Rancher, Zalando | 轻量K8s + PostgreSQL Operator生产部署 |

---

## 2. 现状深度诊断

### 2.1 现有基础设施

```
AI-Novels/
├── config/
│   ├── docker-compose.yaml          ← 仅有基础设施服务编排
│   ├── .env.example                 ← 环境变量模板
│   ├── init/
│   │   ├── mysql_init.sql           ← MySQL初始化脚本
│   │   ├── mongodb_init.js          ← MongoDB初始化
│   │   └── neo4j_apoc.conf          ← Neo4j配置
│   └── server.json                  ← 服务器配置
├── docker-images/                   ← 预导出镜像tar包（离线部署用）
│   ├── chromadb.tar
│   ├── mongodb.tar
│   ├── mysql.tar
│   ├── neo4j.tar
│   └── rocketmq.tar
├── scripts/
│   ├── manage-server.sh             ← Linux管理脚本（start/test/status/logs）
│   ├── restart-server.bat           ← Windows重启脚本
│   ├── server-manager.ps1           ← PowerShell管理脚本
│   ├── run_server.py                ← 调试服务器启动
│   └── start_server_simple.py       ← 极简服务器启动
├── start_server.py                  ← 主生产启动脚本
├── docs/DEPLOYMENT.md               ← 英文部署文档（引用不存在的Dockerfile）
└── doc/06-部署流程文档.md             ← 中文部署流程（同样引用不存在的文件）
```

### 2.2 关键差距

| 维度 | 当前状态 | 目标状态 | 差距等级 |
|-----|---------|---------|---------|
| 容器化 | 无应用Dockerfile，仅基础设施compose | 全服务多阶段容器化 | 🔴 严重 |
| CI/CD | 无流水线配置 | GitHub Actions完整流水线 | 🔴 严重 |
| 可观测性 | 无监控、无日志聚合 | PLG + OpenTelemetry全链路 | 🔴 严重 |
| 网关 | 无反向代理 | Traefik自动HTTPS + Rate Limit | 🟡 中等 |
| 部署脚本 | 碎片化的.bat/.sh/.py | 统一的Taskfile + 一键脚本 | 🟡 中等 |
| 安全 | 无镜像扫描、无密钥管理 | Trivy + Vault + Falco | 🟡 中等 |
| K8s | 无方案 | Helm Charts + Kustomize覆盖 | 🟢 低（可后续） |
| 数据备份 | 无策略 | Restic自动化备份 + PITR | 🟡 中等 |

### 2.3 现有docker-compose.yaml分析

```yaml
# config/docker-compose.yaml — 当前配置的问题
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    # 问题1: 无健康检查
    # 问题2: 无资源限制
    # 问题3: 数据卷未命名
    volumes:
      - ./mysql_data:/var/lib/mysql  # 绑定挂载，不适合跨平台
  neo4j:
    image: neo4j:latest
    # 问题4: latest标签，不可复现
    # 问题5: 无内存限制
  chromadb:
    image: chromadb/chroma:latest
    # 问题6: 无持久化配置
  rocketmq:
    image: apache/rocketmq:5.3.0
    # 问题7: 复杂的手工配置，无健康检查
```

---

## 3. 容器化策略

### 3.1 多阶段Dockerfile设计

#### 3.1.1 Python AI引擎 (FastAPI)

```dockerfile
# ============================================================
# Dockerfile.ai — Python AI引擎
# 构建: docker build -f Dockerfile.ai -t deepnovel-ai .
# ============================================================
# syntax=docker/dockerfile:1.7

# ─── 阶段1: 构建依赖 ───
FROM python:3.12.3-slim AS builder

# 安全: 非root构建
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 利用BuildKit缓存mount加速pip安装
COPY requirements.txt pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --user --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# ─── 阶段2: 生产运行 ───
FROM cgr.dev/chainguard/python:latest AS production

# Chainguard镜像已包含非root用户(65532)
USER 65532

WORKDIR /app

# 从builder复制已安装的Python包
COPY --from=builder --chown=65532:65532 /root/.local /home/nonroot/.local
ENV PATH=/home/nonroot/.local/bin:$PATH

# 复制应用代码
COPY --chown=65532:65532 --from=builder /build/src ./src
COPY --chown=65532:65532 --from=builder /build/alembic ./alembic
COPY --chown=65532:65532 --from=builder /build/alembic.ini ./

# 安全: 只读根文件系统需要在/tmp有写权限
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_ENV=production

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

EXPOSE 8000

# 使用gunicorn + uvicorn workers生产运行
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "src.deepnovel.main:app"]

# ─── 阶段3: 开发运行（可选target） ───
FROM python:3.12.3-slim AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install debugpy watchfiles

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_ENV=development

CMD ["uvicorn", "src.deepnovel.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

#### 3.1.2 NestJS BFF网关

```dockerfile
# ============================================================
# Dockerfile.bff — NestJS BFF网关
# 构建: docker build -f Dockerfile.bff -t deepnovel-bff .
# ============================================================
# syntax=docker/dockerfile:1.7

# ─── 阶段1: 依赖安装 ───
FROM node:20.12.2-alpine AS deps

# 使用libc-compatible的Prisma引擎
RUN apk add --no-cache libc6-compat openssl

WORKDIR /app

# 利用BuildKit缓存mount加速npm安装
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f pnpm-lock.yaml ]; then \
      npm install -g pnpm && pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install; \
    fi

# ─── 阶段2: 构建应用 ───
FROM node:20.12.2-alpine AS builder

RUN apk add --no-cache libc6-compat openssl
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 生成Prisma Client
RUN npx prisma generate

# 构建NestJS
RUN npm run build

# ─── 阶段3: 生产运行 ───
FROM node:20.12.2-alpine AS production

RUN apk add --no-cache dumb-init openssl

# 非root用户
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

WORKDIR /app

# 仅复制生产必要文件
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./
COPY --from=builder --chown=nodejs:nodejs /app/prisma ./prisma

USER nodejs

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

# 使用dumb-init处理信号
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/main.js"]

# ─── 阶段4: 开发运行 ───
FROM builder AS development

ENV NODE_ENV=development

CMD ["npm", "run", "start:dev"]
```

#### 3.1.3 Vue3前端

```dockerfile
# ============================================================
# Dockerfile.frontend — Vue3 SPA静态资源
# 构建: docker build -f Dockerfile.frontend -t deepnovel-frontend .
# ============================================================
# syntax=docker/dockerfile:1.7

# ─── 阶段1: 构建 ───
FROM node:20.12.2-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f pnpm-lock.yaml ]; then \
      npm install -g pnpm && pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm install; \
    fi

COPY . .
RUN npm run build

# ─── 阶段2: Nginx生产运行 ───
FROM nginx:1.26-alpine AS production

# 安全: 使用非root用户
RUN addgroup -g 1001 -S nginxuser && adduser -S nginxuser -u 1001

# 复制自定义Nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder --chown=nginxuser:nginxuser /app/dist /usr/share/nginx/html

# 调整Nginx以非root运行
RUN chown -R nginxuser:nginxuser /var/cache/nginx \
    /var/log/nginx /usr/share/nginx/html \
    && touch /var/run/nginx.pid \
    && chown nginxuser:nginxuser /var/run/nginx.pid

USER nginxuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

#### 3.1.4 Nginx配置

```nginx
# nginx.conf — 前端静态资源 + API代理
server {
    listen 8080;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # 前端路由（Vue Router history模式）
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # WebSocket升级支持（通过Traefik时不需要，直连时需要）
    location /ws {
        proxy_pass http://bff:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

### 3.2 .dockerignore优化

```gitignore
# .dockerignore — 减少构建上下文，提升构建速度

# Git
.git
.gitignore
.gitattributes

# CI/CD
.github
.gitlab-ci.yml

# 文档
*.md
docs/
doc/

# 测试
tests/
*.test.ts
*.test.js
*.spec.ts
*.spec.js
coverage/

# 开发环境
.env
.env.*
!.env.example
.vscode/
.idea/
*.swp
*.swo

# 依赖（在容器内安装）
node_modules/
venv/
__pycache__/
*.pyc
*.pyo
.mypy_cache/
.pytest_cache/

# 构建产物
frontend/dist/
frontend/dist-ssr/
bff/dist/
*.egg-info/
dist/
build/

# 数据
data/
*.tar
*.tar.gz
docker-images/

# 日志
logs/
*.log

# OS
.DS_Store
Thumbs.db
```

### 3.3 Docker BuildKit优化配置

```json
// docker-bake.hcl — 高级构建配置
// 使用: docker buildx bake

group "default" {
    targets = ["ai", "bff", "frontend"]
}

variable "REGISTRY" {
    default = "ghcr.io/laihuiwen"
}

variable "VERSION" {
    default = "latest"
}

target "docker-metadata-action" {}

target "ai" {
    inherits = ["docker-metadata-action"]
    dockerfile = "Dockerfile.ai"
    tags = ["${REGISTRY}/deepnovel-ai:${VERSION}"]
    platforms = ["linux/amd64", "linux/arm64"]
    cache-from = ["type=gha"]
    cache-to = ["type=gha,mode=max"]
    output = ["type=registry"]
}

target "bff" {
    inherits = ["docker-metadata-action"]
    dockerfile = "Dockerfile.bff"
    tags = ["${REGISTRY}/deepnovel-bff:${VERSION}"]
    platforms = ["linux/amd64", "linux/arm64"]
    cache-from = ["type=gha"]
    cache-to = ["type=gha,mode=max"]
    output = ["type=registry"]
}

target "frontend" {
    inherits = ["docker-metadata-action"]
    dockerfile = "Dockerfile.frontend"
    tags = ["${REGISTRY}/deepnovel-frontend:${VERSION}"]
    platforms = ["linux/amd64", "linux/arm64"]
    cache-from = ["type=gha"]
    cache-to = ["type=gha,mode=max"]
    output = ["type=registry"]
}
```

---

## 4. Docker Compose编排体系

### 4.1 核心编排文件 (docker-compose.yml)

```yaml
# ============================================================
# docker-compose.yml — 核心服务编排
# 用法:
#   docker compose up -d                    # 仅核心服务
#   docker compose --profile dev up -d      # 含开发工具
#   docker compose --profile monitoring up -d # 含监控栈
#   docker compose --profile full up -d     # 全部服务
# ============================================================

name: deepnovel

x-common-security: &common-security
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - CHOWN
    - SETGID
    - SETUID

x-common-logging: &common-logging
  logging:
    driver: "json-file"
    options:
      max-size: "100m"
      max-file: "5"
      tag: "{{.ImageName}}|{{.Name}}|{{.ImageFullID}}|{{.FullID}}"

x-common-restart: &common-restart
  restart: unless-stopped

services:
  # ─────────────────────────────────────────────
  # 应用层
  # ─────────────────────────────────────────────

  ai-engine:
    build:
      context: .
      dockerfile: Dockerfile.ai
      target: production
    container_name: deepnovel-ai
    <<: [*common-security, *common-logging, *common-restart]
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql://${DB_USER:-deepnovel}:${DB_PASSWORD}@postgres:5432/deepnovel
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
      - OTEL_SERVICE_NAME=deepnovel-ai
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started
      otel-collector:
        condition: service_started
    networks:
      - deepnovel
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 2G
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ai.rule=Host(`api.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.ai.entrypoints=websecure"
      - "traefik.http.routers.ai.tls.certresolver=letsencrypt"
      - "traefik.http.services.ai.loadbalancer.server.port=8000"
      - "traefik.http.middlewares.ai-ratelimit.ratelimit.average=100"
      - "traefik.http.middlewares.ai-ratelimit.ratelimit.burst=200"
      - "traefik.http.routers.ai.middlewares=ai-ratelimit"

  bff:
    build:
      context: ./bff
      dockerfile: Dockerfile.bff
      target: production
    container_name: deepnovel-bff
    <<: [*common-security, *common-logging, *common-restart]
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=50m
    environment:
      - NODE_ENV=production
      - PORT=3000
      - AI_ENGINE_URL=http://ai-engine:8000
      - DATABASE_URL=postgresql://${DB_USER:-deepnovel}:${DB_PASSWORD}@postgres:5432/deepnovel
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
      - OTEL_SERVICE_NAME=deepnovel-bff
    env_file:
      - .env
    ports:
      - "3000:3000"
    depends_on:
      - ai-engine
      - postgres
      - redis
    networks:
      - deepnovel
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.bff.rule=Host(`bff.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.bff.entrypoints=websecure"
      - "traefik.http.routers.bff.tls.certresolver=letsencrypt"
      - "traefik.http.services.bff.loadbalancer.server.port=3000"
      - "traefik.http.middlewares.bff-ratelimit.ratelimit.average=200"
      - "traefik.http.middlewares.bff-ratelimit.ratelimit.burst=400"
      - "traefik.http.routers.bff.middlewares=bff-ratelimit"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
      target: production
    container_name: deepnovel-frontend
    <<: [*common-security, *common-logging, *common-restart]
    read_only: true
    ports:
      - "80:8080"
    depends_on:
      - bff
    networks:
      - deepnovel
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`${DOMAIN:-localhost}`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
      - "traefik.http.services.frontend.loadbalancer.server.port=8080"
      - "traefik.http.middlewares.frontend-compress.compress=true"
      - "traefik.http.routers.frontend.middlewares=frontend-compress"

  # ─────────────────────────────────────────────
  # 数据层
  # ─────────────────────────────────────────────

  postgres:
    image: postgres:16.3-alpine
    container_name: deepnovel-postgres
    <<: [*common-security, *common-logging, *common-restart]
    environment:
      - POSTGRES_DB=deepnovel
      - POSTGRES_USER=${DB_USER:-deepnovel}
      - POSTGRES_PASSWORD=${DB_PASSWORD:-deepnovel}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - type: volume
        source: postgres_data
        target: /var/lib/postgresql/data
      - type: bind
        source: ./config/init/postgres
        target: /docker-entrypoint-initdb.d
        read_only: true
    ports:
      - "5432:5432"
    networks:
      - deepnovel
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-deepnovel}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  redis:
    image: redis:7.2.4-alpine
    container_name: deepnovel-redis
    <<: [*common-security, *common-logging, *common-restart]
    command: >
      redis-server
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - type: volume
        source: redis_data
        target: /data
    ports:
      - "6379:6379"
    networks:
      - deepnovel
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.25'
          memory: 512M

  qdrant:
    image: qdrant/qdrant:v1.12.0
    container_name: deepnovel-qdrant
    <<: [*common-security, *common-logging, *common-restart]
    volumes:
      - type: volume
        source: qdrant_data
        target: /qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - deepnovel
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  # ─────────────────────────────────────────────
  # 网关层
  # ─────────────────────────────────────────────

  traefik:
    image: traefik:v3.1
    container_name: deepnovel-traefik
    <<: [*common-security, *common-logging, *common-restart]
    command:
      - "--api.dashboard=true"
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=deepnovel"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL:-admin@localhost}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--accesslog=true"
      - "--accesslog.format=json"
      - "--metrics.prometheus=true"
      - "--tracing=true"
      - "--tracing.otlp=true"
      - "--tracing.otlp.http=true"
      - "--tracing.otlp.http.endpoint=http://otel-collector:4318"
      - "--log.level=${TRAEFIK_LOG_LEVEL:-INFO}"
      - "--log.format=json"
      - "--ping=true"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - type: bind
        source: /var/run/docker.sock
        target: /var/run/docker.sock
        read_only: true
      - type: volume
        source: letsencrypt_data
        target: /letsencrypt
    networks:
      - deepnovel
    healthcheck:
      test: ["CMD", "traefik", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 3
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`traefik.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.tls.certresolver=letsencrypt"
      - "traefik.http.routers.dashboard.middlewares=auth@file"
      - "traefik.http.middlewares.auth@file.basicauth.users=${TRAEFIK_DASHBOARD_AUTH:-}""

  # ─────────────────────────────────────────────
  # 可观测性层
  # ─────────────────────────────────────────────

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.100.0
    container_name: deepnovel-otel
    <<: [*common-logging, *common-restart]
    command: ["--config=/etc/otelcol-contrib/config.yaml"]
    volumes:
      - type: bind
        source: ./config/otel/otel-collector-config.yaml
        target: /etc/otelcol-contrib/config.yaml
        read_only: true
    ports:
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
      - "8888:8888"     # Metrics
    networks:
      - deepnovel
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  prometheus:
    image: prom/prometheus:v2.52.0
    container_name: deepnovel-prometheus
    <<: [*common-security, *common-logging, *common-restart]
    profiles:
      - monitoring
      - full
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--enable-feature=otlp-write-receiver'
      - '--enable-feature=exemplar-storage'
    volumes:
      - type: bind
        source: ./config/prometheus/prometheus.yml
        target: /etc/prometheus/prometheus.yml
        read_only: true
      - type: volume
        source: prometheus_data
        target: /prometheus
    ports:
      - "9090:9090"
    networks:
      - deepnovel

  grafana:
    image: grafana/grafana:10.4.2
    container_name: deepnovel-grafana
    <<: [*common-security, *common-logging, *common-restart]
    profiles:
      - monitoring
      - full
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://grafana.${DOMAIN:-localhost}
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    volumes:
      - type: volume
        source: grafana_data
        target: /var/lib/grafana
      - type: bind
        source: ./config/grafana/provisioning
        target: /etc/grafana/provisioning
        read_only: true
      - type: bind
        source: ./config/grafana/dashboards
        target: /var/lib/grafana/dashboards
        read_only: true
    ports:
      - "3001:3000"
    networks:
      - deepnovel
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.grafana.entrypoints=websecure"
      - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
      - "traefik.http.services.grafana.loadbalancer.server.port=3000"

  loki:
    image: grafana/loki:3.0.0
    container_name: deepnovel-loki
    <<: [*common-security, *common-logging, *common-restart]
    profiles:
      - monitoring
      - full
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - type: bind
        source: ./config/loki/loki-config.yaml
        target: /etc/loki/local-config.yaml
        read_only: true
      - type: volume
        source: loki_data
        target: /loki
    ports:
      - "3100:3100"
    networks:
      - deepnovel

  jaeger:
    image: jaegertracing/all-in-one:1.57.0
    container_name: deepnovel-jaeger
    <<: [*common-logging, *common-restart]
    profiles:
      - monitoring
      - full
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"
    networks:
      - deepnovel

  # ─────────────────────────────────────────────
  # 开发工具层 (profile: dev)
  # ─────────────────────────────────────────────

  adminer:
    image: adminer:4.8.1
    container_name: deepnovel-adminer
    <<: [*common-logging, *common-restart]
    profiles:
      - dev
      - full
    ports:
      - "8081:8080"
    networks:
      - deepnovel
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.adminer.rule=Host(`db.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.adminer.entrypoints=websecure"
      - "traefik.http.routers.adminer.tls.certresolver=letsencrypt"

  redis-insight:
    image: redis/redisinsight:2.48.0
    container_name: deepnovel-redis-insight
    <<: [*common-logging, *common-restart]
    profiles:
      - dev
      - full
    ports:
      - "5540:5540"
    networks:
      - deepnovel

  mailhog:
    image: mailhog/mailhog:v1.0.1
    container_name: deepnovel-mailhog
    <<: [*common-logging, *common-restart]
    profiles:
      - dev
      - full
    ports:
      - "1025:1025"
      - "8025:8025"
    networks:
      - deepnovel
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mailhog.rule=Host(`mail.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.mailhog.entrypoints=websecure"
      - "traefik.http.routers.mailhog.tls.certresolver=letsencrypt"

  # ─────────────────────────────────────────────
  # 测试层 (profile: test)
  # ─────────────────────────────────────────────

  test-db:
    image: postgres:16.3-alpine
    container_name: deepnovel-test-db
    <<: [*common-logging]
    profiles:
      - test
    environment:
      - POSTGRES_DB=deepnovel_test
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
    tmpfs:
      - /var/lib/postgresql/data:size=500m
    ports:
      - "5433:5432"
    networks:
      - deepnovel

  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.ai
      target: development
    container_name: deepnovel-test-runner
    <<: [*common-logging]
    profiles:
      - test
    environment:
      - DATABASE_URL=postgresql://test:test@test-db:5432/deepnovel_test
      - REDIS_URL=redis://redis:6379/1
      - APP_ENV=test
      - PYTEST_CURRENT_TEST=1
    volumes:
      - .:/app
      - /app/__pycache__
      - /app/src/__pycache__
      - /app/.pytest_cache
    depends_on:
      - test-db
      - redis
    networks:
      - deepnovel
    command: ["pytest", "-xvs", "--tb=short", "--cov=src", "--cov-report=term-missing", "tests/"]

# ─────────────────────────────────────────────
# 网络与卷
# ─────────────────────────────────────────────

networks:
  deepnovel:
    name: deepnovel
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  qdrant_data:
    driver: local
  letsencrypt_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  loki_data:
    driver: local
```

### 4.2 开发覆盖配置 (docker-compose.override.yml)

```yaml
# docker-compose.override.yml — 开发环境自动加载
# Docker Compose会自动合并此文件，无需-f指定

services:
  ai-engine:
    build:
      target: development
    volumes:
      - ./src:/app/src:cached
      - ./alembic:/app/alembic:cached
      - /app/src/__pycache__
    environment:
      - APP_ENV=development
      - LOG_LEVEL=DEBUG
      - DEBUG=1
    ports:
      - "8000:8000"
      - "5678:5678"  # debugpy端口

  bff:
    build:
      target: development
    volumes:
      - ./bff/src:/app/src:cached
      - ./bff/prisma:/app/prisma:cached
      - /app/node_modules
    environment:
      - NODE_ENV=development
    ports:
      - "3000:3000"
      - "9229:9229"  # Node调试端口

  frontend:
    build:
      target: development
    volumes:
      - ./frontend/src:/app/src:cached
      - ./frontend/public:/app/public:cached
      - ./frontend/index.html:/app/index.html:cached
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - VITE_API_URL=http://localhost:3000
      - VITE_WS_URL=ws://localhost:3000
    ports:
      - "5173:5173"
```

### 4.3 OpenTelemetry Collector配置

```yaml
# config/otel/otel-collector-config.yaml

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

  resource:
    attributes:
      - key: service.namespace
        value: deepnovel
        action: upsert

  memory_limiter:
    limit_mib: 512
    spike_limit_mib: 128

exporters:
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write

  loki:
    endpoint: http://loki:3100/loki/api/v1/push
    labels:
      attributes:
        service.name: service_name
        service.version: service_version

  jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  # 调试输出（开发环境）
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [jaeger]

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheusremotewrite]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki]
```

### 4.4 Prometheus配置

```yaml
# config/prometheus/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: deepnovel
    replica: '{{.ExternalURL}}'

scrape_configs:
  # Prometheus自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Traefik
  - job_name: 'traefik'
    static_configs:
      - targets: ['traefik:8080']
    metrics_path: /metrics

  # AI引擎
  - job_name: 'ai-engine'
    static_configs:
      - targets: ['ai-engine:8000']
    metrics_path: /metrics

  # BFF
  - job_name: 'bff'
    static_configs:
      - targets: ['bff:3000']
    metrics_path: /metrics

  # Node Exporter (主机指标，可选)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # cAdvisor (容器指标，可选)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

# 告警规则
rule_files:
  - /etc/prometheus/rules/*.yml

# AlertManager
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### 4.5 AlertManager配置

```yaml
# config/prometheus/alertmanager.yml

global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@deepnovel.local'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@deepnovel.local'
        subject: '[DeepNovel Alert] {{ .GroupLabels.alertname }}'

  - name: 'slack'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts'
        title: 'DeepNovel Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'service']
```

### 4.6 告警规则

```yaml
# config/prometheus/rules/deepnovel-alerts.yml

groups:
  - name: deepnovel
    rules:
      # AI引擎不可用
      - alert: AIEngineDown
        expr: up{job="ai-engine"} == 0
        for: 1m
        labels:
          severity: critical
          service: ai-engine
        annotations:
          summary: "AI引擎宕机"
          description: "AI引擎 {{ $labels.instance }} 已宕机超过1分钟"

      # BFF不可用
      - alert: BFFDown
        expr: up{job="bff"} == 0
        for: 1m
        labels:
          severity: critical
          service: bff
        annotations:
          summary: "BFF服务宕机"
          description: "BFF {{ $labels.instance }} 已宕机超过1分钟"

      # 高错误率
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "高错误率"
          description: "服务 {{ $labels.service }} 错误率超过10%"

      # 响应时间过高
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应延迟过高"
          description: "P95延迟超过2秒"

      # PostgreSQL连接数高
      - alert: PostgresHighConnections
        expr: pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL连接数高"
          description: "活跃连接数: {{ $value }}"

      # Redis内存高
      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis内存使用率过高"
          description: "使用率: {{ $value | humanizePercentage }}"

      # 磁盘空间不足
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "磁盘空间不足"
          description: "分区 {{ $labels.device }} 剩余空间不足10%"
```

---

## 5. 应用层可观测性接入

### 5.1 Python AI引擎接入

```python
# src/deepnovel/core/telemetry.py
"""OpenTelemetry全链路追踪与指标采集"""

import os
from contextlib import asynccontextmanager

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from deepnovel.utils.logger import get_logger

logger = get_logger(__name__)


def setup_telemetry(app, app_name: str = "deepnovel-ai", app_version: str = "1.0.0"):
    """初始化OpenTelemetry全链路追踪

    自动接入:
    - FastAPI请求追踪（自动记录HTTP方法、路径、状态码、耗时）
    - Redis操作追踪（命令、键、耗时）
    - SQLAlchemy数据库查询追踪（SQL语句、耗时）
    - 自定义业务指标（LLM调用次数、Token消耗、任务队列深度）
    """
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    resource = Resource.create({
        SERVICE_NAME: app_name,
        SERVICE_VERSION: app_version,
        "deployment.environment": os.getenv("APP_ENV", "development"),
        "host.name": os.getenv("HOSTNAME", "localhost"),
    })

    # ─── Traces ───
    trace_provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # ─── Metrics ───
    otlp_metric_exporter = OTLPMetricExporter(endpoint=otel_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=15000)
    metrics_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metrics_provider)

    # ─── Auto-Instrumentation ───
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace_provider,
        meter_provider=metrics_provider,
    )
    RedisInstrumentor().instrument(tracer_provider=trace_provider)
    SQLAlchemyInstrumentor().instrument(
        enable_commenter=True,
        commenter_options={"db_driver": True, "db_framework": True},
        tracer_provider=trace_provider,
    )

    # ─── 自定义业务指标 ───
    meter = metrics.get_meter(app_name)

    # LLM调用指标
    llm_call_counter = meter.create_counter(
        "llm.calls.total",
        description="Total LLM API calls",
    )
    llm_token_histogram = meter.create_histogram(
        "llm.tokens.used",
        description="LLM token consumption",
        unit="token",
    )
    llm_latency_histogram = meter.create_histogram(
        "llm.latency.seconds",
        description="LLM API latency",
        unit="s",
    )

    # 任务指标
    task_counter = meter.create_counter(
        "tasks.total",
        description="Total task executions",
    )
    task_latency = meter.create_histogram(
        "tasks.duration.seconds",
        description="Task execution duration",
        unit="s",
    )

    # RAG指标
    rag_query_counter = meter.create_counter(
        "rag.queries.total",
        description="Total RAG queries",
    )
    rag_latency = meter.create_histogram(
        "rag.latency.seconds",
        description="RAG query latency",
        unit="s",
    )

    logger.info("telemetry_initialized", endpoint=otel_endpoint, service=app_name)

    return {
        "llm_call_counter": llm_call_counter,
        "llm_token_histogram": llm_token_histogram,
        "llm_latency_histogram": llm_latency_histogram,
        "task_counter": task_counter,
        "task_latency": task_latency,
        "rag_query_counter": rag_query_counter,
        "rag_latency": rag_latency,
    }


@asynccontextmanager
async def telemetry_lifespan(app):
    """FastAPI lifespan事件处理器"""
    metrics = setup_telemetry(app)
    app.state.telemetry_metrics = metrics
    yield
    # 关闭时flush
    trace.get_tracer_provider().shutdown()
    metrics.get_meter_provider().shutdown()
```

### 5.2 NestJS BFF接入

```typescript
// bff/src/core/telemetry/telemetry.module.ts
import { Module } from '@nestjs/common';
import { OpenTelemetryModule } from 'nestjs-otel';

@Module({
  imports: [
    OpenTelemetryModule.forRoot({
      metrics: {
        hostMetrics: true,
        apiMetrics: {
          enable: true,
        },
      },
    }),
  ],
})
export class TelemetryModule {}

// bff/src/core/telemetry/telemetry.service.ts
import { Injectable } from '@nestjs/common';
import { TraceService } from 'nestjs-otel';
import { Counter, Histogram } from '@opentelemetry/api';

@Injectable()
export class TelemetryService {
  private requestCounter: Counter;
  private requestDuration: Histogram;
  private wsConnectionCounter: Counter;

  constructor(private readonly traceService: TraceService) {
    const meter = traceService.getMeter();
    this.requestCounter = meter.createCounter('bff.requests.total');
    this.requestDuration = meter.createHistogram('bff.request.duration');
    this.wsConnectionCounter = meter.createCounter('websocket.connections.total');
  }

  recordRequest(method: string, path: string, status: number, durationMs: number) {
    this.requestCounter.add(1, { method, path, status: String(status) });
    this.requestDuration.record(durationMs / 1000, { method, path });
  }

  recordWsConnection(userId: string) {
    this.wsConnectionCounter.add(1, { user_id: userId });
  }
}
```

### 5.3 Grafana Dashboards

```json
// config/grafana/dashboards/deepnovel-overview.json (关键面板摘要)
// 因文件较大，此处展示面板结构

{
  "dashboard": {
    "title": "DeepNovel - 系统概览",
    "panels": [
      {
        "title": "服务健康状态",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=~\"ai-engine|bff|frontend\"}",
            "legendFormat": "{{job}}"
          }
        ]
      },
      {
        "title": "HTTP请求速率 (RPS)",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{handler}}"
          }
        ]
      },
      {
        "title": "P95响应延迟",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "LLM调用量 / Token消耗",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(llm_calls_total[5m])",
            "legendFormat": "Calls/sec"
          },
          {
            "expr": "rate(llm_tokens_used_total[5m])",
            "legendFormat": "Tokens/sec"
          }
        ]
      },
      {
        "title": "任务队列深度",
        "type": "gauge",
        "targets": [
          {
            "expr": "celery_tasks_pending",
            "legendFormat": "Pending"
          }
        ]
      },
      {
        "title": "数据库连接数",
        "type": "timeseries",
        "targets": [
          {
            "expr": "pg_stat_activity_count",
            "legendFormat": "Active Connections"
          }
        ]
      },
      {
        "title": "错误率",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

---

## 6. 安全加固体系

### 6.1 容器镜像安全扫描 (CI/CD集成)

```yaml
# .github/workflows/security.yml

name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # 每周一早2点

env:
  REGISTRY: ghcr.io

jobs:
  trivy-image-scan:
    name: Trivy Image Scan
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: read
      security-events: write
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Build images
        run: |
          docker build -f Dockerfile.ai -t deepnovel-ai:scan .
          docker build -f Dockerfile.bff -t deepnovel-bff:scan .
          docker build -f Dockerfile.frontend -t deepnovel-frontend:scan .

      - name: Scan AI Engine
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'deepnovel-ai:scan'
          format: 'sarif'
          output: 'trivy-ai.sarif'

      - name: Scan BFF
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'deepnovel-bff:scan'
          format: 'sarif'
          output: 'trivy-bff.sarif'

      - name: Scan Frontend
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'deepnovel-frontend:scan'
          format: 'sarif'
          output: 'trivy-frontend.sarif'

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-ai.sarif'

  trivy-fs-scan:
    name: Trivy Filesystem Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Run Trivy filesystem scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-fs.sarif'

      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-fs.sarif'

  secret-scan:
    name: Secret Detection
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 0

      - name: Detect secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
          extra_args: --debug --only-verified
```

### 6.2 运行时安全 (Falco)

```yaml
# config/falco/falco.yaml (关键规则)

- rule: Unauthorized Container Privilege Escalation
  desc: Detect privilege escalation attempts
  condition: spawned_process and container and shell_procs
  output: >
    Privilege escalation attempt
    user=%user.name command=%proc.cmdline container=%container.name
  priority: WARNING

- rule: Unexpected Outbound Connection
  desc: Detect unexpected network connections from containers
  condition: outbound and container and not (dst_port in (80, 443, 5432, 6379, 6333))
  output: >
    Unexpected outbound connection
    connection=%fd.name container=%container.name command=%proc.cmdline
  priority: NOTICE

- rule: Sensitive File Access
  desc: Detect access to sensitive files
  condition: >
    open_read and container and
    (fd.name contains "/etc/shadow" or
     fd.name contains "/etc/passwd" or
     fd.name contains "/proc/")
  output: >
    Sensitive file access
    file=%fd.name user=%user.name command=%proc.cmdline container=%container.name
  priority: WARNING
```

### 6.3 网络安全策略

```yaml
# docker-compose.security.yml — 额外安全层

services:
  ai-engine:
    security_opt:
      - seccomp:./config/security/seccomp-ai.json
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    networks:
      deepnovel:
        aliases:
          - ai-internal

  bff:
    security_opt:
      - seccomp:./config/security/seccomp-node.json
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=50m
```

---

## 7. CI/CD流水线

### 7.1 完整GitHub Actions工作流

```yaml
# .github/workflows/ci-cd.yml

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository_owner }}/deepnovel

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ─── 阶段1: 代码质量 ───
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 1

      - name: Setup Python
        uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b
        with:
          python-version: '3.12'

      - name: Setup Node
        uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af
        with:
          node-version: '20'

      - name: Cache pip
        uses: actions/cache@6849a6489940f00c2f30c0fb92c6274307ccb58a
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: Python lint
        run: |
          pip install ruff mypy
          ruff check src/
          ruff format --check src/
          mypy src/ --ignore-missing-imports

      - name: Node.js lint
        run: |
          cd bff && npm ci && npm run lint
          cd ../frontend && npm ci && npm run lint

  # ─── 阶段2: 测试 ───
  test-python:
    name: Python Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: deepnovel_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Setup Python
        uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b
        with:
          python-version: '3.12'

      - name: Cache pip
        uses: actions/cache@6849a6489940f00c2f30c0fb92c6274307ccb58a
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/deepnovel_test
          REDIS_URL: redis://localhost:6379/0
          APP_ENV: test
        run: pytest -xvs --cov=src --cov-report=xml --tb=short tests/

      - name: Upload coverage
        uses: codecov/codecov-action@985343d70564a82044c1b7fcb84c2fa05405c1a2
        with:
          file: ./coverage.xml
          flags: python

  test-node:
    name: Node.js Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Setup Node
        uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af
        with:
          node-version: '20'

      - name: Cache npm
        uses: actions/cache@6849a6489940f00c2f30c0fb92c6274307ccb58a
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

      - name: BFF tests
        run: |
          cd bff
          npm ci
          npm run test:cov

      - name: Frontend tests
        run: |
          cd frontend
          npm ci
          npm run test:unit -- --coverage

  # ─── 阶段3: 构建 ───
  build:
    name: Build & Push Images
    needs: [lint, test-python, test-node]
    if: github.event_name != 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
    strategy:
      matrix:
        service: [ai, bff, frontend]
        include:
          - service: ai
            dockerfile: Dockerfile.ai
            context: .
          - service: bff
            dockerfile: Dockerfile.bff
            context: ./bff
          - service: frontend
            dockerfile: Dockerfile.frontend
            context: ./frontend
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@c47758b77c9736f4b2ef4073d4d51994fabfe349

      - name: Login to GHCR
        uses: docker/login-action@9780b0c442fbb1117ed29e0efdff1e18412f7567
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@8e5442c4ef9f78752691e2d8f8d19755c6f78e81
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.service }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=,suffix=,format=short

      - name: Build and push
        uses: docker/build-push-action@4f58ea79222b3b9dc2c8bbdd6debcef730109a75
        with:
          context: ${{ matrix.context }}
          file: ${{ matrix.dockerfile }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          sbom: true
          provenance: true
          platforms: linux/amd64,linux/arm64

  # ─── 阶段4: 安全扫描 ───
  security:
    name: Security Scan
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: read
      security-events: write
    strategy:
      matrix:
        service: [ai, bff, frontend]
    steps:
      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.service }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-${{ matrix.service }}.sarif'

      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-${{ matrix.service }}.sarif'

  # ─── 阶段5: 发布 ───
  release:
    name: Semantic Release
    needs: [build, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Node
        uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af
        with:
          node-version: '20'

      - name: Semantic Release
        run: |
          npm install -g semantic-release @semantic-release/changelog @semantic-release/git
          semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # ─── 阶段6: 部署到预发布 ───
  deploy-staging:
    name: Deploy to Staging
    needs: release
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683

      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/deepnovel
            docker compose pull
            docker compose up -d
            docker system prune -f
```

### 7.2 Semantic Release配置

```json
// .releaserc.json

{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    [
      "@semantic-release/git",
      {
        "assets": ["CHANGELOG.md", "package.json"],
        "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
      }
    ],
    "@semantic-release/github"
  ]
}
```

### 7.3 Commit规范

```
<type>(<scope>): <subject>

<body>

<footer>

类型(Type):
  feat:     新功能 (触发minor版本)
  fix:      修复bug (触发patch版本)
  docs:     文档更新
  style:    代码格式 (不影响功能)
  refactor: 重构 (不添加功能也不修复bug)
  perf:     性能优化
  test:     测试相关
  chore:    构建/工具/依赖更新
  ci:       CI/CD配置
  infra:    基础设施变更

范围(Scope):
  ai:       Python AI引擎
  bff:      NestJS BFF网关
  frontend: Vue3前端
  db:       数据库/存储
  api:      API接口
  deps:     依赖更新

示例:
  feat(ai): 添加GPT-4o支持
  fix(bff): 修复WebSocket连接泄漏
  docs: 更新部署文档
  infra(docker): 优化AI引擎镜像大小
```

---

## 8. 一键部署体系

### 8.1 Taskfile (跨平台任务管理)

```yaml
# Taskfile.yml — 项目任务定义

version: '3'

vars:
  PROJECT_NAME: deepnovel
  COMPOSE_FILE: docker-compose.yml
  REGISTRY: ghcr.io/laihuiwen
  VERSION:
    sh: git describe --tags --always --dirty 2>/dev/null || echo "dev"

tasks:
  default:
    desc: 显示可用任务
    cmds:
      - task --list

  # ─── 初始化 ───
  setup:
    desc: 交互式环境初始化向导
    prompt: 这将设置DeepNovel开发环境，继续?
    deps: [check-deps, copy-env]
    cmds:
      - echo "==> 正在初始化..."
      - task: network-create
      - task: pull-images
      - echo "==> 初始化完成!"
      - echo "==> 请编辑 .env 文件配置您的环境变量"
      - echo "==> 然后运行: task dev"

  check-deps:
    desc: 检查必要依赖
    preconditions:
      - sh: docker --version
        msg: "Docker未安装，请访问 https://docs.docker.com/get-docker/"
      - sh: docker compose version
        msg: "Docker Compose未安装"
      - sh: git --version
        msg: "Git未安装"

  copy-env:
    desc: 复制环境配置文件
    status:
      - test -f .env
    cmds:
      - cp config/.env.example .env
      - echo ".env 文件已创建，请编辑配置"

  network-create:
    desc: 创建Docker网络
    status:
      - docker network inspect deepnovel >/dev/null 2>&1
    cmds:
      - docker network create deepnovel

  pull-images:
    desc: 拉取基础镜像
    cmds:
      - docker compose pull postgres redis qdrant

  # ─── 开发环境 ───
  dev:
    desc: 启动开发环境（含热重载）
    cmds:
      - docker compose up -d postgres redis qdrant
      - echo "==> 等待数据库就绪..."
      - docker compose exec -T postgres pg_isready -U deepnovel
      - echo "==> 启动应用服务..."
      - docker compose up -d ai-engine bff frontend
      - echo "==> 开发环境已启动!"
      - echo "    Frontend: http://localhost:5173"
      - echo "    BFF API:  http://localhost:3000"
      - echo "    AI API:   http://localhost:8000"
      - echo "    Traefik:  http://localhost:8080 (dashboard)"

  dev-with-tools:
    desc: 启动开发环境 + 开发工具
    cmds:
      - docker compose --profile dev up -d
      - echo "==> 附加服务:"
      - echo "    Adminer:      http://localhost:8081"
      - echo "    Redis Insight: http://localhost:5540"
      - echo "    MailHog:      http://localhost:8025"

  dev-logs:
    desc: 查看开发日志
    cmds:
      - docker compose logs -f ai-engine bff frontend

  dev-stop:
    desc: 停止开发环境
    cmds:
      - docker compose down

  # ─── 测试 ───
  test:
    desc: 运行全部测试
    cmds:
      - echo "==> 运行Python测试..."
      - docker compose --profile test up --exit-code-from test-runner
      - echo "==> 运行Node.js测试..."
      - cd bff && npm run test
      - cd ../frontend && npm run test:unit

  test-python:
    desc: 仅运行Python测试
    cmds:
      - docker compose --profile test up --exit-code-from test-runner

  test-e2e:
    desc: 运行E2E测试
    cmds:
      - cd frontend
      - npx playwright test

  # ─── 数据库 ───
  db-migrate:
    desc: 执行数据库迁移
    cmds:
      - docker compose exec ai-engine alembic upgrade head
      - docker compose exec bff npx prisma migrate deploy

  db-reset:
    desc: 重置数据库（危险！）
    prompt: 这将删除所有数据，确认重置?
    cmds:
      - docker compose down -v postgres redis
      - docker volume rm deepnovel_postgres_data deepnovel_redis_data 2>/dev/null || true
      - docker compose up -d postgres redis
      - sleep 5
      - task: db-migrate

  db-seed:
    desc: 填充测试数据
    cmds:
      - docker compose exec ai-engine python scripts/seed_data.py

  db-backup:
    desc: 备份数据库
    cmds:
      - mkdir -p backups
      - docker compose exec -T postgres pg_dumpall -U deepnovel > backups/postgres_{{ now | date "20060102_150405" }}.sql
      - docker compose exec redis redis-cli BGSAVE
      - echo "备份完成: backups/"

  db-restore:
    desc: 恢复数据库
    requires:
      vars: [BACKUP_FILE]
    cmds:
      - docker compose exec -T postgres psql -U deepnovel < {{.BACKUP_FILE}}

  # ─── 构建 ───
  build:
    desc: 构建生产镜像
    cmds:
      - docker compose build

  build-push:
    desc: 构建并推送镜像到仓库
    cmds:
      - docker compose build
      - docker compose push

  # ─── 监控 ───
  monitoring:
    desc: 启动监控栈
    cmds:
      - docker compose --profile monitoring up -d
      - echo "==> 监控面板:"
      - echo "    Grafana:    http://localhost:3001"
      - echo "    Prometheus: http://localhost:9090"
      - echo "    Jaeger:     http://localhost:16686"

  # ─── 安全 ───
  security-scan:
    desc: 扫描镜像安全漏洞
    cmds:
      - docker build -f Dockerfile.ai -t deepnovel-ai:scan .
      - docker build -f Dockerfile.bff -t deepnovel-bff:scan .
      - docker build -f Dockerfile.frontend -t deepnovel-frontend:scan .
      - trivy image deepnovel-ai:scan
      - trivy image deepnovel-bff:scan
      - trivy image deepnovel-frontend:scan

  # ─── 清理 ───
  clean:
    desc: 清理构建缓存和临时文件
    cmds:
      - docker system prune -f
      - docker buildx prune -f
      - find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
      - find . -type d -name "node_modules" -prune -o -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

  clean-all:
    desc: 完全清理（包括数据卷！）
    prompt: 这将删除所有容器和数据卷，确认?
    cmds:
      - docker compose down -v --remove-orphans
      - docker volume prune -f
      - task: clean

  # ─── 信息 ───
  status:
    desc: 查看系统状态
    cmds:
      - echo "=== 容器状态 ==="
      - docker compose ps
      - echo ""
      - echo "=== 资源使用 ==="
      - docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
      - echo ""
      - echo "=== 日志统计 ==="
      - docker compose logs --tail=5 ai-engine bff frontend

  version:
    desc: 显示版本信息
    cmds:
      - echo "DeepNovel {{.VERSION}}"
      - docker --version
      - docker compose version
      - git --version
```

### 8.2 环境验证脚本

```bash
#!/bin/bash
# scripts/validate-env.sh — 环境变量验证

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REQUIRED_VARS=(
    "DATABASE_URL"
    "REDIS_URL"
    "JWT_SECRET"
    "OPENAI_API_KEY"
)

WARN_VARS=(
    "SENTRY_DSN"
    "SMTP_HOST"
    "BACKUP_S3_BUCKET"
)

ERRORS=0
WARNINGS=0

echo "=== DeepNovel 环境验证 ==="
echo ""

# 检查必需变量
echo "检查必需环境变量..."
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo -e "${RED}  [缺失] ${var}${NC}"
        ((ERRORS++))
    else
        # 隐藏敏感值
        if [[ "$var" == *SECRET* ]] || [[ "$var" == *KEY* ]] || [[ "$var" == *PASSWORD* ]]; then
            echo -e "${GREEN}  [OK]   ${var} = ********${NC}"
        else
            echo -e "${GREEN}  [OK]   ${var} = ${!var}${NC}"
        fi
    fi
done

echo ""
echo "检查可选环境变量..."
for var in "${WARN_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo -e "${YELLOW}  [未设置] ${var} (可选)${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}  [OK]     ${var}${NC}"
    fi
done

echo ""

# 检查Docker
echo "检查Docker环境..."
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}  [错误] Docker守护进程未运行${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}  [OK]   Docker运行正常${NC}"
fi

if ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}  [错误] Docker Compose未安装${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}  [OK]   Docker Compose运行正常${NC}"
fi

# 检查端口占用
echo ""
echo "检查端口占用..."
PORTS=(80 443 3000 8000 5432 6379)
for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN >/dev/null 2>&1; then
        echo -e "${YELLOW}  [警告] 端口 $port 已被占用${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}  [OK]   端口 $port 可用${NC}"
    fi
done

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}验证失败: ${ERRORS}个错误，${WARNINGS}个警告${NC}"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "${YELLOW}验证通过: ${WARNINGS}个可选变量未设置${NC}"
    exit 0
else
    echo -e "${GREEN}验证通过: 所有检查通过!${NC}"
    exit 0
fi
```

### 8.3 一键安装脚本

```bash
#!/bin/bash
# install.sh — DeepNovel 一键安装脚本
# 用法: curl -fsSL https://deepnovel.local/install.sh | bash

set -euo pipefail

REPO_URL="https://github.com/Laihuiwen/AI-Novels"
INSTALL_DIR="${INSTALL_DIR:-$HOME/deepnovel}"

echo "========================================"
echo "  DeepNovel 企业级AI小说平台 - 安装脚本"
echo "========================================"
echo ""

# 检查系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "错误: 不支持的操作系统: $OSTYPE"
    exit 1
fi

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "Docker未安装，正在安装..."
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker $USER
    echo "Docker安装完成，请重新登录以应用权限变更"
    exit 0
fi

# 检查Task
if ! command -v task &> /dev/null; then
    echo "Task未安装，正在安装..."
    if [[ "$OS" == "linux" ]]; then
        sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
        export PATH="$HOME/.local/bin:$PATH"
    else
        brew install go-task
    fi
fi

# 克隆仓库
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "克隆仓库到 $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# 初始化环境
echo ""
echo "初始化环境..."
task setup

echo ""
echo "========================================"
echo "  安装完成!"
echo "========================================"
echo ""
echo "下一步:"
echo "  1. 编辑 .env 文件配置环境变量"
echo "  2. 运行: task dev"
echo "  3. 访问: http://localhost:5173"
echo ""
echo "常用命令:"
echo "  task dev         - 启动开发环境"
echo "  task dev-logs    - 查看日志"
echo "  task test        - 运行测试"
echo "  task monitoring  - 启动监控"
echo "  task --list      - 查看所有命令"
echo ""
```

---

## 9. Kubernetes生产部署

### 9.1 项目结构

```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml (encrypted with Sealed Secrets)
│   ├── postgres/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── redis/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── qdrant/
│   │   ├── statefulset.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── ai-engine/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── pdb.yaml
│   ├── bff/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── pdb.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pdb.yaml
│   ├── traefik/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingressroute.yaml
│   │   └── middleware.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── development/
│   │   ├── kustomization.yaml
│   │   ├── replica-count.yaml
│   │   └── resource-limits.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   ├── replica-count.yaml
│   │   ├── resource-limits.yaml
│   │   └── ingress-patch.yaml
│   └── production/
│       ├── kustomization.yaml
│       ├── replica-count.yaml
│       ├── resource-limits.yaml
│       ├── ingress-patch.yaml
│       ├── pdb.yaml
│       └── backup-cronjob.yaml
└── helm/
    └── deepnovel/
        ├── Chart.yaml
        ├── values.yaml
        ├── values-production.yaml
        └── templates/
            ├── _helpers.tpl
            ├── deployment.yaml
            ├── service.yaml
            ├── ingress.yaml
            ├── hpa.yaml
            ├── pdb.yaml
            └── secret.yaml
```

### 9.2 AI引擎Deployment (关键配置)

```yaml
# k8s/base/ai-engine/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: deepnovel-ai
  labels:
    app: deepnovel-ai
    version: v1
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: deepnovel-ai
  template:
    metadata:
      labels:
        app: deepnovel-ai
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: deepnovel-ai
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        fsGroup: 65532
      containers:
        - name: ai
          image: ghcr.io/laihuiwen/deepnovel-ai:latest
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8000
              protocol: TCP
          env:
            - name: APP_ENV
              value: "production"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: deepnovel-secrets
                  key: database-url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: deepnovel-secrets
                  key: redis-url
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.monitoring:4317"
            - name: OTEL_SERVICE_NAME
              value: "deepnovel-ai"
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 60
            periodSeconds: 30
            timeoutSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health/ready
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 100Mi
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values:
                        - deepnovel-ai
                topologyKey: kubernetes.io/hostname
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: deepnovel-ai
```

### 9.3 HPA (水平自动伸缩)

```yaml
# k8s/base/ai-engine/hpa.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: deepnovel-ai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: deepnovel-ai
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
```

### 9.4 ArgoCD Application

```yaml
# k8s/argocd/application.yaml

apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: deepnovel
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/Laihuiwen/AI-Novels
    targetRevision: main
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

---

## 10. 数据备份与灾难恢复

### 10.1 备份策略

```yaml
# docker-compose.backup.yml

services:
  pg-backup:
    image: offen/docker-volume-backup:v2
    profiles:
      - backup
    environment:
      BACKUP_CRON_EXPRESSION: "0 2 * * *"
      BACKUP_RETENTION_DAYS: "30"
      BACKUP_FILENAME: "postgres-%Y-%m-%dT%H-%M-%S.tar.gz"
      AWS_S3_BUCKET_NAME: ${BACKUP_S3_BUCKET}
      AWS_ACCESS_KEY_ID: ${BACKUP_AWS_KEY}
      AWS_SECRET_ACCESS_KEY: ${BACKUP_AWS_SECRET}
      AWS_S3_ENDPOINT: ${BACKUP_S3_ENDPOINT:-s3.amazonaws.com}
      NOTIFICATION_URLS: ${BACKUP_NOTIFICATION_URL}
    volumes:
      - postgres_data:/backup/data:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - deepnovel

  redis-backup:
    image: offen/docker-volume-backup:v2
    profiles:
      - backup
    environment:
      BACKUP_CRON_EXPRESSION: "0 3 * * *"
      BACKUP_RETENTION_DAYS: "14"
      BACKUP_FILENAME: "redis-%Y-%m-%dT%H-%M-%S.tar.gz"
      AWS_S3_BUCKET_NAME: ${BACKUP_S3_BUCKET}
    volumes:
      - redis_data:/backup/data:ro
    networks:
      - deepnovel

  qdrant-snapshot:
    image: curlimages/curl:latest
    profiles:
      - backup
    entrypoint: >
      sh -c '
      while true; do
        sleep 86400;
        curl -X POST http://qdrant:6333/snapshots;
      done
      '
    networks:
      - deepnovel
```

### 10.2 备份脚本

```bash
#!/bin/bash
# scripts/backup.sh — 统一备份脚本

set -euo pipefail

BACKUP_DIR="/backup/deepnovel/$(date +%Y%m%d_%H%M%S)"
RETENTION_DAYS=30
S3_BUCKET="${BACKUP_S3_BUCKET:-}"

echo "=== DeepNovel 备份开始: $(date) ==="
mkdir -p "$BACKUP_DIR"

# PostgreSQL逻辑备份
echo "备份 PostgreSQL..."
docker compose exec -T postgres pg_dumpall -U deepnovel | gzip > "$BACKUP_DIR/postgres.sql.gz"

# Redis RDB备份
echo "备份 Redis..."
docker compose exec redis redis-cli BGSAVE
sleep 2
docker cp "$(docker compose ps -q redis):/data/dump.rdb" "$BACKUP_DIR/redis.rdb"

# Qdrant快照
echo "备份 Qdrant..."
curl -s -X POST http://localhost:6333/snapshots > "$BACKUP_DIR/qdrant_snapshot.json"

# 配置备份
echo "备份配置..."
tar czf "$BACKUP_DIR/config.tar.gz" config/ .env

# 打包
echo "打包备份..."
tar czf "$BACKUP_DIR.tar.gz" -C "$(dirname $BACKUP_DIR)" "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

# 上传到S3
if [[ -n "$S3_BUCKET" ]]; then
    echo "上传到S3..."
    aws s3 cp "$BACKUP_DIR.tar.gz" "s3://$S3_BUCKET/backups/"
fi

# 清理旧备份
echo "清理 ${RETENTION_DAYS} 天前的备份..."
find /backup/deepnovel -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "=== 备份完成: $BACKUP_DIR.tar.gz ==="
```

---

## 11. 实施计划

### 11.1 里程碑

| 阶段 | 时间 | 交付物 | 验收标准 |
|-----|------|--------|---------|
| **Phase 1: 容器化** | 第1-2周 | Dockerfile × 3、docker-compose.yml | `docker compose up` 一键启动全部服务 |
| **Phase 2: 可观测性** | 第3-4周 | OTel采集器、Grafana面板、告警规则 | 全链路Trace可见、P95延迟<2s告警 |
| **Phase 3: CI/CD** | 第5-6周 | GitHub Actions流水线、镜像仓库 | main分支push自动构建并推送镜像 |
| **Phase 4: 安全** | 第7周 | Trivy扫描、Falco规则、Secrets加密 | CI通过、无高危CVE |
| **Phase 5: K8s** | 第8-10周 | Helm Chart、Kustomize、ArgoCD | 生产环境滚动更新零停机 |
| **Phase 6: 自动化** | 第11-12周 | Taskfile、一键脚本、备份策略 | 新开发者5分钟完成环境搭建 |

### 11.2 文件变更清单

#### 新增文件

```
Dockerfile.ai                              # Python AI引擎容器
Dockerfile.bff                             # NestJS BFF容器
Dockerfile.frontend                        # Vue3前端容器
.dockerignore                              # Docker构建上下文忽略

docker-compose.yml                         # 核心服务编排
docker-compose.override.yml                # 开发覆盖
docker-compose.security.yml                # 安全配置
docker-compose.backup.yml                  # 备份编排

docker-bake.hcl                            # BuildKit高级构建

config/otel/otel-collector-config.yaml     # OTel采集器配置
config/prometheus/prometheus.yml           # Prometheus配置
config/prometheus/alertmanager.yml         # 告警管理器
config/prometheus/rules/                   # 告警规则目录
  ├── deepnovel-alerts.yml
  └── system-alerts.yml
config/grafana/provisioning/               # Grafana自动化配置
  ├── dashboards/
  │   ├── deepnovel-overview.json
  │   ├── deepnovel-ai-engine.json
  │   ├── deepnovel-bff.json
  │   └── deepnovel-database.json
  └── datasources/
      └── datasources.yml
config/loki/loki-config.yaml               # Loki日志配置
config/falco/falco.yaml                    # Falco运行时安全
config/security/                           # 安全配置文件
  ├── seccomp-ai.json
  └── seccomp-node.json
config/init/postgres/                      # PostgreSQL初始化
  └── 001_schema.sql

frontend/nginx.conf                        # Nginx静态服务配置
bff/nginx.conf                             # (如需要)

taskfile.yml                               # 统一任务管理
scripts/
  ├── validate-env.sh                      # 环境验证
  ├── backup.sh                            # 备份脚本
  ├── restore.sh                           # 恢复脚本
  ├── install.sh                           # 一键安装
  └── health-check.sh                      # 健康检查

.github/
  ├── workflows/
  │   ├── ci-cd.yml                        # 主CI/CD流水线
  │   ├── security.yml                     # 安全扫描
  │   └── dependency-review.yml            # 依赖审查
  └── dependabot.yml                       # 自动依赖更新

.releaserc.json                            # 语义化发布配置

k8s/                                       # Kubernetes部署
  ├── base/
  ├── overlays/
  └── helm/
```

#### 修改文件

```
config/.env.example                        # 增加新环境变量
config/docker-compose.yaml                 # 标记deprecated，迁移到新配置
start_server.py                            # 增加OTel初始化
docs/DEPLOYMENT.md                         # 更新为容器化部署指南
doc/06-部署流程文档.md                       # 更新中文部署文档
scripts/manage-server.sh                   # 标记deprecated
scripts/restart-server.bat                 # 标记deprecated
scripts/server-manager.ps1                 # 标记deprecated
```

#### 废弃文件

```
docker-images/*.tar                        # 迁移到镜像仓库
scripts/start_server_simple.py             # 由Taskfile替代
scripts/run_server.py                      # 由Taskfile替代
```

---

## 12. 环境变量清单

```bash
# .env — 完整环境变量参考

# ═══════════════════════════════════════
# 基础配置
# ═══════════════════════════════════════
DOMAIN=localhost                          # 生产环境: deepnovel.local
ACME_EMAIL=admin@deepnovel.local          # Let's Encrypt邮箱
LOG_LEVEL=INFO                            # DEBUG | INFO | WARN | ERROR

# ═══════════════════════════════════════
# 数据库
# ═══════════════════════════════════════
DB_USER=deepnovel
DB_PASSWORD=changeme-strong-password
DB_NAME=deepnovel
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}

# Redis
REDIS_PASSWORD=changeme-redis-password
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

# ═══════════════════════════════════════
# 应用安全
# ═══════════════════════════════════════
JWT_SECRET=changeme-jwt-secret-min-32-chars
JWT_EXPIRY=24h
ENCRYPTION_KEY=changeme-encryption-key

# ═══════════════════════════════════════
# LLM API密钥
# ═══════════════════════════════════════
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# ═══════════════════════════════════════
# 可观测性
# ═══════════════════════════════════════
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=deepnovel
SENTRY_DSN=https://...@sentry.io/...

# ═══════════════════════════════════════
# 监控
# ═══════════════════════════════════════
GRAFANA_USER=admin
GRAFANA_PASSWORD=changeme-grafana
TRAEFIK_DASHBOARD_AUTH=admin:$$apr1$$H6uskkkW$$IgXLP6ewTrSuBkTrqE8wj/  # admin:admin

# ═══════════════════════════════════════
# 备份
# ═══════════════════════════════════════
BACKUP_S3_BUCKET=deepnovel-backups
BACKUP_AWS_KEY=AKIA...
BACKUP_AWS_SECRET=...
BACKUP_S3_ENDPOINT=s3.amazonaws.com
BACKUP_NOTIFICATION_URL=

# ═══════════════════════════════════════
# 告警
# ═══════════════════════════════════════
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
PAGERDUTY_KEY=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# ═══════════════════════════════════════
# 对象存储 (MinIO/S3)
# ═══════════════════════════════════════
MINIO_ROOT_USER=deepnovel
MINIO_ROOT_PASSWORD=changeme-minio
S3_ENDPOINT=http://minio:9000
S3_BUCKET=deepnovel-uploads
S3_ACCESS_KEY=
S3_SECRET_KEY=
```

---

## 13. 总结

### 13.1 重构前后对比

| 维度 | 重构前 | 重构后 |
|-----|-------|-------|
| 容器化 | 无Dockerfile | 3个多阶段Dockerfile，BuildKit优化 |
| 编排 | 单一docker-compose（仅基础设施） | Profile分层，dev/test/monitoring隔离 |
| 部署 | 手动start_server.py | Taskfile一键管理，GitHub Actions全自动 |
| 可观测性 | 无 | PLG + OpenTelemetry全链路 |
| 安全 | 无 | Trivy扫描 + Falco运行时 + 安全上下文 |
| K8s | 无 | Helm + Kustomize + ArgoCD GitOps |
| 备份 | 无 | Restic自动化 + S3归档 + 保留策略 |
| 网关 | 无 | Traefik自动HTTPS + Rate Limit + WAF |
| 开发者体验 | Windows批处理 + PowerShell + Bash碎片化 | 跨平台Taskfile，5分钟环境搭建 |
| 镜像安全 | latest标签，root用户 | 固定版本，非root，distroless/chainguard |

### 13.2 关键设计决策

1. **Traefik而非Nginx**：Docker标签自动服务发现，内置Rate Limit和Let's Encrypt
2. **Taskfile而非Makefile**：跨平台兼容，更好的依赖管理和错误处理
3. **Chainguard镜像而非Alpine**：零CVE基础镜像，避免musl兼容问题
4. **OpenTelemetry而非Prometheus直接采集**：统一标准，解耦采集与存储
5. **Kustomize + Helm混合**：应用层Kustomize，第三方Helm
6. **Profile而非多个Compose文件**：避免文件爆炸，使用标准Docker Compose特性

### 13.3 与Step14的对齐

| Step14设计 | Step15实现 |
|-----------|-----------|
| NestJS BFF + Python AI引擎微服务 | 独立Dockerfile + 独立Deployment + HPA |
| Redis Streams事件总线 | Redis容器 + Cluster配置 |
| PostgreSQL主数据库 | PostgreSQL容器 + 初始化脚本 + 备份 |
| Qdrant向量数据库 | Qdrant容器 + 快照策略 |
| Pino结构化日志 + OpenTelemetry | OTel Collector → Loki + Jaeger |
| gRPC通信 | 容器网络内部通信 |
| Celery异步任务队列 | Redis作为Broker + 单独Worker Deployment |
| WebSocket实时推送 | Traefik原生WebSocket支持 |
