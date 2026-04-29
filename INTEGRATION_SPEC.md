# AI-Novels 总装集成规范

> 文档版本: v1.0  
> 创建日期: 2026-04-28  
> 适用范围: Step1 ~ Step10 跨模块集成  
> 目标: 解决跨模块冲突，消除边界模糊，建立可执行的模块契约

---

## 1. 模块边界契约

### 1.1 核心原则

- **单一初始化入口**: 所有模块通过 `ConfigHub` 获取配置，禁止直接读取环境变量或配置文件。
- **显式依赖声明**: 每个模块必须在 `__init__` 中声明上游依赖，由 DI 容器按序注入。
- **接口优先**: 模块间调用必须通过公开接口，禁止穿透访问内部实现。

### 1.2 模块清单与契约

| 模块 | 提供能力 | 消费方 | 上游依赖 | 初始化顺序 | 关键文件 |
|------|---------|--------|----------|-----------|----------|
| **config_hub** | `AppConfig` 实例（含 `novel` 子配置） | 所有模块 | 无 | 第 1 位 | `config/hub.py`, `config/models.py` |
| **llm_router** | `generate()` / `embed()` / `stream()` | memory_manager, rag_engine, tool_registry, prompt_composer, agent_orchestrator | config_hub | 第 2 位 | `llm/router.py`, `llm/factory.py` |
| **memory_manager** | `store()` / `retrieve()` / `consolidate()` | tool_registry, agent_orchestrator | config_hub, vector_store | 第 3 位 | `memory/manager.py` |
| **fact_manager** | `set_fact()` / `query_facts()` | tool_registry, agent_orchestrator | config_hub, database | 第 3 位 | `world/fact_manager.py` |
| **rag_engine** | `NovelRAGService` | tool_registry, agent_orchestrator | config_hub, llm_router, vector_store | 第 4 位 | `rag/engine.py`, `rag/retrievers.py` |
| **tool_registry** | `register()` / `execute()` / `get_schemas()` | prompt_composer, agent_orchestrator | config_hub, rag_engine, fact_manager, memory_manager | 第 5 位 | `tools/registry.py`, `tools/decorator.py` |
| **prompt_composer** | `compose()` / `render()` | agent_orchestrator | config_hub, tool_registry, example_selector | 第 5 位 | `prompts/composer.py`, `prompts/components.py` |
| **task_orchestrator** | `TaskOrchestrator` / `CheckpointManager` | agent_orchestrator | config_hub, event_bus | 第 6 位 | `scheduling/orchestrator.py`, `scheduling/checkpoint.py` |
| **agent_orchestrator** | `DirectorAgent` / `PlotManager` | API 层 / 前端 | task_orchestrator, tool_registry, prompt_composer | 第 7 位 | `agents/director.py`, `agents/plot_manager.py` |

> **命名变更说明**: `workflow_engine`（Step5 原命名）已正式更名为 `task_orchestrator`，以避免与 Step4 Agent 层内部的编排概念混淆。

### 1.3 初始化时序图

```
Phase 1: 基础设施层
  [1] config_hub       ──→ AppConfig 加载完成
       │
       ▼
  [2] llm_router       ──→ LLM 工厂就绪，至少一个 Provider 可用

Phase 2: 数据与记忆层
  [3] memory_manager   ──→ 向量存储连接就绪
  [3] fact_manager     ──→ 数据库连接就绪（与 memory_manager 并行）

Phase 3: 检索与工具层
  [4] rag_engine       ──→ Embedding + HybridRetriever 就绪
       │
       ▼
  [5] tool_registry    ──→ 领域工具注册完成
  [5] prompt_composer  ──→ 模板引擎 + 示例库加载完成（与 tool_registry 并行）

Phase 4: 编排与智能层
  [6] task_orchestrator ──→ 任务队列 + 断点管理器就绪
       │
       ▼
  [7] agent_orchestrator ──→ DirectorAgent + PlotManager 初始化完成
```

### 1.4 依赖禁止穿透规则

| 禁止行为 | 说明 | 正确做法 |
|----------|------|----------|
| Agent 直接调用 `VectorStore` | Agent 层不应感知向量存储细节 | 通过 `rag_engine` 或 `tool_registry` 间接访问 |
| PromptComposer 直接调用 `LLMRouter` | Prompt 层不应触发 LLM 调用 | PromptComposer 仅负责文本组装，调用方负责执行 |
| TaskOrchestrator 直接操作 `Database` | 调度层不应感知持久化细节 | 通过 `fact_manager` / `memory_manager` 接口操作 |
| 任何模块直接读取 `os.environ` | 破坏配置集中管理 | 统一通过 `ConfigHub().config` 获取 |

---

## 2. 关键接口标准化

### 2.1 配置访问接口（所有 Step 统一）

```python
# 唯一入口
from src.deepnovel.config import ConfigHub

config = ConfigHub().config

# 访问小说业务配置
novel_config = config.novel
world_config = config.novel.world
character_config = config.novel.characters

# 访问系统级配置
llm_config = config.llm
db_config = config.database
```

**禁止方式（逐步迁移，兼容期内允许，新代码禁止）**:

```python
# 旧接口（标记为 deprecated）
from src.deepnovel.config import settings  # ❌ 逐步废弃

# 直接读取环境变量（绝对禁止）
os.environ.get("OPENAI_API_KEY")  # ❌ 禁止

# 直接读取配置文件（绝对禁止）
json.load(open("config.json"))  # ❌ 禁止
```

### 2.2 LLM 调用接口（Step3/4/6/8 统一）

```python
from src.deepnovel.llm import LLMRouter

router = LLMRouter()

# 文本生成
result = await router.generate(
    prompt="...",
    provider="openai",
    model="gpt-4o",
    tier="premium"  # 新增字段，见冲突 E 解决
)

# 嵌入向量
embedding = await router.embed(text="...", provider="openai")

# 流式生成
async for chunk in router.stream(prompt="...", provider="openai"):
    yield chunk
```

### 2.3 数据库访问接口（Step1/2/6 统一）

```python
# 统一通过 FactManager 和 MemoryManager，禁止直接操作底层客户端
from src.deepnovel.world import FactManager
from src.deepnovel.memory import MemoryManager

# 事实操作（结构化数据）
fact_manager = FactManager()
await fact_manager.set_fact(entity="主角", attribute="境界", value="筑基期")
facts = await fact_manager.query_facts(entity="主角")

# 记忆操作（非结构化语义数据）
memory_manager = MemoryManager()
await memory_manager.store(content="主角在青云山修炼", context={"chapter": 3})
memories = await memory_manager.retrieve(query="主角修炼地点", top_k=5)
```

**禁止方式**:

```python
# 禁止直接操作底层数据库客户端
from src.deepnovel.database import MySQLClient  # ❌ 禁止
from src.deepnovel.vector_store import ChromaStore  # ❌ 禁止
```

### 2.4 工具调用接口（Step8 统一）

```python
from src.deepnovel.tools import ToolRegistry

registry = ToolRegistry()

# 注册工具
@registry.register(description="检索世界观知识")
async def retrieve_world_knowledge(query: str) -> str:
    ...

# 执行工具
result = await registry.execute("retrieve_world_knowledge", {"query": "修仙境界划分"})

# 获取工具 Schema（供 PromptComposer 使用）
schemas = registry.get_schemas()
```

### 2.5 Prompt 组装接口（Step9 统一）

```python
from src.deepnovel.prompts import PromptComposer

composer = PromptComposer()

# 组装 Prompt
prompt = composer.compose(
    template_id="chapter_generation",
    params={
        "novel_context": {...},
        "chapter_outline": {...},
        "tools": registry.get_schemas(),  # 动态注入工具 Schema
        "reasoning_mode": "chain_of_thought"
    }
)

# 渲染模板
rendered = composer.render(template_id="system_prompt", params={"role": "writer"})
```

---

## 3. 跨 Step 冲突解决记录

### 3.1 冲突 A: Step7 ↔ Step10 — 配置模型体系冲突

| 属性 | 内容 |
|------|------|
| **严重程度** | 高 |
| **问题描述** | Step7 定义 `NovelConfig` / `WorldConfig` / `CharacterConfig` / `OutlineConfig` 等小说业务配置模型；Step10 定义 `AppConfig` 作为根配置，包含 `llm` / `database` / `agents` / `rag` 等系统级配置。两套模型体系完全平行，无关联关系。 |
| **解决方案** | 1. `AppConfig` 增加 `novel: Optional[NovelConfig]` 字段，将小说业务配置纳入统一配置体系。<br>2. 删除 Step7 独立的 `ConfigComposer`，复用 Step10 的 `ProfileMerger`。<br>3. `LLMConfigCompleter` 作为 `novel` 字段的验证器集成到 `AppConfig`。 |
| **当前状态** | 已解决，代码已更新 |
| **兼容层** | `ConfigComposer` 保留为 deprecated 别名，计划 v1.2 移除 |

```python
# 解决后的 AppConfig 结构
class AppConfig(ConfigBase):
    # 系统级配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DBConfig = Field(default_factory=DBConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    
    # 整合 Step7 的小说业务配置
    novel: Optional[NovelConfig] = Field(default=None, description="当前小说配置")
    novel_presets: Dict[str, NovelConfig] = Field(default_factory=dict, description="小说配置预设")
    
    # 整合 Step7 的模板引擎配置
    templates: TemplateConfig = Field(default_factory=TemplateConfig, description="Prompt 模板配置")
```

### 3.2 冲突 B: Step4 ↔ Step5 — WorkflowEngine 命名与职责冲突

| 属性 | 内容 |
|------|------|
| **严重程度** | 中 |
| **问题描述** | Step4 定义 `DirectorAgent` + `WorkflowEngine`（Agent 层内部编排）；Step5 定义独立的 `WorkflowEngine` + `TaskScheduler` + `CheckpointManager`。两个 `WorkflowEngine` 名称相同但职责不同。 |
| **解决方案** | 1. Step5 的 `WorkflowEngine` 改名为 `TaskOrchestrator`，避免混淆。<br>2. Step4 的 `DirectorAgent` 通过 API 调用 Step5 的服务，而非直接继承。<br>3. 明确分层：Step4 为 Agent 编排层（决策+调度请求），Step5 为任务调度层（基础设施）。 |
| **当前状态** | 已解决，代码已更新 |
| **兼容层** | `WorkflowEngine` 保留为 `TaskOrchestrator` 的 deprecated 别名，计划 v1.1 移除 |

```
明确分层：
┌─────────────────────────────────────────┐
│ Step4: Agent 编排层                      │
│  • DirectorAgent - 导演（决策+调度请求） │
│  • PlotManagerAgent - 情节管理          │
│  • 使用 Step5 的引擎执行                │
├─────────────────────────────────────────┤
│ Step5: 任务调度层（基础设施）            │
│  • TaskOrchestrator（原 WorkflowEngine）│
│  • TaskScheduler - 任务队列             │
│  • CheckpointManager - 断点恢复         │
└─────────────────────────────────────────┘
```

### 3.3 冲突 C: Step6 ↔ Step8 — RAG 核心实现归属冲突

| 属性 | 内容 |
|------|------|
| **严重程度** | 中 |
| **问题描述** | Step6 设计完整 RAG 六层架构；Step8 将 RAG 封装为工具。但 Step6 的 Application Layer 已包含 `NovelRAGService` 和 `RetrieverTools`，导致同一功能在不同层重复定义。 |
| **解决方案** | 1. Step6 实现 RAG 服务层（核心实现：`NovelRAGService` / `EmbeddingEngine` / `HybridRetriever`）。<br>2. Step8 只做工具代理层，工具函数内部调用 Step6 的服务，不做重复实现。<br>3. Step6 的 `RetrieverTools` 标记为 `@internal`，不直接暴露给 Agent。 |
| **当前状态** | 已解决，代码已更新 |
| **兼容层** | Step6 `RetrieverTools` 保留但标记为内部使用，计划 v1.3 移除外部访问入口 |

```
明确边界：
┌─────────────────────────────────────────┐
│ Step8: 工具层（Agent 调用入口）          │
│  • @tool retrieve_world_knowledge()     │
│  • 内部实现：调用 Step6 的 RAG 服务      │
│  • 职责：协议转换（MCP/Function Call）   │
├─────────────────────────────────────────┤
│ Step6: RAG 服务层（核心实现）            │
│  • NovelRAGService                      │
│  • EmbeddingEngine / HybridRetriever    │
│  • 职责：检索逻辑、向量运算、重排序       │
└─────────────────────────────────────────┘
```

### 3.4 冲突 D: Step8 ↔ Step9 — ToolEnabledAgent Prompt 生成冲突

| 属性 | 内容 |
|------|------|
| **严重程度** | 中 |
| **问题描述** | Step8 的 `ToolEnabledAgent._build_system_prompt_with_tools()` 使用字符串拼接注入工具 Schema；Step9 设计 `PromptComposer` + `PromptComponent` 的声明式模板组装。Step8 未引用 Step9 的任何组件。 |
| **解决方案** | 1. `ToolEnabledAgent` 优先使用 `PromptComposer` 组装带工具 Schema 的 System Prompt。<br>2. 废弃字符串拼接方式，统一接入模板引擎、少样本示例、推理模式。 |
| **当前状态** | 已解决，代码已更新 |
| **兼容层** | `_build_system_prompt_with_tools()` 保留为 fallback，计划 v1.2 移除 |

```python
# 解决后的 ToolEnabledAgent
class ToolEnabledAgent(BaseAgent):
    def _build_system_prompt_with_tools(self, base_prompt: str) -> str:
        # 旧方式（字符串拼接）→ 废弃
        # 新方式：使用 Step9 的 PromptComposer
        from src.deepnovel.prompts.composer import PromptComposer
        composer = PromptComposer()
        return composer.compose(
            "tool_enabled_agent",
            params={
                "base_role": base_prompt,
                "available_tools": self._get_tool_schemas(),
                "reasoning_mode": self._reasoning_mode
            }
        )
```

### 3.5 冲突 E: Step3 ↔ Step10 — LLM 功能分级字段缺失

| 属性 | 内容 |
|------|------|
| **严重程度** | 低 |
| **问题描述** | LLM 功能分级（Tier）在 Step3 定义，Step10 的 `LLMConfig` 未体现该字段，导致配置层无法支持按能力分级路由。 |
| **解决方案** | 1. `LLMConfig` 增加 `tier: str` 和 `capability: List[str]` 字段。<br>2. `LLMRouter` 根据 `tier` 字段选择对应级别的模型实例。 |
| **当前状态** | 已解决，代码已更新 |
| **兼容层** | 无，字段新增不影响向后兼容 |

```python
# 解决后的 LLMConfig
class LLMConfig(ConfigBase):
    provider: str = "openai"
    model: str = "gpt-4o"
    tier: str = Field(default="premium", description="模型能力级别: basic/standard/premium")
    capability: List[str] = Field(default_factory=list, description="模型能力标签")
    api_key: Optional[str] = None
    base_url: Optional[str] = None
```

---

## 4. 数据流图

### 4.1 模块间数据流向

```
                         ┌─────────────────┐
                         │   ConfigHub     │
                         │  (AppConfig)    │
                         └────────┬────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌─────────────┐      ┌─────────────────┐      ┌─────────────┐
   │ LLMRouter   │      │  FactManager    │      │VectorStore  │
   │(generate/  │      │(set_fact/      │      │(embed/     │
   │ embed)      │      │ query_facts)    │      │ search)     │
   └──────┬──────┘      └────────┬────────┘      └──────┬──────┘
          │                       │                       │
          │         ┌─────────────┘                       │
          │         │                                     │
          ▼         ▼                                     ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                      RAG Engine                             │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │EmbeddingEngine│ │HybridRetriever│ │   NovelRAGService   │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                   Memory Manager                            │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ 感知记忆     │ │  工作记忆    │ │      长期记忆        │  │
   │  │ (Sensory)   │ │ (Working)   │ │    (Long-term)      │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                   Tool Registry                             │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │  @tool 装饰器 │ │  工具执行器   │ │    Schema 生成器     │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                  Prompt Composer                            │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ 模板组件     │ │ 少样本选择器  │ │    推理模式注入      │  │
   │  │(Components) │ │(Few-shot)   │ │  (Chain-of-Thought) │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                Task Orchestrator                            │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ 任务调度器   │ │  状态管理    │ │    断点恢复器        │  │
   │  │(Scheduler)  │ │(State Machine)│ │ (CheckpointManager) │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                Agent Orchestrator                           │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ DirectorAgent│ │ PlotManager │ │   NarrativePlanner  │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                     API Layer                               │
   │              (FastAPI Routes / Frontend)                    │
   └─────────────────────────────────────────────────────────────┘
```

### 4.2 典型请求数据流示例

**场景: 用户请求生成新章节**

```
1. API Layer 接收请求
   │
   ▼
2. Agent Orchestrator
   ├─ DirectorAgent 决策生成策略
   └─ 调用 TaskOrchestrator 创建任务图
        │
        ▼
3. Task Orchestrator
   ├─ 调度任务节点
   ├─ 加载 Checkpoint（如存在）
   └─ 通过 EventBus 广播状态变更
        │
        ▼
4. Prompt Composer
   ├─ 加载章节生成模板
   ├─ 注入工具 Schema（来自 ToolRegistry）
   ├─ 选择少样本示例
   └─ 组装完整 Prompt
        │
        ▼
5. Tool Registry（如需要工具调用）
   ├─ 检索世界观知识 → RAG Engine → VectorStore
   ├─ 查询角色状态 → FactManager → Database
   └─ 检索相关记忆 → MemoryManager → VectorStore
        │
        ▼
6. LLM Router
   ├─ 根据 tier 选择模型
   ├─ 调用 generate() 或 stream()
   └─ 返回生成结果
        │
        ▼
7. Agent Orchestrator
   ├─ 解析 LLM 输出
   ├─ 更新 PlotManager 状态
   └─ 存储新生成的事实到 FactManager
        │
        ▼
8. Task Orchestrator
   └─ 保存 Checkpoint，标记任务完成
        │
        ▼
9. API Layer 返回响应
```

---

## 5. 错误处理契约

### 5.1 异常分类体系

| 异常类别 | 基类 | 使用场景 | HTTP 状态码映射 |
|----------|------|----------|----------------|
| **配置异常** | `ConfigError` | 配置加载失败、验证错误、缺失必填项 | 500 |
| **LLM 异常** | `LLMError` | 模型调用失败、配额超限、网络超时 | 503 |
| **数据异常** | `DataError` | 数据库操作失败、事实冲突、Schema 不匹配 | 500 |
| **检索异常** | `RetrievalError` | 向量检索失败、索引缺失、Embedding 错误 | 500 |
| **工具异常** | `ToolError` | 工具执行失败、参数验证错误、工具未注册 | 400 |
| **Prompt 异常** | `PromptError` | 模板渲染失败、变量缺失、组件未找到 | 500 |
| **调度异常** | `OrchestrationError` | 任务调度失败、状态机非法转换、断点损坏 | 500 |
| **Agent 异常** | `AgentError` | Agent 决策失败、工具调用链过长、循环检测 | 500 |

### 5.2 异常传播规范

#### 5.2.1 向上传播原则

```python
# 模块内部捕获具体异常，转换为模块级异常后向上传播
class RAGEngine:
    async def retrieve(self, query: str) -> List[Document]:
        try:
            embedding = await self.llm_router.embed(query)
        except LLMError as e:
            # 转换为模块级异常，保留原始异常链
            raise RetrievalError(
                f"Embedding generation failed for query: {query}",
                cause=e
            ) from e
        
        try:
            results = await self.vector_store.search(embedding)
        except ConnectionError as e:
            raise RetrievalError(
                f"Vector store search failed",
                cause=e
            ) from e
        
        return results
```

#### 5.2.2 跨模块调用异常处理

```python
# 调用方必须处理被调用模块的异常
class ToolRegistry:
    async def execute(self, tool_name: str, params: dict) -> Any:
        tool = self._tools.get(tool_name)
        if not tool:
            raise ToolError(f"Tool '{tool_name}' not registered")
        
        try:
            # 调用 RAG Engine
            if tool.category == "retrieval":
                return await self.rag_engine.retrieve(**params)
        except RetrievalError as e:
            # 转换为 ToolError，保留原始信息
            raise ToolError(
                f"Tool '{tool_name}' execution failed: {e.message}",
                tool_name=tool_name,
                cause=e
            ) from e
        
        try:
            # 调用 FactManager
            if tool.category == "fact":
                return await self.fact_manager.query_facts(**params)
        except DataError as e:
            raise ToolError(
                f"Tool '{tool_name}' execution failed: {e.message}",
                tool_name=tool_name,
                cause=e
            ) from e
```

#### 5.2.3 边界异常处理（API 层）

```python
# API 层统一捕获所有异常，转换为标准响应格式
@app.exception_handler(ConfigError)
async def config_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "config_error",
                "message": exc.message,
                "details": exc.details,
                "module": exc.module
            }
        }
    )

@app.exception_handler(LLMError)
async def llm_error_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "type": "llm_error",
                "message": exc.message,
                "provider": exc.provider,
                "model": exc.model,
                "retryable": exc.is_retryable
            }
        }
    )
```

### 5.3 重试与降级策略

| 模块 | 可重试异常 | 重试策略 | 降级策略 |
|------|-----------|----------|----------|
| LLMRouter | `LLMError` (timeout/quota) | 指数退避，最多 3 次 | 切换备用 Provider，或返回 cached response |
| RAG Engine | `RetrievalError` (network) | 立即重试 1 次 | 返回空结果，标记为 "检索不可用" |
| MemoryManager | `DataError` (connection) | 指数退避，最多 3 次 | 写入本地文件队列，异步回放 |
| FactManager | `DataError` (conflict) | 不重试 | 返回冲突详情，由 Agent 决策解决 |
| TaskOrchestrator | `OrchestrationError` | 根据 Checkpoint 恢复 | 人工介入，或回滚到上一个稳定状态 |

---

## 6. 版本兼容性策略

### 6.1 向后兼容层清单

| 兼容层 | 原名称 | 新名称 | 保留版本 | 移除计划 | 当前状态 |
|--------|--------|--------|----------|----------|----------|
| ConfigComposer | `ConfigComposer` (Step7) | `ProfileMerger` (Step10) | v1.0 | v1.2 | deprecated，输出警告 |
| WorkflowEngine | `WorkflowEngine` (Step5) | `TaskOrchestrator` | v1.0 | v1.1 | deprecated，输出警告 |
| RetrieverTools | `RetrieverTools` (Step6) | `NovelRAGService` | v1.0 | v1.3 | 标记为 `@internal` |
| ToolPromptBuilder | `_build_system_prompt_with_tools()` (Step8) | `PromptComposer.compose()` | v1.0 | v1.2 | fallback 模式 |
| SettingsModule | `from src.deepnovel.config import settings` | `ConfigHub().config` | v1.0 | v1.3 | deprecated，输出警告 |

### 6.2 兼容层实现规范

```python
# 示例: WorkflowEngine → TaskOrchestrator 兼容层
import warnings
from .orchestrator import TaskOrchestrator

class WorkflowEngine(TaskOrchestrator):
    """
    向后兼容别名，计划 v1.1 移除。
    
    迁移指南:
        旧: from src.deepnovel.scheduling import WorkflowEngine
        新: from src.deepnovel.scheduling import TaskOrchestrator
    """
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WorkflowEngine is deprecated and will be removed in v1.1. "
            "Use TaskOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
```

### 6.3 移除时间表

```
v1.0 (当前)
  ├── 所有兼容层启用
  ├── 旧接口输出 DeprecationWarning
  └── 新接口全面可用

v1.1 (预计 6 周后)
  ├── 移除 WorkflowEngine 兼容层
  └── 更新所有内部引用为 TaskOrchestrator

v1.2 (预计 10 周后)
  ├── 移除 ConfigComposer 兼容层
  ├── 移除 _build_system_prompt_with_tools() fallback
  └── 更新所有内部引用

v1.3 (预计 14 周后)
  ├── 移除 RetrieverTools 外部访问入口
  ├── 移除 settings 模块兼容层
  └── 仅保留 ConfigHub 作为配置入口
```

### 6.4 迁移检查清单

- [ ] 全局搜索 `WorkflowEngine`，替换为 `TaskOrchestrator`
- [ ] 全局搜索 `ConfigComposer`，替换为 `ProfileMerger`
- [ ] 全局搜索 `from src.deepnovel.config import settings`，替换为 `ConfigHub`
- [ ] 全局搜索 `_build_system_prompt_with_tools`，替换为 `PromptComposer.compose`
- [ ] 全局搜索 `RetrieverTools` 的直接调用，改为通过 `ToolRegistry` 或 `NovelRAGService`
- [ ] 运行集成测试，确认无 `DeprecationWarning`
- [ ] 更新 API 文档和代码注释

---

## 7. 附录

### 7.1 术语表

| 术语 | 定义 |
|------|------|
| ConfigHub | 统一配置管理中心，提供类型安全的配置访问 |
| TaskOrchestrator | 任务编排器（原 WorkflowEngine），负责任务调度与状态管理 |
| PromptComposer | 声明式 Prompt 组装引擎，支持模板、组件、少样本示例 |
| ToolRegistry | 工具注册中心，管理 `@tool` 装饰器注册的工具 |
| NovelRAGService | 小说领域 RAG 服务，封装检索逻辑与向量运算 |
| FactManager | 事实管理器，提供结构化的世界状态读写 |
| MemoryManager | 记忆管理器，管理感知/工作/长期三级记忆 |
| DirectorAgent | 导演 Agent，负责小说生成的高层决策与编排 |

### 7.2 相关文档

- `Step1.md` ~ `Step10.md` — 各模块详细设计文档
- `REVIEW_Step1-10.md` — 综合审查报告（冲突分析来源）
- `src/deepnovel/config/models.py` — Pydantic 配置模型定义
- `src/deepnovel/agents/base.py` — Agent 基类与接口

### 7.3 修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|----------|--------|
| v1.0 | 2026-04-28 | 初始版本，涵盖模块边界、接口标准、冲突解决、数据流、错误处理、兼容性策略 | 架构师 |
