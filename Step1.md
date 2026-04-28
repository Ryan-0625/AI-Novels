# Step 1: 数据层重构 - 世界模拟架构（深化版）

## 1. 设计哲学

### 核心转变

```
从：数据存储 → 到：世界模拟基础设施
从：CRUD操作 → 到：因果推理、心智模拟、叙事生成
从：被动查询 → 到：主动推理、预测、反事实分析
```

### 设计原则

1. **时间是一等公民**：所有状态变化必须记录时间范围
2. **因果链不可断裂**：每个事实必须有推理链
3. **心智即数据**：角色的记忆、信念、情感都是可查的数据
4. **模拟即真相**：世界状态是模拟的结果，叙事是模拟的记录

---

## 2. 架构深化

### 2.1 六层数据模型

```
┌─────────────────────────────────────────────────────────┐
│ Layer 6: 叙事表达层 (Narrative Expression)                │
│  - 场景、对话、描述、风格                                │
│  - 与模拟事件的精确映射                                  │
├─────────────────────────────────────────────────────────┤
│ Layer 5: 模拟记录层 (Simulation Record)                  │
│  - 决策记录、行动记录、感知记录                            │
│  - 时间线、因果链                                        │
├─────────────────────────────────────────────────────────┤
│ Layer 4: 心智模拟层 (Mind Simulation)                    │
│  - 记忆系统、信念系统、情感系统                            │
│  - 决策过程、人格模型                                    │
├─────────────────────────────────────────────────────────┤
│ Layer 3: 世界状态层 (World State)                        │
│  - 事实图谱、实体关系、属性变化                            │
│  - 规则引擎、物理约束                                    │
├─────────────────────────────────────────────────────────┤
│ Layer 2: 数据持久层 (Persistence)                        │
│  - SQLite（关系+时序+JSON）                              │
│  - Qdrant（向量语义检索）                                │
│  - 文件系统（大对象存储）                                │
├─────────────────────────────────────────────────────────┤
│ Layer 1: 基础设施层 (Infrastructure)                     │
│  - 连接池、事务管理、缓存                                │
│  - 备份、迁移、监控                                      │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流设计

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   世界状态   │───→│   角色心智   │───→│   角色决策   │
│  WorldState │    │ CharacterMind│    │  Decision   │
└─────────────┘    └─────────────┘    └──────┬──────┘
       ↑                                      │
       │         ┌─────────────┐              │
       └─────────│   效果传播   │←─────────────┘
                 │  Propagation│
                 └──────┬──────┘
                        │
       ┌────────────────┘
       ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   事件记录   │───→│   因果推理   │───→│   叙事生成   │
│    Event    │    │   Causal    │    │  Narrative  │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 3. 数据库设计深化

### 3.1 事实表（facts）- 世界状态机核心

```sql
-- 启用 WAL 模式（支持并发读写）
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 事实分类
    fact_type TEXT NOT NULL CHECK (fact_type IN (
        'attribute',    -- 实体属性（位置、健康、情绪）
        'relation',      -- 实体关系（爱慕、敌对、师徒）
        'possession',    -- 拥有关系（持有物品）
        'event',         -- 事件事实（发生过的事）
        'rule',          -- 世界规则（物理法则、魔法规则）
        'inference'      -- 推理结果（推导出的结论）
    )),
    
    -- 事实内容（主谓宾结构，支持多主语多宾语）
    subject_id INTEGER NOT NULL,           -- 主语实体ID
    subject_role TEXT DEFAULT 'primary',   -- 主语角色（primary/secondary）
    predicate TEXT NOT NULL,               -- 谓语（属性/关系类型）
    object_value TEXT,                     -- 宾语值（JSON格式）
    object_entity_id INTEGER,              -- 宾语实体ID（关系类型）
    
    -- 时间范围（支持时间旅行和历史查询）
    valid_from INTEGER DEFAULT (unixepoch()),
    valid_until INTEGER,                   -- NULL表示当前有效
    
    -- 置信度和来源
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    source TEXT DEFAULT 'inferred' CHECK (source IN (
        'observed',      -- 直接观察
        'inferred',      -- 逻辑推理
        'told',          -- 他人告知
        'assumed',       -- 假设默认
        'simulated'      -- 模拟生成
    )),
    
    -- 上下文关联
    chapter_id INTEGER,                    -- 首次出现的章节
    scene_id INTEGER,                      -- 关联场景
    
    -- 推理链（JSON数组，记录推理路径）
    inference_chain JSON DEFAULT '[]',     -- ["event:123", "rule:456", "inference:789"]
    
    -- 反事实标记（用于假设分析）
    is_counterfactual INTEGER DEFAULT 0,   -- 0=真实, 1=假设
    counterfactual_branch TEXT,            -- 假设分支ID
    
    -- 元数据
    metadata JSON DEFAULT '{}',            -- 扩展信息
    
    -- 审计字段
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch()),
    created_by TEXT DEFAULT 'system',      -- 创建者（agent/用户/系统）
    
    -- 约束
    FOREIGN KEY (subject_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (object_entity_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

-- 核心索引（优化时间旅行查询）
CREATE INDEX idx_facts_subject_time ON facts(subject_id, predicate, valid_from DESC, valid_until);
CREATE INDEX idx_facts_predicate_time ON facts(predicate, valid_from DESC);
CREATE INDEX idx_facts_current ON facts(subject_id, predicate, valid_until) WHERE valid_until IS NULL;
CREATE INDEX idx_facts_chapter ON facts(chapter_id, fact_type);
CREATE INDEX idx_facts_counterfactual ON facts(counterfactual_branch, is_counterfactual);

-- 触发器：自动更新 updated_at
CREATE TRIGGER trg_facts_updated AFTER UPDATE ON facts
BEGIN
    UPDATE facts SET updated_at = unixepoch() WHERE id = NEW.id;
END;
```

**核心操作深化**：

```python
class FactManager:
    """
    事实管理器 - 世界状态机核心
    
    支持：
    1. 原子性事实设置（自动处理时间范围）
    2. 批量事实传播（连锁反应）
    3. 时间旅行查询（任意时间点状态）
    4. 反事实分析（假设推理）
    5. 一致性约束（规则检查）
    """
    
    def set_fact(
        self,
        subject_id: int,
        predicate: str,
        value: Any,
        fact_type: str = "attribute",
        confidence: float = 1.0,
        source: str = "inferred",
        chapter_id: Optional[int] = None,
        inference_chain: List[str] = None,
        auto_propagate: bool = True  # 是否自动传播效果
    ) -> Fact:
        """
        设置事实（原子操作）
        
        流程：
        1. 验证约束（规则检查）
        2. 标记旧事实为历史（设置 valid_until）
        3. 插入新事实（设置 valid_from）
        4. 触发传播（如果 auto_propagate=True）
        5. 记录推理链
        """
        now = int(datetime.now().timestamp())
        
        with self.transaction() as conn:
            # 1. 验证约束
            self._validate_constraint(subject_id, predicate, value, conn)
            
            # 2. 标记旧事实为历史
            conn.execute("""
                UPDATE facts 
                SET valid_until = ?,
                    updated_at = ?
                WHERE subject_id = ? 
                  AND predicate = ? 
                  AND valid_until IS NULL
                  AND is_counterfactual = 0
            """, (now, now, subject_id, predicate))
            
            # 3. 插入新事实
            fact = Fact(
                fact_type=fact_type,
                subject_id=subject_id,
                predicate=predicate,
                object_value=json.dumps(value),
                valid_from=now,
                confidence=confidence,
                source=source,
                chapter_id=chapter_id,
                inference_chain=json.dumps(inference_chain or [])
            )
            
            fact.id = conn.execute("""
                INSERT INTO facts 
                (fact_type, subject_id, predicate, object_value, valid_from,
                 confidence, source, chapter_id, inference_chain)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, fact.to_tuple()).lastrowid
            
            # 4. 触发传播
            if auto_propagate:
                self._propagate_effects(fact, conn)
            
            return fact
    
    def get_fact(
        self,
        subject_id: int,
        predicate: str,
        timestamp: Optional[int] = None,
        include_counterfactual: bool = False
    ) -> Optional[Fact]:
        """
        获取事实（支持时间旅行）
        
        例如：
        - get_fact(1, "location") -> 获取当前位置
        - get_fact(1, "location", 1714300000) -> 获取历史位置
        - get_fact(1, "location", include_counterfactual=True) -> 包含假设
        """
        timestamp = timestamp or int(datetime.now().timestamp())
        
        sql = """
            SELECT * FROM facts 
            WHERE subject_id = ? AND predicate = ?
              AND valid_from <= ? 
              AND (valid_until IS NULL OR valid_until > ?)
        """
        params = [subject_id, predicate, timestamp, timestamp]
        
        if not include_counterfactual:
            sql += " AND is_counterfactual = 0"
        
        sql += " ORDER BY valid_from DESC LIMIT 1"
        
        row = self.conn.execute(sql, params).fetchone()
        return Fact.from_row(row) if row else None
    
    def get_entity_state(
        self,
        entity_id: int,
        timestamp: Optional[int] = None,
        predicates: Optional[List[str]] = None
    ) -> EntityState:
        """
        获取实体完整状态（所有有效事实）
        
        例如：
        - get_entity_state(1) -> 获取角色1的当前完整状态
        - get_entity_state(1, predicates=["location", "health"]) -> 只获取特定属性
        """
        timestamp = timestamp or int(datetime.now().timestamp())
        
        sql = """
            SELECT predicate, object_value, confidence, valid_from
            FROM facts 
            WHERE subject_id = ?
              AND valid_from <= ? 
              AND (valid_until IS NULL OR valid_until > ?)
              AND is_counterfactual = 0
        """
        params = [entity_id, timestamp, timestamp]
        
        if predicates:
            placeholders = ','.join('?' * len(predicates))
            sql += f" AND predicate IN ({placeholders})"
            params.extend(predicates)
        
        sql += """
            GROUP BY predicate
            HAVING valid_from = MAX(valid_from)
        """
        
        rows = self.conn.execute(sql, params).fetchall()
        
        state = EntityState(entity_id=entity_id, timestamp=timestamp)
        for row in rows:
            state.add_fact(
                predicate=row["predicate"],
                value=json.loads(row["object_value"]),
                confidence=row["confidence"],
                since=row["valid_from"]
            )
        
        return state
    
    def propagate_effects(
        self,
        fact: Fact,
        depth: int = 3
    ) -> List[Fact]:
        """
        传播事实效果（连锁反应）
        
        例如：
        - 设置 "李逍遥.health = 0" -> 传播："李逍遥.status = dead"
        - 设置 "李逍遥.location = 仙灵岛" -> 传播："赵灵儿.perception = 发现入侵者"
        
        规则来源：
        1. 世界规则（rule类型事实）
        2. 角色心智（信念系统）
        3. 物理约束（硬编码规则）
        """
        propagated = []
        
        # 1. 应用世界规则
        rules = self._get_applicable_rules(fact)
        for rule in rules:
            new_facts = self._apply_rule(rule, fact)
            propagated.extend(new_facts)
        
        # 2. 触发角色感知（如果影响角色）
        affected_characters = self._get_affected_characters(fact)
        for char_id in affected_characters:
            perception = self._generate_perception(char_id, fact)
            if perception:
                propagated.append(perception)
        
        # 3. 递归传播（如果深度>0）
        if depth > 0:
            for new_fact in propagated:
                sub_propagated = self.propagate_effects(new_fact, depth - 1)
                propagated.extend(sub_propagated)
        
        return propagated
    
    def create_counterfactual(
        self,
        base_branch: str,
        changes: List[Tuple[int, str, Any]],  # [(subject_id, predicate, new_value), ...]
        name: str = "假设分析"
    ) -> str:
        """
        创建反事实分支（假设分析）
        
        例如：
        - create_counterfactual("主线", [(1, "location", "蜀山")], "如果李逍遥去了蜀山")
        
        用途：
        1. 探索不同剧情分支
        2. 分析角色决策影响
        3. 生成"如果...会怎样"的叙事
        """
        branch_id = f"cf_{base_branch}_{int(time.time())}"
        
        # 1. 复制当前所有事实到分支
        self.conn.execute("""
            INSERT INTO facts (
                fact_type, subject_id, predicate, object_value,
                valid_from, confidence, source, inference_chain,
                is_counterfactual, counterfactual_branch
            )
            SELECT 
                fact_type, subject_id, predicate, object_value,
                valid_from, confidence, 'copied', inference_chain,
                1, ?
            FROM facts
            WHERE is_counterfactual = 0
              AND valid_until IS NULL
        """, (branch_id,))
        
        # 2. 应用假设变化
        for subject_id, predicate, new_value in changes:
            self.set_fact(
                subject_id=subject_id,
                predicate=predicate,
                value=new_value,
                source="counterfactual",
                inference_chain=[f"branch:{branch_id}"],
                auto_propagate=False
            )
        
        # 3. 在分支内传播效果
        for subject_id, predicate, new_value in changes:
            fact = self.get_fact(subject_id, predicate, include_counterfactual=True)
            self.propagate_effects(fact)
        
        return branch_id
```

### 3.2 实体表（entities）- 世界存在

```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL,
    
    -- 实体分类（支持多级类型）
    entity_type TEXT NOT NULL,      -- 主类型：character/item/location/organization
    entity_subtype TEXT,             -- 子类型：protagonist/antagonist/weapon/magic_place
    
    -- 基础信息
    name TEXT NOT NULL,
    aliases JSON DEFAULT '[]',       -- 别名列表
    description TEXT,
    
    -- 动态属性（JSON，支持复杂结构）
    attributes JSON DEFAULT '{}',    -- {age: 19, gender: "male", martial_arts: 30}
    
    -- 初始状态（世界种子，不可变）
    initial_state JSON DEFAULT '{}',
    
    -- 生命周期
    birth_step INTEGER DEFAULT 0,    -- 诞生时间步
    death_step INTEGER,              -- 死亡时间步（NULL表示存活）
    
    -- 元数据
    tags JSON DEFAULT '[]',          -- 标签
    metadata JSON DEFAULT '{}',      -- 扩展信息
    
    -- 审计字段
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch()),
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_entities_novel ON entities(novel_id, entity_type, entity_subtype);
CREATE INDEX idx_entities_lifecycle ON entities(birth_step, death_step);
CREATE INDEX idx_entities_name ON entities(name);
```

### 3.3 角色心智表（character_minds）- 意识模拟

```sql
CREATE TABLE character_minds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL UNIQUE,
    
    -- 记忆系统（分层存储）
    episodic_memory JSON DEFAULT '[]',     -- 情节记忆（时间排序）
    -- [{event_id, emotion, importance, timestamp, decay_factor}]
    
    semantic_memory JSON DEFAULT '{}',      -- 语义记忆（知识结构）
    -- {"魔法体系": "五行相生相克", "门派关系": {"蜀山": "正派", "魔教": "反派"}}
    
    emotional_memory JSON DEFAULT '[]',     -- 情感记忆（触发-反应）
    -- [{trigger_event, emotion_type, intensity, conditioning}]
    
    procedural_memory JSON DEFAULT '{}',    -- 程序记忆（技能、习惯）
    -- {"剑法": "蜀山剑诀", "炼丹": "基础炼丹术"}
    
    -- 信念系统（概率表示）
    beliefs JSON DEFAULT '{}',
    -- {
    --   "about_world": {"magic_exists": {"value": 0.95, "evidence": ["event:123"]}},
    --   "about_others": {
    --     "李逍遥": {"trust": {"value": 0.8, "evidence": ["event:456"]}, 
    --               "love": {"value": 0.9, "evidence": ["event:789"]}}
    --   },
    --   "about_self": {"i_am_hero": {"value": 0.6, "evidence": []}}
    -- }
    
    -- 情感状态（实时）
    current_emotion JSON DEFAULT '{}',
    -- {"joy": 0.5, "fear": 0.3, "anger": 0.1, "sadness": 0.0, "surprise": 0.1}
    
    emotional_baseline JSON DEFAULT '{}',   -- 基线情感倾向（人格决定）
    -- {"joy": 0.6, "fear": 0.3} -- 天生乐观
    
    emotional_regulation REAL DEFAULT 0.5,  -- 情感调节能力（0-1）
    
    -- 目标系统（分层）
    explicit_goals JSON DEFAULT '[]',      -- 显式目标（角色自知）
    -- [{"goal": "become_hero", "priority": 1.0, "progress": 0.3, 
    --    "deadline": null, "subgoals": ["learn_sword", "defeat_demon"]}]
    
    implicit_goals JSON DEFAULT '[]',      -- 隐式目标（潜意识）
    -- [{"goal": "find_love", "source": "childhood_trauma", 
    --    "strength": 0.8, "awareness": 0.2}]
    
    -- 人格模型（大五人格 + 价值观 + 防御机制）
    personality JSON DEFAULT '{}',
    -- {
    --   "big_five": {
    --     "openness": 0.8, "conscientiousness": 0.4,
    --     "extraversion": 0.7, "agreeableness": 0.6,
    --     "neuroticism": 0.5
    --   },
    --   "values": ["freedom", "justice", "loyalty"],
    --   "defenses": ["denial", "projection"],
    --   "attachment_style": "anxious"
    -- }
    
    -- 决策历史（用于学习）
    decision_history JSON DEFAULT '[]',
    -- [{"situation": "...", "decision": "...", "outcome": "...",
    --   "satisfaction": 0.8, "timestamp": 1714300000}]
    
    -- 认知状态
    attention_focus INTEGER,                -- 当前注意力焦点（实体ID）
    awareness_radius INTEGER DEFAULT 5,   -- 感知范围（地点/事件数）
    cognitive_load REAL DEFAULT 0.0,       -- 认知负荷（0-1，影响决策质量）
    
    -- 审计字段
    updated_at INTEGER DEFAULT (unixepoch()),
    
    FOREIGN KEY (character_id) REFERENCES entities(id) ON DELETE CASCADE
);
```

**心智操作深化**：

```python
class MindManager:
    """
    心智管理器 - 角色意识模拟
    
    支持：
    1. 记忆编码（事件→记忆，含遗忘机制）
    2. 信念更新（贝叶斯更新）
    3. 情感计算（情感反应+调节）
    4. 决策生成（基于心智状态）
    5. 感知过滤（选择性注意）
    """
    
    def encode_memory(
        self,
        character_id: int,
        event_id: int,
        emotion: str,
        importance: float,
        rehearsal_count: int = 1
    ) -> Memory:
        """
        编码记忆（含遗忘机制）
        
        遗忘曲线：
        - 重要性高 → 遗忘慢
        - 情感强 → 遗忘慢
        - 复述多 → 遗忘慢
        """
        mind = self.get_mind(character_id)
        
        # 计算记忆强度（基于重要性、情感、复述）
        emotion_intensity = mind.get("current_emotion", {}).get(emotion, 0.5)
        memory_strength = importance * (1 + emotion_intensity) * (1 + rehearsal_count * 0.1)
        
        memory = Memory(
            event_id=event_id,
            emotion=emotion,
            importance=importance,
            strength=memory_strength,
            timestamp=int(time.time()),
            decay_factor=self._calculate_decay(personality=mind["personality"], emotion=emotion)
        )
        
        # 添加到情节记忆
        episodic = mind.get("episodic_memory", [])
        episodic.append(memory.to_dict())
        
        # 排序（按强度）
        episodic.sort(key=lambda m: m["strength"], reverse=True)
        
        # 遗忘：只保留前100条
        if len(episodic) > 100:
            forgotten = episodic[100:]
            episodic = episodic[:100]
            
            # 重要遗忘记录到日志
            for m in forgotten:
                if m["importance"] > 0.8:
                    self._log_important_forgetting(character_id, m)
        
        self.update_mind(character_id, {"episodic_memory": episodic})
        
        return memory
    
    def update_belief(
        self,
        character_id: int,
        belief_category: str,    # "about_world" / "about_others" / "about_self"
        belief_key: str,          # "magic_exists" / "李逍遥"
        new_evidence: Dict,       # {"value": 0.9, "confidence": 0.8, "source": "event:123"}
    ) -> Belief:
        """
        更新信念（贝叶斯更新）
        
        例如：
        - 角色看到魔法 → 更新 "magic_exists" 信念
        - 角色被背叛 → 更新 "trust" 信念
        """
        mind = self.get_mind(character_id)
        beliefs = mind.get("beliefs", {})
        
        category_beliefs = beliefs.get(belief_category, {})
        old_belief = category_beliefs.get(belief_key, {"value": 0.5, "evidence": []})
        
        # 贝叶斯更新
        old_value = old_belief["value"]
        new_value = new_evidence["value"]
        confidence = new_evidence["confidence"]
        
        # 加权平均（旧信念按证据数量加权）
        evidence_count = len(old_belief.get("evidence", []))
        weight = min(evidence_count / 10, 0.9)  # 最多0.9权重
        
        updated_value = old_value * weight + new_value * confidence * (1 - weight)
        updated_value = max(0, min(1, updated_value))  # 限制在0-1
        
        # 更新证据链
        evidence = old_belief.get("evidence", [])
        evidence.append(new_evidence["source"])
        evidence = evidence[-10:]  # 只保留最近10条证据
        
        new_belief = Belief(
            value=updated_value,
            evidence=evidence,
            last_updated=int(time.time())
        )
        
        category_beliefs[belief_key] = new_belief.to_dict()
        beliefs[belief_category] = category_beliefs
        
        self.update_mind(character_id, {"beliefs": beliefs})
        
        return new_belief
    
    def compute_emotion(
        self,
        character_id: int,
        event: Event,
        appraisal: Dict  # 认知评估结果
    ) -> EmotionState:
        """
        计算情感反应（基于OCC模型）
        
        输入：
        - 事件类型（成就、损失、威胁等）
        - 认知评估（期望、重要性、可控性）
        - 人格特征（神经质、外向性等）
        
        输出：
        - 情感状态（joy, fear, anger, sadness, surprise, disgust, trust, anticipation）
        """
        mind = self.get_mind(character_id)
        personality = mind.get("personality", {})
        baseline = mind.get("emotional_baseline", {})
        
        # OCC情感计算
        emotions = {}
        
        # 1. 愉悦度（基于期望-结果匹配）
        if appraisal.get("desirability", 0) > 0:
            emotions["joy"] = appraisal["desirability"] * (1 + personality.get("extraversion", 0.5))
        else:
            emotions["sadness"] = abs(appraisal["desirability"]) * (1 + personality.get("neuroticism", 0.5))
        
        # 2. 控制感（基于可控性评估）
        if appraisal.get("controllability", 0.5) < 0.3:
            emotions["fear"] = (1 - appraisal["controllability"]) * appraisal.get("importance", 0.5)
        
        # 3. 公平感（基于责任归因）
        if appraisal.get("blame", 0) > 0:
            emotions["anger"] = appraisal["blame"] * appraisal.get("importance", 0.5)
        
        # 4. 新奇感
        if appraisal.get("novelty", 0) > 0.7:
            emotions["surprise"] = appraisal["novelty"]
        
        # 应用基线调节
        for emotion, value in emotions.items():
            baseline_value = baseline.get(emotion, 0.5)
            emotions[emotion] = value * 0.7 + baseline_value * 0.3
        
        # 情感调节（人格特质）
        regulation = mind.get("emotional_regulation", 0.5)
        for emotion in emotions:
            emotions[emotion] *= (1 - regulation * 0.3)  # 调节能力强→情感波动小
        
        # 更新当前情感
        self.update_mind(character_id, {"current_emotion": emotions})
        
        return EmotionState(emotions)
    
    def generate_decision(
        self,
        character_id: int,
        situation: Dict,
        available_actions: List[str],
        llm_router: LLMRouter
    ) -> Decision:
        """
        生成决策（基于心智状态）
        
        流程：
        1. 感知过滤（选择性注意）
        2. 记忆检索（相关经验）
        3. 目标评估（哪个目标最相关）
        4. 情感影响（当前情感如何影响判断）
        5. LLM生成（基于以上输入）
        6. 决策记录（用于未来学习）
        """
        mind = self.get_mind(character_id)
        
        # 1. 感知过滤（基于注意力和感知范围）
        filtered_situation = self._filter_perception(
            mind.get("attention_focus"),
            mind.get("awareness_radius"),
            situation
        )
        
        # 2. 检索相关记忆
        relevant_memories = self._retrieve_relevant_memories(
            character_id,
            filtered_situation,
            top_k=5
        )
        
        # 3. 评估目标优先级（受情感影响）
        goals = mind.get("explicit_goals", [])
        prioritized_goals = self._prioritize_goals(
            goals,
            mind.get("current_emotion", {}),
            filtered_situation
        )
        
        # 4. 构建决策提示
        prompt = f"""
        # 角色决策
        
        ## 角色信息
        姓名：{mind.get('character_name', 'Unknown')}
        人格：{mind.get('personality', {})}
        当前情感：{mind.get('current_emotion', {})}
        
        ## 当前情境
        {filtered_situation}
        
        ## 相关记忆
        {relevant_memories}
        
        ## 当前目标（按优先级排序）
        {prioritized_goals}
        
        ## 可选行动
        {available_actions}
        
        ## 要求
        1. 选择最符合角色人格和目标的行动
        2. 考虑当前情感的影响
        3. 参考相关记忆的经验教训
        4. 提供决策理由（基于以上因素）
        5. 预测预期效果和情感变化
        
        请输出JSON格式：
        {{
            "choice": "选择的行动",
            "reasoning": "决策理由",
            "confidence": 0.8,
            "expected_outcome": "预期效果",
            "emotional_change": {{"joy": 0.1, "fear": -0.2}}
        }}
        """
        
        # 5. LLM生成决策
        result = llm_router.generate(prompt)
        decision = Decision.from_json(result)
        
        # 6. 记录决策历史
        history = mind.get("decision_history", [])
        history.append({
            "situation": filtered_situation,
            "decision": decision.choice,
            "outcome": None,  # 待后续更新
            "satisfaction": None,
            "timestamp": int(time.time())
        })
        
        # 限制历史长度
        if len(history) > 50:
            history = history[-50:]
        
        self.update_mind(character_id, {"decision_history": history})
        
        return decision
```

### 3.4 事件表（events）- 时间线

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL,
    chapter_id INTEGER,
    scene_id INTEGER,                      -- 关联场景
    
    -- 事件分类
    event_type TEXT NOT NULL CHECK (event_type IN (
        'action',        -- 角色行动
        'perception',    -- 角色感知
        'decision',      -- 角色决策
        'change',        -- 状态变化
        'interaction',   -- 角色互动
        'environment',   -- 环境变化
        'system'         -- 系统事件
    )),
    
    event_subtype TEXT,                     -- 子类型
    
    -- 事件内容
    description TEXT NOT NULL,              -- 自然语言描述
    structured_data JSON DEFAULT '{}',     -- 结构化数据
    
    -- 参与实体（支持多角色）
    actor_id INTEGER,                       -- 主要行动者
    target_id INTEGER,                      -- 主要目标
    participants JSON DEFAULT '[]',         -- 所有参与者 [entity_id, ...]
    
    -- 事件效果（JSON）
    effects JSON DEFAULT '{}',
    -- {
    --   "facts_changed": [{"subject": 1, "predicate": "location", "old": "余杭镇", "new": "仙灵岛"}],
    --   "emotions_triggered": [{"character": 2, "emotion": "surprise", "intensity": 0.8}],
    --   "goals_affected": [{"character": 1, "goal": "find_love", "impact": 0.5}],
    --   "beliefs_updated": [{"character": 2, "belief": "strangers_are_dangerous", "delta": 0.1}]
    -- }
    
    -- 因果链
    caused_by JSON DEFAULT '[]',            -- 前置事件 [event_id, ...]
    causes JSON DEFAULT '[]',               -- 后续事件 [event_id, ...]
    causal_strength REAL DEFAULT 1.0,       -- 因果强度（0-1）
    
    -- 时间信息
    timestamp INTEGER DEFAULT (unixepoch()),
    simulation_step INTEGER NOT NULL,       -- 模拟时间步（核心排序字段）
    duration INTEGER DEFAULT 1,             -- 事件持续时间（步数）
    
    -- 空间信息
    location_id INTEGER,                    -- 发生地点
    
    -- 叙事关联
    narrative_coverage JSON DEFAULT '[]',   -- 覆盖的叙事片段 [narrative_id, ...]
    
    -- 元数据
    importance REAL DEFAULT 0.5,           -- 重要性（0-1）
    is_significant INTEGER DEFAULT 0,      -- 是否重大事件（转折点）
    tags JSON DEFAULT '[]',                -- 标签
    
    -- 审计字段
    created_at INTEGER DEFAULT (unixepoch()),
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL,
    FOREIGN KEY (actor_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (location_id) REFERENCES entities(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX idx_events_timeline ON events(novel_id, simulation_step, timestamp);
CREATE INDEX idx_events_chapter ON events(chapter_id, event_type);
CREATE INDEX idx_events_actor ON events(actor_id, simulation_step);
CREATE INDEX idx_events_causal ON events(caused_by, causes);
CREATE INDEX idx_events_significant ON events(novel_id, is_significant, importance);
```

### 3.5 叙事表（narratives）- 文学表达

```sql
CREATE TABLE narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    
    -- 叙事分类
    narrative_type TEXT NOT NULL CHECK (narrative_type IN (
        'scene',         -- 场景（有动作、对话）
        'dialogue',      -- 纯对话
        'description',   -- 描述（环境、心理）
        'monologue',     -- 内心独白
        'transition',    -- 过渡（时间、空间）
        'summary'        -- 总结（省略叙述）
    )),
    
    -- 内容
    content TEXT NOT NULL,                  -- 文学内容
    content_structured JSON DEFAULT '{}',  -- 结构化内容（对话列表、动作列表等）
    
    -- 视角和风格
    pov_character INTEGER,                  -- 视角角色（NULL=全知视角）
    pov_type TEXT DEFAULT 'third_limited', -- 视角类型
    -- third_limited / third_omniscient / first_person / second_person
    
    style_profile JSON DEFAULT '{}',        -- 风格配置
    -- {"tone": "melancholic", "pace": "slow", "detail_level": "high"}
    
    -- 与模拟的关联（核心：叙事必须映射到模拟）
    covers_events JSON DEFAULT '[]',        -- 覆盖的模拟事件 [event_id, ...]
    covers_steps JSON DEFAULT '[]',         -- 覆盖的模拟时间步 [step, ...]
    covers_facts JSON DEFAULT '[]',         -- 涉及的事实 [fact_id, ...]
    
    -- 叙事功能
    plot_function TEXT,                     -- 情节功能
    -- exposition / rising_action / climax / falling_action / resolution
    
    emotional_arc JSON DEFAULT '{}',        -- 情感弧线
    -- {"start": {"joy": 0.2}, "end": {"joy": 0.8}, "peak": {"step": 5, "emotion": "joy"}}
    
    -- 质量评估
    quality_metrics JSON DEFAULT '{}',
    -- {"coherence": 0.9, "engagement": 0.8, "style_consistency": 0.85}
    
    -- 版本控制
    version INTEGER DEFAULT 1,
    previous_version INTEGER,               -- 上一个版本（修改追踪）
    
    -- 元数据
    word_count INTEGER,
    reading_time INTEGER,                   -- 预计阅读时间（秒）
    tags JSON DEFAULT '[]',
    
    -- 审计字段
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch()),
    generated_by TEXT DEFAULT 'system',      -- 生成者（agent/用户）
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    FOREIGN KEY (pov_character) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (previous_version) REFERENCES narratives(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX idx_narratives_chapter ON narratives(chapter_id, narrative_type);
CREATE INDEX idx_narratives_pov ON narratives(pov_character, narrative_type);
CREATE INDEX idx_narratives_events ON narratives(covers_events);
```

### 3.6 世界规则表（world_rules）- 约束引擎

```sql
CREATE TABLE world_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL,
    
    -- 规则定义
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN (
        'physical',      -- 物理规则（重力、时间）
        'magical',       -- 魔法规则（法术体系）
        'social',        -- 社会规则（礼仪、法律）
        'causal',        -- 因果规则（如果A则B）
        'constraint'     -- 约束规则（不能同时成立）
    )),
    
    -- 规则内容
    condition JSON NOT NULL,              -- 触发条件
    -- {"subject_type": "character", "predicate": "health", "operator": "<=", "value": 0}
    
    action JSON NOT NULL,                   -- 执行动作
    -- {"set_fact": {"subject": "self", "predicate": "status", "value": "dead"}}
    
    priority INTEGER DEFAULT 100,          -- 优先级（数字越小优先级越高）
    
    -- 规则属性
    is_active INTEGER DEFAULT 1,
    description TEXT,
    
    -- 审计字段
    created_at INTEGER DEFAULT (unixepoch()),
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
);

-- 示例规则
-- INSERT INTO world_rules (novel_id, rule_name, rule_type, condition, action, priority)
-- VALUES (1, '死亡规则', 'physical', 
--         '{"predicate": "health", "operator": "<=", "value": 0}',
--         '{"set_fact": {"predicate": "status", "value": "dead"}}',
--         10);
```

---

## 4. Agent工具深化

### 4.1 WorldStateTool - 世界状态机

```python
class WorldStateTool:
    """
    世界状态机工具 - Agent可直接调用
    
    新增功能：
    1. 批量事实操作（事务）
    2. 规则引擎集成
    3. 反事实分支管理
    4. 状态快照/恢复
    """
    
    def __init__(self, dao: WorldSimulationDAO, rule_engine: RuleEngine):
        self.dao = dao
        self.rules = rule_engine
    
    def query_state(
        self,
        entity_id: int,
        timestamp: int = None,
        predicates: List[str] = None,
        include_metadata: bool = False
    ) -> EntityState:
        """
        查询实体状态（增强版）
        
        支持：
        - 时间点查询（历史状态）
        - 属性筛选（只查特定属性）
        - 元数据包含（置信度、来源、推理链）
        """
        return self.dao.get_entity_state(
            entity_id=entity_id,
            timestamp=timestamp,
            predicates=predicates,
            include_metadata=include_metadata
        )
    
    def query_world_state(
        self,
        novel_id: int,
        timestamp: int = None,
        entity_types: List[str] = None
    ) -> WorldState:
        """
        查询完整世界状态
        
        用于：
        - 生成章节前的世界快照
        - 一致性检查
        - 反事实分析
        """
        return self.dao.get_world_state(
            novel_id=novel_id,
            timestamp=timestamp,
            entity_types=entity_types
        )
    
    def set_state(
        self,
        entity_id: int,
        attribute: str,
        value: Any,
        source: str = "simulation",
        confidence: float = 1.0,
        chapter_id: int = None,
        inference_chain: List[str] = None,
        auto_propagate: bool = True,
        transaction: bool = True
    ) -> Fact:
        """
        设置实体状态（增强版）
        
        新增：
        - 事务支持（批量操作原子性）
        - 自动传播控制
        - 推理链记录
        """
        return self.dao.set_fact(
            subject_id=entity_id,
            predicate=attribute,
            value=value,
            source=source,
            confidence=confidence,
            chapter_id=chapter_id,
            inference_chain=inference_chain,
            auto_propagate=auto_propagate,
            transaction=transaction
        )
    
    def batch_set_state(
        self,
        changes: List[Dict],
        source: str = "simulation"
    ) -> List[Fact]:
        """
        批量设置状态（事务）
        
        例如：
        - 战斗结果：多个角色同时受伤
        - 场景切换：多个角色同时移动
        """
        facts = []
        
        with self.dao.transaction():
            for change in changes:
                fact = self.set_state(
                    entity_id=change["entity_id"],
                    attribute=change["attribute"],
                    value=change["value"],
                    source=source,
                    auto_propagate=False  # 延迟传播
                )
                facts.append(fact)
            
            # 批量传播
            for fact in facts:
                self.propagate_effects(fact.id)
        
        return facts
    
    def propagate_effects(
        self,
        fact_id: int,
        depth: int = 3,
        visited: Set[int] = None
    ) -> List[Fact]:
        """
        传播效果（增强版）
        
        新增：
        - 传播深度控制
        - 循环检测
        - 规则引擎集成
        """
        if visited is None:
            visited = set()
        
        if fact_id in visited or depth <= 0:
            return []
        
        visited.add(fact_id)
        
        fact = self.dao.get_fact(fact_id)
        propagated = []
        
        # 1. 应用世界规则
        applicable_rules = self.rules.find_applicable(fact)
        for rule in applicable_rules:
            new_facts = self.rules.apply(rule, fact)
            propagated.extend(new_facts)
        
        # 2. 触发角色感知
        affected = self._get_affected_characters(fact)
        for char_id in affected:
            perception = self._generate_perception(char_id, fact)
            if perception:
                propagated.append(perception)
        
        # 3. 递归传播
        for new_fact in propagated:
            sub_propagated = self.propagate_effects(
                new_fact.id,
                depth - 1,
                visited
            )
            propagated.extend(sub_propagated)
        
        return propagated
    
    def create_branch(
        self,
        name: str,
        base_state: int = None,
        changes: List[Dict] = None
    ) -> str:
        """
        创建反事实分支
        
        用途：
        - 探索不同剧情分支
        - 分析角色决策影响
        - 生成"如果...会怎样"的叙事
        """
        return self.dao.create_counterfactual(
            base_branch="main" if base_state is None else f"state_{base_state}",
            changes=changes or [],
            name=name
        )
    
    def compare_branches(
        self,
        branch_a: str,
        branch_b: str,
        entity_id: int = None
    ) -> Dict:
        """
        比较两个分支的差异
        
        输出：
        - 事实差异
        - 事件差异
        - 角色状态差异
        """
        return self.dao.compare_counterfactuals(branch_a, branch_b, entity_id)
    
    def save_snapshot(
        self,
        novel_id: int,
        name: str,
        simulation_step: int = None
    ) -> int:
        """
        保存世界状态快照
        
        用于：
        - 章节生成前的状态保存
        - 快速回滚
        - 分支创建
        """
        state = self.query_world_state(novel_id, simulation_step=simulation_step)
        return self.dao.save_snapshot(novel_id, name, state)
    
    def load_snapshot(self, snapshot_id: int) -> WorldState:
        """加载世界状态快照"""
        return self.dao.load_snapshot(snapshot_id)
```

### 4.2 CharacterMindTool - 角色心智

```python
class CharacterMindTool:
    """
    角色心智工具（深化版）
    
    新增功能：
    1. 记忆检索（语义+时序+情感）
    2. 信念推理（链式推理）
    3. 情感预测（预期情感）
    4. 人格一致性检查
    """
    
    def __init__(
        self,
        dao: WorldSimulationDAO,
        llm_router: LLMRouter,
        vector_store: VectorStore
    ):
        self.dao = dao
        self.llm = llm_router
        self.vector = vector_store
    
    def retrieve_memories(
        self,
        character_id: int,
        query: str,
        retrieval_type: str = "mixed",
        top_k: int = 5
    ) -> List[Memory]:
        """
        检索记忆（多策略）
        
        策略：
        - "semantic": 语义相似度（向量检索）
        - "temporal": 时间邻近性（最近事件）
        - "emotional": 情感关联性（同情感色彩）
        - "mixed": 混合策略（默认）
        """
        mind = self.get_mind(character_id)
        memories = mind.get("episodic_memory", [])
        
        if retrieval_type == "semantic":
            # 向量检索
            return self._semantic_retrieval(character_id, query, top_k)
        
        elif retrieval_type == "temporal":
            # 时间排序（最近优先）
            return sorted(memories, key=lambda m: m["timestamp"], reverse=True)[:top_k]
        
        elif retrieval_type == "emotional":
            # 情感匹配
            current_emotion = mind.get("current_emotion", {})
            return self._emotional_retrieval(memories, current_emotion, top_k)
        
        else:  # mixed
            # 混合评分
            scored = []
            for memory in memories:
                score = (
                    self._semantic_score(memory, query) * 0.4 +
                    self._temporal_score(memory) * 0.3 +
                    self._emotional_score(memory, current_emotion) * 0.3
                )
                scored.append((score, memory))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            return [m for _, m in scored[:top_k]]
    
    def infer_belief(
        self,
        character_id: int,
        belief_category: str,
        belief_key: str,
        reasoning_depth: int = 2
    ) -> Belief:
        """
        推理信念（链式推理）
        
        例如：
        - "李逍遥是否值得信任？"
        - 检索相关记忆 → 统计信任行为 → 计算概率
        """
        mind = self.get_mind(character_id)
        
        # 1. 直接检索
        direct_belief = self._get_direct_belief(mind, belief_category, belief_key)
        if direct_belief and direct_belief.confidence > 0.8:
            return direct_belief
        
        # 2. 推理检索
        related_memories = self.retrieve_memories(
            character_id,
            query=f"{belief_category} {belief_key}",
            retrieval_type="semantic",
            top_k=10
        )
        
        # 3. LLM推理
        prompt = f"""
        基于以下记忆，判断角色对"{belief_key}"的信念：
        
        记忆：{related_memories}
        
        请输出：
        1. 信念值（0-1）
        2. 推理过程
        3. 置信度
        """
        
        result = self.llm.generate(prompt)
        inferred = Belief.from_json(result)
        
        # 4. 缓存推理结果
        self.update_belief(character_id, belief_category, belief_key, {
            "value": inferred.value,
            "confidence": inferred.confidence * 0.8,  # 推理降低置信度
            "source": "inferred"
        })
        
        return inferred
    
    def predict_emotion(
        self,
        character_id: int,
        hypothetical_event: Dict
    ) -> EmotionState:
        """
        预测情感（假设事件）
        
        用途：
        - 角色决策前的情感预期
        - 叙事张力计算
        - 读者情感预测
        """
        mind = self.get_mind(character_id)
        
        # 1. 评估事件
        appraisal = self._appraise_event(character_id, hypothetical_event)
        
        # 2. 计算预期情感
        predicted = self.compute_emotion(character_id, hypothetical_event, appraisal)
        
        # 3. 考虑情感调节
        regulation = mind.get("emotional_regulation", 0.5)
        for emotion, value in predicted.emotions.items():
            baseline = mind.get("emotional_baseline", {}).get(emotion, 0.5)
            predicted.emotions[emotion] = baseline + (value - baseline) * (1 - regulation)
        
        return predicted
    
    def check_consistency(
        self,
        character_id: int,
        proposed_action: str
    ) -> ConsistencyReport:
        """
        检查人格一致性
        
        例如：
        - 善良角色提议杀人 → 不一致警告
        - 胆小角色提议冒险 → 低一致性
        """
        mind = self.get_mind(character_id)
        personality = mind.get("personality", {})
        
        prompt = f"""
        角色人格：{personality}
        角色价值观：{personality.get('values', [])}
        
        提议行动：{proposed_action}
        
        请评估该行动与人格的一致性：
        1. 一致性评分（0-1）
        2. 冲突点（如果有）
        3. 需要的动机强度
        4. 可能的内心挣扎
        """
        
        result = self.llm.generate(prompt)
        return ConsistencyReport.from_json(result)
```

### 4.3 CausalReasoningTool - 因果推理

```python
class CausalReasoningTool:
    """
    因果推理工具（深化版）
    
    新增功能：
    1. 多路径追溯（支持汇聚/分叉）
    2. 概率预测（不确定性建模）
    3. 反事实对比（A/B分支分析）
    4. 解释生成（自然语言解释）
    """
    
    def __init__(self, dao: WorldSimulationDAO, llm_router: LLMRouter):
        self.dao = dao
        self.llm = llm_router
    
    def trace_causes(
        self,
        event_id: int,
        depth: int = 3,
        strategy: str = "primary"
    ) -> CausalTree:
        """
        追溯原因（多策略）
        
        策略：
        - "primary": 主路径（最强因果链）
        - "all": 所有路径（支持汇聚）
        - "necessary": 必要条件（缺一不可）
        - "sufficient": 充分条件（任一即可）
        """
        event = self.dao.get_event(event_id)
        
        if strategy == "primary":
            return self._trace_primary_causes(event, depth)
        elif strategy == "all":
            return self._trace_all_causes(event, depth)
        elif strategy == "necessary":
            return self._trace_necessary_causes(event, depth)
        else:
            return self._trace_sufficient_causes(event, depth)
    
    def predict_consequences(
        self,
        event_id: int,
        steps: int = 5,
        model: str = "rule_based"  # "rule_based" / "llm" / "hybrid"
    ) -> List[PredictedEvent]:
        """
        预测后果（多模型）
        
        模型：
        - "rule_based": 基于规则快速预测
        - "llm": LLM深度推理
        - "hybrid": 规则+LLM（默认）
        """
        if model == "rule_based":
            return self._rule_based_prediction(event_id, steps)
        elif model == "llm":
            return self._llm_prediction(event_id, steps)
        else:
            # hybrid: 规则快速筛选 + LLM深度分析
            rule_based = self._rule_based_prediction(event_id, steps)
            return self._llm_refine_prediction(event_id, rule_based)
    
    def generate_explanation(
        self,
        event_id: int,
        audience: str = "reader",  # "reader" / "character" / "author"
        depth: str = "simple"      # "simple" / "detailed" / "technical"
    ) -> str:
        """
        生成因果解释（自然语言）
        
        受众：
        - "reader": 读者友好，文学化
        - "character": 角色视角，主观
        - "author": 作者视角，技术化
        """
        causes = self.trace_causes(event_id, depth=3)
        consequences = self.predict_consequences(event_id, steps=3)
        
        prompt = f"""
        事件：{self.dao.get_event(event_id)['description']}
        
        原因链：{causes}
        预期后果：{consequences}
        
        受众：{audience}
        深度：{depth}
        
        请生成{depth}的因果解释，面向{audience}。
        """
        
        return self.llm.generate(prompt)
    
    def analyze_what_if(
        self,
        event_id: int,
        modification: Dict,
        compare_depth: int = 5
    ) -> WhatIfAnalysis:
        """
        深度"如果"分析
        
        例如：
        - "如果李逍遥没有闯入仙灵岛"
        - 创建分支 → 模拟发展 → 对比差异
        """
        # 1. 创建反事实分支
        branch_id = self.dao.create_counterfactual(
            base_branch="main",
            changes=[(modification["subject"], modification["predicate"], modification["value"])],
            name=f"what_if_{event_id}"
        )
        
        # 2. 模拟分支发展
        self._simulate_branch(branch_id, steps=compare_depth)
        
        # 3. 对比差异
        comparison = self.dao.compare_counterfactuals("main", branch_id)
        
        return WhatIfAnalysis(
            original_event=event_id,
            modification=modification,
            branch_id=branch_id,
            comparison=comparison,
            key_differences=self._extract_key_differences(comparison)
        )
```

### 4.4 NarrativeRecordTool - 叙事记录

```python
class NarrativeRecordTool:
    """
    叙事记录工具（深化版）
    
    新增功能：
    1. 多视角叙事（同一事件不同视角）
    2. 情感弧线追踪
    3. 节奏控制（详略得当）
    4. 风格一致性检查
    """
    
    def __init__(
        self,
        dao: WorldSimulationDAO,
        llm_router: LLMRouter,
        style_manager: StyleManager
    ):
        self.dao = dao
        self.llm = llm_router
        self.style = style_manager
    
    def record_scene(
        self,
        chapter_id: int,
        events: List[int],
        pov_character: int = None,
        style_profile: Dict = None,
        pacing: str = "normal"  # "fast" / "normal" / "slow"
    ) -> Narrative:
        """
        记录场景（增强版）
        
        新增：
        - 节奏控制（详略）
        - 多角色感知整合
        - 情感弧线追踪
        """
        # 1. 获取事件详情
        event_details = [self.dao.get_event(eid) for eid in events]
        
        # 2. 确定视角
        if pov_character:
            mind = self.dao.get_character_mind(pov_character)
            pov_type = "third_limited"
        else:
            mind = None
            pov_type = "third_omniscient"
        
        # 3. 获取风格配置
        style = style_profile or self.style.get_default_style()
        
        # 4. 根据节奏调整细节级别
        detail_level = {"fast": "low", "normal": "medium", "slow": "high"}[pacing]
        
        # 5. 生成叙事
        prompt = f"""
        # 场景生成
        
        ## 事件序列
        {event_details}
        
        ## 视角
        类型：{pov_type}
        角色：{mind['character_name'] if mind else '全知'}
        当前情感：{mind['current_emotion'] if mind else 'N/A'}
        
        ## 风格
        {style}
        
        ## 节奏
        速度：{pacing}
        细节级别：{detail_level}
        
        ## 要求
        1. 按{detail_level}细节级别描写
        2. 展现{pov_type}视角的特点
        3. 保持{style['tone']}的基调
        4. 控制节奏为{pacing}
        5. 情感弧线：从{event_details[0]['emotions']}到{event_details[-1]['emotions']}
        """
        
        content = self.llm.generate(prompt)
        
        # 6. 情感弧线计算
        emotional_arc = self._compute_emotional_arc(event_details, mind)
        
        # 7. 保存叙事
        narrative = self.dao.create_narrative(
            chapter_id=chapter_id,
            narrative_type="scene",
            content=content,
            content_structured=self._structure_content(content),
            pov_character=pov_character,
            pov_type=pov_type,
            style_profile=style,
            covers_events=events,
            emotional_arc=emotional_arc,
            plot_function=self._determine_plot_function(event_details),
            word_count=len(content),
            generated_by="narrative_engine"
        )
        
        return narrative
    
    def record_multi_pov_scene(
        self,
        chapter_id: int,
        events: List[int],
        pov_characters: List[int],
        transition_style: str = "sequential"  # "sequential" / "interleaved" / "parallel"
    ) -> List[Narrative]:
        """
        多视角场景（同一事件，多个视角）
        
        例如：
        - 战斗场景：双方视角
        - 误会场景：双方误解
        """
        narratives = []
        
        if transition_style == "sequential":
            # 顺序叙述（一个视角接另一个）
            for char_id in pov_characters:
                narrative = self.record_scene(chapter_id, events, char_id)
                narratives.append(narrative)
        
        elif transition_style == "interleaved":
            # 交织叙述（切换视角）
            narrative = self._generate_interleaved(events, pov_characters)
            narratives.append(narrative)
        
        else:  # parallel
            # 并行叙述（同时展现）
            narrative = self._generate_parallel(events, pov_characters)
            narratives.append(narrative)
        
        return narratives
    
    def check_style_consistency(
        self,
        chapter_id: int,
        tolerance: float = 0.8
    ) -> StyleReport:
        """
        检查风格一致性
        
        检查项：
        - 口吻一致性（角色语言风格）
        - 基调一致性（情感色彩）
        - 节奏一致性（叙事速度）
        - 细节一致性（描写密度）
        """
        narratives = self.dao.get_chapter_narratives(chapter_id)
        
        metrics = {
            "tone_consistency": self._check_tone(narratives),
            "pacing_consistency": self._check_pacing(narratives),
            "detail_consistency": self._check_detail(narratives),
            "voice_consistency": self._check_voice(narratives)
        }
        
        overall = sum(metrics.values()) / len(metrics)
        
        return StyleReport(
            metrics=metrics,
            overall=overall,
            is_consistent=overall >= tolerance,
            suggestions=self._generate_suggestions(metrics) if overall < tolerance else []
        )
```

---

## 5. 实施计划（细化）

### 5.1 删除旧数据层（Day 1）

```bash
# 删除文件
rm src/deepnovel/database/mysql_client.py
rm src/deepnovel/database/mongodb_client.py
rm src/deepnovel/database/neo4j_client.py
rm src/deepnovel/database/chromadb_client.py
rm src/deepnovel/database/mysql_crud.py
rm src/deepnovel/database/mongodb_crud.py
rm src/deepnovel/database/neo4j_crud.py
rm src/deepnovel/database/chromadb_crud.py
rm src/deepnovel/database/connection_pool.py
rm src/deepnovel/database/optimized_clients.py

# 保留文件
# database/base.py - 重构基类
# database/orm.py - 重构ORM
# database/migrations.py - 保留迁移历史
```

### 5.2 创建新Schema（Day 1-2）

```sql
-- 执行顺序
1. novels.sql          -- 小说表（基础）
2. entities.sql        -- 实体表
3. facts.sql           -- 事实表（核心）
4. character_minds.sql -- 心智表
5. events.sql          -- 事件表
6. narratives.sql     -- 叙事表
7. world_rules.sql     -- 规则表
8. snapshots.sql       -- 快照表
9. indexes.sql         -- 所有索引
10. triggers.sql       -- 所有触发器
```

### 5.3 实现核心DAO（Day 2-4）

```python
# 文件结构
database/
├── __init__.py
├── base.py                    # 重构基类（简化）
├── schema.sql                 # 完整Schema
├── world_dao.py              # 世界模拟DAO（核心）
│   ├── fact_manager.py        # 事实管理
│   ├── entity_manager.py      # 实体管理
│   ├── mind_manager.py        # 心智管理
│   ├── event_manager.py       # 事件管理
│   └── snapshot_manager.py   # 快照管理
├── tools/                     # Agent工具
│   ├── __init__.py
│   ├── world_state_tool.py    # 世界状态机
│   ├── character_mind_tool.py # 角色心智
│   ├── causal_reasoning_tool.py # 因果推理
│   └── narrative_record_tool.py # 叙事记录
└── vector/                    # 向量存储
    ├── __init__.py
    └── qdrant_store.py        # Qdrant封装
```

### 5.4 实现Agent工具（Day 4-6）

```python
# 每个工具的实现步骤
1. 定义工具接口（输入/输出）
2. 实现核心逻辑
3. 集成LLM调用
4. 添加错误处理
5. 编写单元测试
```

### 5.5 集成测试（Day 6-8）

```python
# 测试场景
1. 创建小说 + 世界种子
2. 创建角色 + 初始状态
3. 创建角色心智 + 人格
4. 模拟事件（角色决策）
5. 传播效果（世界状态变化）
6. 更新心智（记忆/信念/情感）
7. 生成叙事（场景/对话）
8. 验证因果链
9. 反事实分析
10. 快照/恢复
```

---

## 6. 验收标准（量化）

### 6.1 功能验收

| 功能 | 测试场景 | 通过标准 |
|------|---------|---------|
| 事实设置 | 设置角色位置 | 旧事实自动标记历史，新事实生效 |
| 时间旅行 | 查询10步前的状态 | 返回准确的历史状态 |
| 效果传播 | 角色受伤→健康下降 | 自动传播3层，记录推理链 |
| 心智感知 | 事件→情感反应 | 情感变化符合人格特征 |
| 决策生成 | 角色面对选择 | 决策符合目标+情感+记忆 |
| 因果追溯 | 查询事件原因 | 追溯到3层前因 |
| 反事实 | 假设角色未死亡 | 生成分支，模拟发展 |
| 叙事生成 | 事件→场景 | 叙事覆盖所有事件，风格一致 |

### 6.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 事实查询 | <10ms | 1000次随机查询 |
| 状态恢复 | <50ms | 加载100实体状态 |
| 效果传播 | <100ms | 传播5层深度 |
| 心智决策 | <2s | 包含LLM调用 |
| 叙事生成 | <5s | 生成1000字场景 |

### 6.3 质量验收

| 指标 | 目标 | 评估方法 |
|------|------|---------|
| 一致性 | >95% | 100次随机检查 |
| 因果合理性 | >90% | 人工评估20个因果链 |
| 决策合理性 | >85% | 人工评估20个决策 |
| 叙事质量 | >80% | 人工评估10个场景 |

---

## 7. 风险与应对

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| Schema设计缺陷 | 中 | 高 | 预留扩展字段，支持迁移 |
| 性能瓶颈 | 中 | 中 | 预计算+缓存+索引优化 |
| LLM调用成本 | 高 | 中 | 本地模型+缓存+批量 |
| 心智模型不准确 | 高 | 高 | 迭代优化+人工反馈 |
| 因果链断裂 | 中 | 高 | 强制验证+自动修复 |

---

## 8. 附录

### 8.1 术语表

| 术语 | 定义 |
|------|------|
| 事实（Fact） | 世界状态的断言，带时间范围 |
| 实体（Entity） | 世界中的存在（角色/物品/地点） |
| 心智（Mind） | 角色的认知状态（记忆/信念/情感） |
| 事件（Event） | 世界中的变化，带因果链 |
| 叙事（Narrative） | 事件的文学表达 |
| 反事实（Counterfactual） | 假设分支，用于分析 |
| 推理链（Inference Chain） | 事实的推导路径 |

### 8.2 参考文档

- `REFACTOR_PLAN.md` - 整体重构计划
- `WORLD_SIMULATION_FEASIBILITY.md` - 可行性分析
- `NOVEL_GENERATION_ARCHITECTURE.md` - 架构设计

## 9. 实施状态追踪

| 日期 | 完成内容 | 状态 |
|------|---------|------|
| 2026-04-28 | 完成Step1.md设计文档 | ✅ |

---

*版本: v1.0（深化版）*
*创建日期: 2026-04-28*
*更新日期: 2026-04-28*
*负责人: Ryan + 小R*
*状态: 设计中*
*预计工期: 8天*
