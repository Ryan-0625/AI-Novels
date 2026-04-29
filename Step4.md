# Step 4: Agent层重构 - 分层自治智能体架构

## 1. 设计哲学

### 核心转变

```
从：功能型Agent（按任务粗分） → 到：分层自治Agent（按认知层级分离）
从：消息驱动（命令式）        → 到：状态驱动（声明式）
从：单体大Agent              → 到：微智能体协作
从：人工编排工作流            → 到：自组织状态图执行
从：模拟与叙事混为一体        → 到：Simulation-to-Narrative Pipeline
```

### 设计原则

1. **Agent即认知单元**：每个Agent对应一种认知功能（感知/推理/决策/创造/审查）
2. **状态即契约**：Agent间通过共享状态交互，而非直接消息调用
3. **模拟先于叙事**：世界模拟（fabula）和文学表达（syuzhet）严格分离
4. **工具即能力边界**：Agent的能力由工具集定义，工具即权限
5. **记忆分层共享**：感知/工作/长期记忆按Step2三级阶梯管理
6. **LLM即推理引擎**：Agent的核心推理由LLM驱动，但由状态机控制调用时机

### 行业前沿参考

| 来源 | 核心借鉴 |
|------|---------|
| LangGraph (2026) | 状态图驱动、增量状态更新、Checkpoints |
| CrewAI / AutoGen | 角色专业化、层次化监督 |
| ACL 2025 Character Simulation | Director-Agent框架、fabula→syuzhet分离 |
| StoryWriter (2025) | Outline→Planning→Writing三级流水线 |
| MUSE (2026) | Plan-Execute-Verify-Revise闭环验证 |
| OpenAI Swarm | 自然Handoff、轻量级协调 |
| A2A/ACP Protocol | Agent间标准化通信协议 |

---

## 2. 架构总览

### 2.1 五层Agent架构

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: 用户交互层 (User Interface)                         │
│  • UserIntentParser - 用户意图解析                           │
│  • SessionController - 会话状态管理                          │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: 编排控制层 (Orchestration)                          │
│  • DirectorAgent - 导演智能体（叙事总控）                     │
│  • PlotManagerAgent - 情节管理智能体（节奏/转折）              │
│  • WorkflowEngine - 工作流引擎（状态图执行）                  │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: 世界模拟层 (World Simulation)                       │
│  • WorldStateAgent - 世界状态智能体（事实/规则）               │
│  • CharacterMindAgent - 角色心智智能体（记忆/信念/情感/决策）   │
│  • CausalEngineAgent - 因果推理智能体（追溯/预测/反事实）      │
│  • EventSimulatorAgent - 事件模拟智能体（生成/传播/连锁）      │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: 叙事生成层 (Narrative Generation)                   │
│  • NarrativePlannerAgent - 叙事规划智能体（弧线/结构/视角）     │
│  • SceneWriterAgent - 场景写作智能体（描写/动作/环境）         │
│  • DialogueWriterAgent - 对话写作智能体（对话/语气/潜台词）    │
│  • StyleEnforcerAgent - 风格约束智能体（一致性/修辞/规范）     │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: 基础设施层 (Infrastructure)                         │
│  • EventBus - 事件总线（Agent间通信）                        │
│  • ToolRegistry - 工具注册中心                               │
│  • MemoryManager - 记忆管理器（三级阶梯）                    │
│  • LLMRouter - LLM路由（Step3）                             │
│  • VectorStore - 向量存储（语义检索）                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Agent通信拓扑

```
                      ┌──────────────┐
                      │   Director   │
                      │    Agent     │
                      └──────┬───────┘
                             │ 状态图调度
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
   │  Plot   │         │  World  │         │Narrative│
   │ Manager │         │  State  │         │ Planner │
   └────┬────┘         └────┬────┘         └────┬────┘
        │                   │                   │
   ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
   │ Event   │         │Character│         │ Scene   │
   │Simulator│         │  Mind   │         │ Writer  │
   └────┬────┘         └────┬────┘         └────┬────┘
        │                   │                   │
   ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
   │ Causal  │         │ Dialogue│         │ Style   │
   │ Engine  │         │ Writer  │         │Enforcer │
   └─────────┘         └─────────┘         └─────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                   ┌────────┴────────┐
                   │Consistency/     │
                   │Continuity       │
                   │Checker          │
                   └─────────────────┘
```

**通信规则**：
- 同层Agent通过EventBus异步通信
- 跨层Agent通过状态读写交互（上层读下层状态，下层响应上层指令）
- DirectorAgent拥有全局状态写权限，其他Agent只写自己的状态分区
- Quality Layer Agent只读不写，输出审查报告到共享状态

### 2.3 核心数据流：Simulation-to-Narrative Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   用户输入   │───→│   Director  │───→│  PlotManager│
│             │    │   Agent     │    │             │
└─────────────┘    └──────┬──────┘    └──────┬──────┘
                          │                    │
                          ↓                    ↓
                   ┌─────────────┐    ┌─────────────┐
                   │  叙事意图    │    │  情节节拍    │
                   │  (Intent)   │    │  (Beats)    │
                   └──────┬──────┘    └──────┬──────┘
                          │                    │
                          └────────┬───────────┘
                                   ↓
┌──────────────────────────────────────────────────────┐
│              世界模拟层 (Fabula)                       │
│                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│   │Character │   │  Event   │   │  Causal  │        │
│   │  Mind    │──→│Simulator │──→│ Engine   │        │
│   │(决策生成) │   │(事件传播) │   │(因果验证) │        │
│   └──────────┘   └──────────┘   └──────────┘        │
│         ↑                              │             │
│         └──────────┬───────────────────┘             │
│                    ↓                                 │
│            ┌──────────────┐                          │
│            │  WorldState  │                          │
│            │  (事实图谱)   │                          │
│            └──────────────┘                          │
└──────────────────────┬───────────────────────────────┘
                       │ 模拟事件流
                       ↓
┌──────────────────────────────────────────────────────┐
│              叙事生成层 (Syuzhet)                      │
│                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│   │Narrative │   │  Scene   │   │ Dialogue │        │
│   │ Planner  │──→│  Writer  │──→│  Writer  │        │
│   │(弧线规划) │   │(场景描写) │   │(对话润色) │        │
│   └──────────┘   └──────────┘   └──────────┘        │
│         ↑                              │             │
│         └──────────┬───────────────────┘             │
│                    ↓                                 │
│            ┌──────────────┐                          │
│            │StyleEnforcer │                          │
│            │  (风格约束)   │                          │
│            └──────────────┘                          │
└──────────────────────┬───────────────────────────────┘
                       │ 叙事片段
                       ↓
┌──────────────────────────────────────────────────────┐
│              质量保障层 (Quality Gate)                 │
│                                                      │
│   ┌──────────────┐   ┌──────────────┐               │
│   │ Consistency  │   │  Continuity  │               │
│   │   Checker    │──→│   Auditor    │               │
│   │(事实/角色一致)│   │(跨章节连续)  │               │
│   └──────────────┘   └──────────────┘               │
└──────────────────────┬───────────────────────────────┘
                       │ 通过/驳回
                       ↓
                ┌──────────────┐
                │   最终输出   │
                │  (叙事文本)  │
                └──────────────┘
```

---

## 3. Agent分类与定义

### 3.1 编排控制层

#### DirectorAgent - 导演智能体

**职责**：叙事总导演，解析用户意图，制定创作策略，调度下层Agent

**核心能力**：
- 用户意图解析（genre/style/length/theme提取）
- 创作策略制定（模拟优先 vs 叙事优先）
- Agent编排调度（状态图实例化与执行）
- 创作中断与恢复（Checkpoint管理）

**状态分区**：`director.*`

**工具集**：
- `parse_intent` - 解析用户自然语言意图
- `create_workflow` - 创建工作流实例
- `set_strategy` - 设置创作策略参数
- `pause_resume` - 暂停/恢复创作流程

**LLM配置**：
```python
{
    "primary": {"provider": "openai", "model": "gpt-4o", "temperature": 0.3, "tier": "reasoning"},
    "fallback": {"provider": "anthropic", "model": "claude-sonnet-4-6", "temperature": 0.3}
}
```

**实现模板**：
```python
class DirectorAgent(BaseAgent):
    """
    导演智能体 - 叙事总控

    参考：LangGraph StateGraph + OpenAI Swarm Handoff
    """

    STATE_SCHEMA = {
        "user_intent": UserIntent,      # 用户意图结构化
        "creation_strategy": Strategy,   # 创作策略
        "workflow_state": WorkflowState, # 工作流执行状态
        "checkpoints": List[Checkpoint], # 检查点列表
        "active_agents": Set[str],       # 当前活跃Agent
    }

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._workflow_engine = WorkflowEngine()
        self._strategy_planner = StrategyPlanner()

    def process(self, state: AgentState) -> AgentState:
        """
        导演处理循环

        流程：
        1. 读取用户输入状态
        2. 解析/更新意图
        3. 评估当前策略是否需要调整
        4. 生成下一步指令写入共享状态
        5. 返回更新后的状态
        """
        user_input = state.get("director.user_input")

        if user_input:
            # 解析用户意图
            intent = self._parse_intent(user_input)
            state.set("director.user_intent", intent)

        # 获取当前工作流状态
        wf_state = state.get("director.workflow_state")

        # 基于意图和策略，决定下一步
        next_action = self._decide_next_action(state)

        # 将指令写入共享状态（下层Agent读取）
        state.set("shared.directive", next_action)
        state.set("director.workflow_state", self._update_workflow_state(wf_state, next_action))

        return state

    def _parse_intent(self, user_input: str) -> UserIntent:
        """使用LLM解析用户意图"""
        prompt = self._build_intent_prompt(user_input)
        result = self.llm.generate_structured(prompt, schema=UserIntent)
        return result

    def _decide_next_action(self, state: AgentState) -> Directive:
        """
        决策下一步行动

        基于：
        - 用户意图（目标）
        - 当前世界状态（事实）
        - 叙事进度（章节）
        - 质量反馈（审查报告）
        """
        context = self._assemble_director_context(state)
        prompt = self._build_decision_prompt(context)
        result = self.llm.generate_structured(prompt, schema=Directive)
        return result
```

---

#### PlotManagerAgent - 情节管理智能体

**职责**：管理情节节奏、设计转折点、调度冲突升级

**核心能力**：
- 情节节拍生成（Beats generation）
- 转折点调度（Plot point scheduling）
- 冲突强度曲线管理（Tension arc management）
- 伏笔播种与回收（Foreshadowing tracking）

**状态分区**：`plot.*`

**工具集**：
- `generate_beats` - 生成情节节拍序列
- `schedule_turning_point` - 调度转折点
- `measure_tension` - 测量当前叙事张力
- `track_foreshadowing` - 跟踪伏笔状态

**实现模板**：
```python
class PlotManagerAgent(BaseAgent):
    """
    情节管理智能体

    参考：StoryWriter Outline Agent + Dramatron Plot Manager
    """

    STATE_SCHEMA = {
        "plot_beats": List[PlotBeat],           # 情节节拍序列
        "turning_points": List[TurningPoint],   # 转折点列表
        "tension_curve": List[float],           # 张力曲线
        "foreshadowing": Dict[str, Foreshadow], # 伏笔跟踪
        "conflict_stack": List[Conflict],       # 冲突栈
    }

    def process(self, state: AgentState) -> AgentState:
        """
        情节管理循环

        输入：导演指令 + 当前叙事状态 + 世界状态
        输出：更新后的情节节拍 + 下一步叙事指令
        """
        directive = state.get("shared.directive")

        if directive.type == "plan_plot":
            # 生成整体情节结构
            beats = self._generate_plot_beats(state)
            state.set("plot.plot_beats", beats)

        elif directive.type == "next_beat":
            # 为下一章节生成节拍
            next_beat = self._generate_next_beat(state)
            state.set("shared.current_beat", next_beat)

        elif directive.type == "check_turning_point":
            # 检查是否需要转折点
            tp = self._evaluate_turning_point(state)
            if tp:
                state.set("shared.turning_point", tp)

        # 更新张力曲线
        tension = self._calculate_tension(state)
        state.append("plot.tension_curve", tension)

        return state

    def _generate_plot_beats(self, state: AgentState) -> List[PlotBeat]:
        """基于三幕结构生成情节节拍"""
        intent = state.get("director.user_intent")
        world_state = state.get("world.snapshot")
        characters = state.get("world.characters")

        prompt = f"""
        # 情节节拍生成

        ## 用户意图
        {intent}

        ## 世界状态概要
        {world_state.summary()}

        ## 主要角色
        {characters}

        ## 要求
        1. 使用三幕结构
        2. 每个节拍包含：事件描述、涉及角色、情感冲击、对世界状态的影响
        3. 设计3-5个主要转折点
        4. 伏笔与回收成对出现

        输出格式：JSON数组 of PlotBeat
        """

        return self.llm.generate_structured(prompt, schema=List[PlotBeat])
```

---

### 3.2 世界模拟层

#### WorldStateAgent - 世界状态智能体

**职责**：管理世界事实图谱、执行世界规则、提供状态查询

**核心能力**：
- 事实CRUD（对应Step1 FactManager）
- 规则引擎执行（世界规则触发）
- 状态快照/恢复
- 反事实分支管理

**状态分区**：`world.*`

**工具集**：
- `set_fact` - 设置事实（对应Step1 set_fact）
- `get_fact` - 查询事实（支持时间旅行）
- `query_state` - 查询实体完整状态
- `propagate` - 传播事实效果
- `create_branch` - 创建反事实分支
- `apply_rule` - 应用世界规则

**实现模板**：
```python
class WorldStateAgent(BaseAgent):
    """
    世界状态智能体

    对应Step1数据层：FactManager + WorldStateTool
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._fact_manager = FactManager()  # Step1实现
        self._rule_engine = RuleEngine()

    def process(self, state: AgentState) -> AgentState:
        """
        世界状态处理循环

        监听：world.pending_changes（待处理事实变更）
        输出：world.snapshot（更新后的世界快照）
        """
        pending = state.get("world.pending_changes", [])

        for change in pending:
            # 1. 设置事实
            fact = self._fact_manager.set_fact(
                subject_id=change["subject_id"],
                predicate=change["predicate"],
                value=change["value"],
                source="simulation",
                auto_propagate=False  # 手动控制传播
            )

            # 2. 触发规则
            rules = self._rule_engine.find_applicable(fact)
            for rule in rules:
                new_facts = self._rule_engine.apply(rule, fact)
                state.extend("world.rule_effects", new_facts)

            # 3. 传播效果
            propagated = self._fact_manager.propagate_effects(fact, depth=3)
            state.extend("world.propagated_effects", propagated)

        # 4. 更新世界快照
        novel_id = state.get("shared.novel_id")
        snapshot = self._fact_manager.get_world_state(novel_id)
        state.set("world.snapshot", snapshot)

        # 清空待处理
        state.set("world.pending_changes", [])

        return state
```

---

#### CharacterMindAgent - 角色心智智能体

**职责**：模拟角色心智（记忆/信念/情感/决策），每个角色一个实例

**核心能力**：
- 记忆编码与检索（Step2三级阶梯）
- 信念贝叶斯更新
- 情感计算（OCC模型）
- 决策生成（基于心智状态）
- 人格一致性检查

**状态分区**：`mind.{character_id}.*`

**工具集**：
- `encode_memory` - 编码事件为记忆
- `retrieve_memories` - 检索相关记忆
- `update_belief` - 更新信念
- `compute_emotion` - 计算情感反应
- `generate_decision` - 生成决策
- `check_consistency` - 检查人格一致性

**实现模板**：
```python
class CharacterMindAgent(BaseAgent):
    """
    角色心智智能体

    每个角色一个实例，独立心智状态
    对应Step1数据层：MindManager
    参考：ACL 2025 Character Simulation + OCC情感模型
    """

    def __init__(self, config: AgentConfig, character_id: int):
        super().__init__(config)
        self._character_id = character_id
        self._mind_manager = MindManager()
        self._memory_tier = MemoryTier()  # Step2三级阶梯

    def process(self, state: AgentState) -> AgentState:
        """
        角色心智处理循环

        输入：world.events（新发生的事件）
        输出：mind.{id}.decisions（角色决策）
        """
        events = state.get("world.new_events", [])

        for event in events:
            # 1. 感知过滤（角色是否感知到此事件）
            if not self._can_perceive(event):
                continue

            # 2. 编码记忆
            memory = self._mind_manager.encode_memory(
                character_id=self._character_id,
                event_id=event["id"],
                emotion=event.get("emotion", "neutral"),
                importance=event.get("importance", 0.5)
            )
            state.append(f"mind.{self._character_id}.new_memories", memory)

            # 3. 更新信念
            belief_updates = self._infer_beliefs(event)
            for update in belief_updates:
                self._mind_manager.update_belief(
                    character_id=self._character_id,
                    **update
                )

            # 4. 计算情感
            appraisal = self._appraise_event(event)
            emotion = self._mind_manager.compute_emotion(
                character_id=self._character_id,
                event=event,
                appraisal=appraisal
            )
            state.set(f"mind.{self._character_id}.current_emotion", emotion)

        # 5. 生成决策（如果轮到该角色行动）
        if state.get("shared.awaiting_decision") == self._character_id:
            decision = self._generate_decision(state)
            state.set(f"mind.{self._character_id}.decision", decision)

        return state

    def _generate_decision(self, state: AgentState) -> Decision:
        """基于心智状态生成决策"""
        mind = self._mind_manager.get_mind(self._character_id)

        # 检索相关记忆
        situation = state.get("shared.current_situation")
        memories = self._mind_manager.retrieve_memories(
            character_id=self._character_id,
            query=situation,
            retrieval_type="mixed",
            top_k=5
        )

        prompt = f"""
        # 角色决策

        ## 角色信息
        人格：{mind.personality}
        当前情感：{mind.current_emotion}
        显式目标：{mind.explicit_goals}

        ## 当前情境
        {situation}

        ## 相关记忆
        {memories}

        ## 可选行动
        {state.get("shared.available_actions", [])}

        请输出JSON：{{"choice", "reasoning", "confidence", "expected_outcome", "emotional_change"}}
        """

        return self.llm.generate_structured(prompt, schema=Decision)
```

---

#### CausalEngineAgent - 因果推理智能体

**职责**：因果链追溯、后果预测、反事实分析

**核心能力**：
- 多路径因果追溯
- 概率后果预测
- 反事实分支模拟
- 因果解释生成

**状态分区**：`causal.*`

**工具集**：
- `trace_causes` - 追溯事件原因
- `predict_consequences` - 预测后果
- `create_counterfactual` - 创建反事实分支
- `generate_explanation` - 生成因果解释

**实现模板**：
```python
class CausalEngineAgent(BaseAgent):
    """
    因果推理智能体

    对应Step1数据层：CausalReasoningTool
    """

    def process(self, state: AgentState) -> AgentState:
        """
        因果推理循环

        监听：shared.causal_queries（因果查询请求）
        输出：causal.results（推理结果）
        """
        queries = state.get("shared.causal_queries", [])

        for query in queries:
            if query["type"] == "trace":
                result = self._trace_causes(query["event_id"], query.get("depth", 3))

            elif query["type"] == "predict":
                result = self._predict_consequences(query["event_id"], query.get("steps", 5))

            elif query["type"] == "what_if":
                result = self._analyze_what_if(query["event_id"], query["modification"])

            state.append("causal.results", {
                "query_id": query["id"],
                "result": result
            })

        # 清空查询
        state.set("shared.causal_queries", [])
        return state
```

---

#### EventSimulatorAgent - 事件模拟智能体

**职责**：基于角色决策生成事件，传播效果，维护事件时间线

**核心能力**：
- 事件生成（从决策到事件）
- 效果传播（连锁反应）
- 事件时间线维护
- 重大事件标记

**状态分区**：`events.*`

**工具集**：
- `simulate_event` - 模拟单个事件
- `propagate_effects` - 传播事件效果
- `add_to_timeline` - 添加到时间线
- `mark_significant` - 标记重大事件

**实现模板**：
```python
class EventSimulatorAgent(BaseAgent):
    """
    事件模拟智能体

    将角色决策转化为世界事件，触发效果传播
    """

    def process(self, state: AgentState) -> AgentState:
        """
        事件模拟循环

        输入：mind.*.decisions（角色决策）
        输出：world.new_events（新事件） + world.pending_changes（状态变更）
        """
        decisions = self._collect_decisions(state)

        for char_id, decision in decisions:
            # 1. 将决策转化为事件
            event = self._decision_to_event(char_id, decision, state)
            state.append("events.new", event)

            # 2. 计算事件效果
            effects = self._compute_effects(event, state)
            state.extend("world.pending_changes", effects)

            # 3. 标记重大事件
            if self._is_significant(event):
                state.append("events.significant", event["id"])

        return state

    def _decision_to_event(self, char_id: int, decision: Decision, state: AgentState) -> Event:
        """将角色决策转化为结构化事件"""
        prompt = f"""
        将角色决策转化为世界事件：

        角色：{char_id}
        决策：{decision.choice}
        理由：{decision.reasoning}
        预期效果：{decision.expected_outcome}

        输出结构化事件（JSON）：
        {{"event_type", "description", "actor_id", "target_id", "effects", "importance"}}
        """
        return self.llm.generate_structured(prompt, schema=Event)
```

---

### 3.3 叙事生成层

#### NarrativePlannerAgent - 叙事规划智能体

**职责**：规划叙事弧线、选择视角、设计场景结构

**核心能力**：
- 叙事弧线设计（情感曲线）
- 视角选择（POV）
- 场景分段规划
- 详略节奏控制

**状态分区**：`narrative.plan.*`

**工具集**：
- `plan_arc` - 规划叙事弧线
- `select_pov` - 选择视角
- `segment_scene` - 分段场景
- `control_pacing` - 控制节奏

**实现模板**：
```python
class NarrativePlannerAgent(BaseAgent):
    """
    叙事规划智能体

    参考：StoryWriter Planning Agent + Dramatron结构
    """

    def process(self, state: AgentState) -> AgentState:
        """
        叙事规划循环

        输入：plot.beats + world.snapshot + mind.*
        输出：narrative.plan.scene_plan（场景写作计划）
        """
        beat = state.get("shared.current_beat")
        if not beat:
            return state

        # 1. 规划叙事弧线
        arc = self._plan_emotional_arc(beat, state)
        state.set("narrative.plan.emotional_arc", arc)

        # 2. 选择视角
        pov = self._select_pov(beat, state)
        state.set("narrative.plan.pov", pov)

        # 3. 分段规划
        segments = self._plan_segments(beat, arc, pov)
        state.set("narrative.plan.segments", segments)

        # 4. 生成写作指令
        writing_directive = self._compose_writing_directive(beat, arc, pov, segments)
        state.set("shared.writing_directive", writing_directive)

        return state

    def _select_pov(self, beat: PlotBeat, state: AgentState) -> POVConfig:
        """基于情节和角色状态选择最佳视角"""
        # 如果情节涉及角色内心冲突，选择该角色视角
        # 如果涉及多方互动，选择第三人称有限
        # 如果涉及世界观揭示，选择全知视角

        characters = beat.involved_characters
        minds = {cid: state.get(f"mind.{cid}") for cid in characters}

        prompt = f"""
        为以下情节选择最佳叙事视角：

        情节：{beat.description}
        涉及角色：{characters}
        角色当前情感：{minds}

        选择标准：
        1. 最大化情感冲击
        2. 最有利于悬念营造
        3. 避免信息过度暴露

        输出：{{"pov_type", "pov_character", "pov_reasoning"}}
        """
        return self.llm.generate_structured(prompt, schema=POVConfig)
```

---

#### SceneWriterAgent - 场景写作智能体

**职责**：将模拟事件转化为文学场景描写

**核心能力**：
- 场景描写（环境/动作/心理）
- 动作序列生成
- 氛围渲染
- 感官细节注入

**状态分区**：`narrative.scene.*`

**工具集**：
- `write_scene` - 写作场景
- `describe_environment` - 描写环境
- `render_action` - 渲染动作
- `inject_sensory` - 注入感官细节

**实现模板**：
```python
class SceneWriterAgent(BaseAgent):
    """
    场景写作智能体

    将事件转化为文学场景（不含对话）
    """

    def process(self, state: AgentState) -> AgentState:
        """
        场景写作循环

        输入：shared.writing_directive + events.new
        输出：narrative.scene.draft（场景草稿）
        """
        directive = state.get("shared.writing_directive")
        events = state.get("events.new", [])

        # 构建写作上下文
        context = self._build_writing_context(state)

        # 分段生成
        segments = directive.segments
        written_segments = []

        for segment in segments:
            text = self._write_segment(segment, context, written_segments)
            written_segments.append(text)

        # 组装完整场景
        scene_text = self._assemble_scene(written_segments, directive)
        state.set("narrative.scene.draft", scene_text)

        # 记录覆盖的事件（用于溯源）
        state.set("narrative.scene.covers_events", [e["id"] for e in events])

        return state

    def _write_segment(self, segment: SegmentPlan, context: Context, prev_segments: List[str]) -> str:
        """写作单个段落"""
        prompt = f"""
        # 场景写作任务

        ## 段落类型：{segment.type}
        ## 目标字数：{segment.target_words}
        ## 情感基调：{segment.emotion}

        ## 写作上下文
        {context}

        ## 已写内容（前文）
        {''.join(prev_segments)[-1000:]}

        ## 要求
        1. 使用中文撰写
        2. 符合{segment.type}类型的写作规范
        3. 保持与前文的连贯性
        4. 注入感官细节（视觉/听觉/嗅觉/触觉）
        5. 控制节奏：{segment.pacing}

        请直接输出段落内容，不要添加任何说明文字。
        """
        return self.llm.generate(prompt, max_tokens=segment.target_words * 2)
```

---

#### DialogueWriterAgent - 对话写作智能体

**职责**：为场景中的对话部分生成角色对话

**核心能力**：
- 角色语气匹配
- 潜台词生成
- 对话节奏控制
- 方言/口头禅模拟

**状态分区**：`narrative.dialogue.*`

**工具集**：
- `write_dialogue` - 写作对话
- `match_voice` - 匹配角色声音
- `inject_subtext` - 注入潜台词
- `control_rhythm` - 控制对话节奏

---

#### StyleEnforcerAgent - 风格约束智能体

**职责**：确保叙事风格一致性

**核心能力**：
- 风格一致性检查
- 语言规范化
- 修辞一致性
- 口吻匹配验证

**状态分区**：`style.*`

**工具集**：
- `check_consistency` - 检查风格一致性
- `normalize_language` - 规范化语言
- `match_tone` - 匹配口吻
- `enforce_rhetoric` - 强制执行修辞规范

---

### 3.4 质量保障层

#### ConsistencyCheckerAgent - 一致性检查智能体

**职责**：检查事实一致性、角色一致性、世界观一致性

**核心能力**：
- 事实一致性验证（与world.snapshot比对）
- 角色行为一致性（与人格模型比对）
- 世界观规则遵守检查
- 时间线一致性验证

**状态分区**：`quality.consistency.*`

**特点**：只读不写，输出审查报告

---

#### ContinuityAuditorAgent - 连续性审计智能体

**职责**：审计跨章节连续性

**核心能力**：
- 跨章节伏笔回收检查
- 角色发展连续性
- 情节线索追踪
- 时间线审计

**状态分区**：`quality.continuity.*`

**特点**：只读不写，输出审计报告

---

### 3.5 基础设施层

#### WorkflowEngine - 工作流引擎

**职责**：状态图执行、任务调度、并行控制

**核心设计**：
- 基于LangGraph模式的状态图
- 增量状态更新（非全量覆盖）
- 内置Checkpoint（断点续作）
- 支持并行节点（fan-out/fan-in）

**实现模板**：
```python
class WorkflowEngine:
    """
    工作流引擎

    参考：LangGraph StateGraph + Checkpointing
    """

    def __init__(self):
        self._graph: StateGraph = StateGraph(SharedState)
        self._checkpointer = Checkpointer()

    def register_agent(self, agent: BaseAgent, node_id: str):
        """注册Agent为图节点"""
        self._graph.add_node(node_id, agent.process)

    def add_edge(self, from_node: str, to_node: str, condition: Callable = None):
        """添加边（支持条件边）"""
        if condition:
            self._graph.add_conditional_edges(from_node, condition, {True: to_node})
        else:
            self._graph.add_edge(from_node, to_node)

    def compile(self) -> CompiledGraph:
        """编译状态图"""
        return self._graph.compile(checkpointer=self._checkpointer)

    def invoke(self, initial_state: SharedState, config: RunConfig) -> SharedState:
        """执行工作流"""
        app = self.compile()
        return app.invoke(initial_state, config=config)
```

---

#### EventBus - 事件总线

**职责**：轻量级Agent间通信

**设计原则**：
- 发布-订阅模式
- 事件驱动（非命令驱动）
- 异步非阻塞
- 类型安全的事件定义

**替代**：取代原有的RocketMQ + AgentCommunicator + EnhancedCommunicator三层复杂通信

---

#### ToolRegistry - 工具注册中心

**职责**：Agent工具注册、发现、权限管理

**设计原则**：
- MCP (Model Context Protocol) 兼容
- 工具即能力声明（schema + handler）
- 权限分级（读/写/执行）
- 版本管理

---

## 4. 状态机设计

### 4.1 共享状态结构 (SharedState)

```python
class SharedState(TypedDict):
    """全局共享状态 - 所有Agent读写"""

    # 导演层
    director: DirectorState

    # 情节层
    plot: PlotState

    # 世界模拟层
    world: WorldState
    minds: Dict[int, MindState]  # character_id -> mind
    events: EventState
    causal: CausalState

    # 叙事生成层
    narrative: NarrativeState

    # 质量保障层
    quality: QualityState

    # 共享指令区（跨层通信）
    shared: SharedDirective

    # 元数据
    meta: MetaState
```

### 4.2 状态更新规则

```
Rule 1: Agent只能写入自己的状态分区
  - WorldStateAgent -> world.*
  - CharacterMindAgent -> mind.{id}.*
  - SceneWriterAgent -> narrative.scene.*

Rule 2: 跨层通信通过 shared.* 进行
  - 上层写入指令：shared.directive
  - 下层写入结果：shared.result

Rule 3: 状态更新是增量式的
  - 节点返回 {"world.facts": [new_fact]} 而非整个状态
  - 引擎自动合并更新

Rule 4: 质量层只读
  - ConsistencyCheckerAgent 读取 world.* + narrative.*
  - 输出写入 quality.consistency.report
```

### 4.3 核心状态图

```
                    ┌─────────┐
         ┌─────────→│  START  │←────────┐
         │          └────┬────┘         │
         │               │              │
         │          ┌────┴────┐         │
         │          │ Director│         │
         │          │  Agent  │         │
         │          └────┬────┘         │
         │               │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │  Plot   │    │  World  │    │Narrative│
    │ Manager │    │  State  │    │ Planner │
    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │
         │         ┌────┴────┐         │
         │         │Character│         │
         │         │  Mind   │         │
         │         └────┬────┘         │
         │              │              │
         │         ┌────┴────┐         │
         │         │  Event  │         │
         │         │Simulator│         │
         │         └────┬────┘         │
         │              │              │
         └──────────────┼──────────────┘
                        │
                   ┌────┴────┐
                   │  Scene  │
                   │ Writer  │
                   └────┬────┘
                        │
                   ┌────┴────┐
                   │ Dialogue│
                   │ Writer  │
                   └────┬────┘
                        │
                   ┌────┴────┐
                   │  Style  │
                   │Enforcer │
                   └────┬────┘
                        │
                   ┌────┴────┐
                   │ Quality │
                   │  Gate   │
                   └────┬────┘
                        │
              ┌─────────┴─────────┐
              │                   │
         ┌────┴────┐         ┌────┴────┐
         │  PASS   │         │  FAIL   │
         │ (输出)  │         │(Revision│
         └─────────┘         │ Loop)   │
                             └────┬────┘
                                  │
                                  └────────→ (返回 SceneWriter)
```

---

## 5. 工具系统设计

### 5.1 工具定义规范（MCP兼容）

```python
@dataclass
class AgentTool:
    """Agent工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable
    permissions: List[str]      # 权限标签
    returns: Dict[str, Any]     # 返回值Schema

# 示例：WorldStateAgent的工具
world_tools = [
    AgentTool(
        name="set_fact",
        description="设置世界事实",
        parameters={
            "subject_id": {"type": "integer"},
            "predicate": {"type": "string"},
            "value": {"type": "any"},
            "confidence": {"type": "number", "default": 1.0}
        },
        handler=FactManager.set_fact,
        permissions=["world.write"]
    ),
    AgentTool(
        name="get_fact",
        description="查询世界事实（支持时间旅行）",
        parameters={
            "subject_id": {"type": "integer"},
            "predicate": {"type": "string"},
            "timestamp": {"type": "integer", "optional": True}
        },
        handler=FactManager.get_fact,
        permissions=["world.read"]
    ),
]
```

### 5.2 工具权限矩阵

| Agent | world.read | world.write | mind.read | mind.write | narrative.read | narrative.write |
|-------|-----------|------------|----------|-----------|---------------|----------------|
| Director | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| PlotManager | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| WorldState | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| CharacterMind | ✅ | ❌ | ✅(self) | ✅(self) | ❌ | ❌ |
| EventSimulator | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| NarrativePlanner | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| SceneWriter | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Quality* | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |

---

## 6. 与已有Step的对接

### 6.1 与Step1（数据层）对接

| Step1组件 | 对接Agent | 对接方式 |
|-----------|----------|---------|
| FactManager | WorldStateAgent | 直接调用 |
| MindManager | CharacterMindAgent | 直接调用 |
| EventManager | EventSimulatorAgent | 直接调用 |
| CausalReasoningTool | CausalEngineAgent | 直接调用 |
| NarrativeRecordTool | SceneWriterAgent + DialogueWriterAgent | 直接调用 |
| WorldStateTool | WorldStateAgent | 封装为工具 |
| CharacterMindTool | CharacterMindAgent | 封装为工具 |

### 6.2 与Step2（记忆系统）对接

| Step2组件 | 使用Agent | 使用方式 |
|-----------|----------|---------|
| 感知记忆 (Sensory) | CharacterMindAgent | 事件输入缓冲区 |
| 工作记忆 (Working) | 所有Agent | 当前上下文窗口 |
| 长期记忆 (Long-Term) | CharacterMindAgent | 记忆编码/检索 |
| 注意力控制器 | CharacterMindAgent | 感知过滤 |

### 6.3 与Step3（LLM层）对接

| Step3组件 | 使用方式 |
|-----------|---------|
| LLMRouter | 所有Agent通过BaseAgent._llm调用 |
| 功能分级 | AgentConfig中指定tier |
| 流式生成 | SceneWriterAgent使用（长文本） |
| 容错降级 | 所有Agent继承 |

---

## 7. Agent增删对照表

### 7.1 新增Agent（12个）

| Agent名称 | 层级 | 职责 | 新增原因 |
|-----------|------|------|---------|
| DirectorAgent | 编排层 | 叙事总控 | 替代coordinator，统一调度 |
| PlotManagerAgent | 编排层 | 情节管理 | 专业情节节奏控制 |
| SessionController | 用户层 | 会话管理 | 用户交互管理 |
| WorldStateAgent | 模拟层 | 世界状态 | 对应Step1 FactManager |
| CharacterMindAgent | 模拟层 | 角色心智 | 对应Step1 MindManager |
| CausalEngineAgent | 模拟层 | 因果推理 | 对应Step1 CausalReasoningTool |
| EventSimulatorAgent | 模拟层 | 事件模拟 | 连接决策与事件 |
| NarrativePlannerAgent | 叙事层 | 叙事规划 | 替代outline_planner |
| SceneWriterAgent | 叙事层 | 场景写作 | 替代content_generator（场景部分）|
| DialogueWriterAgent | 叙事层 | 对话写作 | 专业对话生成 |
| StyleEnforcerAgent | 叙事层 | 风格约束 | 风格一致性保障 |
| ContinuityAuditorAgent | 质量层 | 连续性审计 | 跨章节质量保障 |

### 7.2 删除Agent（11个）

| Agent名称 | 原职责 | 去向 | 删除原因 |
|-----------|--------|------|---------|
| coordinator | 任务协调 | 合并到DirectorAgent | 职责重叠 |
| config_enhancer | 配置增强 | 合并到DirectorAgent | 属于意图解析的一部分 |
| task_manager | 任务管理 | 合并到SessionController | 会话管理包含任务管理 |
| health_checker | 健康检查 | 移到基础设施监控 | 非业务Agent |
| workflow_orchestrator | 工作流编排 | 替换为WorkflowEngine | 基础设施化 |
| enhanced_workflow_orchestrator | 增强编排 | 替换为WorkflowEngine | 过度工程化 |
| agent_communicator | Agent通信 | 替换为EventBus | 过度工程化 |
| enhanced_communicator | 增强通信 | 替换为EventBus | 过度工程化 |
| hook_generator | 钩子生成 | 合并到PlotManagerAgent | 情节管理的一部分 |
| conflict_generator | 冲突生成 | 合并到EventSimulatorAgent | 事件模拟包含冲突 |
| chapter_summary | 章节摘要 | 合并到NarrativePlannerAgent | 叙事规划的一部分 |

### 7.3 保留/重构Agent（5个）

| 原Agent | 新Agent | 变更说明 |
|---------|---------|---------|
| character_generator | CharacterMindAgent | 从"生成器"变为"心智模拟器"，职责深化 |
| world_builder | WorldStateAgent | 从"构建器"变为"状态管理器"，对接数据层 |
| outline_planner | NarrativePlannerAgent | 从"大纲规划"变为"叙事规划"，范围扩展 |
| content_generator | SceneWriterAgent + DialogueWriterAgent | 拆分为场景+对话两个专业Agent |
| quality_checker | ConsistencyCheckerAgent + ContinuityAuditorAgent | 拆分为一致性+连续性两个专业Agent |

---

## 8. 文件结构规划

```
src/deepnovel/agents/
├── __init__.py
├── base.py                          # Agent基类（重写）
│   ├── BaseAgent                    # 状态驱动基类
│   ├── AgentConfig                  # Agent配置
│   ├── AgentState                   # 状态接口
│   └── AgentTool                    # 工具接口
│
├── core/                            # 基础设施层
│   ├── __init__.py
│   ├── workflow_engine.py           # 工作流引擎（LangGraph模式）
│   ├── event_bus.py                 # 事件总线（轻量级）
│   ├── tool_registry.py             # 工具注册中心
│   ├── checkpointer.py              # 状态检查点
│   └── state_graph.py               # 状态图定义
│
├── orchestration/                   # 编排控制层
│   ├── __init__.py
│   ├── director.py                  # DirectorAgent
│   ├── plot_manager.py              # PlotManagerAgent
│   └── session_controller.py        # SessionController
│
├── simulation/                      # 世界模拟层
│   ├── __init__.py
│   ├── world_state.py               # WorldStateAgent
│   ├── character_mind.py            # CharacterMindAgent
│   ├── causal_engine.py             # CausalEngineAgent
│   └── event_simulator.py           # EventSimulatorAgent
│
├── narrative/                       # 叙事生成层
│   ├── __init__.py
│   ├── planner.py                   # NarrativePlannerAgent
│   ├── scene_writer.py              # SceneWriterAgent
│   ├── dialogue_writer.py           # DialogueWriterAgent
│   └── style_enforcer.py            # StyleEnforcerAgent
│
├── quality/                         # 质量保障层
│   ├── __init__.py
│   ├── consistency_checker.py       # ConsistencyCheckerAgent
│   └── continuity_auditor.py        # ContinuityAuditorAgent
│
├── tools/                           # Agent工具集
│   ├── __init__.py
│   ├── world_tools.py               # 世界状态工具
│   ├── mind_tools.py                # 角色心智工具
│   ├── causal_tools.py              # 因果推理工具
│   ├── narrative_tools.py           # 叙事记录工具
│   └── writing_tools.py             # 写作辅助工具
│
└── schemas/                         # 数据结构定义
    ├── __init__.py
    ├── state.py                     # 状态Schema
    ├── directive.py                 # 指令Schema
    └── events.py                    # 事件Schema
```

---

## 9. 实施计划

### Phase 1: 基础设施搭建（Day 1-3）

```python
# Day 1: 核心框架
- 重写 BaseAgent（状态驱动）
- 实现 WorkflowEngine（状态图）
- 实现 EventBus（轻量通信）

# Day 2: 工具系统
- 实现 ToolRegistry（MCP兼容）
- 定义 AgentTool 规范
- 迁移基础工具（file_read, calculation等）

# Day 3: 状态管理
- 定义 SharedState Schema
- 实现 Checkpointer（断点续作）
- 集成Step3 LLMRouter
```

### Phase 2: 世界模拟层（Day 4-7）

```python
# Day 4: WorldStateAgent
- 对接Step1 FactManager
- 实现 set_fact / get_fact / propagate
- 编写单元测试

# Day 5-6: CharacterMindAgent
- 对接Step1 MindManager
- 实现记忆/信念/情感/决策
- 支持多角色实例

# Day 7: CausalEngineAgent + EventSimulatorAgent
- 实现因果推理
- 实现事件模拟与传播
```

### Phase 3: 叙事生成层（Day 8-11）

```python
# Day 8: NarrativePlannerAgent
- 实现叙事弧线规划
- 实现视角选择

# Day 9-10: SceneWriterAgent + DialogueWriterAgent
- 实现场景分段写作
- 实现对话生成

# Day 11: StyleEnforcerAgent
- 实现风格一致性检查
- 实现语言规范化
```

### Phase 4: 编排与质量层（Day 12-14）

```python
# Day 12-13: DirectorAgent + PlotManagerAgent
- 实现意图解析
- 实现工作流编排
- 实现情节节奏管理

# Day 14: 质量保障Agent
- 实现ConsistencyCheckerAgent
- 实现ContinuityAuditorAgent
```

### Phase 5: 集成与清理（Day 15-17）

```python
# Day 15: 集成测试
- 端到端工作流测试
- 状态一致性验证
- 性能基准测试

# Day 16: 旧代码清理
- 删除旧Agent实现
- 删除RocketMQ通信代码
- 删除enhanced_*冗余代码

# Day 17: 文档与优化
- 完善Agent文档
- 优化状态更新性能
- 添加监控指标
```

---

## 10. 验收标准

### 10.1 功能验收

| 功能 | 测试场景 | 通过标准 |
|------|---------|---------|
| 状态图执行 | 运行完整小说生成工作流 | 所有节点按拓扑序执行，无死锁 |
| 状态增量更新 | 并行执行两个Agent | 状态正确合并，无覆盖丢失 |
| Checkpoint | 执行中中断再恢复 | 从中断点继续，结果一致 |
| Simulation-to-Narrative | 角色决策→事件→场景 | 场景准确反映角色决策 |
| 因果推理 | 追溯事件原因 | 追溯到3层前因，置信度>0.8 |
| 反事实分析 | "如果角色未死亡" | 生成分支，模拟发展 |
| 风格一致性 | 跨章节风格检查 | 一致性评分>0.85 |
| 跨章节连续 | 伏笔回收检查 | 所有伏笔有回收或标记 |

### 10.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 状态图执行 | <500ms/节点 | 100个节点工作流 |
| 状态序列化 | <50ms | 序列化1000个事实 |
| 并行节点 | <100ms额外开销 | 4个节点并行 |
| Agent决策 | <2s | 包含LLM调用 |
| 场景生成 | <5s/1000字 | 包含上下文组装 |
| 质量检查 | <1s | 单章节一致性检查 |

### 10.3 架构验收

| 指标 | 目标 | 验证方法 |
|------|------|---------|
| Agent职责单一性 | 每个Agent只处理一个认知功能 | 代码审查 |
| 状态分区隔离 | Agent只写自己的分区 | 静态检查 |
| 工具权限合规 | Agent不越权访问 | 单元测试 |
| 数据层对接 | 所有模拟Agent对接Step1 | 集成测试 |
| 记忆系统对接 | CharacterMindAgent使用Step2 | 集成测试 |

---

## 11. 风险与应对

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| 状态图复杂度失控 | 中 | 高 | 限制图深度<10，子图模块化 |
| 状态序列化性能 | 中 | 中 | 增量更新+差异同步 |
| LLM调用成本激增 | 高 | 中 | 本地模型兜底+缓存复用 |
| Agent实例过多 | 中 | 中 | 角色Agent按需创建，用完销毁 |
| 与旧系统兼容 | 高 | 高 | 保留API适配层，逐步迁移 |
| 调试困难 | 中 | 高 | 可视化状态图+详细日志+Checkpoint回放 |

---

## 12. 附录

### 12.1 术语表

| 术语 | 定义 |
|------|------|
| Fabula | 故事素材（按时间顺序的事件） |
| Syuzhet | 叙事表达（文学化的故事呈现） |
| State Graph | 状态图（节点=Agent，边=状态流转） |
| Checkpoint | 检查点（状态快照，支持恢复） |
| MCP | Model Context Protocol（模型上下文协议） |
| Handoff | 控制权交接（Agent间任务转移） |
| POV | Point of View（叙事视角） |
| Beat | 情节节拍（最小叙事单元） |

### 12.2 参考文档

- `Step1.md` - 数据层重构（世界模拟架构）
- `Step2.md` - 记忆系统重构（三级阶梯）
- `Step3.md` - LLM层重构（多模型工厂）
- LangGraph Docs - 状态图执行模型
- ACL 2025 "Multi-Agent Based Character Simulation for Story Writing"
- StoryWriter (2025) "A Multi-Agent Framework for Long Story Generation"

---

## 13. 实施状态追踪

| 日期 | 完成内容 | 状态 |
|------|---------|------|
| 2026-04-28 | 完成Step4.md v2.0设计文档 | ✅ |

---

*版本: v2.0（深化版）*
*创建日期: 2026-04-28*
*更新日期: 2026-04-28*
*负责人: Ryan + 小R*
*状态: 设计中*
*预计工期: 17天*
*依赖: Step1（数据层）、Step2（记忆系统）、Step3（LLM层）*
*同步状态: 本地文件（不同步GitHub）*
