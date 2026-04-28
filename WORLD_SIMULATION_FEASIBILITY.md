# 世界模拟架构可行性分析

## 用户的核心愿景

```
创造世界 → 创造意识 → 设定情境 → 模拟生活 → 记录故事 → 文学表达
```

这不是传统的小说生成，而是**世界模拟器**——先构建一个自洽的虚拟世界，让角色在其中"生活"，然后记录发生的故事。

---

## 当前技术可行性评估

### ✅ 可以立即实现（已有成熟方案）

| 模块 | 技术方案 | 成熟度 |
|------|---------|--------|
| **世界状态机** | 事实图谱 + 规则引擎 | ⭐⭐⭐⭐⭐ |
| **角色基础档案** | 结构化数据 + 向量检索 | ⭐⭐⭐⭐⭐ |
| **情节管理** | 状态机 + 事件驱动 | ⭐⭐⭐⭐⭐ |
| **上下文检索** | RAG + 向量数据库 | ⭐⭐⭐⭐⭐ |
| **风格控制** | 提示工程 + 微调 | ⭐⭐⭐⭐ |

### 🔄 需要创新实现（有技术基础）

| 模块 | 技术挑战 | 可行路径 |
|------|---------|---------|
| **角色心智模型** | 模拟认知、情感、决策 | LLM + 认知架构 |
| **自主决策** | 角色自主行动 | Agent框架 + 目标规划 |
| **因果推理** | 事件连锁反应 | 图神经网络 + LLM推理 |
| **情感模拟** | 真实情感反应 | 情感计算 + 人格模型 |

### ⚠️ 当前限制（需要妥协）

| 限制 | 说明 | 妥协方案 |
|------|------|---------|
| **实时模拟** | 无法做到真正的实时 | 离散时间步模拟 |
| **多角色并发** | 同时模拟多个角色心智开销大 | 轮流模拟 + 缓存 |
| **物理世界** | 无法模拟真实物理 | 简化规则 + 手工设定 |
| **视觉感知** | 没有视觉理解 | 文本描述替代 |

---

## 分阶段实现路线图

### 第一阶段：基础世界模拟（1-2个月）

```python
# 核心：世界状态机 + 基础角色
class BasicWorldSimulation:
    """
    基础世界模拟器
    
    能力：
    1. 维护世界事实（谁在哪里、有什么、发生了什么）
    2. 角色基础状态（位置、健康、物品）
    3. 简单规则（如果A则B）
    4. 事件记录（时间线）
    """
    
    def __init__(self):
        self.facts = FactGraph()          # 事实图谱
        self.characters = {}              # 角色基础状态
        self.locations = {}               # 地点
        self.timeline = EventTimeline()   # 时间线
        self.rules = RuleEngine()         # 规则引擎
    
    def simulate_step(self, actions: List[Action]) -> SimulationResult:
        """
        模拟一个时间步
        
        输入：角色行动
        输出：世界变化
        """
        results = []
        
        # 1. 应用行动
        for action in actions:
            # 检查前提条件
            if not self.rules.check_preconditions(action):
                results.append(ActionResult(action, success=False, reason="前提不满足"))
                continue
            
            # 应用行动效果
            effects = self.rules.apply_action(action)
            
            # 传播连锁反应
            cascade = self._propagate_effects(effects)
            
            # 记录事件
            event = Event(
                timestamp=self.timeline.now(),
                action=action,
                effects=effects + cascade
            )
            self.timeline.add_event(event)
            
            results.append(ActionResult(action, success=True, effects=effects + cascade))
        
        # 2. 更新世界状态
        self._update_world_state(results)
        
        # 3. 检查触发规则
        triggered = self._check_triggered_rules()
        for rule in triggered:
            effects = self.rules.apply_triggered(rule)
            self._propagate_effects(effects)
        
        return SimulationResult(results, self.timeline.now())
```

**示例场景：**
```
初始状态：
- 主角在"客栈"
- 反派在"暗巷"
- 宝物在"密室"

主角行动：[移动到"密室", 获取"宝物"]

模拟结果：
- 主角位置 → "密室"
- 主角物品 + ["宝物"]
- 触发规则："宝物被取走" → 反派感知 → 反派目标更新
- 反派行动：[移动到"密室", 攻击"主角"]

下一步模拟：
- 冲突发生
- 结果取决于角色属性
```

### 第二阶段：角色心智模拟（2-3个月）

```python
class CharacterMind:
    """
    角色心智模型（简化版）
    
    核心组件：
    1. 记忆系统（短期 + 长期）
    2. 信念系统（对世界、他人、自我的认知）
    3. 情感系统（当前情绪 + 情感反应）
    4. 目标系统（想要达成什么）
    5. 决策系统（选择行动）
    """
    
    def __init__(self, character_id, profile):
        self.character_id = character_id
        self.profile = profile
        
        # 记忆
        self.short_term_memory = []  # 最近事件（容量有限）
        self.long_term_memory = MemoryGraph()  # 长期记忆（关联存储）
        
        # 信念
        self.beliefs = BeliefSystem()
        self.beliefs.add("self.location", "未知")
        self.beliefs.add("self.health", "良好")
        
        # 情感
        self.emotions = EmotionalState(
            baseline=profile.emotional_baseline,
            current={}
        )
        
        # 目标
        self.goals = GoalHierarchy()
        self.goals.add(profile.primary_goal, priority=1.0)
        
        # 人格
        self.personality = profile.personality
    
    def perceive(self, event: Event) -> Perception:
        """
        感知事件 → 主观解读
        
        不是客观记录，而是经过人格过滤的解读
        """
        # 1. 注意力过滤（人格决定关注什么）
        attention = self._filter_attention(event)
        
        # 2. 情感反应
        emotional_response = self._emotional_reaction(attention)
        
        # 3. 信念更新
        belief_updates = self._update_beliefs(attention)
        
        # 4. 记忆编码
        memory = self._encode_memory(attention, emotional_response)
        
        return Perception(
            attention=attention,
            emotion=emotional_response,
            belief_updates=belief_updates,
            memory=memory
        )
    
    def decide(self, situation: Situation) -> Decision:
        """
        决策：基于心智状态选择行动
        
        简化版：使用LLM模拟决策
        """
        # 构建决策上下文
        context = self._build_decision_context(situation)
        
        # 使用LLM生成决策
        prompt = f"""
        你是{self.profile.name}，一个{self.profile.personality_summary}的人。
        
        当前状态：
        - 位置：{self.beliefs.get('self.location')}
        - 健康：{self.beliefs.get('self.health')}
        - 情绪：{self.emotions.current}
        - 目标：{self.goals.top()}
        
        记忆：
        {self._format_recent_memories(3)}
        
        当前情境：
        {situation.description}
        
        可选行动：
        {situation.available_actions}
        
        你会选择什么行动？为什么？
        """
        
        decision_text = llm.generate(prompt, temperature=0.7)
        
        return self._parse_decision(decision_text)
    
    def express(self, thought: Thought, audience: str) -> Expression:
        """
        表达：将内心想法转化为言行
        
        考虑：
        - 社交面具（对不同的人说不同的话）
        - 情感调节（抑制或放大）
        - 语言风格
        """
        # 根据关系调整
        relationship = self.beliefs.get(f"relationship.{audience}", "neutral")
        
        # 根据情绪调节
        modulation = self._emotional_modulation(thought)
        
        # 生成表达
        expression = self._generate_expression(modulation, relationship)
        
        return expression
```

**关键简化：**
- 不追求真正的"意识"，而是**模拟出一致的行为模式**
- 使用LLM作为"黑盒认知"，输入角色状态，输出合理行为
- 通过结构化约束保证一致性

### 第三阶段：叙事引擎（2-3个月）

```python
class NarrativeEngine:
    """
    叙事引擎：将模拟结果转化为文学表达
    
    流程：
    1. 观察模拟事件
    2. 选择叙事视角
    3. 决定详略
    4. 文学化表达
    """
    
    def __init__(self, style_config):
        self.style = style_config
        self.perspective = PerspectiveManager()
        self.pacing = PacingController()
        self.expression = ExpressionEngine()
    
    def narrate(self, simulation_result: SimulationResult) -> Chapter:
        """
        将模拟结果转化为章节
        """
        scenes = []
        
        # 1. 将事件分组为场景
        scene_events = self._group_into_scenes(simulation_result.events)
        
        for scene_event_group in scene_events:
            # 2. 选择叙事视角
            pov = self.perspective.select(scene_event_group)
            
            # 3. 构建场景
            scene = Scene(
                events=scene_event_group,
                pov_character=pov.character,
                location=pov.location,
                time=pov.time
            )
            
            # 4. 决定叙事策略
            strategy = self._select_narrative_strategy(scene)
            
            # 5. 生成场景文本
            scene_text = self.expression.render_scene(scene, strategy)
            
            scenes.append(SceneContent(
                text=scene_text,
                events=scene_event_group,
                strategy=strategy
            ))
        
        # 6. 组装章节
        chapter = Chapter(
            scenes=scenes,
            pacing=self.pacing.calculate(scenes),
            word_count=sum(s.word_count for s in scenes)
        )
        
        return chapter
    
    def _select_narrative_strategy(self, scene: Scene) -> NarrativeStrategy:
        """
        选择叙事策略
        
        考虑：
        - 场景重要性（决定详略）
        - 情感强度（决定描写深度）
        - 信息密度（决定节奏）
        """
        importance = self._calculate_importance(scene)
        emotional_intensity = self._calculate_emotional_intensity(scene)
        
        if importance > 0.8 and emotional_intensity > 0.7:
            return NarrativeStrategy.DETAILED_SLOW  # 慢镜头，细节丰富
        elif importance > 0.5:
            return NarrativeStrategy.STANDARD  # 标准叙述
        else:
            return NarrativeStrategy.SUMMARY  # 概括性叙述
```

---

## 最小可行产品（MVP）设计

### 核心循环

```python
class WorldSimulationMVP:
    """
    最小可行世界模拟
    
    目标：证明"模拟→叙事"的可行性
    """
    
    def __init__(self, novel_config):
        self.world = BasicWorldSimulation()
        self.minds = {}  # character_id -> CharacterMind
        self.narrative = NarrativeEngine(novel_config.style)
        self.chapters = []
    
    async def run_simulation(self, target_chapters: int):
        """
        运行模拟，生成小说
        """
        for chapter_num in range(1, target_chapters + 1):
            print(f"\n=== 生成第 {chapter_num} 章 ===")
            
            # 1. 角色决策阶段
            actions = []
            for char_id, mind in self.minds.items():
                # 获取当前情境
                situation = self._get_situation(char_id)
                
                # 角色决策
                decision = mind.decide(situation)
                
                # 记录决策理由
                print(f"  {char_id}: {decision.action} (因为: {decision.reasoning})")
                
                actions.append(Action(char_id, decision.action))
            
            # 2. 世界模拟阶段
            sim_result = self.world.simulate_step(actions)
            
            # 3. 角色感知更新
            for event in sim_result.events:
                for char_id in event.involved_characters:
                    if char_id in self.minds:
                        perception = self.minds[char_id].perceive(event)
                        print(f"  {char_id} 感知: {perception.emotion}")
            
            # 4. 叙事生成阶段
            chapter = self.narrative.narrate(sim_result)
            
            # 5. 保存
            self.chapters.append(chapter)
            self._save_chapter(chapter_num, chapter)
            
            print(f"  完成: {chapter.word_count} 字")
    
    def _get_situation(self, character_id: str) -> Situation:
        """
        获取角色当前情境
        """
        char_state = self.world.get_character_state(character_id)
        location = self.world.get_location(char_state.location_id)
        nearby = self.world.get_characters_at(char_state.location_id)
        
        return Situation(
            description=f"你在{location.name}，周围有{', '.join(nearby)}",
            location=location,
            nearby_characters=nearby,
            available_actions=self._generate_available_actions(character_id)
        )
```

### 示例运行

```
=== 生成第 1 章 ===
  主角: 决定探索密室 (因为: 我听说那里有宝物，我需要变强)
  反派: 决定跟踪主角 (因为: 他看起来很可疑，可能知道宝物的位置)
  盟友: 决定留在客栈 (因为: 我需要休息，恢复体力)

  世界模拟结果:
  - 主角移动到密室
  - 主角获得宝物
  - 反派感知到宝物被取走
  - 反派移动到密室入口

  主角 感知: 兴奋、警惕
  反派 感知: 愤怒、贪婪

  叙事生成:
  - 场景1: 主角探索密室（详细描写，紧张氛围）
  - 场景2: 反派跟踪（侧面描写，制造悬念）
  - 场景3: 宝物获得（高潮，情感爆发）

  完成: 3500 字

=== 生成第 2 章 ===
  主角: 决定离开密室 (因为: 我感觉到危险，需要找个安全的地方)
  反派: 决定拦截主角 (因为: 他拿走了我的宝物，必须夺回来)
  盟友: 决定寻找主角 (因为: 他去了很久，可能遇到麻烦)

  ...
```

---

## 技术实现要点

### 1. 世界状态存储

```python
# 使用SQLite + 简单图结构
class WorldState:
    """
    世界状态存储
    
    核心表：
    - entities: 实体（角色、物品、地点）
    - facts: 事实（实体属性）
    - relations: 关系（实体间连接）
    - events: 事件（时间线）
    """
    
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self._init_tables()
    
    def set_fact(self, entity_id, attribute, value, timestamp=None):
        """设置事实"""
        timestamp = timestamp or datetime.now()
        
        # 旧事实标记为历史
        self.db.execute(
            "UPDATE facts SET valid_until = ? WHERE entity_id = ? AND attribute = ? AND valid_until IS NULL",
            (timestamp, entity_id, attribute)
        )
        
        # 插入新事实
        self.db.execute(
            "INSERT INTO facts (entity_id, attribute, value, valid_from) VALUES (?, ?, ?, ?)",
            (entity_id, attribute, json.dumps(value), timestamp)
        )
        
        self.db.commit()
    
    def get_fact(self, entity_id, attribute, timestamp=None):
        """获取事实（支持时间旅行）"""
        timestamp = timestamp or datetime.now()
        
        cursor = self.db.execute(
            """SELECT value FROM facts 
               WHERE entity_id = ? AND attribute = ? 
               AND valid_from <= ? AND (valid_until IS NULL OR valid_until > ?)
               ORDER BY valid_from DESC LIMIT 1""",
            (entity_id, attribute, timestamp, timestamp)
        )
        
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
    def get_state_at(self, timestamp):
        """获取特定时间点的完整世界状态"""
        # 查询所有实体在该时间点的最新事实
        pass
```

### 2. 角色决策（LLM驱动）

```python
class LLMDecisionEngine:
    """
    LLM驱动的角色决策
    
    不是真正的AI，而是"角色扮演"——让LLM扮演角色做决策
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def decide(self, character_state, situation, available_actions) -> Decision:
        """
        生成决策
        
        关键：提供足够的角色上下文，让LLM"入戏"
        """
        prompt = self._build_decision_prompt(character_state, situation, available_actions)
        
        response = await self.llm.generate(
            prompt,
            temperature=0.8,  # 有一定创造性
            max_tokens=500
        )
        
        return self._parse_decision(response)
    
    def _build_decision_prompt(self, character_state, situation, actions):
        """构建决策提示"""
        
        # 角色档案
        profile = character_state.profile
        
        # 当前状态
        current = character_state.current_status
        
        # 记忆（最近3条）
        memories = character_state.get_recent_memories(3)
        
        # 目标
        goals = character_state.get_active_goals()
        
        prompt = f"""【角色决策模拟】

你正在扮演一个小说角色。请完全沉浸在这个角色中，以他的视角思考。

=== 角色档案 ===
姓名：{profile.name}
身份：{profile.identity}
性格：{profile.personality_summary}
核心动机：{profile.primary_motivation}
恐惧：{profile.fears}
渴望：{profile.desires}

=== 当前状态 ===
位置：{current.location}
健康：{current.health}
情绪：{current.emotion}
持有物品：{current.inventory}

=== 记忆 ===
{self._format_memories(memories)}

=== 当前情境 ===
{situation.description}

=== 可选行动 ===
{self._format_actions(actions)}

=== 决策要求 ===
1. 选择最符合角色性格的行动
2. 考虑当前情绪和动机
3. 基于记忆做出合理判断
4. 说明决策理由（内心独白）

请输出：
行动：[选择哪个行动]
理由：[角色的内心想法，100字以内]
预期结果：[角色希望发生什么]
"""
        
        return prompt
```

### 3. 叙事生成

```python
class NarrativeGenerator:
    """
    叙事生成器：将模拟事件转化为文学文本
    """
    
    def __init__(self, llm_client, style_config):
        self.llm = llm_client
        self.style = style_config
    
    async def generate_scene(self, scene_events, pov_character, context) -> str:
        """
        生成场景文本
        """
        # 构建场景提示
        prompt = self._build_scene_prompt(scene_events, pov_character, context)
        
        # 生成文本
        text = await self.llm.generate(
            prompt,
            temperature=self.style.temperature,
            max_tokens=2000
        )
        
        return text
    
    def _build_scene_prompt(self, events, pov, context):
        """构建场景提示"""
        
        # 事件描述
        event_descriptions = []
        for event in events:
            desc = f"- {event.action.character_id}: {event.action.description}"
            if event.effects:
                desc += f" → 结果: {', '.join(e.description for e in event.effects)}"
            event_descriptions.append(desc)
        
        # POV角色感知
        pov_perceptions = []
        if pov:
            for event in events:
                if pov.character_id in event.involved_characters:
                    perception = pov.get_perception(event)
                    pov_perceptions.append(f"- 你{perception.description}")
        
        prompt = f"""【场景写作】

=== 场景设定 ===
地点：{context.location.name}
时间：{context.time}
氛围：{context.atmosphere}

=== 发生的事件 ===
{'\n'.join(event_descriptions)}

=== 你的感知（{pov.name}视角）===
{'\n'.join(pov_perceptions)}

=== 写作要求 ===
风格：{self.style.name}
节奏：{context.pacing}
情感基调：{context.emotional_tone}

请以{pov.name}的视角，将上述事件写成一段文学性的场景描写。
要求：
1. 展现角色的内心活动
2. 描写环境氛围
3. 对话符合角色性格
4. 动作有画面感
5. 字数：800-1200字
"""
        
        return prompt
```

---

## 当前限制与应对

### 限制1：计算成本

**问题：** 每章需要多次LLM调用（决策×角色数 + 叙事生成）

**应对：**
- 缓存角色决策（相似情境复用）
- 批量生成（一次生成多个场景）
- 本地模型（使用较小模型处理简单决策）

### 限制2：一致性维护

**问题：** LLM可能"忘记"之前的设定

**应对：**
- 结构化状态存储（不是依赖LLM记忆）
- 生成前检索相关上下文
- 生成后验证一致性

### 限制3：创意局限

**问题：** 模拟可能产生"平庸"的故事

**应对：**
- 引入"命运事件"（作者预设的关键节点）
- 随机扰动（引入意外因素）
- 多轮迭代（生成→评估→改进）

---

## 结论

### 可以实现，但需要分阶段

| 阶段 | 时间 | 可行性 | 质量 |
|------|------|--------|------|
| **MVP** | 1-2月 | ⭐⭐⭐⭐⭐ | 可运行，故事基本合理 |
| **基础版** | 3-4月 | ⭐⭐⭐⭐ | 角色有个性，情节有起伏 |
| **进阶版** | 6-12月 | ⭐⭐⭐ | 情感深度，文学性 |
| **完整版** | 1-2年 | ⭐⭐ | 真正"涌现"的创意 |

### 关键成功因素

1. **不要追求真正的AI意识** —— 模拟出"看起来像有意识"的行为即可
2. **结构化约束 + LLM创意** —— 规则保证一致性，LLM提供灵活性
3. **快速迭代** —— 先跑起来，再优化
4. **人机协作** —— 关键节点人工干预，日常模拟自动运行

### 立即可以开始

1. 实现基础世界状态机（SQLite存储）
2. 实现简单角色决策（LLM驱动）
3. 实现事件→文本的转换
4. 跑通一个5章的短故事

**这不是科幻，是工程。** 用现有技术可以做出一个"看起来像世界模拟"的系统，而且质量会超过传统生成方法。

---

*文档版本: v1.0*
*更新日期: 2026-04-28*
*作者: 小R*
