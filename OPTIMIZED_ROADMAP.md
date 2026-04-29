# AI-Novels 重构优化实施路线图

> 基于 REVIEW_Step1-10.md 审查报告反向优化后的实施路线
> 从线性16周串行 → 5 Phase并行12周

---

## 冲突修复清单

| 冲突 | 状态 | 修复位置 |
|------|------|---------|
| A: Step7↔Step10 配置双体系 | ✅ 已修复 | Step10 AppConfig增加 `novel`/`novel_presets` 字段；Step7 ConfigComposer标记为deprecated |
| B: Step4↔Step5 WorkflowEngine重名 | ✅ 已修复 | Step5 `WorkflowEngine` → `TaskOrchestrator`；Step4保留Agent层编排器，通过API调用TaskOrchestrator |
| C: Step6↔Step8 RAG边界不清 | ✅ 已修复 | Step6 `RAGToolRegistry` 标记为内部封装层；Step8通过 `@tool` 代理暴露给Agent |
| D: Step8↔Step9 Prompt未整合 | ✅ 已修复 | Step8 `_build_system_prompt_with_tools` 优先使用 Step9 `PromptComposer`，字符串拼接作为fallback |
| E: Step3↔Step10 Tier未体现 | ✅ 已修复 | Step10 `LLMConfig` 增加 `default_tier` 和 `tier_mapping` 字段 |

---

## 全局实施路线（5 Phase并行）

### Phase 1: 基础设施加固（第1-2周）

**目标**: 建立类型安全基础和统一配置入口，清理死代码

**并行实施**:
```
Step10 配置层 ──────┐
                    ├──→ ConfigHub可用 + 死代码清理完成
Step3 LLM层 ────────┤      （向后兼容层确保旧代码运行）
                    │
清理清单: coordinator, task_manager, rocketmq, chromadb_client
```

**检查点 CP1**: `ConfigHub().initialize()` 成功，Pydantic验证通过  
**检查点 CP2**: 至少一个LLM提供商可成功生成文本

**Step1-10关联调整**:
- Step10: 优先完成AppConfig + NovelConfig整合
- Step3: 优先实现Embedding（解锁Step6）

---

### Phase 2: 核心引擎替换（第3-5周）

**目标**: 替换假Embedding，建立事实管理和RAG检索

**并行实施**:
```
Step1 数据层 ───────┐
                    ├──→ FactManager可写 + RAG可搜 + Embedding可用
Step6 RAG层 ────────┤
                    │
Step2 记忆层(轻量) ──┘
```

**检查点 CP3**: FactManager可创建事实并查询  
**检查点 CP4**: RAG向量检索返回语义相关结果  
**检查点 CP5**: 至少一个适配器实现 embed/embed_batch

**Step1-10关联调整**:
- Step6: RAGToolRegistry作为内部层，为Step8预留代理接口
- Step1: FactManager接入ConfigHub获取数据库配置

---

### Phase 3: Agent能力升级（第6-8周）

**目标**: 新BaseAgent接入工具和Prompt，建立模板引擎

**并行实施**:
```
Step4 Agent层 ──────┐
                    ├──→ ToolEnabledAgent可用 + PromptComposer可用
Step8 工具层 ───────┤      （Agent可通过工具调用RAG/事实/记忆）
                    │
Step9 Prompt层 ─────┘
```

**检查点 CP6**: `@tool` 注册的工具可被Agent调用  
**检查点 CP7**: PromptComposer生成完整Prompt  
**检查点 CP8**: ToolEnabledAgent使用PromptComposer注入工具Schema

**Step1-10关联调整**:
- Step8: `_build_system_prompt_with_tools` 对接Step9 PromptComposer
- Step4: DirectorAgent通过API调用Step5 TaskOrchestrator（非直接继承）

---

### Phase 4: 编排与体验（第9-10周）

**目标**: TaskOrchestrator替换Coordinator，三级记忆接入Agent

**串行/并行混合**:
```
Step5 调度层 ───────┐
                    ├──→ TaskOrchestrator替换Coordinator
Step2 记忆层(完整) ──┤      （三级记忆接入Agent上下文）
                    │
Step7 配置补全 ──────┘      （NovelConfig通过ConfigHub统一管理）
```

**检查点 CP9**: TaskOrchestrator完成一次端到端小说生成  
**检查点 CP10**: 输入"修仙小说"自动补全完整配置  
**检查点 CP11**: MemoryManager三级记忆可存储和检索

**Step1-10关联调整**:
- Step5: TaskOrchestrator（原WorkflowEngine）避免与Step4混淆
- Step7: ConfigComposer deprecated，复用Step10 ProfileMerger

---

### Phase 5: 集成测试与清理（第11-12周）

**目标**: 端到端测试、删除旧兼容层、性能调优

**并行实施**:
```
端到端测试 ──────┐
                 ├──→ 系统可观测 + 旧兼容层删除
API层适配 ───────┤      （新增Step11: API网关层）
                 │
前端适配 ────────┘      （新增Step12: 前端可视化层）
```

**检查点 CP12**: DirectorAgent完成一次完整小说生成流水线  
**检查点 CP13**: API路由适配新架构（Step11）  
**检查点 CP14**: 任务可视化界面可实时监控（Step12）

**Step1-10关联调整**:
- Step11: FastAPI路由适配ConfigHub + TaskOrchestrator
- Step12: D3.js任务可视化对接Step5 EventBus统计

---

## 模块初始化顺序（运行时依赖）

```
1. ConfigHub        → 提供 AppConfig（包含novel子配置）
2. LLMRouter        → 依赖 ConfigHub
3. MemoryManager    → 依赖 ConfigHub, VectorStore
4. FactManager      → 依赖 ConfigHub, Database
5. RAGEngine        → 依赖 ConfigHub, LLMRouter, VectorStore
6. ToolRegistry     → 依赖 ConfigHub, RAGEngine, FactManager, MemoryManager
7. PromptComposer   → 依赖 ConfigHub, ToolRegistry
8. TaskOrchestrator → 依赖 ConfigHub, EventBus
9. DirectorAgent    → 依赖 TaskOrchestrator, ToolRegistry, PromptComposer
```

---

## 与旧路线图的关键变化

| 变化 | 旧方案 | 优化后 |
|------|--------|--------|
| 实施方式 | 10个Step线性串行（16周） | 5个Phase并行（12周） |
| Step5核心类 | `WorkflowEngine` | `TaskOrchestrator`（避免与Step4混淆） |
| 配置入口 | Step7 ConfigComposer + Step10 ConfigHub 双入口 | 统一为 ConfigHub，NovelConfig挂载到AppConfig |
| 工具Prompt | Step8 字符串拼接 | 优先使用 Step9 PromptComposer |
| RAG暴露 | Step6 直接暴露给Agent | Step6 内部层 → Step8 代理层 → Agent |
| 缺失覆盖 | 无API/前端规划 | 新增 Step11(API) + Step12(前端) |
| 测试保障 | 无 | 每个Phase配套集成测试 |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Phase 1 ConfigHub延期 | Phase 2-5全部阻塞 | ConfigHub设计保持最小可用，复杂功能（Vault/热加载）可延后 |
| Embedding适配器实现复杂 | Step3/6阻塞 | 优先实现OpenAI适配器，Ollama/BGE可延后 |
| 旧代码删除影响运行 | 开发中断 | Phase 1-4保留向后兼容层，Phase 5统一删除 |
| Agent迁移工作量大 | Phase 3延期 | BaseAgent改造后，各Agent通过继承自动获得能力 |

---

*生成日期: 2026-04-28*  
*基于: REVIEW_Step1-10.md 反向优化*
