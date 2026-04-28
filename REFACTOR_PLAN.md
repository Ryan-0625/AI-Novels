# AI-Novels 重构优化计划（融合世界模拟架构）

## 项目定位

**单机版智能小说生成系统** —— 不追求吞吐量，追求单章质量。核心哲学：

> "慢即是快" —— 通过缩小生成粒度、强制检索-生成-更新循环、实时持久化，实现更高的小说质量。

---

## 核心架构升级：从"文本工程"到"世界模拟"

基于世界模拟的可行性分析，将重构方向升级为**世界模拟架构**：

```
创造世界 → 创造意识 → 设定情境 → 模拟生活 → 记录故事 → 文学表达
```

### 新架构层次

```
┌─────────────────────────────────────────────────────────────────┐
│                      文学表达层 (Expression)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   叙事引擎    │  │   风格模拟   │  │   润色优化   │          │
│  │  Narrative   │  │   Style      │  │   Polish     │          │
│  │   Engine     │  │  Simulator   │  │   Engine     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                      模拟记录层 (Simulation)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   事件记录    │  │   视角选择   │  │   详略控制   │          │
│  │   Event Log  │  │   POV Select │  │   Pacing     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                      世界模拟层 (World Sim)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   世界状态机  │  │   角色心智   │  │   情节引力   │          │
│  │  World State │  │   Character  │  │   Plot       │          │
│  │   Machine    │  │    Mind      │  │   Gravity    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                      基础设施层 (Infrastructure)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   数据层      │  │   任务管理   │  │   上下文管理  │          │
│  │   SQLite+    │  │   Visual     │  │   Context    │          │
│  │   Qdrant     │  │   Task Mgr   │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 架构演进关系

| 层级 | 传统架构 | 世界模拟架构 | 升级重点 |
|------|---------|------------|---------|
| 数据层 | 4种数据库 | SQLite+Qdrant | 精简+本地 |
| 任务层 | 简单队列 | 可视化状态机 | 可暂停恢复 |
| 上下文 | RAG检索 | 世界状态+心智 | 语义→模拟 |
| 生成层 | 模板填充 | 模拟→叙事 | 涌现创意 |
| 质量层 | 事后检查 | 实时一致性 | 内在逻辑 |

---

## 第一阶段：数据层重构（2-3周）—— 世界模拟基础

### 1.0 设计目标

为世界模拟提供数据支撑：
- **世界状态存储**：事实图谱 + 时间旅行
- **角色心智存储**：记忆系统 + 信念系统
- **事件时间线**：完整的因果链
- **上下文片段**：支持语义检索

### 1.1 数据库选型精简

当前：MySQL + MongoDB + Neo4j + ChromaDB（4种）

**目标：SQLite + Qdrant（本地向量）**

```
┌─────────────────────────────────────────┐
│           单机版数据架构                  │
│                                          │
│  ┌──────────────┐  ┌──────────────┐    │
│  │   SQLite     │  │   Qdrant     │    │
│  │   (关系+文档) │  │   (向量)      │    │
│  │              │  │              │    │
│  │ • 小说/章节   │  │ • 语义检索    │    │
│  │ • 角色/关系   │  │ • 风格匹配    │    │
│  │ • 任务/配置   │  │ • 相似度分析  │    │
│  │ • JSON文档    │  │ • 上下文召回  │    │
│  └──────────────┘  └──────────────┘    │
│                                          │
│  ┌──────────────┐  ┌──────────────┐    │
│  │   本地文件    │  │   内存缓存    │    │
│  │   (大对象)    │  │   (LRU)      │    │
│  │              │  │              │    │
│  │ • 章节内容    │  │ • 热数据      │    │
│  │ • 生成历史    │  │ • 会话状态    │    │
│  │ • 检查点      │  │ • 向量缓冲    │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
```

**为什么这样选：**
- SQLite：零配置、单文件、支持 JSON、足够单机使用
- Qdrant：本地模式、高性能向量检索、支持过滤
- 本地文件：章节内容等大文本直接存文件，SQLite 只存元数据和索引
- 内存缓存：热数据 LRU 缓存，避免重复查库

### 1.2 SQLite 详细设计 —— 世界模拟专用

```sql
-- 启用 WAL 模式（支持并发读写）
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- 小说表
CREATE TABLE novels (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    genre TEXT,
    status TEXT DEFAULT 'draft', -- draft/outline/writing/completed
    config JSON, -- 生成配置
    summary TEXT, -- 故事梗概
    premise TEXT, -- 核心设定（世界模拟种子）
    world_seed JSON, -- 世界初始状态
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- 章节表（核心）
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER REFERENCES novels(id),
    number INTEGER NOT NULL,
    title TEXT,
    status TEXT DEFAULT 'pending', -- pending/generating/completed/revised
    
    -- 内容引用（实际内容存文件）
    content_path TEXT, -- 文件路径
    content_hash TEXT, -- 校验
    
    -- 生成元数据
    generation_log JSON, -- [{step, timestamp, duration, model, tokens}]
    version INTEGER DEFAULT 1,
    
    -- 质量评估
    quality_score REAL,
    coherence_score REAL,
    
    -- 上下文快照（生成时的完整上下文）
    context_snapshot JSON,
    
    -- 模拟关联
    simulation_step INTEGER, -- 对应模拟时间步
    
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch()),
    
    UNIQUE(novel_id, number)
);

-- 实体表（世界模拟核心：角色、物品、地点等）
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER REFERENCES novels(id),
    entity_type TEXT NOT NULL, -- character/item/location/organization
    name TEXT NOT NULL,
    description TEXT,
    
    -- 动态属性（JSON）
    attributes JSON,
    
    -- 初始状态（世界种子）
    initial_state JSON,
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 事实表（世界状态机核心）
CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    fact_type TEXT NOT NULL, -- entity/attribute/relation/event/rule
    
    -- 事实内容
    subject_id INTEGER REFERENCES entities(id), -- 主语实体
    predicate TEXT NOT NULL, -- 谓语（属性/关系类型）
    object_value TEXT, -- 宾语（值或目标实体ID）
    
    -- 时间范围（支持时间旅行）
    valid_from INTEGER DEFAULT (unixepoch()),
    valid_until INTEGER, -- NULL表示当前有效
    
    -- 元数据
    confidence REAL DEFAULT 1.0, -- 置信度
    source TEXT DEFAULT 'inferred', -- observed/inferred/told/assumed
    chapter_id INTEGER REFERENCES chapters(id), -- 首次出现的章节
    
    -- 推理链（用于解释）
    inference_chain JSON,
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 关系表（实体间关系）
CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    from_entity INTEGER REFERENCES entities(id),
    to_entity INTEGER REFERENCES entities(id),
    relation_type TEXT NOT NULL, -- romantic/rivalry/family/mentor
    dynamics TEXT, -- 动态描述
    intensity REAL DEFAULT 0.5, -- 0-1
    
    -- 发展弧线
    development JSON, -- [{chapter, stage, tension}]
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 事件表（时间线）
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    chapter_id INTEGER REFERENCES chapters(id),
    
    -- 事件内容
    event_type TEXT, -- action/perception/decision/change
    description TEXT,
    
    -- 参与实体
    actor_id INTEGER REFERENCES entities(id),
    target_id INTEGER REFERENCES entities(id),
    
    -- 事件效果（JSON）
    effects JSON,
    
    -- 时间
    timestamp INTEGER DEFAULT (unixepoch()),
    simulation_step INTEGER,
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 角色心智表
CREATE TABLE character_minds (
    id INTEGER PRIMARY KEY,
    character_id INTEGER REFERENCES entities(id),
    
    -- 记忆系统
    episodic_memory JSON, -- [{event_id, emotion, importance}]
    semantic_memory JSON, -- {knowledge_key: value}
    emotional_memory JSON, -- [{trigger, response, intensity}]
    
    -- 信念系统
    beliefs JSON, -- {about_world: {}, about_others: {}, about_self: {}}
    
    -- 情感状态
    current_emotion JSON, -- {joy: 0.5, fear: 0.3, ...}
    emotional_baseline JSON, -- 基线情感倾向
    
    -- 目标系统
    explicit_goals JSON, -- [{goal, priority, progress}]
    implicit_goals JSON, -- [{goal, source, strength}]
    
    -- 人格模型
    personality JSON, -- {big_five: {}, values: [], defenses: []}
    
    -- 决策历史
    decision_history JSON, -- [{situation, decision, outcome}]
    
    updated_at INTEGER DEFAULT (unixepoch())
);

-- 上下文片段表（向量检索源）
CREATE TABLE context_fragments (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    fragment_type TEXT, -- chapter_summary/character_state/world_fact/dialogue_sample
    
    -- 内容
    content TEXT,
    content_hash TEXT,
    
    -- 元数据（用于过滤）
    metadata JSON, -- {chapter, character, location, ...}
    
    -- 向量ID（Qdrant中的ID）
    vector_id TEXT,
    
    -- 重要性
    importance REAL DEFAULT 0.5,
    
    -- 使用统计
    retrieval_count INTEGER DEFAULT 0,
    last_retrieved INTEGER,
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 生成任务表（可视化任务管理核心）
CREATE TABLE generation_tasks (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    chapter_id INTEGER,
    
    -- 任务定义
    task_type TEXT, -- generate_chapter/simulate_step/narrate/revise
    task_config JSON, -- {granularity, model, temperature, ...}
    
    -- 执行状态
    status TEXT DEFAULT 'pending', -- pending/running/paused/completed/failed
    progress REAL DEFAULT 0, -- 0-100
    
    -- 执行信息
    started_at INTEGER,
    completed_at INTEGER,
    duration INTEGER, -- 秒
    
    -- 资源使用
    tokens_used INTEGER,
    cost REAL,
    
    -- 错误信息
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- 依赖关系
    dependencies JSON, -- [task_id, ...]
    
    -- 检查点（用于恢复）
    checkpoint_data JSON,
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 配置表
CREATE TABLE app_config (
    key TEXT PRIMARY KEY,
    value JSON,
    updated_at INTEGER DEFAULT (unixepoch())
);

-- 索引
CREATE INDEX idx_facts_subject ON facts(subject_id, valid_until);
CREATE INDEX idx_facts_predicate ON facts(predicate, valid_until);
CREATE INDEX idx_facts_time ON facts(valid_from, valid_until);
CREATE INDEX idx_events_novel ON events(novel_id, timestamp);
CREATE INDEX idx_events_chapter ON events(chapter_id);
CREATE INDEX idx_entities_novel ON entities(novel_id, entity_type);
CREATE INDEX idx_relations_from ON entity_relations(from_entity);
CREATE INDEX idx_relations_to ON entity_relations(to_entity);
CREATE INDEX idx_tasks_status ON generation_tasks(status);
CREATE INDEX idx_tasks_novel ON generation_tasks(novel_id);
CREATE INDEX idx_fragments_type ON context_fragments(fragment_type, novel_id);
CREATE INDEX idx_fragments_vector ON context_fragments(vector_id);
```

### 1.3 文件存储结构 —— 世界模拟专用

```
workspace/
├── data/
│   ├── novels.db              # SQLite 主库
│   ├── vector_storage/        # Qdrant 本地存储
│   └── novels/                # 小说内容目录
│       └── {novel_id}/
│           ├── meta.json      # 小说元数据
│           ├── world_seed.json # 世界初始状态
│           ├── chapters/       # 章节内容
│           │   └── {chapter_number}/
│           │       ├── v{version}.md      # 章节正文
│           │       ├── v{version}.json    # 结构化数据（场景、对话等）
│           │       ├── generation.log     # 生成日志
│           │       └── simulation.json    # 模拟事件记录
│           ├── entities/        # 实体档案
│           │   └── {entity_id}.json       # 角色/物品/地点完整档案
│           ├── minds/           # 角色心智
│           │   └── {character_id}.json    # 记忆、信念、情感、目标
│           ├── events/          # 事件时间线
│           │   └── timeline.json          # 完整事件序列
│           └── snapshots/       # 世界状态快照
│               └── step_{number}_{timestamp}.json
```

### 1.4 世界模拟数据访问层（DAO）

```python
# src/deepnovel/database/world_dao.py
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WorldState:
    """世界状态快照"""
    simulation_step: int
    timestamp: int
    facts: List[Dict]  # 当前有效的事实
    entity_states: Dict[int, Dict]  # 实体当前状态

class WorldSimulationDAO:
    """世界模拟专用数据访问层"""
    
    def __init__(self, db_path: str = "data/novels.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库和表"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== 实体管理 ====================
    
    def create_entity(self, novel_id: int, entity_type: str, name: str,
                     description: str = "", attributes: Dict = None,
                     initial_state: Dict = None) -> int:
        """创建实体（角色、物品、地点等）"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO entities (novel_id, entity_type, name, description, 
                   attributes, initial_state)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (novel_id, entity_type, name, description,
                 json.dumps(attributes or {}), json.dumps(initial_state or {}))
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_entity(self, entity_id: int) -> Optional[Dict]:
        """获取实体"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def get_entities_by_type(self, novel_id: int, entity_type: str) -> List[Dict]:
        """按类型获取实体"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM entities WHERE novel_id = ? AND entity_type = ?",
                (novel_id, entity_type)
            ).fetchall()
            return [dict(row) for row in rows]
    
    # ==================== 事实管理（世界状态机核心） ====================
    
    def set_fact(self, subject_id: int, predicate: str, value: Any,
                fact_type: str = "attribute", confidence: float = 1.0,
                source: str = "inferred", chapter_id: Optional[int] = None,
                inference_chain: List[str] = None) -> int:
        """
        设置事实（自动处理时间范围）
        
        例如：
        set_fact(1, "location", "密室")  # 角色1的位置变为密室
        set_fact(1, "health", 80)      # 角色1的健康变为80
        """
        now = int(datetime.now().timestamp())
        
        with self._get_connection() as conn:
            # 1. 将旧事实标记为历史
            conn.execute(
                """UPDATE facts 
                   SET valid_until = ? 
                   WHERE subject_id = ? AND predicate = ? AND valid_until IS NULL""",
                (now, subject_id, predicate)
            )
            
            # 2. 插入新事实
            cursor = conn.execute(
                """INSERT INTO facts 
                   (fact_type, subject_id, predicate, object_value,
                    valid_from, confidence, source, chapter_id, inference_chain)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fact_type, subject_id, predicate, json.dumps(value),
                 now, confidence, source, chapter_id,
                 json.dumps(inference_chain or []))
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_fact(self, subject_id: int, predicate: str,
                timestamp: Optional[int] = None) -> Optional[Dict]:
        """
        获取事实（支持时间旅行）
        
        例如：
        get_fact(1, "location", 1714300000)  # 获取角色1在特定时间的位置
        """
        timestamp = timestamp or int(datetime.now().timestamp())
        
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM facts 
                   WHERE subject_id = ? AND predicate = ?
                   AND valid_from <= ? AND (valid_until IS NULL OR valid_until > ?)
                   ORDER BY valid_from DESC LIMIT 1""",
                (subject_id, predicate, timestamp, timestamp)
            ).fetchone()
            
            if row:
                result = dict(row)
                result["object_value"] = json.loads(result["object_value"])
                return result
            return None
    
    def get_entity_state(self, entity_id: int,
                        timestamp: Optional[int] = None) -> Dict:
        """获取实体完整状态（所有有效事实）"""
        timestamp = timestamp or int(datetime.now().timestamp())
        
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT predicate, object_value FROM facts 
                   WHERE subject_id = ?
                   AND valid_from <= ? AND (valid_until IS NULL OR valid_until > ?)
                   GROUP BY predicate
                   HAVING valid_from = MAX(valid_from)""",
                (entity_id, timestamp, timestamp)
            ).fetchall()
            
            state = {}
            for row in rows:
                state[row["predicate"]] = json.loads(row["object_value"])
            return state
    
    def get_world_state(self, novel_id: int,
                       timestamp: Optional[int] = None) -> WorldState:
        """获取完整世界状态（所有实体）"""
        timestamp = timestamp or int(datetime.now().timestamp())
        
        with self._get_connection() as conn:
            # 获取所有实体
            entities = conn.execute(
                "SELECT id FROM entities WHERE novel_id = ?",
                (novel_id,)
            ).fetchall()
            
            entity_states = {}
            for entity in entities:
                entity_states[entity["id"]] = self.get_entity_state(
                    entity["id"], timestamp
                )
            
            # 获取所有有效事实
            facts = conn.execute(
                """SELECT * FROM facts 
                   WHERE subject_id IN (SELECT id FROM entities WHERE novel_id = ?)
                   AND valid_from <= ? AND (valid_until IS NULL OR valid_until > ?)""",
                (novel_id, timestamp, timestamp)
            ).fetchall()
            
            return WorldState(
                simulation_step=0,  # 需要额外记录
                timestamp=timestamp,
                facts=[dict(f) for f in facts],
                entity_states=entity_states
            )
    
    # ==================== 事件管理 ====================
    
    def record_event(self, novel_id: int, event_type: str, description: str,
                    actor_id: Optional[int] = None,
                    target_id: Optional[int] = None,
                    effects: Dict = None,
                    chapter_id: Optional[int] = None,
                    simulation_step: int = 0) -> int:
        """记录事件"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO events 
                   (novel_id, chapter_id, event_type, description,
                    actor_id, target_id, effects, simulation_step)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (novel_id, chapter_id, event_type, description,
                 actor_id, target_id, json.dumps(effects or {}),
                 simulation_step)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_timeline(self, novel_id: int,
                    from_step: int = 0,
                    to_step: Optional[int] = None) -> List[Dict]:
        """获取事件时间线"""
        with self._get_connection() as conn:
            if to_step:
                rows = conn.execute(
                    """SELECT * FROM events 
                       WHERE novel_id = ? AND simulation_step BETWEEN ? AND ?
                       ORDER BY simulation_step, timestamp""",
                    (novel_id, from_step, to_step)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM events 
                       WHERE novel_id = ? AND simulation_step >= ?
                       ORDER BY simulation_step, timestamp""",
                    (novel_id, from_step)
                ).fetchall()
            
            return [dict(row) for row in rows]
    
    # ==================== 角色心智管理 ====================
    
    def create_character_mind(self, character_id: int,
                             personality: Dict,
                             initial_goals: List[Dict]) -> int:
        """创建角色心智"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO character_minds 
                   (character_id, personality, explicit_goals,
                    episodic_memory, semantic_memory, emotional_memory,
                    beliefs, current_emotion, emotional_baseline)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (character_id, json.dumps(personality), json.dumps(initial_goals),
                 json.dumps([]), json.dumps({}), json.dumps([]),
                 json.dumps({"about_world": {}, "about_others": {}, "about_self": {}}),
                 json.dumps({}), json.dumps({}))
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_character_mind(self, character_id: int) -> Optional[Dict]:
        """获取角色心智"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM character_minds WHERE character_id = ?",
                (character_id,)
            ).fetchone()
            
            if row:
                result = dict(row)
                # 解析JSON字段
                for field in ["personality", "explicit_goals", "implicit_goals",
                             "episodic_memory", "semantic_memory", "emotional_memory",
                             "beliefs", "current_emotion", "emotional_baseline",
                             "decision_history"]:
                    if result.get(field):
                        result[field] = json.loads(result[field])
                return result
            return None
    
    def update_character_mind(self, character_id: int,
                           updates: Dict) -> bool:
        """更新角色心智"""
        allowed_fields = [
            "episodic_memory", "semantic_memory", "emotional_memory",
            "beliefs", "current_emotion", "explicit_goals", "implicit_goals",
            "decision_history"
        ]
        
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(json.dumps(value))
        
        if not set_clauses:
            return False
        
        values.append(character_id)
        
        with self._get_connection() as conn:
            conn.execute(
                f"""UPDATE character_minds 
                   SET {', '.join(set_clauses)}, updated_at = unixepoch()
                   WHERE character_id = ?""",
                values
            )
            conn.commit()
            return True
    
    def add_episodic_memory(self, character_id: int, event_id: int,
                           emotion: str, importance: float = 0.5):
        """添加情节记忆"""
        mind = self.get_character_mind(character_id)
        if not mind:
            return False
        
        memory = {
            "event_id": event_id,
            "emotion": emotion,
            "importance": importance,
            "timestamp": int(datetime.now().timestamp())
        }
        
        episodic = mind.get("episodic_memory", [])
        episodic.append(memory)
        
        # 保持最近100条
        if len(episodic) > 100:
            episodic = sorted(episodic, key=lambda x: x["importance"])[-100:]
        
        return self.update_character_mind(character_id, {
            "episodic_memory": episodic
        })
    
    # ==================== 章节管理 ====================
    
    def create_chapter(self, novel_id: int, number: int, title: str,
                      simulation_step: int = 0) -> int:
        """创建章节"""
        content_path = f"data/novels/{novel_id}/chapters/{number}/"
        Path(content_path).mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO chapters 
                   (novel_id, number, title, content_path, simulation_step)
                   VALUES (?, ?, ?, ?, ?)""",
                (novel_id, number, title, content_path, simulation_step)
            )
            conn.commit()
            return cursor.lastrowid
    
    def save_chapter_simulation(self, chapter_id: int,
                                simulation_data: Dict):
        """保存章节模拟数据"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT novel_id, number, content_path FROM chapters WHERE id = ?",
                (chapter_id,)
            ).fetchone()
            
            if not row:
                raise ValueError(f"Chapter {chapter_id} not found")
            
            # 保存模拟数据
            sim_path = Path(row["content_path"]) / "simulation.json"
            sim_path.write_text(
                json.dumps(simulation_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
    
    def get_chapter_simulation(self, chapter_id: int) -> Optional[Dict]:
        """获取章节模拟数据"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT content_path FROM chapters WHERE id = ?",
                (chapter_id,)
            ).fetchone()
            
            if not row:
                return None
            
            sim_path = Path(row["content_path"]) / "simulation.json"
            if sim_path.exists():
                return json.loads(sim_path.read_text(encoding="utf-8"))
            return None
    
    # ==================== 快照管理 ====================
    
    def save_world_snapshot(self, novel_id: int, simulation_step: int,
                           state: WorldState) -> str:
        """保存世界状态快照"""
        snapshot_dir = Path(f"data/novels/{novel_id}/snapshots")
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot_path = snapshot_dir / f"step_{simulation_step}_{state.timestamp}.json"
        snapshot_path.write_text(
            json.dumps({
                "simulation_step": state.simulation_step,
                "timestamp": state.timestamp,
                "facts": state.facts,
                "entity_states": state.entity_states
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return str(snapshot_path)
    
    def load_world_snapshot(self, snapshot_path: str) -> WorldState:
        """加载世界状态快照"""
        data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        return WorldState(**data)

# 使用示例
def example_usage():
    dao = WorldSimulationDAO()
    
    # 创建小说
    novel_id = dao.create_novel("仙剑奇侠传", "仙侠")
    
    # 创建实体
    protagonist = dao.create_entity(
        novel_id, "character", "李逍遥",
        description="余杭镇的小混混，梦想成为大侠",
        attributes={"age": 19, "gender": "male", "martial_arts": 30},
        initial_state={"location": "余杭镇", "health": 100, "mood": "carefree"}
    )
    
    # 设置初始事实
    dao.set_fact(protagonist, "location", "余杭镇", source="initial")
    dao.set_fact(protagonist, "health", 100, source="initial")
    dao.set_fact(protagonist, "mood", "carefree", source="initial")
    
    # 创建角色心智
    dao.create_character_mind(
        protagonist,
        personality={
            "big_five": {"openness": 0.8, "conscientiousness": 0.4,
                        "extraversion": 0.7, "agreeableness": 0.6,
                        "neuroticism": 0.5},
            "values": ["freedom", "adventure", "justice"]
        },
        initial_goals=[
            {"goal": "become a hero", "priority": 1.0},
            {"goal": "find true love", "priority": 0.8}
        ]
    )
    
    # 模拟事件
    event_id = dao.record_event(
        novel_id, "action", "李逍遥决定前往仙灵岛",
        actor_id=protagonist,
        effects={"location_change": "仙灵岛"}
    )
    
    # 更新事实
    dao.set_fact(protagonist, "location", "仙灵岛",
                source="event", chapter_id=1,
                inference_chain=[f"event:{event_id}"])
    
    # 添加记忆
    dao.add_episodic_memory(protagonist, event_id, "excited", importance=0.9)
    
    # 获取当前状态
    state = dao.get_entity_state(protagonist)
    print(f"李逍遥当前状态: {state}")
    
    # 获取时间线
    timeline = dao.get_timeline(novel_id)
    print(f"事件数量: {len(timeline)}")
```

---

## 第二阶段：任务管理层重构（2-3周）—— 可视化模拟控制

### 2.1 任务类型扩展（世界模拟专用）

```python
class TaskType(Enum):
    # 世界模拟任务
    SIMULATE_WORLD = "simulate_world"           # 模拟世界时间步
    GENERATE_SCENE = "generate_scene"           # 生成场景
    GENERATE_DIALOGUE = "generate_dialogue"     # 生成对话
    CHARACTER_DECISION = "character_decision"   # 角色决策
    
    # 叙事任务
    NARRATE_CHAPTER = "narrate_chapter"         # 叙事化章节
    POLISH_PROSE = "polish_prose"               # 润色文字
    
    # 系统任务
    UPDATE_CONTEXT = "update_context"           # 更新上下文
    CHECK_CONSISTENCY = "check_consistency"    # 一致性检查
    BUILD_SNAPSHOT = "build_snapshot"           # 构建快照
```

### 2.2 可视化任务状态机

```python
class SimulationTask:
    """
    模拟任务 - 可暂停、可恢复、可视化
    
    新增：模拟专用步骤
    """
    
    def __init__(self, task_type: TaskType, novel_id: int, config: Dict):
        self.task_type = task_type
        self.novel_id = novel_id
        self.config = config
        
        # 模拟专用状态
        self.simulation_step = 0           # 当前模拟时间步
        self.world_state_hash = None     # 世界状态指纹
        self.character_actions = {}      # 角色行动记录
        
        # 步骤定义
        self.steps = self._define_steps()
    
    def _define_steps(self) -> List[GenerationStep]:
        """定义任务步骤"""
        
        if self.task_type == TaskType.SIMULATE_WORLD:
            return [
                GenerationStep("load_world_state", "加载世界状态"),
                GenerationStep("character_decisions", "角色决策"),
                GenerationStep("apply_actions", "应用行动"),
                GenerationStep("propagate_effects", "传播效果"),
                GenerationStep("update_minds", "更新心智"),
                GenerationStep("record_events", "记录事件"),
                GenerationStep("check_consistency", "一致性检查"),
                GenerationStep("save_snapshot", "保存快照")
            ]
        
        elif self.task_type == TaskType.NARRATE_CHAPTER:
            return [
                GenerationStep("analyze_events", "分析事件"),
                GenerationStep("select_pov", "选择视角"),
                GenerationStep("plan_scenes", "规划场景"),
                GenerationStep("generate_scenes", "生成场景"),
                GenerationStep("weave_dialogues", "编织对话"),
                GenerationStep("polish_prose", "润色文字"),
                GenerationStep("verify_quality", "质量验证")
            ]
        
        return []
```

### 2.3 可视化数据结构

```json
{
  "task": {
    "id": "task_123_simulate_world_1714300000",
    "type": "simulate_world",
    "novel_id": 123,
    "status": "running",
    "progress": 45.5,
    "current_step": 3,
    "simulation_step": 15,
    
    "steps": [
      {
        "name": "load_world_state",
        "display_name": "加载世界状态",
        "status": "completed",
        "progress": 100,
        "duration": 0.5,
        "details": {
          "entities_loaded": 5,
          "facts_loaded": 23
        }
      },
      {
        "name": "character_decisions",
        "display_name": "角色决策",
        "status": "running",
        "progress": 60,
        "duration": null,
        "details": {
          "characters_total": 3,
          "characters_decided": 2,
          "current_character": "李逍遥"
        }
      }
    ],
    
    "world_state_preview": {
      "entities": [
        {"id": 1, "name": "李逍遥", "location": "仙灵岛", "health": 100},
        {"id": 2, "name": "赵灵儿", "location": "仙灵岛", "mood": "nervous"}
      ],
      "recent_events": [
        {"step": 14, "description": "李逍遥闯入仙灵岛"},
        {"step": 15, "description": "赵灵儿发现入侵者"}
      ]
    }
  }
}
```

---

## 第三阶段：任务调度层重构（2周）—— 模拟调度

### 3.1 调度策略（世界模拟专用）

```python
class SimulationScheduler:
    """
    模拟调度器
    
    策略：
    1. 连续性优先：同一小说的模拟连续执行
    2. 依赖优先：前置步骤完成后才执行后续
    3. 资源均衡：控制LLM调用频率
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.task_queue = PriorityQueue()
        self.running_tasks = {}
        
        # 调度策略
        self.strategy = "simulation_continuity"
    
    def submit_simulation_task(self, novel_id: int, simulation_steps: int):
        """
        提交模拟任务
        
        自动拆分为多个子任务：
        - 每个时间步一个子任务
        - 子任务间有依赖关系
        """
        tasks = []
        prev_task_id = None
        
        for step in range(simulation_steps):
            task = SimulationTask(
                task_type=TaskType.SIMULATE_WORLD,
                novel_id=novel_id,
                config={"simulation_step": step}
            )
            
            if prev_task_id:
                task.dependencies.append(prev_task_id)
            
            tasks.append(task)
            prev_task_id = task.id
        
        # 最后添加叙事任务
        narrate_task = SimulationTask(
            task_type=TaskType.NARRATE_CHAPTER,
            novel_id=novel_id,
            config={"chapter_number": self._get_next_chapter(novel_id)}
        )
        narrate_task.dependencies.append(prev_task_id)
        tasks.append(narrate_task)
        
        # 提交所有任务
        for task in tasks:
            self.task_queue.put(task)
        
        return tasks
```

---

## 第四阶段：消息通信模块重构（1-2周）—— 模拟事件流

### 4.1 事件类型扩展

```python
class SimulationEventType(Enum):
    # 世界事件
    WORLD_STATE_CHANGED = "world.state_changed"
    ENTITY_UPDATED = "entity.updated"
    FACT_CHANGED = "fact.changed"
    
    # 角色事件
    CHARACTER_DECIDED = "character.decided"
    CHARACTER_ACTED = "character.acted"
    CHARACTER_PERCEIVED = "character.perceived"
    
    # 模拟事件
    SIMULATION_STEP_STARTED = "simulation.step_started"
    SIMULATION_STEP_COMPLETED = "simulation.step_completed"
    SIMULATION_PAUSED = "simulation.paused"
    SIMULATION_RESUMED = "simulation.resumed"
    
    # 叙事事件
    SCENE_GENERATED = "scene.generated"
    DIALOGUE_GENERATED = "dialogue.generated"
    CHAPTER_COMPLETED = "chapter.completed"
```

### 4.2 流式通信

```python
class SimulationEventBus:
    """
    模拟事件总线
    
    支持：
    1. 实时推送模拟进度
    2. 世界状态可视化
    3. 角色决策展示
    """
    
    async def publish_world_state(self, novel_id: int, state: WorldState):
        """发布世界状态更新"""
        event = Event(
            type=SimulationEventType.WORLD_STATE_CHANGED,
            payload={
                "novel_id": novel_id,
                "simulation_step": state.simulation_step,
                "entities": [
                    {"id": eid, "state": est}
                    for eid, est in state.entity_states.items()
                ],
                "timestamp": state.timestamp
            }
        )
        await self.publish(event)
    
    async def publish_character_decision(self, character_id: int, decision: Decision):
        """发布角色决策"""
        event = Event(
            type=SimulationEventType.CHARACTER_DECIDED,
            payload={
                "character_id": character_id,
                "character_name": decision.character_name,
                "decision": decision.choice,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence
            }
        )
        await self.publish(event)
```

---

## 第五阶段：上下文管理层重构（3-4周）—— 世界上下文

### 5.1 上下文片段扩展（世界模拟专用）

```python
class WorldContextFragment(FragmentType):
    """
    世界上下文片段类型
    
    新增：
    - 世界事实：当前世界状态
    - 角色心智：角色当前认知
    - 事件因果：事件前因后果
    - 模拟预测：可能的发展
    """
    
    WORLD_FACT = "world_fact"               # 世界事实
    CHARACTER_MIND = "character_mind"       # 角色心智状态
    EVENT_CAUSAL = "event_causal"          # 事件因果链
    SIMULATION_PREDICTION = "sim_prediction" # 模拟预测
    
    # 原有类型
    CHAPTER_SUMMARY = "chapter_summary"
    CHARACTER_STATE = "character_state"
    DIALOGUE_SAMPLE = "dialogue_sample"
    STYLE_SAMPLE = "style_sample"
```

### 5.2 世界上下文检索

```python
class WorldContextRetriever:
    """
    世界上下文检索器
    
    策略：
    1. 检索当前世界状态
    2. 检索相关角色心智
    3. 检索因果链
    4. 检索风格参考
    """
    
    async def retrieve_for_simulation(self, novel_id: int, character_id: int) -> List[ContextFragment]:
        """
        为角色决策检索上下文
        
        包含：
        1. 角色当前状态（位置、健康、情绪）
        2. 角色记忆（最近事件）
        3. 周围实体（同地点的角色、物品）
        4. 相关世界规则
        5. 角色目标
        """
        fragments = []
        
        # 1. 角色当前状态
        state = self.dao.get_entity_state(character_id)
        fragments.append(ContextFragment(
            type=FragmentType.CHARACTER_STATE,
            content=json.dumps(state),
            priority=FragmentPriority.CRITICAL
        ))
        
        # 2. 角色心智
        mind = self.dao.get_character_mind(character_id)
        if mind:
            fragments.append(ContextFragment(
                type=FragmentType.CHARACTER_MIND,
                content=json.dumps({
                    "goals": mind.get("explicit_goals", []),
                    "current_emotion": mind.get("current_emotion", {}),
                    "recent_memories": mind.get("episodic_memory", [])[-3:]
                }),
                priority=FragmentPriority.CRITICAL
            ))
        
        # 3. 周围实体
        location = state.get("location")
        if location:
            nearby = self.dao.get_entities_at_location(novel_id, location)
            for entity in nearby:
                if entity["id"] != character_id:
                    fragments.append(ContextFragment(
                        type=FragmentType.WORLD_FACT,
                        content=f"{entity['name']}也在{location}",
                        priority=FragmentPriority.HIGH
                    ))
        
        # 4. 最近事件
        recent_events = self.dao.get_timeline(novel_id, limit=5)
        for event in recent_events:
            fragments.append(ContextFragment(
                type=FragmentType.EVENT_CAUSAL,
                content=event["description"],
                priority=FragmentPriority.HIGH
            ))
        
        return fragments
    
    async def retrieve_for_narration(self, novel_id: int, chapter_id: int) -> List[ContextFragment]:
        """
        为叙事生成检索上下文
        
        包含：
        1. 本章模拟事件
        2. 角色状态变化
        3. 情感高潮点
        4. 风格参考
        """
        fragments = []
        
        # 1. 本章模拟事件
        simulation = self.dao.get_chapter_simulation(chapter_id)
        if simulation:
            for event in simulation.get("events", []):
                fragments.append(ContextFragment(
                    type=FragmentType.EVENT_CAUSAL,
                    content=event["description"],
                    priority=FragmentPriority.CRITICAL
                ))
        
        # 2. 风格参考
        style_fragments = self.vector_store.match_style(
            genre=self.dao.get_novel(novel_id).get("genre"),
            limit=3
        )
        fragments.extend(style_fragments)
        
        return fragments
```

---

## 实施路线图（融合世界模拟）

### Phase 1: 数据层重构（2-3周）
- [ ] 设计世界模拟专用SQLite schema（实体、事实、事件、心智）
- [ ] 实现WorldSimulationDAO（事实管理、时间旅行、心智存储）
- [ ] 集成Qdrant本地模式（向量检索）
- [ ] 文件存储结构（实体档案、心智、事件时间线）

### Phase 2: 世界模拟核心（3-4周）⭐ 新增
- [ ] 实现世界状态机（事实图谱、规则引擎）
- [ ] 实现角色决策引擎（LLM驱动）
- [ ] 实现事件传播系统（连锁反应）
- [ ] 实现心智更新机制（记忆、信念、情感）

### Phase 3: 任务管理层（2-3周）
- [ ] 设计模拟专用任务状态机
- [ ] 实现可暂停/恢复的时间步模拟
- [ ] 细粒度步骤分解（决策→行动→效果→记录）
- [ ] WebSocket实时推送（世界状态、角色决策）

### Phase 4: 叙事引擎（2-3周）⭐ 新增
- [ ] 实现事件→场景转换
- [ ] 实现视角选择（POV）
- [ ] 实现详略控制（节奏）
- [ ] 实现文学化表达（风格）

### Phase 5: 上下文管理层（3-4周）
- [ ] 世界上下文片段定义（事实、心智、因果）
- [ ] 多策略检索（语义+结构+时序）
- [ ] 智能窗口管理（优先级填充）
- [ ] 模拟后自动更新（提取新事实）

### Phase 6: 系统集成（2周）
- [ ] 整合数据层+模拟层+叙事层
- [ ] 实现完整生成循环
- [ ] 跑通5章短故事MVP

---

## 关键技术决策

1. **SQLite + WAL模式**：支持读写并发，事实表支持时间旅行
2. **Qdrant本地模式**：向量检索角色心智、风格匹配
3. **文件存储大文本**：实体档案、心智状态、事件时间线
4. **LLM驱动角色决策**：模拟认知，非真正意识
5. **结构化约束 + LLM创意**：规则保一致性，LLM保灵活性
6. **强制模拟→叙事循环**：先模拟世界，再记录故事

---

## 预期效果

### 短期（3个月）
- 可运行5章短故事
- 角色行为有逻辑
- 情节有因果链

### 中期（6个月）
- 角色有个性
- 情感有层次
- 伏笔有呼应

### 长期（1年）
- 故事有深度
- 创意有惊喜
- 文学有质量

---

*文档版本: v2.0（融合世界模拟）*
*更新日期: 2026-04-28*
*作者: 小R*
