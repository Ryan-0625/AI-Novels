# Step 2: 记忆系统重构 - 三级阶梯模式

## 1. 设计哲学

### 核心转变

```
从：简单存储 → 到：认知架构核心
从：被动查询 → 到：主动检索、联想、遗忘
从：统一存储 → 到：三级阶梯（感知/工作/长期）
从：精确匹配 → 到：语义关联、情感共鸣
```

### 设计原则

1. **感知即筛选**：99%的信息被遗忘，只有重要的进入工作记忆
2. **工作记忆即舞台**：当前意识焦点，容量有限（7±2）
3. **长期记忆即网络**：语义关联、情感标记、情境编码
4. **遗忘即优化**：主动遗忘低价值信息，强化高价值记忆
5. **回忆即重构**：记忆不是读取，是重新构建

---

## 2. 三级阶梯架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    三级记忆阶梯                            │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Level 3: 长期记忆 (Long-Term Memory)                ││
│  │  • 情节记忆（Episodic）- 个人经历                    ││
│  │  • 语义记忆（Semantic）- 知识概念                    ││
│  │  • 情感记忆（Emotional）- 情绪关联                    ││
│  │  │  • 程序记忆（Procedural）- 技能习惯              ││
│  │ 存储：SQLite + Qdrant（向量索引）                    ││
│  │ 容量：理论上无限                                     ││
│  │ 保留时间：永久（主动遗忘除外）                        ││
│  └─────────────────────────────────────────────────────┘│
│                              ↑↓ 巩固/提取                 │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Level 2: 工作记忆 (Working Memory)                   ││
│  │  • 当前意识焦点（4个槽位）                            ││
│  │  • 情感状态缓存                                       ││
│  │  • 目标栈（当前追求）                                 ││
│  │  • 推理上下文                                         ││
│  │ 存储：内存（Redis/SQLite内存模式）                    ││
│  │ 容量：4±1 个 chunk                                   ││
│  │ 保留时间：秒级（随时间衰减）                          ││
│  └─────────────────────────────────────────────────────┘│
│                              ↑↓ 注意力筛选                │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Level 1: 感知记忆 (Sensory Memory)                   ││
│  │  • 原始感知输入（视觉/听觉/触觉）                     ││
│  │  • 环境快照                                           ││
│  │  • 即时情感触发                                       ││
│  │ 存储：内存（临时缓冲区）                              ││
│  │ 容量：大量（未筛选）                                  ││
│  │ 保留时间：毫秒级（立即筛选）                          ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 注意力控制器 (Attention Controller)                  ││
│  │  • 显著性检测（新奇/威胁/情感）                       ││
│  │  • 目标相关性评估                                     ││
│  │  • 情感共鸣检测                                       ││
│  │  • 认知负荷管理                                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
环境输入 → 感知记忆 → [注意力筛选] → 工作记忆 → [巩固机制] → 长期记忆
                ↑                           ↑
                └────── 情感标记 ────────────┘
                └────── 目标关联 ────────────┘

长期记忆 → [提取线索] → 工作记忆 → 决策/行动
    ↑___________________________|
         （联想激活）
```

---

## 3. 记忆类型设计

### 3.1 情节记忆（Episodic Memory）

```sql
CREATE TABLE episodic_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    
    -- 记忆内容
    event_id INTEGER,                      -- 关联事件
    scene_description TEXT,                -- 场景描述（自然语言）
    
    -- 时间编码
    experienced_at INTEGER,                -- 实际经历时间
    encoded_at INTEGER DEFAULT (unixepoch()), -- 编码时间
    
    -- 情感标记（核心：情感决定记忆强度）
    emotional_valence REAL,                -- 情感效价（-1到+1）
    emotional_arousal REAL,                -- 情感唤醒度（0到1）
    emotional_tags JSON,                   -- ["joy", "surprise", "fear"]
    
    -- 记忆强度（决定可提取性）
    strength REAL DEFAULT 0.5,             -- 当前强度（0-1）
    initial_strength REAL DEFAULT 0.5,   -- 初始强度
    decay_rate REAL DEFAULT 0.1,        -- 衰减率（人格相关）
    
    -- 巩固状态
    rehearsal_count INTEGER DEFAULT 0,   -- 复述次数
    last_rehearsed INTEGER,               -- 最后复述时间
    is_consolidated INTEGER DEFAULT 0,  -- 是否已巩固
    
    -- 情境编码（提取线索）
    context_tags JSON,                    -- ["location:仙灵岛", "time:夜晚", "people:赵灵儿"]
    sensory_cues JSON,                    -- ["sound:水声", "smell:花香"]
    
    -- 元数据
    importance REAL DEFAULT 0.5,        -- 重要性（0-1）
    is_flashbulb INTEGER DEFAULT 0,      -- 是否闪光灯记忆（重大事件）
    
    FOREIGN KEY (character_id) REFERENCES entities(id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);

-- 索引
CREATE INDEX idx_episodic_character ON episodic_memories(character_id, strength DESC);
CREATE INDEX idx_episodic_emotion ON episodic_memories(emotional_tags, emotional_valence);
CREATE INDEX idx_episodic_context ON episodic_memories(context_tags);
CREATE INDEX idx_episodic_time ON episodic_memories(experienced_at);
```

### 3.2 语义记忆（Semantic Memory）

```sql
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    
    -- 知识内容
    concept_key TEXT NOT NULL,            -- 概念键（如 "魔法体系"）
    concept_value TEXT,                    -- 概念值（如 "五行相生相克"）
    
    -- 知识类型
    knowledge_type TEXT CHECK (knowledge_type IN (
        'world_fact',      -- 世界事实（物理规则、历史）
        'social_norm',     -- 社会规范（礼仪、法律）
        'personal_trait',  -- 个人特质（"我勇敢"）
        'relationship',    -- 关系知识（"李逍遥是剑客"）
        'skill',           -- 技能知识（"蜀山剑诀"）
        'belief'          -- 信念（"正义终将胜利"）
    )),
    
    -- 置信度（知识的确定性）
    confidence REAL DEFAULT 0.8,
    evidence_count INTEGER DEFAULT 1,    -- 支持证据数量
    
    -- 来源
    source_type TEXT CHECK (source_type IN (
        'direct_experience',  -- 直接经验
        'told_by_trusted',    -- 可信之人告知
        'told_by_untrusted',  -- 不可信之人告知
        'inferred',           -- 推理得出
        'assumed'             -- 假设默认
    )),
    source_event_id INTEGER,              -- 来源事件
    
    -- 关联网络
    related_concepts JSON,               -- ["related_key:weight", ...]
    
    -- 使用统计
    access_count INTEGER DEFAULT 0,     -- 被提取次数
    last_accessed INTEGER,               -- 最后提取时间
    
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch()),
    
    FOREIGN KEY (character_id) REFERENCES entities(id)
);

-- 索引
CREATE INDEX idx_semantic_character ON semantic_memories(character_id, knowledge_type);
CREATE INDEX idx_semantic_concept ON semantic_memories(concept_key);
CREATE INDEX idx_semantic_confidence ON semantic_memories(confidence DESC);
```

### 3.3 情感记忆（Emotional Memory）

```sql
CREATE TABLE emotional_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    
    -- 触发器
    trigger_type TEXT CHECK (trigger_type IN (
        'situation_pattern',  -- 情境模式（如 "被背叛"）
        'person_presence',    -- 特定人物出现
        'location_return',    -- 回到特定地点
        'sensory_cue',        -- 感官线索（气味、声音）
        'anniversary'         -- 时间 anniversary
    )),
    trigger_pattern TEXT,                  -- 触发模式描述
    
    -- 情感反应
    triggered_emotion TEXT,               -- 触发的情感
    intensity REAL,                        -- 强度（0-1）
    reaction_type TEXT CHECK (reaction_type IN (
        'automatic',      -- 自动反应（无法控制）
        'conditioned',    -- 条件反射（可弱化）
        'learned',        -- 习得反应（可改变）
        'empathetic'      -- 共情反应
    )),
    
    -- 关联记忆
    source_episodic_id INTEGER,           -- 源情节记忆
    
    -- 条件化程度
    conditioning_strength REAL DEFAULT 0.5,  -- 条件化强度
    extinction_count INTEGER DEFAULT 0,    -- 消退尝试次数
    
    created_at INTEGER DEFAULT (unixepoch()),
    
    FOREIGN KEY (character_id) REFERENCES entities(id),
    FOREIGN KEY (source_episodic_id) REFERENCES episodic_memories(id)
);

-- 索引
CREATE INDEX idx_emotional_character ON emotional_memories(character_id, trigger_type);
```

### 3.4 程序记忆（Procedural Memory）

```sql
CREATE TABLE procedural_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    
    -- 技能内容
    skill_name TEXT NOT NULL,
    skill_description TEXT,
    
    -- 熟练度
    proficiency REAL DEFAULT 0.0,         -- 熟练度（0-1）
    practice_count INTEGER DEFAULT 0,    -- 练习次数
    
    -- 技能类型
    skill_category TEXT CHECK (skill_category IN (
        'combat',         -- 战斗技能
        'magic',          -- 魔法技能
        'social',         -- 社交技能
        'craft',          --  crafting技能
        'movement',       -- 移动技能
        'cognitive'       -- 认知技能
    )),
    
    -- 执行条件
    prerequisites JSON,                  -- 前置条件
    execution_context JSON,              -- 执行情境
    
    -- 自动化程度
    is_automatic INTEGER DEFAULT 0,    -- 是否自动化（无需思考）
    attention_required REAL DEFAULT 0.5, -- 所需注意力
    
    FOREIGN KEY (character_id) REFERENCES entities(id)
);
```

---

## 4. 工作记忆设计

### 4.1 工作记忆模型

```python
class WorkingMemory:
    """
    工作记忆 - 当前意识焦点
    
    容量限制：4±1 个 chunk（基于现代认知心理学）
    持续时间：秒级（随时间衰减）
    功能：
    - 维持当前意识内容
    - 整合新旧信息
    - 支持推理和决策
    """
    
    def __init__(self, character_id: int, capacity: int = 4):
        self.character_id = character_id
        self.capacity = capacity
        self.slots: List[MemoryChunk] = []  # 当前内容
        self.focus_stack: List[FocusItem] = []  # 焦点栈
        self.emotional_state: EmotionState = EmotionState()
        self.goal_stack: List[Goal] = []  # 当前目标
        
        # 衰减参数
        self.decay_rate = 0.1  # 每秒衰减10%
        self.last_update = time.time()
    
    def add_to_working_memory(
        self,
        content: Any,
        content_type: str,
        priority: float = 0.5,
        source: str = "perception"
    ) -> bool:
        """
        添加到工作记忆
        
        策略：
        1. 如果容量未满，直接添加
        2. 如果容量已满，比较优先级，替换最低优先级
        3. 如果新内容优先级最高，触发注意转移
        """
        chunk = MemoryChunk(
            content=content,
            type=content_type,
            priority=priority,
            source=source,
            timestamp=time.time()
        )
        
        if len(self.slots) < self.capacity:
            self.slots.append(chunk)
            return True
        
        # 找到最低优先级的 chunk
        min_idx = min(range(len(self.slots)), key=lambda i: self.slots[i].priority)
        
        if priority > self.slots[min_idx].priority:
            # 替换（注意转移）
            displaced = self.slots[min_idx]
            self.slots[min_idx] = chunk
            
            # 被替换的内容：如果重要，尝试巩固到长期记忆
            if displaced.priority > 0.7:
                self._trigger_consolidation(displaced)
            
            return True
        
        return False  # 无法添加（优先级不够）
    
    def get_current_focus(self) -> Optional[MemoryChunk]:
        """获取当前焦点（最高优先级）"""
        if not self.slots:
            return None
        return max(self.slots, key=lambda c: c.priority)
    
    def update(self):
        """更新工作记忆（衰减）"""
        now = time.time()
        elapsed = now - self.last_update
        
        # 衰减所有 chunk 的优先级
        for chunk in self.slots:
            chunk.priority *= (1 - self.decay_rate) ** elapsed
        
        # 移除衰减到阈值的 chunk
        self.slots = [c for c in self.slots if c.priority > 0.1]
        
        self.last_update = now
    
    def _trigger_consolidation(self, chunk: MemoryChunk):
        """触发巩固（将工作记忆内容转移到长期记忆）"""
        consolidation_event = ConsolidationEvent(
            character_id=self.character_id,
            content=chunk.content,
            emotional_context=self.emotional_state.to_dict(),
            goal_context=[g.to_dict() for g in self.goal_stack]
        )
        
        # 发送到巩固队列
        consolidation_queue.put(consolidation_event)
```

### 4.2 注意力控制器

```python
class AttentionController:
    """
    注意力控制器 - 决定什么进入工作记忆
    
    筛选标准：
    1. 显著性（新奇、威胁、情感强度）
    2. 目标相关性（与当前目标的关联）
    3. 情感共鸣（与当前情感状态的匹配）
    4. 认知负荷（当前工作记忆的负荷）
    """
    
    def __init__(
        self,
        character_id: int,
        personality: Dict,
        current_goals: List[Goal]
    ):
        self.character_id = character_id
        self.personality = personality
        self.current_goals = current_goals
        
        # 注意力参数（人格相关）
        self.sensitivity = {
            'novelty': personality.get('openness', 0.5) * 0.8 + 0.2,
            'threat': personality.get('neuroticism', 0.5) * 0.8 + 0.2,
            'opportunity': personality.get('extraversion', 0.5) * 0.8 + 0.2,
            'social': personality.get('agreeableness', 0.5) * 0.8 + 0.2
        }
    
    def evaluate_stimulus(
        self,
        stimulus: Stimulus,
        working_memory: WorkingMemory
    ) -> AttentionScore:
        """
        评估刺激的重要性
        
        返回：注意力分数（0-1）
        """
        scores = {}
        
        # 1. 显著性检测
        scores['novelty'] = self._evaluate_novelty(stimulus)
        scores['threat'] = self._evaluate_threat(stimulus)
        scores['emotional_salience'] = self._evaluate_emotional_salience(
            stimulus, working_memory.emotional_state
        )
        
        # 2. 目标相关性
        scores['goal_relevance'] = self._evaluate_goal_relevance(stimulus)
        
        # 3. 情感共鸣
        scores['emotional_resonance'] = self._evaluate_emotional_resonance(
            stimulus, working_memory.emotional_state
        )
        
        # 4. 认知负荷（负荷高时，阈值提高）
        cognitive_load = len(working_memory.slots) / working_memory.capacity
        load_penalty = cognitive_load * 0.3  # 负荷高，扣分
        
        # 加权总分
        total_score = (
            scores['novelty'] * self.sensitivity['novelty'] * 0.2 +
            scores['threat'] * self.sensitivity['threat'] * 0.25 +
            scores['emotional_salience'] * 0.2 +
            scores['goal_relevance'] * 0.25 +
            scores['emotional_resonance'] * 0.1
        ) - load_penalty
        
        return AttentionScore(
            total=max(0, min(1, total_score)),
            components=scores,
            should_attend=total_score > 0.5
        )
    
    def _evaluate_novelty(self, stimulus: Stimulus) -> float:
        """评估新奇性（与长期记忆的差异）"""
        # 检索相似记忆
        similar_memories = self._retrieve_similar(stimulus, top_k=5)
        
        if not similar_memories:
            return 1.0  # 完全新奇
        
        # 计算平均相似度
        avg_similarity = sum(m.similarity for m in similar_memories) / len(similar_memories)
        
        return 1.0 - avg_similarity  # 相似度越低，新奇性越高
    
    def _evaluate_threat(self, stimulus: Stimulus) -> float:
        """评估威胁性"""
        threat_signals = [
            stimulus.contains('danger'),
            stimulus.contains('enemy'),
            stimulus.get('aggression_level', 0) > 0.5,
            stimulus.get('health_change', 0) < -0.3
        ]
        
        return sum(threat_signals) / len(threat_signals)
    
    def _evaluate_goal_relevance(self, stimulus: Stimulus) -> float:
        """评估与当前目标的相关性"""
        if not self.current_goals:
            return 0.5
        
        relevances = []
        for goal in self.current_goals:
            relevance = self._calculate_goal_relevance(stimulus, goal)
            relevances.append(relevance * goal.priority)
        
        return max(relevances) if relevances else 0.0
    
    def _evaluate_emotional_resonance(
        self,
        stimulus: Stimulus,
        current_emotion: EmotionState
    ) -> float:
        """评估情感共鸣（刺激情感与当前情感的匹配/互补）"""
        stimulus_emotion = stimulus.get('emotional_tone', {})
        
        # 计算情感相似度
        similarity = self._emotion_similarity(stimulus_emotion, current_emotion)
        
        # 人格调节（高神经质的人更容易被负面情感共鸣）
        neuroticism = self.personality.get('neuroticism', 0.5)
        if stimulus_emotion.get('valence', 0) < 0:
            similarity *= (1 + neuroticism * 0.5)
        
        return similarity
```

---

## 5. 记忆操作算法

### 5.1 编码（Encoding）

```python
class MemoryEncoder:
    """
    记忆编码器 - 将经历转化为记忆
    
    流程：
    1. 感知输入 → 特征提取
    2. 情感评估 → 情感标记
    3. 目标关联 → 重要性评估
    4. 情境编码 → 提取线索
    5. 巩固判断 → 是否进入长期记忆
    """
    
    def encode_experience(
        self,
        character_id: int,
        experience: Experience,
        emotional_context: EmotionState,
        goal_context: List[Goal]
    ) -> MemoryTrace:
        """
        编码经历
        
        输出：记忆痕迹（包含所有编码信息）
        """
        # 1. 特征提取
        features = self._extract_features(experience)
        
        # 2. 情感评估
        emotional_valence = emotional_context.valence
        emotional_arousal = emotional_context.arousal
        
        # 3. 重要性评估（基于情感和目标）
        importance = self._calculate_importance(
            experience=experience,
            emotional_arousal=emotional_arousal,
            goal_relevance=self._calculate_goal_relevance(experience, goal_context)
        )
        
        # 4. 情境编码
        context_tags = self._encode_context(experience)
        sensory_cues = self._encode_sensory(experience)
        
        # 5. 初始记忆强度（基于重要性和情感）
        initial_strength = self._calculate_initial_strength(
            importance=importance,
            emotional_arousal=emotional_arousal,
            novelty=self._calculate_novelty(features, character_id)
        )
        
        # 6. 创建记忆痕迹
        trace = MemoryTrace(
            character_id=character_id,
            experience=experience,
            features=features,
            emotional_valence=emotional_valence,
            emotional_arousal=emotional_arousal,
            importance=importance,
            context_tags=context_tags,
            sensory_cues=sensory_cues,
            initial_strength=initial_strength,
            decay_rate=self._calculate_decay_rate(character_id, emotional_arousal)
        )
        
        # 7. 判断是否立即巩固
        if importance > 0.8 or emotional_arousal > 0.8:
            # 高重要性/高情感 → 立即巩固
            self._immediate_consolidation(trace)
        else:
            # 低重要性 → 进入工作记忆，等待巩固
            self._add_to_working_memory(trace)
        
        return trace
    
    def _calculate_importance(
        self,
        experience: Experience,
        emotional_arousal: float,
        goal_relevance: float
    ) -> float:
        """
        计算重要性
        
        公式：重要性 = 情感唤醒度 * 0.3 + 目标相关性 * 0.4 + 新奇性 * 0.2 + 结果影响 * 0.1
        """
        novelty = experience.get('novelty', 0.5)
        outcome_impact = abs(experience.get('outcome_change', 0))
        
        importance = (
            emotional_arousal * 0.3 +
            goal_relevance * 0.4 +
            novelty * 0.2 +
            outcome_impact * 0.1
        )
        
        return min(1.0, importance)
    
    def _calculate_initial_strength(
        self,
        importance: float,
        emotional_arousal: float,
        novelty: float
    ) -> float:
        """
        计算初始记忆强度
        
        高重要性 + 高情感 + 新奇 → 强记忆
        """
        return min(1.0, importance * 0.5 + emotional_arousal * 0.3 + novelty * 0.2)
```

### 5.2 存储（Storage）

```python
class MemoryStorage:
    """
    记忆存储 - 长期记忆的持久化
    
    功能：
    1. 分层存储（情节/语义/情感/程序）
    2. 向量索引（语义检索）
    3. 关联网络（记忆之间的连接）
    """
    
    def __init__(
        self,
        sqlite_db: Database,
        vector_store: QdrantStore
    ):
        self.db = sqlite_db
        self.vector = vector_store
    
    def store_episodic(self, trace: MemoryTrace) -> int:
        """存储情节记忆"""
        # 1. 存储到 SQLite
        memory_id = self.db.insert_episodic(trace)
        
        # 2. 生成向量表示
        vector = self._generate_vector(trace)
        
        # 3. 存储到向量数据库
        self.vector.store(
            collection=f"episodic_{trace.character_id}",
            id=memory_id,
            vector=vector,
            payload={
                'emotional_valence': trace.emotional_valence,
                'emotional_arousal': trace.emotional_arousal,
                'importance': trace.importance,
                'context_tags': trace.context_tags
            }
        )
        
        # 4. 更新关联网络
        self._update_association_network(trace.character_id, memory_id, trace)
        
        return memory_id
    
    def store_semantic(self, character_id: int, knowledge: Knowledge) -> int:
        """存储语义记忆（知识）"""
        # 知识去重：如果已存在相似知识，合并或更新
        existing = self._find_similar_knowledge(character_id, knowledge)
        
        if existing:
            # 合并知识（置信度加权）
            merged = self._merge_knowledge(existing, knowledge)
            self.db.update_semantic(existing.id, merged)
            return existing.id
        else:
            # 新建知识
            return self.db.insert_semantic(character_id, knowledge)
    
    def _update_association_network(
        self,
        character_id: int,
        memory_id: int,
        trace: MemoryTrace
    ):
        """更新记忆关联网络"""
        # 找到相关记忆
        related_memories = self._find_related_memories(character_id, trace)
        
        for related in related_memories:
            # 计算关联强度
            association_strength = self._calculate_association(
                trace, related
            )
            
            # 存储关联
            self.db.store_association(
                character_id=character_id,
                memory_a=memory_id,
                memory_b=related.id,
                strength=association_strength,
                association_type=self._determine_association_type(trace, related)
            )
```

### 5.3 提取（Retrieval）

```python
class MemoryRetrieval:
    """
    记忆提取 - 从长期记忆召回信息
    
    策略：
    1. 线索驱动提取（基于当前情境）
    2. 语义检索（向量相似度）
    3. 情感匹配（情感共鸣）
    4. 联想扩散（关联记忆激活）
    """
    
    def __init__(
        self,
        storage: MemoryStorage,
        vector_store: QdrantStore
    ):
        self.storage = storage
        self.vector = vector_store
    
    def retrieve(
        self,
        character_id: int,
        query: RetrievalQuery,
        strategy: str = "adaptive"
    ) -> List[RetrievedMemory]:
        """
        提取记忆（主入口）
        
        策略：
        - "adaptive": 自适应（根据情境选择最佳策略）
        - "semantic": 语义检索
        - "emotional": 情感匹配
        - "associative": 联想扩散
        - "temporal": 时间邻近
        """
        if strategy == "adaptive":
            strategy = self._select_best_strategy(query)
        
        if strategy == "semantic":
            return self._semantic_retrieval(character_id, query)
        elif strategy == "emotional":
            return self._emotional_retrieval(character_id, query)
        elif strategy == "associative":
            return self._associative_retrieval(character_id, query)
        elif strategy == "temporal":
            return self._temporal_retrieval(character_id, query)
        else:
            return self._hybrid_retrieval(character_id, query)
    
    def _semantic_retrieval(
        self,
        character_id: int,
        query: RetrievalQuery
    ) -> List[RetrievedMemory]:
        """
        语义检索（基于向量相似度）
        """
        # 生成查询向量
        query_vector = self._generate_query_vector(query)
        
        # 向量检索
        results = self.vector.search(
            collection=f"episodic_{character_id}",
            vector=query_vector,
            top_k=query.top_k * 2,  # 检索更多，后续过滤
            filters={
                'importance': {'$gte': query.min_importance}
            }
        )
        
        # 转换为 RetrievedMemory
        memories = []
        for result in results:
            memory = self.storage.get_episodic(result.id)
            memories.append(RetrievedMemory(
                memory=memory,
                relevance_score=result.score,
                retrieval_path="semantic"
            ))
        
        return memories
    
    def _emotional_retrieval(
        self,
        character_id: int,
        query: RetrievalQuery
    ) -> List[RetrievedMemory]:
        """
        情感检索（基于情感匹配）
        
        原理：当前情感状态会激活相似情感色彩的记忆
        （情感一致性效应）
        """
        current_emotion = query.current_emotion
        
        # 检索情感标记相似的记忆
        sql = """
            SELECT * FROM episodic_memories
            WHERE character_id = ?
              AND emotional_valence BETWEEN ? AND ?
              AND emotional_arousal BETWEEN ? AND ?
            ORDER BY strength DESC
            LIMIT ?
        """
        
        # 情感容差（允许一定差异）
        valence_tolerance = 0.3
        arousal_tolerance = 0.2
        
        rows = self.db.execute(sql, (
            character_id,
            current_emotion.valence - valence_tolerance,
            current_emotion.valence + valence_tolerance,
            current_emotion.arousal - arousal_tolerance,
            current_emotion.arousal + arousal_tolerance,
            query.top_k
        )).fetchall()
        
        memories = []
        for row in rows:
            memory = EpisodicMemory.from_row(row)
            
            # 计算情感匹配度
            emotional_match = self._calculate_emotional_match(
                current_emotion, memory
            )
            
            memories.append(RetrievedMemory(
                memory=memory,
                relevance_score=emotional_match,
                retrieval_path="emotional"
            ))
        
        return memories
    
    def _associative_retrieval(
        self,
        character_id: int,
        query: RetrievalQuery
    ) -> List[RetrievedMemory]:
        """
        联想检索（基于记忆关联网络）
        
        原理：从一个记忆出发，沿着关联网络扩散激活
        （类似于人类思维的联想）
        """
        # 获取起始记忆（最相关的几个）
        seed_memories = self._semantic_retrieval(character_id, query)[:3]
        
        activated = set()
        results = []
        
        for seed in seed_memories:
            # 扩散激活
            spread_results = self._spread_activation(
                character_id=character_id,
                seed_memory_id=seed.memory.id,
                depth=query.spread_depth or 2,
                threshold=query.activation_threshold or 0.3
            )
            
            for memory_id, activation in spread_results:
                if memory_id not in activated:
                    activated.add(memory_id)
                    memory = self.storage.get_episodic(memory_id)
                    results.append(RetrievedMemory(
                        memory=memory,
                        relevance_score=activation,
                        retrieval_path="associative"
                    ))
        
        # 按激活强度排序
        results.sort(key=lambda m: m.relevance_score, reverse=True)
        return results[:query.top_k]
    
    def _spread_activation(
        self,
        character_id: int,
        seed_memory_id: int,
        depth: int,
        threshold: float,
        current_depth: int = 0,
        current_activation: float = 1.0
    ) -> Dict[int, float]:
        """
        扩散激活算法
        
        原理：
        1. 起始记忆激活度 = 1.0
        2. 沿关联传播，激活度 *= 关联强度 * 衰减因子
        3. 低于阈值停止传播
        """
        if current_depth >= depth or current_activation < threshold:
            return {}
        
        results = {seed_memory_id: current_activation}
        
        # 获取关联记忆
        associations = self.db.get_associations(character_id, seed_memory_id)
        
        for assoc in associations:
            next_activation = current_activation * assoc.strength * 0.8  # 衰减因子
            
            if next_activation >= threshold:
                sub_results = self._spread_activation(
                    character_id=character_id,
                    seed_memory_id=assoc.memory_b,
                    depth=depth,
                    threshold=threshold,
                    current_depth=current_depth + 1,
                    current_activation=next_activation
                )
                
                # 合并结果（取最大激活度）
                for mem_id, activation in sub_results.items():
                    if mem_id not in results or results[mem_id] < activation:
                        results[mem_id] = activation
        
        return results
```

### 5.4 遗忘（Forgetting）

```python
class MemoryForgetting:
    """
    记忆遗忘 - 主动优化记忆系统
    
    策略：
    1. 时间衰减（艾宾浩斯遗忘曲线）
    2. 干扰抑制（相似记忆竞争）
    3. 主动遗忘（低价值记忆清除）
    4. 巩固保护（已巩固记忆不易遗忘）
    """
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
    
    def apply_forgetting(
        self,
        character_id: int,
        current_time: int = None
    ) -> List[int]:
        """
        应用遗忘（定期执行）
        
        返回：被遗忘的记忆ID列表
        """
        current_time = current_time or int(time.time())
        forgotten = []
        
        # 1. 获取所有记忆
        memories = self.storage.get_all_memories(character_id)
        
        for memory in memories:
            # 2. 计算当前强度
            current_strength = self._calculate_current_strength(
                memory, current_time
            )
            
            # 3. 更新强度
            self.storage.update_memory_strength(memory.id, current_strength)
            
            # 4. 判断是否遗忘
            if current_strength < 0.1:  # 遗忘阈值
                # 检查是否应该保护
                if self._should_protect(memory):
                    continue
                
                # 标记为遗忘（软删除）
                self.storage.mark_forgotten(memory.id)
                forgotten.append(memory.id)
        
        return forgotten
    
    def _calculate_current_strength(
        self,
        memory: Memory,
        current_time: int
    ) -> float:
        """
        计算当前记忆强度
        
        公式：
        当前强度 = 初始强度 * e^(-衰减率 * 时间差) * 复述增益 * 情感增益
        """
        # 时间衰减
        time_diff = (current_time - memory.encoded_at) / 86400  # 天数
        time_decay = math.exp(-memory.decay_rate * time_diff)
        
        # 复述增益
        rehearsal_boost = 1 + memory.rehearsal_count * 0.2
        
        # 情感增益（高情感记忆衰减更慢）
        emotional_boost = 1 + memory.emotional_arousal * 0.5
        
        # 巩固保护（已巩固记忆衰减更慢）
        consolidation_boost = 2.0 if memory.is_consolidated else 1.0
        
        current_strength = (
            memory.initial_strength *
            time_decay *
            rehearsal_boost *
            emotional_boost *
            consolidation_boost
        )
        
        return min(1.0, current_strength)
    
    def _should_protect(self, memory: Memory) -> bool:
        """判断是否应该保护记忆不被遗忘"""
        # 保护条件：
        # 1. 闪光灯记忆（重大事件）
        if memory.is_flashbulb:
            return True
        
        # 2. 高频提取记忆（经常使用的）
        if memory.access_count > 10:
            return True
        
        # 3. 与核心信念相关
        if memory.is_core_belief:
            return True
        
        # 4. 与当前目标高度相关
        if memory.goal_relevance > 0.9:
            return True
        
        return False
```

---

## 6. Agent工具封装

### 6.1 MemoryEncodingTool - 记忆编码工具

```python
class MemoryEncodingTool:
    """
    记忆编码工具 - Agent可直接调用
    
    功能：
    1. 编码经历为记忆
    2. 评估重要性
    3. 情感标记
    4. 触发巩固
    """
    
    def __init__(
        self,
        encoder: MemoryEncoder,
        storage: MemoryStorage,
        working_memory: WorkingMemory
    ):
        self.encoder = encoder
        self.storage = storage
        self.wm = working_memory
    
    def encode_experience(
        self,
        character_id: int,
        experience: Dict,
        emotional_context: Dict = None
    ) -> int:
        """
        编码经历
        
        输入：
        - 经历描述
        - 情感上下文（可选）
        
        输出：
        - 记忆ID
        """
        # 1. 构建情感上下文
        emotion = emotional_context or self.wm.emotional_state.to_dict()
        
        # 2. 编码
        trace = self.encoder.encode_experience(
            character_id=character_id,
            experience=Experience.from_dict(experience),
            emotional_context=EmotionState.from_dict(emotion),
            goal_context=self.wm.goal_stack
        )
        
        # 3. 存储
        memory_id = self.storage.store_episodic(trace)
        
        return memory_id
    
    def encode_knowledge(
        self,
        character_id: int,
        knowledge: Dict
    ) -> int:
        """
        编码知识（语义记忆）
        
        输入：
        - 知识内容（概念键值对）
        - 置信度
        - 来源
        
        输出：
        - 知识ID
        """
        knowledge_obj = Knowledge.from_dict(knowledge)
        return self.storage.store_semantic(character_id, knowledge_obj)
    
    def rehearse_memory(
        self,
        memory_id: int,
        rehearsal_type: str = "active"
    ) -> float:
        """
        复述记忆（增强记忆强度）
        
        类型：
        - "active": 主动复述（有意识回忆）
        - "passive": 被动复述（联想触发）
        - "emotional": 情感复述（情感再体验）
        """
        memory = self.storage.get_episodic(memory_id)
        
        # 更新复述次数
        memory.rehearsal_count += 1
        memory.last_rehearsed = int(time.time())
        
        # 根据复述类型增强
        if rehearsal_type == "active":
            boost = 0.15
        elif rehearsal_type == "emotional":
            boost = 0.25  # 情感复述效果更强
        else:
            boost = 0.1
        
        # 更新强度
        memory.strength = min(1.0, memory.strength + boost)
        
        # 检查是否巩固
        if memory.rehearsal_count >= 3 and not memory.is_consolidated:
            memory.is_consolidated = True
            self._trigger_consolidation(memory)
        
        self.storage.update_episodic(memory)
        
        return memory.strength
```

### 6.2 MemoryRetrievalTool - 记忆提取工具

```python
class MemoryRetrievalTool:
    """
    记忆提取工具 - Agent可直接调用
    
    功能：
    1. 语义检索
    2. 情感检索
    3. 联想检索
    4. 混合检索
    """
    
    def __init__(
        self,
        retrieval: MemoryRetrieval,
        working_memory: WorkingMemory
    ):
        self.retrieval = retrieval
        self.wm = working_memory
    
    def recall(
        self,
        character_id: int,
        query: str,
        context: Dict = None,
        strategy: str = "adaptive",
        top_k: int = 5
    ) -> List[RetrievedMemory]:
        """
        回忆记忆（主入口）
        
        输入：
        - 查询（自然语言）
        - 上下文（可选）
        - 策略（可选）
        - 返回数量
        
        输出：
        - 记忆列表（按相关性排序）
        """
        # 构建查询
        retrieval_query = RetrievalQuery(
            text=query,
            current_emotion=self.wm.emotional_state,
            current_goals=self.wm.goal_stack,
            context=context or {},
            top_k=top_k
        )
        
        # 执行检索
        results = self.retrieval.retrieve(
            character_id=character_id,
            query=retrieval_query,
            strategy=strategy
        )
        
        # 更新工作记忆（将检索结果放入）
        for result in results[:2]:  # 只放入最相关的2个
            self.wm.add_to_working_memory(
                content=result.memory,
                content_type="retrieved_memory",
                priority=result.relevance_score
            )
        
        return results
    
    def recall_by_emotion(
        self,
        character_id: int,
        target_emotion: str,
        intensity_threshold: float = 0.5
    ) -> List[RetrievedMemory]:
        """
        按情感回忆（情感一致性效应）
        
        例如：
        - 当前感到悲伤 → 回忆悲伤的记忆
        - 当前感到兴奋 → 回忆兴奋的记忆
        """
        query = RetrievalQuery(
            current_emotion=EmotionState({target_emotion: intensity_threshold}),
            top_k=10
        )
        
        return self.retrieval.retrieve(
            character_id=character_id,
            query=query,
            strategy="emotional"
        )
    
    def recall_by_association(
        self,
        character_id: int,
        seed_memory_id: int,
        spread_depth: int = 2
    ) -> List[RetrievedMemory]:
        """
        联想回忆（从一个记忆出发，联想相关记忆）
        
        例如：
        - 看到一把剑 → 联想到练剑的记忆 → 联想到师父的记忆
        """
        query = RetrievalQuery(
            seed_memory_id=seed_memory_id,
            spread_depth=spread_depth,
            top_k=10
        )
        
        return self.retrieval.retrieve(
            character_id=character_id,
            query=query,
            strategy="associative"
        )
    
    def recall_recent(
        self,
        character_id: int,
        time_window: int = 86400  # 默认最近24小时
    ) -> List[RetrievedMemory]:
        """
        回忆最近经历
        
        用途：
        - 角色回忆今天发生了什么
        - 短期决策参考
        """
        current_time = int(time.time())
        
        sql = """
            SELECT * FROM episodic_memories
            WHERE character_id = ?
              AND experienced_at > ?
            ORDER BY experienced_at DESC
        """
        
        rows = self.db.execute(sql, (character_id, current_time - time_window)).fetchall()
        
        return [
            RetrievedMemory(
                memory=EpisodicMemory.from_row(row),
                relevance_score=1.0,  # 最近记忆默认高相关
                retrieval_path="temporal"
            )
            for row in rows
        ]
```

### 6.3 MemoryConsolidationTool - 记忆巩固工具

```python
class MemoryConsolidationTool:
    """
    记忆巩固工具 - Agent可直接调用
    
    功能：
    1. 工作记忆→长期记忆转移
    2. 记忆整合（提取共同模式）
    3. 语义化（情节记忆→语义记忆）
    4. 睡眠巩固（批量处理）
    """
    
    def __init__(
        self,
        encoder: MemoryEncoder,
        storage: MemoryStorage,
        working_memory: WorkingMemory
    ):
        self.encoder = encoder
        self.storage = storage
        self.wm = working_memory
    
    def consolidate_working_memory(
        self,
        character_id: int
    ) -> List[int]:
        """
        巩固工作记忆内容
        
        流程：
        1. 获取工作记忆中的重要内容
        2. 转移到长期记忆
        3. 更新关联网络
        """
        consolidated = []
        
        # 获取高优先级的工作记忆内容
        important_chunks = [
            chunk for chunk in self.wm.slots
            if chunk.priority > 0.6
        ]
        
        for chunk in important_chunks:
            if chunk.type == "experience":
                # 巩固为情节记忆
                memory_id = self.encoder.encode_experience(
                    character_id=character_id,
                    experience=chunk.content,
                    emotional_context=self.wm.emotional_state,
                    goal_context=self.wm.goal_stack
                )
                consolidated.append(memory_id)
            
            elif chunk.type == "knowledge":
                # 巩固为语义记忆
                knowledge_id = self.storage.store_semantic(
                    character_id=character_id,
                    knowledge=chunk.content
                )
                consolidated.append(knowledge_id)
        
        return consolidated
    
    def sleep_consolidation(
        self,
        character_id: int,
        recent_memories: List[int] = None
    ) -> ConsolidationReport:
        """
        睡眠巩固（批量处理）
        
        功能：
        1. 强化重要记忆
        2. 整合相似记忆
        3. 提取共同模式（情节→语义）
        4. 清理冗余记忆
        """
        report = ConsolidationReport()
        
        # 1. 获取近期记忆
        if recent_memories is None:
            recent_memories = self.storage.get_recent_memories(
                character_id,
                time_window=86400 * 7  # 最近7天
            )
        
        # 2. 强化重要记忆
        for memory_id in recent_memories:
            memory = self.storage.get_episodic(memory_id)
            
            if memory.importance > 0.7:
                # 强化（增加初始强度，降低衰减率）
                memory.initial_strength = min(1.0, memory.initial_strength + 0.1)
                memory.decay_rate *= 0.9  # 衰减变慢
                
                self.storage.update_episodic(memory)
                report.strengthened += 1
        
        # 3. 整合相似记忆
        similar_groups = self._find_similar_memories(recent_memories)
        
        for group in similar_groups:
            if len(group) >= 3:
                # 提取共同模式
                pattern = self._extract_pattern(group)
                
                # 创建语义记忆
                semantic_id = self.storage.store_semantic(
                    character_id=character_id,
                    knowledge=Knowledge(
                        concept_key=pattern.name,
                        concept_value=pattern.description,
                        knowledge_type='inferred',
                        confidence=pattern.confidence
                    )
                )
                
                report.patterns_extracted += 1
                report.semantic_memories_created += 1
        
        # 4. 清理冗余
        forgotten = self._cleanup_redundant_memories(character_id)
        report.forgotten = len(forgotten)
        
        return report
    
    def _extract_pattern(self, memories: List[EpisodicMemory]) -> Pattern:
        """从相似记忆中提取共同模式"""
        # 使用LLM提取模式
        prompt = f"""
        以下是一系列相似的经历：
        
        {memories}
        
        请提取这些经历的共同模式：
        1. 模式名称
        2. 模式描述
        3. 置信度
        4. 适用情境
        """
        
        result = llm.generate(prompt)
        return Pattern.from_json(result)
```

---

## 7. 实施计划

### 7.1 删除旧记忆系统（Day 1）

```bash
# 删除旧记忆相关文件
rm src/deepnovel/agents/memory_manager.py
rm src/deepnovel/core/memory_store.py
rm src/deepnovel/database/memory_repository.py

# 保留接口（如果其他模块依赖）
# 但标记为 deprecated
```

### 7.2 创建新记忆系统（Day 1-3）

```python
# 文件结构
memory/
├── __init__.py
├── models/                      # 数据模型
│   ├── __init__.py
│   ├── episodic.py             # 情节记忆模型
│   ├── semantic.py             # 语义记忆模型
│   ├── emotional.py            # 情感记忆模型
│   ├── procedural.py           # 程序记忆模型
│   ├── working_memory.py       # 工作记忆模型
│   └── attention.py            # 注意力模型
├── storage/                     # 存储层
│   ├── __init__.py
│   ├── sqlite_storage.py       # SQLite存储
│   └── vector_storage.py       # 向量存储
├── processes/                   # 认知过程
│   ├── __init__.py
│   ├── encoding.py             # 编码过程
│   ├── retrieval.py            # 提取过程
│   ├── consolidation.py        # 巩固过程
│   └── forgetting.py           # 遗忘过程
├── tools/                       # Agent工具
│   ├── __init__.py
│   ├── encoding_tool.py         # 编码工具
│   ├── retrieval_tool.py       # 提取工具
│   └── consolidation_tool.py   # 巩固工具
└── system.py                    # 记忆系统主入口
```

### 7.3 集成测试（Day 3-4）

```python
# 测试场景
1. 编码测试
   - 正常经历编码
   - 高情感经历编码
   - 知识编码
   
2. 提取测试
   - 语义检索
   - 情感检索
   - 联想检索
   - 混合检索
   
3. 遗忘测试
   - 时间衰减
   - 复述保护
   - 主动遗忘
   
4. 巩固测试
   - 工作记忆→长期记忆
   - 睡眠巩固
   - 模式提取
   
5. 注意力测试
   - 显著性检测
   - 目标相关性
   - 工作记忆容量限制
```

---

## 8. 验收标准

### 8.1 功能验收

| 功能 | 测试场景 | 通过标准 |
|------|---------|---------|
| 编码 | 角色经历战斗 | 生成情节记忆，情感标记正确 |
| 提取 | 角色回忆战斗经历 | 检索到相关记忆，排序合理 |
| 遗忘 | 7天后检查记忆 | 不重要记忆衰减，重要记忆保留 |
| 巩固 | 角色睡眠 | 工作记忆内容转移到长期记忆 |
| 注意力 | 角色面对多个刺激 | 正确筛选，工作记忆不超载 |

### 8.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 编码速度 | <100ms | 100次编码 |
| 提取速度 | <200ms | 1000条记忆检索 |
| 遗忘处理 | <1s | 处理10000条记忆 |
| 工作记忆更新 | <10ms | 100次更新 |

### 8.3 质量验收

| 指标 | 目标 | 评估方法 |
|------|------|---------|
| 检索准确率 | >85% | 人工评估50个查询 |
| 情感匹配度 | >80% | 人工评估30个情感查询 |
| 遗忘合理性 | >90% | 检查被遗忘记忆是否确实不重要 |

---

## 9. 与Step 1的关联

### 9.1 数据层支持

```
Step 1 (数据层)          Step 2 (记忆系统)
    │                        │
    ├─ entities ───────────├─ character_id
    ├─ facts ──────────────├─ 世界状态（记忆内容）
    ├─ events ─────────────├─ 经历来源
    ├─ character_minds ────├─ 工作记忆/情感状态
    └─ narratives ─────────├─ 记忆叙事化
```

### 9.2 工具链集成

```python
# 记忆系统使用数据层工具
from step1.tools import WorldStateTool, CharacterMindTool

class MemoryEncodingTool:
    def __init__(self, world_tool: WorldStateTool, mind_tool: CharacterMindTool):
        self.world = world_tool
        self.mind = mind_tool
    
    def encode_experience(self, character_id: int, event_id: int):
        # 获取世界状态（事实）
        world_state = self.world.query_state(character_id)
        
        # 获取心智状态（情感/目标）
        mind_state = self.mind.get_mind(character_id)
        
        # 编码记忆
        return self.encoder.encode(world_state, mind_state)
```

---

## 10. 实施状态追踪

| 日期 | 完成内容 | 状态 |
|------|---------|------|
| 2026-04-28 | 完成Step2.md设计文档 | ✅ |

---

*版本: v1.0*
*创建日期: 2026-04-28*
*负责人: Ryan + 小R*
*状态: 设计中*
*预计工期: 4天*
*同步状态: 本地文件（不同步GitHub）*
