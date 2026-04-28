<div align="center">

# 🤖 AI-Novels

**基于 Multi-Agent 架构的智能小说生成系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.0+-4FC08D.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[English](README_EN.md) | 简体中文

</div>

---

## 📖 项目简介

AI-Novels 是一个基于 **Multi-Agent 架构** 的智能小说生成系统。系统通过协调多个专业 AI 智能体协同工作，实现从故事构思到完整章节生成的一站式小说创作流程。

### ✨ 核心特性

- **🤖 Multi-Agent 协作**: 10+ 个专业智能体分工协作，涵盖角色设计、世界观构建、大纲规划、内容生成、质量检查等环节
- **🔄 DAG 工作流引擎**: 基于有向无环图的任务编排，支持并行章节生成与依赖管理
- **📡 事件驱动架构**: Event Bus + RocketMQ 实现组件解耦与异步通信
- **🗄️ 异构数据存储**: MySQL + MongoDB + Neo4j + ChromaDB 多数据库协同
- **🔌 多模型支持**: 支持 Ollama、OpenAI、通义千问、Gemini、MiniMax 等多种 LLM 提供商
- **🎨 现代化 UI**: Vue 3 + Element Plus 构建的响应式界面
- **📊 实时监控**: 任务进度、系统健康状态实时监控

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│                   Vue 3 + Element Plus                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│                    FastAPI + Middleware                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Core Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Coordinator │  │  Event Bus  │  │      DAG Engine         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │  MySQL   │ │ MongoDB  │ │  Neo4j   │ │ ChromaDB │ │RocketMQ│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- MongoDB 6.0+
- Neo4j 5.x
- RocketMQ 5.x
- Ollama (本地模型) 或 LLM API 密钥

### 1. 克隆项目

```bash
git clone https://github.com/Ryan-0625/AI-Novels.git
cd AI-Novels
```

### 2. 配置环境

```bash
# 复制配置模板
cp config/.env.example config/.env
cp config/agents.json.template config/agents.json
cp config/database.json.template config/database.json
cp config/llm.json.template config/llm.json

# 编辑配置文件，填入你的实际配置
vim config/.env
vim config/database.json
vim config/llm.json
```

### 3. 后端安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python start_server.py
```

### 4. 前端安装

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 查看界面

---

## 📁 项目结构

```
AI-Novels/
├── src/deepnovel/              # 后端核心代码
│   ├── agents/                 # 智能体实现
│   ├── api/                    # API 层
│   ├── core/                   # 核心模块
│   ├── database/               # 数据库客户端
│   ├── messaging/              # 消息队列
│   └── utils/                  # 工具函数
├── frontend/                   # 前端代码
├── config/                     # 配置文件
├── scripts/                    # 脚本工具
├── requirements.txt            # Python 依赖
├── start_server.py            # 启动脚本
└── README.md                  # 项目说明
```

---

## 🔧 配置说明

### 环境变量 (.env)

| 变量 | 说明 | 示例 |
|------|------|------|
| `MYSQL_PASSWORD` | MySQL 密码 | your_password |
| `NEO4J_PASSWORD` | Neo4j 密码 | your_password |
| `OPENAI_API_KEY` | OpenAI API 密钥 | sk-... |
| `QWEN_API_KEY` | 通义千问 API 密钥 | sk-... |

### 智能体配置 (agents.json)

```json
{
  "coordinator": {
    "provider": "ollama",
    "model": "qwen2.5-14b",
    "temperature": 0.7
  }
}
```

---

## 🛠️ 技术栈

### 后端
- **Web 框架**: FastAPI + Uvicorn
- **AI/LLM**: OpenAI SDK, Ollama, DashScope
- **数据库**: SQLAlchemy, PyMongo, Neo4j Driver, ChromaDB
- **消息队列**: RocketMQ Python Client
- **配置**: Pydantic Settings

### 前端
- **框架**: Vue 3 + TypeScript
- **UI 库**: Element Plus
- **路由**: Vue Router 4
- **HTTP**: Axios

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

提交信息规范遵循 [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Ollama](https://ollama.ai/) - 本地 LLM 运行环境

---

<div align="center">

**Made with ❤️ by AI-Novels Team**

</div>
