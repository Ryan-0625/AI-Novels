# Step 12: 前端可视化层重构 - 全链路监控与交互式创作面板

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step5 (任务调度), Step6 (RAG), Step7 (小说配置), Step10 (配置层), Step11 (API网关)
> 目标: 构建覆盖小说创作全链路的前端可视化监控与交互式管理面板

---

## 1. 设计哲学

### 1.1 核心转变

```
从：基础React组件 + 轮询API                → 到：TypeScript + Zustand + WebSocket实时推送
从：Step5提及D3.js但无配套前端计划         → 到：完整DAG可视化 + 节点状态实时着色
从：前端直接调用API，无状态管理规划         → 到：Zustand分层状态管理 + API服务层抽象
从：无小说配置可视化界面                   → 到：NovelConfig表单化配置 + LLM驱动智能补全向导
从：无RAG检索结果可视化                    → 到：向量空间投影 + 检索结果图谱展示
从：无系统配置管理界面                     → 到：ConfigHub可视化配置 + 热加载控制面板
```

### 1.2 设计原则

1. **可见即可控**: 所有后端能力必须在前端有对应的可视化控制面板，禁止"黑盒"操作
2. **实时即可信**: 任务状态、Agent执行、系统指标通过WebSocket/SSE实时推送，延迟 < 500ms
3. **配置即表单**: Pydantic配置模型自动生成表单，减少前端重复编码
4. **检索即可视**: RAG检索结果支持向量空间投影、知识图谱、记忆时间线三种可视化模式
5. **编排即画布**: DAG工作流支持可视化编排（拖拽节点、连接边、配置属性）
6. **状态即单一**: 全局状态使用Zustand单一存储，禁止组件间直接传递复杂状态

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **React Flow** (2024) | 节点式可视化编排、自定义节点、边动画 | DAG工作流可视化 |
| **D3.js v7** (2024) | 力导向图、层级布局、数据绑定 | 知识图谱、关系网络 |
| **Zustand** (2024) | 轻量状态管理、无样板代码、TypeScript友好 | 前端全局状态 |
| **TanStack Query** (2024) | 服务端状态缓存、自动刷新、乐观更新 | REST API数据获取 |
| **shadcn/ui** (2024) | 可组合组件、TailwindCSS、无障碍支持 | UI组件库 |
| **Grafana** (2024) | 指标面板、时序图表、告警可视化 | 系统监控仪表盘 |
| **LangSmith** (2024) | LLM调用追踪、Prompt调试、性能分析 | Agent执行追踪 |
| **Weights & Biases** (2024) | 实验管理、超参数可视化、对比分析 | 小说生成实验管理 |

---

## 2. 现状诊断

### 2.1 当前前端组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| TaskMonitorView | `frontend/src/views/TaskMonitorView.vue` | Vue3项目，但Step5-10全部使用React规划；轮询3秒刷新 | **严重** |
| SystemHealthView | `frontend/src/views/SystemHealthView.vue` | 仅显示组件健康，无任务级监控 | **中** |
| SystemHealthPanel | `frontend/src/components/SystemHealthPanel.vue` | 同上 | **低** |
| API服务 | `frontend/src/services/api.ts` | 纯REST轮询、无WebSocket、无类型定义 | **严重** |
| 路由 | `frontend/src/router/index.ts` | 仅3个基础路由，无任务/配置/知识库路由 | **中** |
| 状态管理 | 无 | 无Vuex/Pinia/Zustand，状态分散在组件中 | **严重** |
| 包管理 | `frontend/package.json` | 无d3、无echarts、无ws客户端 | **中** |

### 2.2 核心问题总结

```
当前状态：前端"可用"但"不可视化"

1. 框架不一致          → Step5提及Vue3+D3，但无实际配套代码；建议统一为React+TypeScript
2. 无状态管理          → 组件间状态传递混乱，数据不同步
3. 无实时推送          → 轮询3秒刷新，无法实时反映任务状态
4. 无DAG可视化        → Step5设计了DAG引擎，前端无对应可视化
5. 无配置表单化       → Step7的NovelConfig、Step10的AppConfig无前端配置界面
6. 无RAG可视化        → Step6的检索结果无法在前端查看和分析
7. 无Agent管理界面    → Step4的Agent列表、配置、性能无前端管理
8. 无知识库浏览器      → Step1的世界事实、角色关系、记忆时间线无前端浏览
```

---

## 3. 架构总览

### 3.1 前端五层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 5: 页面层 (Pages)                                              │
│  • NovelWorkbench        - 小说创作工作台                            │
│  • TaskDashboard         - 任务监控仪表盘                            │
│  • AgentManager          - Agent管理界面                             │
│  • KnowledgeBrowser      - 知识库浏览器                              │
│  • SystemSettings        - 系统设置面板                              │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: 组件层 (Components)                                         │
│  • DAGGraph              - DAG可视化图 (React Flow/D3.js)            │
│  • NodeStatusCard        - 节点状态卡片                              │
│  • LogStream             - 实时日志流                                │
│  • ConfigForm            - 配置表单生成器                            │
│  • VectorProjection      - 向量空间投影图                            │
│  • KnowledgeGraph        - 知识关系图谱                              │
│  • MemoryTimeline        - 记忆时间线                                │
│  • MetricChart           - 指标时序图表                              │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 状态层 (State Management)                                   │
│  • useNovelStore         - 小说配置状态 (Zustand)                    │
│  • useTaskStore          - 任务调度状态 (Zustand)                    │
│  • useAgentStore         - Agent管理状态 (Zustand)                   │
│  • useKnowledgeStore     - 知识库状态 (Zustand)                      │
│  • useConfigStore        - 系统配置状态 (Zustand)                    │
│  • useSystemStore        - 系统监控状态 (Zustand)                    │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 服务层 (Services)                                           │
│  • apiClient             - REST API客户端 (TanStack Query)           │
│  • wsClient              - WebSocket客户端                           │
│  • sseClient             - SSE流客户端                               │
│  • eventBus              - 前端事件总线                              │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 基础设施层 (Infrastructure)                                 │
│  • React 18 + TypeScript                                              │
│  • Vite (构建工具)                                                    │
│  • TailwindCSS (样式)                                                 │
│  • shadcn/ui (组件库)                                                 │
│  • React Flow (DAG编排)                                               │
│  • D3.js (知识图谱)                                                   │
│  • ECharts (指标图表)                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 前后端数据流

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              前端数据流                                        │
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   用户操作    │───→│  Zustand Store│───→│  API Service │                   │
│  │  (点击/输入)  │    │  (状态变更)   │    │  (请求发送)   │                   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                   │
│         ↑                                        │                            │
│         │         ┌──────────────────────────────┼──────────────────┐        │
│         │         │                              │                  │        │
│         │    REST API                     WebSocket            SSE Stream    │
│         │         │                              │                  │        │
│         │         ▼                              ▼                  ▼        │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │   UI更新      │←───│              FastAPI Backend                      │   │
│  │  (React渲染)  │    │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │   │
│  └──────────────┘    │  │ REST API │ │WebSocket │ │ SSE Hub  │        │   │
│                      │  └────┬─────┘ └────┬─────┘ └────┬─────┘        │   │
│                      │       │            │            │               │   │
│                      │       ▼            ▼            ▼               │   │
│                      │  ┌─────────────────────────────────────────┐   │   │
│                      │  │         Step5 TaskOrchestrator          │   │   │
│                      │  │         Step6 RAGEngine                 │   │   │
│                      │  │         Step7 NovelConfigService        │   │   │
│                      │  │         Step10 ConfigHub                │   │   │
│                      │  └─────────────────────────────────────────┘   │   │
│                      └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 核心页面设计

### 4.1 小说创作工作台 (NovelWorkbench)

**职责**: 小说配置管理 + 生成控制 + 实时预览

**URL**: `/novel/workbench`

**布局**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  顶部导航栏  │  小说: 《凡人修仙传》  │  状态: 生成中  │  [暂停] [停止] │
├─────────────────┬───────────────────────────────────────────────────┤
│                 │                                                   │
│  配置面板        │              实时预览面板                          │
│  ├─ 基本信息     │                                                   │
│  │  ├─ 标题      │  ┌─────────────────────────────────────────┐     │
│  │  ├─ 类型      │  │  第3章 炼气入门                            │     │
│  │  ├─ 风格      │  │                                         │     │
│  │  └─ 视角      │  │  林凡盘坐在蒲团上，按照《基础炼气诀》的法门...│     │
│  ├─ 世界设定     │  │  ...                                    │     │
│  │  ├─ 世界观    │  │                                         │     │
│  │  ├─ 力量体系  │  └─────────────────────────────────────────┘     │
│  │  └─ 地理      │                                                   │
│  ├─ 角色管理     │  ┌─────────────────────────────────────────┐     │
│  │  ├─ 主角      │  │  生成进度: ████████░░ 80%                │     │
│  │  ├─ 配角列表  │  │  当前Agent: SceneWriterAgent             │     │
│  │  └─ [+添加]   │  │  预计剩余: 2分钟                          │     │
│  └─ 大纲编辑     │  └─────────────────────────────────────────┘     │
│     ├─ 章节列表  │                                                   │
│     └─ 情节节点  │                                                   │
│                 │                                                   │
└─────────────────┴───────────────────────────────────────────────────┘
```

**核心功能**:
1. **配置表单**: 基于Step7 `NovelConfig` Pydantic模型自动生成表单
2. **LLM补全向导**: 输入"修仙小说"后，调用Step7 `LLMConfigCompleter` 自动补全配置
3. **生成控制**: 启动/暂停/停止小说生成任务，调用Step5 `TaskScheduler`
4. **实时预览**: SSE流推送生成内容，支持Markdown渲染
5. **章节导航**: 大纲树形结构，点击跳转对应章节

**接口依赖**:
```typescript
// 获取小说配置
GET /api/v1/novels/{novel_id}/config

// 更新小说配置
PUT /api/v1/novels/{novel_id}/config

// LLM智能补全
POST /api/v1/novels/completion

// 启动生成任务
POST /api/v1/tasks
{
  "workflow_name": "novel_generation",
  "initial_state": { "novel_id": "xxx", "chapter": 3 }
}

// 实时内容流 (SSE)
GET /api/v1/tasks/{task_id}/stream

// 生成进度 (WebSocket)
WS /api/v1/ws/tasks/{task_id}
```

---

### 4.2 任务监控仪表盘 (TaskDashboard)

**职责**: DAG可视化 + 节点状态 + 日志流

**URL**: `/tasks/dashboard`

**布局**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  [全部] [运行中] [已完成] [失败]  │  搜索任务...  │  [刷新]           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    DAG可视化区域 (React Flow)                 │   │
│  │                                                             │   │
│  │     ┌─────────┐      ┌─────────┐      ┌─────────┐          │   │
│  │     │ director│ ───→ │plot_mgr │ ───→ │world_st │          │   │
│  │     │  ✅     │      │  ✅     │      │  🔄     │          │   │
│  │     └─────────┘      └─────────┘      └─────────┘          │   │
│  │                              │                              │   │
│  │                              ▼                              │   │
│  │     ┌─────────┐      ┌─────────┐      ┌─────────┐          │   │
│  │     │char_mind│ ───→ │event_sim│ ───→ │scene_wr │          │   │
│  │     │  ⏳     │      │  ⏳     │      │  ⏳     │          │   │
│  │     └─────────┘      └─────────┘      └─────────┘          │   │
│  │                                                             │   │
│  │  图例: ⏳待执行  🔄执行中  ✅完成  ❌失败  ⏭跳过              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐   │
│  │    节点详情面板       │  │        实时日志流                 │   │
│  │  ├─ 名称: world_st   │  │  [10:23:45] world_st: 加载世界设定...│   │
│  │  ├─ Agent: WorldState│  │  [10:23:46] world_st: 检索知识库...  │   │
│  │  ├─ 状态: running    │  │  [10:23:47] world_st: 验证规则...    │   │
│  │  ├─ 开始: 10:23:45   │  │  [10:23:48] world_st: 输出世界状态   │   │
│  │  ├─ 耗时: 3.2s       │  │  ...                                │   │
│  │  └─ 输出: {...}      │  │                                    │   │
│  └──────────────────────┘  └──────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**核心功能**:
1. **DAG可视化**: React Flow渲染工作流图，节点实时着色
2. **节点交互**: 点击节点查看详情、日志、输入输出
3. **实时状态**: WebSocket推送节点状态变更
4. **日志流**: SSE流显示实时日志，支持过滤/搜索
5. **执行时间线**: Gantt图展示各节点执行时段

**接口依赖**:
```typescript
// 获取工作流定义 (DAG结构)
GET /api/v1/workflows/{workflow_name}/definition

// 获取工作流实时状态
GET /api/v1/workflows/{workflow_id}/state

// 获取工作流事件时间线
GET /api/v1/workflows/{workflow_id}/timeline

// WebSocket实时推送
WS /api/v1/ws/workflows/{workflow_id}

// SSE日志流
GET /api/v1/tasks/{task_id}/stream
```

---

### 4.3 Agent管理界面 (AgentManager)

**职责**: Agent列表 + 配置调整 + 性能指标

**URL**: `/agents/manager`

**布局**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  [全部Agent] [启用] [禁用]  │  搜索Agent...  │  [注册新Agent]        │
├─────────────────┬───────────────────────────────────────────────────┤
│                 │                                                   │
│  Agent列表       │              Agent详情面板                         │
│  ┌─────────────┐│                                                   │
│  │ 🟢 Director  ││  名称: DirectorAgent                               │
│  │   运行中     ││  描述: 导演Agent，负责整体创作决策                    │
│  └─────────────┘│                                                   │
│  ┌─────────────┐│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │ 🟢 WorldState││  │  LLM配置     │  │  工具列表    │  │ 性能指标  │  │
│  │   运行中     ││  │  ├─ Provider│  │  ├─ tool_1  │  │ ├─ 调用次数│  │
│  └─────────────┘│  │  ├─ Model   │  │  ├─ tool_2  │  │ ├─ 平均耗时│  │
│  ┌─────────────┐│  │  ├─ Temp    │  │  └─ [+添加] │  │ ├─ 成功率  │  │
│  │ 🟡 SceneWrite││  │  └─ [编辑]  │  │             │  │ └─ 趋势图  │  │
│  │   队列中     ││  └─────────────┘  └─────────────┘  └──────────┘  │
│  └─────────────┘│                                                   │
│  ┌─────────────┐│  ┌─────────────────────────────────────────┐     │
│  │ 🔴 Consistency│  │         历史调用记录                      │     │
│  │   上次失败   ││  │  时间          │  输入     │  输出    │ 耗时  │     │
│  └─────────────┘│  │  10:23:45     │  {...}   │  {...}  │ 2.3s │     │
│                 │  │  10:23:40     │  {...}   │  {...}  │ 1.8s │     │
│                 │  │  ...          │  ...     │  ...    │ ...  │     │
│                 │  └─────────────────────────────────────────┘     │
│                 │                                                   │
└─────────────────┴───────────────────────────────────────────────────┘
```

**核心功能**:
1. **Agent列表**: 显示所有已注册Agent，状态指示器
2. **LLM配置**: 调整Agent的模型、温度、最大token等（覆盖Step10全局配置）
3. **工具管理**: 为Agent添加/移除工具（Step8工具层）
4. **性能指标**: 调用次数、平均耗时、成功率、趋势图
5. **历史记录**: 查看Agent历史调用记录

**接口依赖**:
```typescript
// 获取Agent列表
GET /api/v1/agents

// 获取Agent详情
GET /api/v1/agents/{agent_name}

// 更新Agent配置
PUT /api/v1/agents/{agent_name}/config

// 获取Agent性能指标
GET /api/v1/agents/{agent_name}/metrics

// 获取Agent历史调用
GET /api/v1/agents/{agent_name}/history
```

---

### 4.4 知识库浏览器 (KnowledgeBrowser)

**职责**: 世界事实图谱 + 角色关系图 + 记忆时间线

**URL**: `/knowledge/browser`

**布局**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  [世界事实] [角色关系] [记忆时间线] [向量投影]  │  搜索知识库...        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Tab 1: 世界事实图谱 (D3.js力导向图)                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │        ┌─────────┐                                          │   │
│  │        │ 修仙世界 │◄──────────┐                              │   │
│  │        └────┬────┘           │                              │   │
│  │             │                │                              │   │
│  │     ┌───────┼───────┐        │                              │   │
│  │     ▼       ▼       ▼        │                              │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐    │                              │   │
│  │  │灵气体系│ │门派势力│ │地理区域│    │                              │   │
│  │  └──┬──┘ └──┬──┘ └──┬──┘    │                              │   │
│  │     │       │       │        │                              │   │
│  │     ▼       ▼       ▼        │                              │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐    │                              │   │
│  │  │炼气期│ │青云门│ │东大陆│────┘                              │   │
│  │  └─────┘ └─────┘ └─────┘                                   │   │
│  │                                                             │   │
│  │  点击节点: 显示事实详情面板                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Tab 2: 角色关系图                                                   │
│  Tab 3: 记忆时间线 (按时间轴展示角色记忆)                              │
│  Tab 4: 向量投影 (t-SNE/UMAP降维可视化检索结果)                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**核心功能**:
1. **世界事实图谱**: D3.js力导向图展示Step1 `FactManager`中的事实层级关系
2. **角色关系图**: 展示角色间关系网络（师徒、敌对、情侣等）
3. **记忆时间线**: 按时间轴展示Step2 `CharacterMind`的记忆事件
4. **向量投影**: t-SNE/UMAP降维展示Step6向量空间中的文档分布
5. **检索测试**: 输入查询，可视化展示检索结果在向量空间中的位置

**接口依赖**:
```typescript
// 获取世界事实图谱
GET /api/v1/knowledge/world/{world_id}/facts/graph

// 获取角色关系图
GET /api/v1/knowledge/characters/{novel_id}/relations

// 获取角色记忆时间线
GET /api/v1/knowledge/characters/{char_id}/memories/timeline

// 向量空间投影
GET /api/v1/knowledge/vectors/projection?collection=world_knowledge

// 检索测试
POST /api/v1/rag/search
{
  "query": "灵气修炼的方法",
  "retriever": "world_knowledge",
  "top_k": 5
}
```

---

### 4.5 系统设置面板 (SystemSettings)

**职责**: ConfigHub可视化配置 + 热加载控制

**URL**: `/system/settings`

**布局**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  [LLM] [数据库] [Agent] [RAG] [工作流] [日志] [安全] [高级]            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Tab: LLM配置                                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  默认提供商: [ollama ▼]                                      │   │
│  │                                                             │   │
│  │  提供商列表:                                                 │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                       │   │
│  │  │ ollama  │ │ openai  │ │  qwen   │  [+添加提供商]          │   │
│  │  │  ●默认  │ │         │ │         │                       │   │
│  │  └─────────┘ └─────────┘ └─────────┘                       │   │
│  │                                                             │   │
│  │  ollama 详细配置:                                           │   │
│  │  ├─ 模型: [qwen2.5-14b ▼]                                  │   │
│  │  ├─ Base URL: http://localhost:11434                       │   │
│  │  ├─ 温度: [====●====] 0.7                                  │   │
│  │  ├─ 最大Token: 8192                                        │   │
│  │  └─ API密钥: [********] (使用Vault加密)                      │   │
│  │                                                             │   │
│  │  [保存] [重置] [热加载] [导出配置]                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  底部状态栏:                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  配置状态: ✅ 已保存  │  最后更新: 2026-04-28 10:23:45       │   │
│  │  文件监听: 🟢 运行中  │  热加载: 启用                         │   │
│  │  配置验证: ✅ 通过    │  环境: development                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**核心功能**:
1. **配置表单**: 基于Step10 `AppConfig` Pydantic模型自动生成表单
2. **Tab分组**: LLM/数据库/Agent/RAG/工作流/日志/安全/高级
3. **热加载控制**: 启用/禁用文件监听，手动触发reload
4. **配置验证**: 实时验证配置项，显示错误提示
5. **敏感项加密**: API密钥等敏感信息使用Vault加密存储
6. **配置导出**: 导出当前配置为YAML/JSON

**接口依赖**:
```typescript
// 获取当前配置
GET /api/v1/config

// 更新配置
PUT /api/v1/config

// 热加载
POST /api/v1/config/reload

// 配置健康检查
GET /api/v1/config/health

// 生成配置文档
POST /api/v1/config/docs
```

---

## 5. 状态管理设计 (Zustand)

### 5.1 Store分层架构

```typescript
// frontend/src/stores/index.ts

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

// ───────────────────────────────────────────────
// 小说配置 Store (Step7 NovelConfig)
// ───────────────────────────────────────────────

interface NovelState {
  // 状态
  currentNovel: NovelConfig | null
  novels: NovelConfig[]
  isLoading: boolean
  error: string | null
  generationProgress: GenerationProgress | null

  // 动作
  loadNovels: () => Promise<void>
  loadNovel: (id: string) => Promise<void>
  updateNovel: (id: string, config: Partial<NovelConfig>) => Promise<void>
  completeConfig: (input: string) => Promise<NovelConfig>
  startGeneration: (novelId: string, chapter?: number) => Promise<string>
  stopGeneration: (taskId: string) => Promise<void>
  setProgress: (progress: GenerationProgress) => void
}

export const useNovelStore = create<NovelState>()(
  devtools(
    persist(
      (set, get) => ({
        currentNovel: null,
        novels: [],
        isLoading: false,
        error: null,
        generationProgress: null,

        loadNovels: async () => {
          set({ isLoading: true, error: null })
          try {
            const novels = await apiClient.get('/novels')
            set({ novels, isLoading: false })
          } catch (err) {
            set({ error: String(err), isLoading: false })
          }
        },

        loadNovel: async (id: string) => {
          set({ isLoading: true, error: null })
          try {
            const novel = await apiClient.get(`/novels/${id}/config`)
            set({ currentNovel: novel, isLoading: false })
          } catch (err) {
            set({ error: String(err), isLoading: false })
          }
        },

        updateNovel: async (id: string, config: Partial<NovelConfig>) => {
          set({ isLoading: true })
          try {
            const updated = await apiClient.put(`/novels/${id}/config`, config)
            set(state => ({
              currentNovel: state.currentNovel?.id === id ? updated : state.currentNovel,
              novels: state.novels.map(n => n.id === id ? updated : n),
              isLoading: false
            }))
          } catch (err) {
            set({ error: String(err), isLoading: false })
          }
        },

        completeConfig: async (input: string) => {
          const completed = await apiClient.post('/novels/completion', { input })
          return completed
        },

        startGeneration: async (novelId: string, chapter?: number) => {
          const task = await apiClient.post('/tasks', {
            workflow_name: 'novel_generation',
            initial_state: { novel_id: novelId, chapter }
          })
          return task.task_id
        },

        stopGeneration: async (taskId: string) => {
          await apiClient.post(`/tasks/${taskId}/cancel`)
        },

        setProgress: (progress: GenerationProgress) => {
          set({ generationProgress: progress })
        }
      }),
      { name: 'novel-store' }
    )
  )
)

// ───────────────────────────────────────────────
// 任务调度 Store (Step5 TaskOrchestrator)
// ───────────────────────────────────────────────

interface TaskState {
  // 状态
  tasks: Task[]
  currentWorkflow: WorkflowState | null
  workflowDefinition: WorkflowDefinition | null
  logs: LogEntry[]
  isConnected: boolean

  // 动作
  loadTasks: (status?: TaskStatus) => Promise<void>
  loadWorkflow: (workflowId: string) => Promise<void>
  loadWorkflowDefinition: (workflowName: string) => Promise<void>
  submitTask: (workflowName: string, initialState: any) => Promise<string>
  cancelTask: (taskId: string) => Promise<void>
  connectWebSocket: (workflowId: string) => () => void
  appendLog: (log: LogEntry) => void
  updateNodeStatus: (nodeId: string, status: NodeStatus) => void
}

export const useTaskStore = create<TaskState>()(
  devtools((set, get) => ({
    tasks: [],
    currentWorkflow: null,
    workflowDefinition: null,
    logs: [],
    isConnected: false,

    loadTasks: async (status?: TaskStatus) => {
      const params = status ? `?status=${status}` : ''
      const tasks = await apiClient.get(`/tasks${params}`)
      set({ tasks })
    },

    loadWorkflow: async (workflowId: string) => {
      const state = await apiClient.get(`/workflows/${workflowId}/state`)
      set({ currentWorkflow: state })
    },

    loadWorkflowDefinition: async (workflowName: string) => {
      const definition = await apiClient.get(`/workflows/${workflowName}/definition`)
      set({ workflowDefinition: definition })
    },

    submitTask: async (workflowName: string, initialState: any) => {
      const task = await apiClient.post('/tasks', {
        workflow_name: workflowName,
        initial_state: initialState
      })
      return task.task_id
    },

    cancelTask: async (taskId: string) => {
      await apiClient.post(`/tasks/${taskId}/cancel`)
    },

    connectWebSocket: (workflowId: string) => {
      const ws = wsClient.connect(`/ws/workflows/${workflowId}`)

      ws.onMessage((data) => {
        if (data.type === 'node_status_change') {
          get().updateNodeStatus(data.node_id, data.status)
        } else if (data.type === 'workflow_progress') {
          set(state => ({
            currentWorkflow: state.currentWorkflow
              ? { ...state.currentWorkflow, progress: data.progress }
              : null
          }))
        } else if (data.type === 'log') {
          get().appendLog(data)
        }
      })

      set({ isConnected: true })

      // 返回断开函数
      return () => {
        ws.disconnect()
        set({ isConnected: false })
      }
    },

    appendLog: (log: LogEntry) => {
      set(state => ({ logs: [...state.logs.slice(-999), log] }))
    },

    updateNodeStatus: (nodeId: string, status: NodeStatus) => {
      set(state => ({
        currentWorkflow: state.currentWorkflow
          ? {
              ...state.currentWorkflow,
              nodes: {
                ...state.currentWorkflow.nodes,
                [nodeId]: { ...state.currentWorkflow.nodes[nodeId], status }
              }
            }
          : null
      }))
    }
  }))
)

// ───────────────────────────────────────────────
// Agent管理 Store (Step4 Agent层)
// ───────────────────────────────────────────────

interface AgentState {
  agents: AgentInfo[]
  selectedAgent: AgentInfo | null
  agentMetrics: Record<string, AgentMetrics>
  agentHistory: Record<string, AgentCall[]>

  loadAgents: () => Promise<void>
  selectAgent: (name: string) => Promise<void>
  updateAgentConfig: (name: string, config: Partial<AgentConfig>) => Promise<void>
  toggleAgent: (name: string, enabled: boolean) => Promise<void>
}

export const useAgentStore = create<AgentState>()(
  devtools((set, get) => ({
    agents: [],
    selectedAgent: null,
    agentMetrics: {},
    agentHistory: {},

    loadAgents: async () => {
      const agents = await apiClient.get('/agents')
      set({ agents })
    },

    selectAgent: async (name: string) => {
      const [info, metrics, history] = await Promise.all([
        apiClient.get(`/agents/${name}`),
        apiClient.get(`/agents/${name}/metrics`),
        apiClient.get(`/agents/${name}/history`)
      ])
      set({
        selectedAgent: info,
        agentMetrics: { ...get().agentMetrics, [name]: metrics },
        agentHistory: { ...get().agentHistory, [name]: history }
      })
    },

    updateAgentConfig: async (name: string, config: Partial<AgentConfig>) => {
      const updated = await apiClient.put(`/agents/${name}/config`, config)
      set(state => ({
        agents: state.agents.map(a => a.name === name ? updated : a),
        selectedAgent: state.selectedAgent?.name === name ? updated : state.selectedAgent
      }))
    },

    toggleAgent: async (name: string, enabled: boolean) => {
      await apiClient.post(`/agents/${name}/toggle`, { enabled })
      set(state => ({
        agents: state.agents.map(a =>
          a.name === name ? { ...a, enabled } : a
        )
      }))
    }
  }))
)

// ───────────────────────────────────────────────
// 知识库 Store (Step6 RAG + Step1 数据层)
// ───────────────────────────────────────────────

interface KnowledgeState {
  worldGraph: GraphData | null
  characterRelations: GraphData | null
  memoryTimeline: TimelineEntry[]
  vectorProjection: VectorPoint[] | null
  searchResults: SearchResult[]

  loadWorldGraph: (worldId: string) => Promise<void>
  loadCharacterRelations: (novelId: string) => Promise<void>
  loadMemoryTimeline: (charId: string) => Promise<void>
  loadVectorProjection: (collection: string) => Promise<void>
  searchKnowledge: (query: string, retriever: string) => Promise<void>
}

export const useKnowledgeStore = create<KnowledgeState>()(
  devtools((set) => ({
    worldGraph: null,
    characterRelations: null,
    memoryTimeline: [],
    vectorProjection: null,
    searchResults: [],

    loadWorldGraph: async (worldId: string) => {
      const graph = await apiClient.get(`/knowledge/world/${worldId}/facts/graph`)
      set({ worldGraph: graph })
    },

    loadCharacterRelations: async (novelId: string) => {
      const graph = await apiClient.get(`/knowledge/characters/${novelId}/relations`)
      set({ characterRelations: graph })
    },

    loadMemoryTimeline: async (charId: string) => {
      const timeline = await apiClient.get(`/knowledge/characters/${charId}/memories/timeline`)
      set({ memoryTimeline: timeline })
    },

    loadVectorProjection: async (collection: string) => {
      const projection = await apiClient.get(`/knowledge/vectors/projection?collection=${collection}`)
      set({ vectorProjection: projection })
    },

    searchKnowledge: async (query: string, retriever: string) => {
      const results = await apiClient.post('/rag/search', {
        query,
        retriever,
        top_k: 10
      })
      set({ searchResults: results.results })
    }
  }))
)

// ───────────────────────────────────────────────
// 系统配置 Store (Step10 ConfigHub)
// ───────────────────────────────────────────────

interface ConfigState {
  config: AppConfig | null
  isLoading: boolean
  isDirty: boolean
  validationErrors: ValidationError[]
  lastReloadTime: Date | null
  isWatcherRunning: boolean

  loadConfig: () => Promise<void>
  updateConfig: (path: string, value: any) => void
  saveConfig: () => Promise<void>
  reloadConfig: () => Promise<void>
  toggleWatcher: (enabled: boolean) => Promise<void>
  validateConfig: () => Promise<boolean>
}

export const useConfigStore = create<ConfigState>()(
  devtools((set, get) => ({
    config: null,
    isLoading: false,
    isDirty: false,
    validationErrors: [],
    lastReloadTime: null,
    isWatcherRunning: false,

    loadConfig: async () => {
      set({ isLoading: true })
      try {
        const config = await apiClient.get('/config')
        set({ config, isLoading: false, isDirty: false })
      } catch (err) {
        set({ isLoading: false })
      }
    },

    updateConfig: (path: string, value: any) => {
      set(state => ({
        config: setPath(state.config, path, value),
        isDirty: true
      }))
    },

    saveConfig: async () => {
      const { config } = get()
      if (!config) return
      await apiClient.put('/config', config)
      set({ isDirty: false })
    },

    reloadConfig: async () => {
      await apiClient.post('/config/reload')
      await get().loadConfig()
      set({ lastReloadTime: new Date() })
    },

    toggleWatcher: async (enabled: boolean) => {
      await apiClient.post('/config/watcher', { enabled })
      set({ isWatcherRunning: enabled })
    },

    validateConfig: async () => {
      try {
        const result = await apiClient.post('/config/validate', get().config)
        set({ validationErrors: result.errors || [] })
        return result.valid
      } catch (err) {
        return false
      }
    }
  }))
)
```

---

## 6. 服务层设计

### 6.1 API客户端 (TanStack Query)

```typescript
// frontend/src/services/api.ts

import axios, { AxiosInstance, AxiosError } from 'axios'
import { QueryClient } from '@tanstack/react-query'

// 全局QueryClient
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30,        // 30秒视为新鲜
      refetchInterval: 1000 * 60,  // 1分钟自动刷新
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
    }
  }
})

// Axios实例
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // 未授权，跳转登录
      window.location.href = '/login'
    }
    return Promise.reject(error.response?.data || error.message)
  }
)

// API方法封装
export const apiClient = {
  get: (url: string, params?: any) => api.get(url, { params }),
  post: (url: string, data?: any) => api.post(url, data),
  put: (url: string, data?: any) => api.put(url, data),
  delete: (url: string) => api.delete(url),
  patch: (url: string, data?: any) => api.patch(url, data)
}

// TanStack Query Hooks封装
export function useTasks(status?: TaskStatus) {
  return useQuery({
    queryKey: ['tasks', status],
    queryFn: () => apiClient.get('/tasks', { status }),
    refetchInterval: 5000  // 5秒刷新任务列表
  })
}

export function useWorkflow(workflowId: string) {
  return useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => apiClient.get(`/workflows/${workflowId}/state`),
    enabled: !!workflowId,
    refetchInterval: 3000
  })
}

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => apiClient.get('/agents'),
    staleTime: 1000 * 60  // 1分钟内不重复请求
  })
}

export function useNovel(novelId: string) {
  return useQuery({
    queryKey: ['novel', novelId],
    queryFn: () => apiClient.get(`/novels/${novelId}/config`),
    enabled: !!novelId
  })
}
```

### 6.2 WebSocket客户端

```typescript
// frontend/src/services/websocket.ts

interface WSOptions {
  onOpen?: () => void
  onMessage?: (data: any) => void
  onError?: (error: Event) => void
  onClose?: () => void
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnects?: number
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private options: WSOptions
  private reconnectCount = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  constructor(path: string, options: WSOptions = {}) {
    const baseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1'
    this.url = `${baseUrl}${path}`
    this.options = {
      reconnect: true,
      reconnectInterval: 3000,
      maxReconnects: 5,
      ...options
    }
    this.connect()
  }

  private connect() {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectCount = 0
        this.options.onOpen?.()
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.options.onMessage?.(data)
        } catch {
          this.options.onMessage?.(event.data)
        }
      }

      this.ws.onerror = (error) => {
        this.options.onError?.(error)
      }

      this.ws.onclose = () => {
        this.options.onClose?.()
        if (this.options.reconnect && this.reconnectCount < (this.options.maxReconnects || 5)) {
          this.reconnectCount++
          this.reconnectTimer = setTimeout(() => {
            this.connect()
          }, this.options.reconnectInterval)
        }
      }
    } catch (error) {
      console.error('WebSocket connection failed:', error)
    }
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    this.options.reconnect = false
    this.ws?.close()
  }
}

// 工厂函数
export const wsClient = {
  connect: (path: string, options?: WSOptions) => new WebSocketClient(path, options)
}
```

### 6.3 SSE客户端

```typescript
// frontend/src/services/sse.ts

class SSEClient {
  private eventSource: EventSource | null = null

  connect(url: string, options: {
    onMessage?: (data: any) => void
    onError?: (error: Event) => void
    onOpen?: () => void
  } = {}) {
    this.eventSource = new EventSource(url)

    this.eventSource.onopen = () => {
      options.onOpen?.()
    }

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        options.onMessage?.(data)
      } catch {
        options.onMessage?.(event.data)
      }
    }

    this.eventSource.onerror = (error) => {
      options.onError?.(error)
    }

    return this
  }

  disconnect() {
    this.eventSource?.close()
    this.eventSource = null
  }
}

export const sseClient = {
  connect: (url: string, options?: any) => new SSEClient().connect(url, options)
}
```

---

## 7. 核心组件设计

### 7.1 DAG可视化组件 (React Flow)

```typescript
// frontend/src/components/DAGGraph.tsx

import React, { useCallback, useEffect } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  NodeProps
} from 'reactflow'
import 'reactflow/dist/style.css'

// 节点状态到颜色的映射
const statusColors: Record<NodeStatus, string> = {
  pending: '#64748b',
  scheduled: '#8b5cf6',
  running: '#06b6d4',
  completed: '#10b981',
  failed: '#ef4444',
  skipped: '#94a3b8',
  retrying: '#f59e0b'
}

// 自定义节点组件
const WorkflowNode: React.FC<NodeProps<WorkflowNodeData>> = ({ data, selected }) => {
  const color = statusColors[data.status] || statusColors.pending

  return (
    <div
      className={`rounded-lg border-2 px-4 py-2 shadow-md transition-all duration-300 ${
        selected ? 'ring-2 ring-blue-500' : ''
      }`}
      style={{
        borderColor: color,
        backgroundColor: `${color}15`,
        minWidth: 140
      }}
    >
      <div className="flex items-center gap-2">
        <div
          className="h-3 w-3 rounded-full animate-pulse"
          style={{ backgroundColor: color }}
        />
        <span className="text-sm font-medium">{data.label}</span>
      </div>
      <div className="mt-1 text-xs text-gray-500">{data.agent}</div>
      {data.duration && (
        <div className="mt-1 text-xs text-gray-400">{data.duration}ms</div>
      )}
    </div>
  )
}

const nodeTypes = {
  workflowNode: WorkflowNode
}

interface DAGGraphProps {
  workflowId: string
  definition: WorkflowDefinition
  state?: WorkflowState
}

export const DAGGraph: React.FC<DAGGraphProps> = ({
  workflowId,
  definition,
  state
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // 根据工作流定义构建节点和边
  useEffect(() => {
    const flowNodes: Node[] = definition.nodes.map((node, index) => ({
      id: node.id,
      type: 'workflowNode',
      position: { x: index * 200, y: Math.floor(index / 3) * 150 },
      data: {
        label: node.id,
        agent: node.agent,
        status: state?.nodes[node.id]?.status || 'pending',
        duration: state?.nodes[node.id]?.duration_ms
      }
    }))

    const flowEdges: Edge[] = definition.edges.map((edge, index) => ({
      id: `e${index}`,
      source: edge.from,
      target: edge.to,
      animated: state?.nodes[edge.from]?.status === 'running',
      style: { stroke: '#64748b', strokeWidth: 2 }
    }))

    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [definition, state])

  // 实时更新节点状态
  useEffect(() => {
    if (!state) return

    setNodes(prev =>
      prev.map(node => {
        const nodeState = state.nodes[node.id]
        if (!nodeState) return node

        return {
          ...node,
          data: {
            ...node.data,
            status: nodeState.status,
            duration: nodeState.duration_ms
          }
        }
      })
    )

    // 更新边动画
    setEdges(prev =>
      prev.map(edge => ({
        ...edge,
        animated: state.nodes[edge.source]?.status === 'running'
      }))
    )
  }, [state])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    // 触发节点选择事件
    window.dispatchEvent(new CustomEvent('node-selected', { detail: node }))
  }, [])

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#e2e8f0" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  )
}
```

### 7.2 配置表单生成器

```typescript
// frontend/src/components/ConfigForm.tsx

import React from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

// Pydantic模型到Zod Schema的转换
function pydanticToZod(model: PydanticModel): z.ZodTypeAny {
  const schema: Record<string, z.ZodTypeAny> = {}

  for (const [fieldName, fieldInfo] of Object.entries(model.fields)) {
    let fieldSchema: z.ZodTypeAny

    switch (fieldInfo.type) {
      case 'string':
        fieldSchema = z.string()
        break
      case 'integer':
        fieldSchema = z.number().int()
        break
      case 'float':
        fieldSchema = z.number()
        break
      case 'boolean':
        fieldSchema = z.boolean()
        break
      case 'array':
        fieldSchema = z.array(z.string())
        break
      default:
        fieldSchema = z.any()
    }

    if (fieldInfo.default !== undefined) {
      fieldSchema = fieldSchema.optional()
    }

    schema[fieldName] = fieldSchema
  }

  return z.object(schema)
}

interface ConfigFormProps {
  model: PydanticModel
  values: any
  onChange: (path: string, value: any) => void
  onSubmit: () => void
}

export const ConfigForm: React.FC<ConfigFormProps> = ({
  model,
  values,
  onChange,
  onSubmit
}) => {
  const schema = pydanticToZod(model)

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: values
  })

  const renderField = (fieldName: string, fieldInfo: FieldInfo) => {
    const error = errors[fieldName]?.message as string

    return (
      <div key={fieldName} className="mb-4">
        <label className="mb-1 block text-sm font-medium">
          {fieldInfo.title || fieldName}
          {fieldInfo.required && <span className="text-red-500">*</span>}
        </label>

        {fieldInfo.description && (
          <p className="mb-1 text-xs text-gray-500">{fieldInfo.description}</p>
        )}

        {fieldInfo.type === 'string' && fieldInfo.enum ? (
          <select
            {...register(fieldName)}
            className="w-full rounded border p-2"
            onChange={(e) => onChange(fieldName, e.target.value)}
          >
            {fieldInfo.enum.map((opt: string) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        ) : fieldInfo.type === 'boolean' ? (
          <input
            type="checkbox"
            {...register(fieldName)}
            className="h-4 w-4"
            onChange={(e) => onChange(fieldName, e.target.checked)}
          />
        ) : fieldInfo.type === 'integer' || fieldInfo.type === 'float' ? (
          <input
            type="number"
            {...register(fieldName, { valueAsNumber: true })}
            className="w-full rounded border p-2"
            onChange={(e) => onChange(fieldName, parseFloat(e.target.value))}
          />
        ) : (
          <input
            type="text"
            {...register(fieldName)}
            className="w-full rounded border p-2"
            onChange={(e) => onChange(fieldName, e.target.value)}
          />
        )}

        {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {Object.entries(model.fields).map(([name, info]) =>
        renderField(name, info)
      )}
      <button
        type="submit"
        className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
      >
        保存配置
      </button>
    </form>
  )
}
```

### 7.3 实时日志流组件

```typescript
// frontend/src/components/LogStream.tsx

import React, { useEffect, useRef, useState } from 'react'
import { sseClient } from '@/services/sse'

interface LogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  source: string
  message: string
}

interface LogStreamProps {
  taskId: string
  maxLines?: number
}

const levelColors: Record<string, string> = {
  DEBUG: 'text-gray-500',
  INFO: 'text-blue-600',
  WARNING: 'text-yellow-600',
  ERROR: 'text-red-600',
  CRITICAL: 'text-red-800 bg-red-100'
}

export const LogStream: React.FC<LogStreamProps> = ({
  taskId,
  maxLines = 1000
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [filter, setFilter] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const autoScroll = useRef(true)

  useEffect(() => {
    const sse = sseClient.connect(
      `${import.meta.env.VITE_API_BASE_URL}/tasks/${taskId}/stream`,
      {
        onOpen: () => setIsConnected(true),
        onMessage: (data) => {
          if (data.type === 'heartbeat') return

          setLogs(prev => {
            const updated = [...prev, data]
            return updated.length > maxLines
              ? updated.slice(-maxLines)
              : updated
          })
        },
        onError: () => setIsConnected(false)
      }
    )

    return () => sse.disconnect()
  }, [taskId])

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  const filteredLogs = filter
    ? logs.filter(log =>
        log.message.toLowerCase().includes(filter.toLowerCase()) ||
        log.source.toLowerCase().includes(filter.toLowerCase())
      )
    : logs

  return (
    <div className="flex h-full flex-col rounded border">
      <div className="flex items-center justify-between border-b p-2">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm">{isConnected ? '实时' : '断开'}</span>
        </div>
        <input
          type="text"
          placeholder="过滤日志..."
          className="rounded border px-2 py-1 text-sm"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-2 font-mono text-sm"
        onScroll={(e) => {
          const target = e.target as HTMLDivElement
          autoScroll.current =
            target.scrollHeight - target.scrollTop - target.clientHeight < 50
        }}
      >
        {filteredLogs.map((log, index) => (
          <div key={index} className={`mb-1 ${levelColors[log.level] || ''}`}>
            <span className="text-gray-400">[{log.timestamp}]</span>
            <span className="ml-2 font-bold">{log.level}</span>
            <span className="ml-2 text-gray-500">[{log.source}]</span>
            <span className="ml-2">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 8. 与Step1-10的整合

### 8.1 整合矩阵

| Step | 前端页面/组件 | 后端接口 | 数据流 |
|------|-------------|---------|--------|
| **Step5** | TaskDashboard, DAGGraph | `/workflows/*`, `/tasks/*`, WebSocket | TaskOrchestrator状态 → WebSocket → React Flow节点着色 |
| **Step6** | KnowledgeBrowser, VectorProjection | `/rag/*`, `/knowledge/*` | RAG检索结果 → 向量投影图/知识图谱 |
| **Step7** | NovelWorkbench, ConfigForm | `/novels/*` | NovelConfig → 表单生成器 → LLM补全向导 |
| **Step10** | SystemSettings, ConfigForm | `/config/*` | AppConfig → 热加载控制面板 |
| **Step11** | 全部页面 | REST + WebSocket + SSE | API网关统一提供前端所需接口 |

### 8.2 Step5: 任务调度可视化

```
TaskOrchestrator (Step5)
    │
    ├── 节点状态变更 ──→ EventBus ──→ WebSocket Handler
    │                                              │
    │                                              ▼
    │                                        前端 TaskStore
    │                                              │
    │                                              ▼
    │                                        DAGGraph (React Flow)
    │                                              │
    │                                              ▼
    │                                        节点颜色/动画更新
    │
    ├── 工作流定义 ──→ GET /workflows/{name}/definition
    │                         │
    │                         ▼
    │                    前端加载DAG结构
    │                         │
    │                         ▼
    │                    React Flow渲染节点和边
    │
    └── 指标数据 ──→ GET /metrics/timeseries/{name}
                          │
                          ▼
                     MetricChart (ECharts)
```

### 8.3 Step6: RAG检索可视化

```
RAGEngine (Step6)
    │
    ├── 检索结果 ──→ POST /rag/search
    │                    │
    │                    ▼
    │               KnowledgeBrowser
    │                    │
    │                    ├── 文本列表展示
    │                    ├── 相似度分数条
    │                    └── 来源标注
    │
    ├── 向量投影 ──→ GET /knowledge/vectors/projection
    │                    │
    │                    ▼
    │               VectorProjection (D3.js)
    │                    │
    │                    ├── t-SNE/UMAP降维
    │                    ├── 点着色（按集合/类型）
    │                    └── 悬停显示原文
    │
    └── 知识图谱 ──→ GET /knowledge/world/{id}/facts/graph
                         │
                         ▼
                    KnowledgeGraph (D3.js力导向图)
```

### 8.4 Step7: 小说配置表单化

```
NovelConfig (Step7 Pydantic)
    │
    ├── 模型元数据 ──→ GET /novels/schema
    │                      │
    │                      ▼
    │                 ConfigForm组件
    │                      │
    │                      ├── 自动生成表单字段
    │                      ├── 类型验证
    │                      └── 枚举下拉框
    │
    ├── LLM补全 ──→ POST /novels/completion
    │                    │
    │                    ▼
    │               NovelWorkbench
    │                    │
    │                    ├── 输入框: "我想写修仙小说"
    │                    ├── 加载动画
    │                    └── 补全结果填充表单
    │
    └── 配置保存 ──→ PUT /novels/{id}/config
                          │
                          ▼
                     表单验证 → 提交 → 成功提示
```

### 8.5 Step10: ConfigHub可视化管理

```
AppConfig (Step10 Pydantic)
    │
    ├── 配置加载 ──→ GET /config
    │                  │
    │                  ▼
    │             SystemSettings页面
    │                  │
    │                  ├── Tab分组渲染
    │                  ├── 敏感项脱敏显示
    │                  └── 变更标记
    │
    ├── 热加载 ──→ POST /config/reload
    │                 │
    │                 ▼
    │            按钮触发 → 加载动画 → 新配置生效
    │
    └── 文件监听 ──→ WebSocket推送变更
                        │
                        ▼
                   前端提示: "配置已更新，是否刷新？"
```

---

## 9. 实施计划

### 9.1 文件变更清单

#### 新增文件

| 文件 | 职责 | 行数估计 |
|------|------|---------|
| `frontend/src/stores/novelStore.ts` | 小说配置状态管理 | 150 |
| `frontend/src/stores/taskStore.ts` | 任务调度状态管理 | 200 |
| `frontend/src/stores/agentStore.ts` | Agent管理状态管理 | 120 |
| `frontend/src/stores/knowledgeStore.ts` | 知识库状态管理 | 120 |
| `frontend/src/stores/configStore.ts` | 系统配置状态管理 | 150 |
| `frontend/src/services/api.ts` | REST API客户端 + TanStack Query | 120 |
| `frontend/src/services/websocket.ts` | WebSocket客户端封装 | 100 |
| `frontend/src/services/sse.ts` | SSE流客户端封装 | 60 |
| `frontend/src/components/DAGGraph.tsx` | DAG可视化 (React Flow) | 200 |
| `frontend/src/components/LogStream.tsx` | 实时日志流 | 150 |
| `frontend/src/components/ConfigForm.tsx` | Pydantic模型表单生成器 | 180 |
| `frontend/src/components/VectorProjection.tsx` | 向量空间投影 (D3.js) | 200 |
| `frontend/src/components/KnowledgeGraph.tsx` | 知识关系图谱 (D3.js) | 200 |
| `frontend/src/components/MemoryTimeline.tsx` | 记忆时间线 | 150 |
| `frontend/src/components/MetricChart.tsx` | 指标时序图表 (ECharts) | 120 |
| `frontend/src/views/NovelWorkbench.tsx` | 小说创作工作台 | 300 |
| `frontend/src/views/TaskDashboard.tsx` | 任务监控仪表盘 | 250 |
| `frontend/src/views/AgentManager.tsx` | Agent管理界面 | 200 |
| `frontend/src/views/KnowledgeBrowser.tsx` | 知识库浏览器 | 250 |
| `frontend/src/views/SystemSettings.tsx` | 系统设置面板 | 250 |
| `frontend/src/types/index.ts` | TypeScript类型定义 | 200 |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket Hook | 80 |
| `frontend/src/hooks/useSSE.ts` | SSE Hook | 60 |

#### 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `frontend/package.json` | 新增依赖 | reactflow, zustand, @tanstack/react-query, d3, echarts, axios, react-hook-form, zod |
| `frontend/src/App.tsx` | 新增路由 | 5个新页面路由 |
| `frontend/src/router/index.tsx` | 新增路由配置 | NovelWorkbench, TaskDashboard, AgentManager, KnowledgeBrowser, SystemSettings |
| `frontend/src/main.tsx` | 添加QueryClientProvider | TanStack Query支持 |
| `frontend/vite.config.ts` | 代理配置 | 开发环境API代理到后端 |

#### 删除文件

| 文件 | 说明 |
|------|------|
| `frontend/src/views/TaskMonitorView.vue` | Vue3迁移到React |
| `frontend/src/views/SystemHealthView.vue` | 功能合并到TaskDashboard |
| `frontend/src/components/SystemHealthPanel.vue` | 功能合并到TaskDashboard |

### 9.2 实施阶段（2周，与Step5 Phase 5并行）

#### Week 1: 基础设施 + 核心页面

```
Day 1: 项目初始化
- 初始化React + TypeScript + Vite项目
- 安装依赖: reactflow, zustand, tanstack-query, d3, echarts, axios, tailwindcss, shadcn/ui
- 配置TailwindCSS + shadcn/ui
- 搭建项目目录结构

Day 2: 服务层
- 实现apiClient (axios封装)
- 实现wsClient (WebSocket封装)
- 实现sseClient (SSE封装)
- 配置TanStack QueryClient

Day 3: 状态层
- 实现useTaskStore (任务状态)
- 实现useNovelStore (小说状态)
- 实现useConfigStore (配置状态)
- 实现useAgentStore (Agent状态)
- 实现useKnowledgeStore (知识库状态)

Day 4: TaskDashboard
- 实现DAGGraph组件 (React Flow)
- 实现LogStream组件
- 实现TaskDashboard页面
- 集成WebSocket实时更新

Day 5: NovelWorkbench
- 实现ConfigForm组件 (基础版)
- 实现NovelWorkbench页面
- 集成LLM补全向导
- 集成SSE实时预览
```

#### Week 2: 高级页面 + 可视化

```
Day 6: AgentManager
- 实现AgentManager页面
- Agent列表 + 详情面板
- LLM配置调整表单
- 性能指标图表 (ECharts)

Day 7: KnowledgeBrowser (上)
- 实现KnowledgeGraph组件 (D3.js力导向图)
- 世界事实图谱Tab
- 角色关系图Tab

Day 8: KnowledgeBrowser (下)
- 实现MemoryTimeline组件
- 实现VectorProjection组件 (t-SNE/UMAP)
- 检索测试面板

Day 9: SystemSettings
- 实现SystemSettings页面
- ConfigForm增强 (Tab分组、敏感项加密)
- 热加载控制面板
- 配置验证 + 导出

Day 10: 集成测试
- 端到端测试: 创建小说 → 配置 → 启动生成 → 监控DAG
- WebSocket压力测试 (100并发)
- 性能优化 (虚拟列表、懒加载)
```

### 9.3 关键里程碑

| 里程碑 | 日期 | 验收标准 |
|--------|------|---------|
| M1: 基础架构 | Day 2 | React+TypeScript项目运行，API/WebSocket/SSE客户端可用 |
| M2: 任务监控 | Day 5 | TaskDashboard可显示DAG，WebSocket实时更新延迟<500ms |
| M3: 创作工作台 | Day 5 | NovelWorkbench可配置小说，SSE实时预览正常 |
| M4: Agent管理 | Day 7 | AgentManager可查看/配置Agent，性能图表正常 |
| M5: 知识库 | Day 8 | KnowledgeBrowser可浏览图谱/时间线/向量投影 |
| M6: 系统设置 | Day 9 | SystemSettings可管理ConfigHub配置，热加载可用 |
| M7: 集成完成 | Day 10 | 端到端测试通过，所有页面无阻塞性Bug |

---

## 10. 量化验收标准

### 10.1 功能验收

| 编号 | 功能 | 验收标准 |
|------|------|---------|
| F1 | DAG可视化 | React Flow正确渲染Step5工作流定义，节点状态实时着色 |
| F2 | 实时推送 | WebSocket推送延迟<500ms，SSE日志流无丢包 |
| F3 | 小说配置 | NovelConfig表单可完整编辑，LLM补全向导可用 |
| F4 | 生成控制 | 可启动/暂停/停止生成任务，实时预览SSE内容 |
| F5 | Agent管理 | 可查看Agent列表、调整LLM配置、查看性能指标 |
| F6 | 知识图谱 | D3.js力导向图可展示世界事实/角色关系，支持缩放/拖拽 |
| F7 | 记忆时间线 | 按时间轴展示角色记忆，支持过滤/搜索 |
| F8 | 向量投影 | t-SNE/UMAP降维展示检索结果分布，悬停显示原文 |
| F9 | 系统配置 | AppConfig表单可编辑，热加载可控，敏感项加密 |
| F10 | 状态管理 | Zustand Store分层清晰，组件间无直接状态传递 |
| F11 | 类型安全 | 所有API响应有TypeScript类型定义，无any滥用 |
| F12 | 响应式 | 支持1280px+桌面端，布局自适应 |

### 10.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 首屏加载 | < 3s | Lighthouse性能评分 |
| DAG渲染 | < 2s (20节点) | React Flow首次渲染时间 |
| WebSocket延迟 | < 500ms | 事件产生到UI更新 |
| 日志流渲染 | 1000行不卡顿 | 滚动+过滤测试 |
| 知识图谱节点 | 支持500+节点 | D3.js力导向图性能 |
| 内存占用 | < 200MB | Chrome DevTools Memory |

### 10.3 兼容性验收

| 检查项 | 标准 |
|--------|------|
| 浏览器 | Chrome 120+, Firefox 120+, Edge 120+ |
| 后端版本 | 兼容Step5-11所有API |
| 数据格式 | REST JSON + WebSocket JSON + SSE text |
| 错误处理 | API失败显示友好错误，支持重试 |

---

## 11. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| Vue3到React迁移成本高 | 中 | 高 | 保留Vue3旧页面，React新页面并行，渐进式迁移 |
| WebSocket连接不稳定 | 中 | 高 | 实现自动重连+降级到轮询机制 |
| D3.js性能瓶颈（大图谱） | 低 | 中 | 超过500节点启用Canvas渲染，分层加载 |
| 前后端类型不一致 | 中 | 中 | 共享Pydantic模型生成TypeScript类型定义 |
| 配置表单过于复杂 | 中 | 低 | 按Tab分组，支持折叠/展开，搜索过滤 |
| 实时数据量过大 | 低 | 中 | 日志流限制1000行，WebSocket压缩传输 |

---

## 12. 附录

### A. 前端路由规划

```typescript
// frontend/src/router/index.tsx

import { createBrowserRouter } from 'react-router-dom'
import Layout from '@/components/Layout'
import NovelWorkbench from '@/views/NovelWorkbench'
import TaskDashboard from '@/views/TaskDashboard'
import AgentManager from '@/views/AgentManager'
import KnowledgeBrowser from '@/views/KnowledgeBrowser'
import SystemSettings from '@/views/SystemSettings'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        path: 'novel',
        children: [
          {
            path: 'workbench',
            element: <NovelWorkbench />,
            meta: { title: '创作工作台', icon: 'Edit' }
          },
          {
            path: 'workbench/:novelId',
            element: <NovelWorkbench />,
            meta: { title: '创作工作台' }
          }
        ]
      },
      {
        path: 'tasks',
        children: [
          {
            path: 'dashboard',
            element: <TaskDashboard />,
            meta: { title: '任务监控', icon: 'Activity' }
          },
          {
            path: 'dashboard/:workflowId',
            element: <TaskDashboard />,
            meta: { title: '任务监控' }
          }
        ]
      },
      {
        path: 'agents',
        children: [
          {
            path: 'manager',
            element: <AgentManager />,
            meta: { title: 'Agent管理', icon: 'Bot' }
          }
        ]
      },
      {
        path: 'knowledge',
        children: [
          {
            path: 'browser',
            element: <KnowledgeBrowser />,
            meta: { title: '知识库', icon: 'Database' }
          }
        ]
      },
      {
        path: 'system',
        children: [
          {
            path: 'settings',
            element: <SystemSettings />,
            meta: { title: '系统设置', icon: 'Settings' }
          }
        ]
      }
    ]
  }
])
```

### B. 依赖清单

```json
// frontend/package.json 新增依赖
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.8.0",
    "zustand": "^4.4.0",
    "reactflow": "^11.10.0",
    "d3": "^7.8.0",
    "echarts": "^5.4.0",
    "echarts-for-react": "^3.0.0",
    "axios": "^1.6.0",
    "react-hook-form": "^7.48.0",
    "zod": "^3.22.0",
    "@hookform/resolvers": "^3.3.0",
    "tailwindcss": "^3.3.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/d3": "^7.4.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

### C. 开发环境代理配置

```typescript
// frontend/vite.config.ts

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

### D. 环境变量模板

```bash
# frontend/.env.example

# API基础URL
VITE_API_BASE_URL=http://localhost:8000/api/v1

# WebSocket基础URL
VITE_WS_BASE_URL=ws://localhost:8000/api/v1

# 应用标题
VITE_APP_TITLE=AI-Novels 创作平台
```

---

> **文档结束**
>
> **关于Step12的定位**：本Step是REVIEW_Step1-10.md中识别的"未覆盖区域：前端层"的补充。前端作为用户与AI-Novels系统的唯一交互界面，必须覆盖后端所有核心能力的可视化控制。
>
> **实施建议**：
> 1. 建议将前端重构与Step5 Phase 5（测试与文档）并行实施
> 2. 优先实现TaskDashboard和NovelWorkbench，这两个页面是用户最高频使用的功能
> 3. AgentManager和KnowledgeBrowser可作为第二阶段增强
> 4. 如现有Vue3代码量较大，可考虑保留Vue3旧页面，新功能用React实现，逐步迁移
>
> **下一步**：按Week 1开始实施，优先搭建React项目骨架和API服务层。
