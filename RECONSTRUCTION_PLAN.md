# AI-Novels 数据层重构计划（世界模拟架构）

## 重构目标

完全推翻现有数据层体系，基于**世界模拟**架构重新设计：

```
创造世界 → 创造意识 → 设定情境 → 模拟生活 → 记录故事 → 文学表达
```

## 现有数据层问题

1. **4种数据库**：MySQL + MongoDB + Neo4j + ChromaDB（运维复杂）
2. **传统CRUD**：面向文档的增删改查，不支持世界模拟
3. **无时间旅行**：无法回溯历史状态
4. **无心智模型**：角色是静态数据，无记忆/信念/情感
5. **无因果链**：事件孤立，无推理链

## 新数据层架构

### 核心概念

```
┌─────────────────────────────────────────────────────────┐
│                    世界模拟数据层                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   世界状态机  │  │   角色心智   │  │   因果推理   │ │
│  │  World State │  │   Character  │  │   Causal     │ │
│  │   Machine    │  │    Mind      │  │   Reasoning  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   事实图谱    │  │   事件时间线  │  │   叙事记录   │ │
│  │   Fact Graph │  │   Timeline   │  │   Narrative  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐│
│  │              SQLite（单机版，零配置）                  ││
│  │  • 事实表（支持时间旅行）                              ││
│  │  • 实体表（角色/物品/地点）                           ││
│  │  • 心智表（记忆/信念/情感）                           ││
│  │  • 事件表（因果链）                                   ││
│  │  • 叙事表（章节/场景/对话）                           ││
│  └────────────────────────────────────────────────────┘│
│                                                          │
│  ┌────────────────────────────────────────────────────┐│
│  │              Qdrant（本地向量检索）                    ││
│  │  • 语义检索（角色状态、世界事实）                      ││
│  │  • 风格匹配（叙事风格、角色口吻）                      ││
│  │  • 相似度分析（事件相似性）                           ││
│  └────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## 数据库设计

### 1. 事实表（facts）- 世界状态机核心

```sql
CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    
    -- 事实标识
    fact_type TEXT NOT NULL, -- entity/attribute/relation/event/rule
    
    -- 事实内容（主谓宾结构）
    subject_id INTEGER NOT NULL, -- 主语实体ID
    predicate TEXT NOT NULL,     -- 谓语（属性/关系类型）
    object_value TEXT,           -- 宾语（值或目标实体ID）
    
    -- 时间范围（支持时间旅行）
    valid_from INTEGER DEFAULT (unixepoch()),
    valid_until INTEGER,         -- NULL表示当前有效
    
    -- 元数据
    confidence REAL DEFAULT 1.0, -- 置信度
    source TEXT DEFAULT 'inferred', -- observed/inferred/told/assumed
    chapter_id INTEGER,          -- 首次出现的章节
    
    -- 推理链（用于解释）
    inference_chain JSON,        -- ["event:123", "rule:456"]
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 索引
CREATE INDEX idx_facts_subject ON facts(subject_id, valid_until);
CREATE INDEX idx_facts_predicate ON facts(predicate, valid_until);
CREATE INDEX idx_facts_time ON facts(valid_from, valid_until);
```

**核心操作**：
- `set_fact(subject, predicate, value)` - 设置事实（自动处理时间范围）
- `get_fact(subject, predicate, timestamp)` - 获取事实（支持时间旅行）
- `get_entity_state(entity_id, timestamp)` - 获取实体完整状态

### 2. 实体表（entities）- 世界中的存在

```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER NOT NULL,
    
    -- 实体类型
    entity_type TEXT NOT NULL, -- character/item/location/organization
    
    -- 基础信息
    name TEXT NOT NULL,
    description TEXT,
    
    -- 动态属性（JSON）
    attributes JSON, -- {age: 19, gender: "male", martial_arts: 30}
    
    -- 初始状态（世界种子）
    initial_state JSON,
    
    created_at INTEGER DEFAULT (unixepoch())
);
```

**实体类型**：
- `character` - 角色（有心智）
- `item` - 物品（可交互）
- `location` - 地点（有属性）
- `organization` - 组织（有结构）

### 3. 角色心智表（character_minds）- 意识模拟

```sql
CREATE TABLE character_minds (
    id INTEGER PRIMARY KEY,
    character_id INTEGER REFERENCES entities(id),
    
    -- 记忆系统
    episodic_memory JSON,    -- [{event_id, emotion, importance, timestamp}]
    semantic_memory JSON,    -- {knowledge_key: value}
    emotional_memory JSON,   -- [{trigger, response, intensity}]
    
    -- 信念系统
    beliefs JSON, -- {
                  --   about_world: {"magic_exists": 0.9},
                  --   about_others: {"李逍遥": {"trust": 0.8}},
                  --   about_self: {"i_am_hero": 0.7}
                  -- }
    
    -- 情感状态
    current_emotion JSON,    -- {joy: 0.5, fear: 0.3, anger: 0.1}
    emotional_baseline JSON, -- 基线情感倾向
    
    -- 目标系统
    explicit_goals JSON,   -- [{goal: "become hero", priority: 1.0, progress: 0.3}]
    implicit_goals JSON,   -- [{goal: "find love", source: "subconscious", strength: 0.8}]
    
    -- 人格模型
    personality JSON, -- {
                      --   big_five: {openness: 0.8, conscientiousness: 0.4},
                      --   values: ["freedom", "justice"],
                      --   defenses: ["denial", "projection"]
                      -- }
    
    -- 决策历史
    decision_history JSON, -- [{situation, decision, outcome, timestamp}]
    
    updated_at INTEGER DEFAULT (unixepoch())
);
```

**核心操作**：
- `create_mind(character_id, personality, goals)` - 创建心智
- `update_mind(character_id, memory_update)` - 更新记忆
- `get_mind_state(character_id)` - 获取当前心智状态
- `add_episodic_memory(character_id, event, emotion)` - 添加情节记忆

### 4. 事件表（events）- 时间线

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    chapter_id INTEGER,
    
    -- 事件内容
    event_type TEXT, -- action/perception/decision/change
    description TEXT,
    
    -- 参与实体
    actor_id INTEGER REFERENCES entities(id),
    target_id INTEGER REFERENCES entities(id),
    
    -- 事件效果（JSON）
    effects JSON, -- {
                 --   "facts_changed": [{subject, predicate, old, new}],
                 --   "emotions_triggered": [{character, emotion, intensity}],
                 --   "goals_affected": [{goal, impact}]
                 -- }
    
    -- 因果链
    caused_by JSON, -- [event_id, ...]
    causes JSON,    -- [event_id, ...]
    
    -- 时间
    timestamp INTEGER DEFAULT (unixepoch()),
    simulation_step INTEGER,
    
    created_at INTEGER DEFAULT (unixepoch())
);
```

**核心操作**：
- `record_event(novel_id, type, description, actor, target, effects)` - 记录事件
- `get_timeline(novel_id, from_step, to_step)` - 获取时间线
- `get_causal_chain(event_id)` - 获取因果链
- `get_events_affecting(entity_id)` - 获取影响实体的事件

### 5. 叙事表（narratives）- 文学表达

```sql
CREATE TABLE narratives (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    chapter_id INTEGER,
    
    -- 叙事内容
    narrative_type TEXT, -- chapter/scene/dialogue/description
    content TEXT,
    
    -- 叙事元数据
    pov_character INTEGER, -- 视角角色
    style TEXT, -- 风格标签
    
    -- 与模拟的关联
    covers_events JSON, -- [event_id, ...]
    covers_steps JSON, -- [simulation_step, ...]
    
    -- 质量评估
    quality_score REAL,
    coherence_score REAL,
    
    created_at INTEGER DEFAULT (unixepoch())
);
```

## Agent工具封装

### WorldStateTool - 世界状态机工具

```python
class WorldStateTool:
    """
    世界状态机工具 - Agent可直接调用
    
    功能：
    1. 查询世界状态（当前/历史）
    2. 修改世界状态（设置事实）
    3. 传播效果（连锁反应）
    4. 一致性检查
    """
    
    def __init__(self, dao: WorldSimulationDAO):
        self.dao = dao
    
    def query_state(self, entity_id: int, timestamp: int = None) -> Dict:
        """查询实体状态"""
        return self.dao.get_entity_state(entity_id, timestamp)
    
    def set_state(self, entity_id: int, attribute: str, value: Any, 
                  source: str = "simulation") -> int:
        """设置实体状态（自动处理时间范围）"""
        return self.dao.set_fact(entity_id, attribute, value, source=source)
    
    def propagate_effects(self, event_id: int) -> List[int]:
        """传播事件效果（连锁反应）"""
        event = self.dao.get_event(event_id)
        changed_facts = []
        
        for effect in event.get("effects", {}).get("facts_changed", []):
            fact_id = self.dao.set_fact(
                effect["subject"], 
                effect["predicate"], 
                effect["new"],
                source="event",
                inference_chain=[f"event:{event_id}"]
            )
            changed_facts.append(fact_id)
        
        return changed_facts
    
    def check_consistency(self, novel_id: int) -> List[str]:
        """检查世界一致性"""
        issues = []
        
        # 检查：角色不能同时在两个地点
        characters = self.dao.get_entities_by_type(novel_id, "character")
        for char in characters:
            location = self.dao.get_fact(char["id"], "location")
            # ... 更多一致性规则
        
        return issues
```

### CharacterMindTool - 角色心智工具

```python
class CharacterMindTool:
    """
    角色心智工具 - Agent可直接调用
    
    功能：
    1. 获取心智状态（记忆/信念/情感/目标）
    2. 更新心智（添加记忆/改变信念/调整情感）
    3. 决策支持（基于心智状态生成决策）
    4. 感知处理（将事件转化为心智更新）
    """
    
    def __init__(self, dao: WorldSimulationDAO, llm_router: LLMRouter):
        self.dao = dao
        self.llm = llm_router
    
    def get_mind(self, character_id: int) -> Dict:
        """获取角色完整心智"""
        return self.dao.get_character_mind(character_id)
    
    def perceive_event(self, character_id: int, event_id: int) -> Dict:
        """
        角色感知事件
        
        流程：
        1. 获取事件信息
        2. 获取角色心智
        3. LLM判断：角色如何理解这个事件？
        4. 更新心智（记忆、信念、情感）
        """
        event = self.dao.get_event(event_id)
        mind = self.get_mind(character_id)
        
        # LLM生成感知结果
        prompt = f"""
        角色：{mind['character_name']}
        人格：{mind['personality']}
        当前情感：{mind['current_emotion']}
        
        事件：{event['description']}
        
        这个角色会如何理解这个事件？
        请输出：
        1. 情感反应（JSON格式）
        2. 信念更新（如果有）
        3. 记忆重要性（0-1）
        """
        
        result = self.llm.generate(prompt)
        perception = json.loads(result)
        
        # 更新心智
        self.dao.add_episodic_memory(
            character_id, event_id,
            emotion=perception["emotion"],
            importance=perception["importance"]
        )
        
        if perception.get("belief_updates"):
            self.update_beliefs(character_id, perception["belief_updates"])
        
        return perception
    
    def make_decision(self, character_id: int, situation: Dict) -> Dict:
        """
        角色做决策
        
        输入：
        - 角色心智状态
        - 当前情境（感知到的世界状态）
        - 可选行动
        
        输出：
        - 决策选择
        - 决策理由
        - 预期效果
        """
        mind = self.get_mind(character_id)
        
        prompt = f"""
        角色：{mind['character_name']}
        人格：{mind['personality']}
        目标：{mind['explicit_goals']}
        最近记忆：{mind['episodic_memory'][-3:]}
        当前情感：{mind['current_emotion']}
        
        情境：{situation}
        
        这个角色会做什么决策？
        请输出：
        1. 决策选择
        2. 决策理由（基于人格和目标的推理）
        3. 预期效果
        4. 情感变化
        """
        
        result = self.llm.generate(prompt)
        decision = json.loads(result)
        
        # 记录决策历史
        self.dao.update_character_mind(character_id, {
            "decision_history": mind.get("decision_history", []) + [{
                "situation": situation,
                "decision": decision["choice"],
                "outcome": None,  # 待填充
                "timestamp": int(time.time())
            }]
        })
        
        return decision
    
    def update_beliefs(self, character_id: int, updates: Dict):
        """更新角色信念"""
        mind = self.get_mind(character_id)
        beliefs = mind.get("beliefs", {})
        
        for category, changes in updates.items():
            if category not in beliefs:
                beliefs[category] = {}
            beliefs[category].update(changes)
        
        self.dao.update_character_mind(character_id, {"beliefs": beliefs})
```

### CausalReasoningTool - 因果推理工具

```python
class CausalReasoningTool:
    """
    因果推理工具 - Agent可直接调用
    
    功能：
    1. 追溯原因（为什么发生？）
    2. 预测后果（会发生什么？）
    3. 反事实推理（如果...会怎样？）
    4. 解释生成（向读者解释）
    """
    
    def __init__(self, dao: WorldSimulationDAO):
        self.dao = dao
    
    def trace_causes(self, event_id: int, depth: int = 3) -> List[Dict]:
        """追溯事件原因"""
        causes = []
        current = self.dao.get_event(event_id)
        
        for _ in range(depth):
            if not current or not current.get("caused_by"):
                break
            
            parent_id = current["caused_by"][0]
            parent = self.dao.get_event(parent_id)
            causes.append(parent)
            current = parent
        
        return causes
    
    def predict_consequences(self, event_id: int, steps: int = 5) -> List[Dict]:
        """预测事件后果"""
        # 基于规则+LLM的预测
        predictions = []
        
        event = self.dao.get_event(event_id)
        world_state = self.dao.get_world_state(event["novel_id"])
        
        # 规则预测
        for effect in event.get("effects", {}).get("facts_changed", []):
            # 如果角色受伤，预测健康下降
            if effect["predicate"] == "health":
                predictions.append({
                    "type": "fact",
                    "description": f"{effect['subject']}的健康状况会影响行动能力",
                    "confidence": 0.8
                })
        
        return predictions
    
    def counterfactual(self, event_id: int, alternative: str) -> Dict:
        """
        反事实推理
        
        例如：
        "如果李逍遥没有闯入仙灵岛，会发生什么？"
        """
        event = self.dao.get_event(event_id)
        
        prompt = f"""
        原始事件：{event['description']}
        反事实假设：{alternative}
        
        当前世界状态：{self.dao.get_world_state(event['novel_id'])}
        
        如果反事实成立，世界会如何发展？
        请输出：
        1. 直接变化（3个）
        2. 连锁反应（2个）
        3. 长期影响（1个）
        """
        
        result = self.llm.generate(prompt)
        return json.loads(result)
```

### NarrativeRecordTool - 叙事记录工具

```python
class NarrativeRecordTool:
    """
    叙事记录工具 - Agent可直接调用
    
    功能：
    1. 记录场景（从模拟事件生成叙事）
    2. 记录对话（从角色决策生成对话）
    3. 记录描述（世界状态文学化）
    4. 关联模拟（叙事与模拟事件的映射）
    """
    
    def __init__(self, dao: WorldSimulationDAO):
        self.dao = dao
    
    def record_scene(self, chapter_id: int, events: List[int], 
                     pov_character: int, style: str) -> int:
        """
        记录场景
        
        输入：
        - 章节ID
        - 要覆盖的模拟事件
        - 视角角色
        - 叙事风格
        
        输出：
        - 叙事片段ID
        """
        # 获取事件详情
        event_details = [self.dao.get_event(eid) for eid in events]
        
        # 获取视角角色的心智（影响叙事滤镜）
        mind = self.dao.get_character_mind(pov_character)
        
        # 生成叙事（调用LLM）
        prompt = f"""
        事件：{event_details}
        视角：{mind['character_name']}（{mind['current_emotion']}）
        风格：{style}
        
        请将这些事件转化为文学场景。
        注意：
        1. 使用视角角色的感知滤镜
        2. 展现角色的情感变化
        3. 保留事件的因果逻辑
        """
        
        narrative = self.llm.generate(prompt)
        
        # 保存叙事
        return self.dao.create_narrative(
            chapter_id=chapter_id,
            narrative_type="scene",
            content=narrative,
            pov_character=pov_character,
            style=style,
            covers_events=events
        )
    
    def record_dialogue(self, chapter_id: int, interaction: Dict) -> int:
        """
        记录对话
        
        输入：
        - 角色互动（决策结果）
        - 角色心智状态
        
        输出：
        - 对话片段
        """
        # 获取参与角色的心智
        minds = {
            char_id: self.dao.get_character_mind(char_id)
            for char_id in interaction["participants"]
        }
        
        prompt = f"""
        角色心智：{minds}
        互动情境：{interaction['situation']}
        角色决策：{interaction['decisions']}
        
        请生成对话。
        要求：
        1. 每个角色的语言符合其人格
        2. 对话推动情节发展
        3. 展现角色关系动态
        """
        
        dialogue = self.llm.generate(prompt)
        return self.dao.create_narrative(
            chapter_id=chapter_id,
            narrative_type="dialogue",
            content=dialogue
        )
```

## 实施步骤

### 步骤1：删除旧数据层（1天）
- [ ] 删除 `database/mysql_client.py`
- [ ] 删除 `database/mongodb_client.py`
- [ ] 删除 `database/neo4j_client.py`
- [ ] 删除 `database/chromadb_client.py`
- [ ] 删除 `database/*_crud.py`
- [ ] 保留 `database/base.py`（重构基类）

### 步骤2：创建新数据层（3-4天）
- [ ] 创建 `database/world_dao.py`（世界模拟DAO）
- [ ] 创建 `database/schema.sql`（新schema）
- [ ] 创建 `database/tools/`（Agent工具）
  - [ ] `world_state_tool.py`
  - [ ] `character_mind_tool.py`
  - [ ] `causal_reasoning_tool.py`
  - [ ] `narrative_record_tool.py`

### 步骤3：重构模型层（1-2天）
- [ ] 重构 `model/entities.py`（世界模拟实体）
- [ ] 新增 `model/world_state.py`（世界状态）
- [ ] 新增 `model/character_mind.py`（角色心智）
- [ ] 新增 `model/events.py`（事件）

### 步骤4：集成测试（2-3天）
- [ ] 测试世界状态机（设置/获取/时间旅行）
- [ ] 测试角色心智（记忆/决策/感知）
- [ ] 测试因果推理（追溯/预测/反事实）
- [ ] 测试叙事记录（场景/对话/描述）

## 验收标准

1. **世界状态机**：
   - [ ] 可以设置和查询事实
   - [ ] 支持时间旅行查询
   - [ ] 效果传播正确
   - [ ] 一致性检查通过

2. **角色心智**：
   - [ ] 可以创建和更新心智
   - [ ] 感知事件更新心智
   - [ ] 决策基于心智状态
   - [ ] 记忆有遗忘机制

3. **因果推理**：
   - [ ] 可以追溯事件原因
   - [ ] 可以预测事件后果
   - [ ] 反事实推理合理

4. **叙事记录**：
   - [ ] 叙事与模拟事件关联
   - [ ] 视角角色影响叙事
   - [ ] 风格一致性

---

*创建日期: 2026-04-28*
*负责人: Ryan + 小R*
*状态: 待实施*
