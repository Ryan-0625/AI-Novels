# AI-Novels 重构优化计划

## 项目定位

**单机版智能小说生成系统** —— 不追求吞吐量，追求单章质量。核心哲学：

> "慢即是快" —— 通过缩小生成粒度、强制检索-生成-更新循环、实时持久化，实现更高的小说质量。

---

## 第一阶段：数据层重构（2-3周）

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

### 1.2 SQLite 详细设计

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
    
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch()),
    
    UNIQUE(novel_id, number)
);

-- 角色表
CREATE TABLE characters (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER REFERENCES novels(id),
    name TEXT NOT NULL,
    role_type TEXT, -- protagonist/antagonist/supporting
    importance INTEGER DEFAULT 3, -- 1-5
    
    -- 动态属性（JSON）
    attributes JSON, -- {location, mood, health, power_level, ...}
    
    -- 深度档案（引用外部文件）
    profile_path TEXT,
    
    -- 状态历史（时序）
    state_history JSON, -- [{chapter, state, timestamp}]
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 角色关系表（图结构平铺）
CREATE TABLE character_relationships (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    from_char INTEGER REFERENCES characters(id),
    to_char INTEGER REFERENCES characters(id),
    relation_type TEXT, -- romantic/rivalry/family/mentor
    dynamics TEXT, -- 动态描述
    intensity REAL, -- 0-1
    
    -- 发展弧线
    development JSON, -- [{chapter, stage, tension}]
    
    UNIQUE(novel_id, from_char, to_char, relation_type)
);

-- 世界元素表
CREATE TABLE world_elements (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    name TEXT,
    element_type TEXT, -- location/organization/item/rule
    description TEXT,
    attributes JSON,
    parent_id INTEGER REFERENCES world_elements(id),
    created_at INTEGER DEFAULT (unixepoch())
);

-- 生成任务表（可视化任务管理核心）
CREATE TABLE generation_tasks (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    chapter_id INTEGER,
    
    -- 任务定义
    task_type TEXT, -- generate_chapter/revise/expand/bridge
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
    
    created_at INTEGER DEFAULT (unixepoch())
);

-- 上下文片段表（向量检索源）
CREATE TABLE context_fragments (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    fragment_type TEXT, -- chapter_summary/character_state/world_fact/plot_point/dialogue_sample
    
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

-- 上下文关联表（显式关系）
CREATE TABLE context_links (
    id INTEGER PRIMARY KEY,
    from_fragment INTEGER REFERENCES context_fragments(id),
    to_fragment INTEGER REFERENCES context_fragments(id),
    link_type TEXT, -- causal/sequential/thematic/character
    strength REAL,
    created_at INTEGER DEFAULT (unixepoch())
);

-- 配置表
CREATE TABLE app_config (
    key TEXT PRIMARY KEY,
    value JSON,
    updated_at INTEGER DEFAULT (unixepoch())
);

-- 索引
CREATE INDEX idx_chapters_novel ON chapters(novel_id);
CREATE INDEX idx_chapters_status ON chapters(status);
CREATE INDEX idx_characters_novel ON characters(novel_id);
CREATE INDEX idx_tasks_status ON generation_tasks(status);
CREATE INDEX idx_tasks_novel ON generation_tasks(novel_id);
CREATE INDEX idx_fragments_type ON context_fragments(fragment_type, novel_id);
CREATE INDEX idx_fragments_vector ON context_fragments(vector_id);
```

### 1.3 文件存储结构

```
workspace/
├── data/
│   ├── novels.db              # SQLite 主库
│   ├── vector_storage/        # Qdrant 本地存储
│   └── novels/                # 小说内容目录
│       └── {novel_id}/
│           ├── meta.json      # 小说元数据
│           ├── chapters/      # 章节内容
│           │   └── {chapter_number}/
│           │       ├── v{version}.md      # 章节正文
│           │       ├── v{version}.json    # 结构化数据
│           │       └── generation.log     # 生成日志
│           ├── characters/      # 角色档案
│           │   └── {character_id}.json
│           ├── world/           # 世界设定
│           │   └── {element_id}.json
│           └── snapshots/       # 上下文快照
│               └── chapter_{number}_{timestamp}.json
```

### 1.4 数据访问层（DAO）

```python
# src/deepnovel/database/sqlite_dao.py
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class Novel:
    id: Optional[int]
    title: str
    genre: str
    status: str
    config: Dict
    summary: str
    created_at: Optional[int]
    updated_at: Optional[int]

class NovelDAO:
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
    
    # 小说 CRUD
    def create_novel(self, novel: Novel) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO novels (title, genre, status, config, summary)
                   VALUES (?, ?, ?, ?, ?)""",
                (novel.title, novel.genre, novel.status, 
                 json.dumps(novel.config), novel.summary)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_novel(self, novel_id: int) -> Optional[Novel]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM novels WHERE id = ?", (novel_id,)
            ).fetchone()
            
            if row:
                return Novel(
                    id=row["id"],
                    title=row["title"],
                    genre=row["genre"],
                    status=row["status"],
                    config=json.loads(row["config"]),
                    summary=row["summary"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
            return None
    
    def update_novel_status(self, novel_id: int, status: str):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE novels SET status = ?, updated_at = unixepoch() WHERE id = ?",
                (status, novel_id)
            )
            conn.commit()
    
    # 章节操作（含文件读写）
    def create_chapter(self, novel_id: int, number: int, title: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO chapters (novel_id, number, title, content_path)
                   VALUES (?, ?, ?, ?)""",
                (novel_id, number, title, f"data/novels/{novel_id}/chapters/{number}/")
            )
            conn.commit()
            
            # 创建目录
            Path(f"data/novels/{novel_id}/chapters/{number}").mkdir(parents=True, exist_ok=True)
            
            return cursor.lastrowid
    
    def save_chapter_content(self, chapter_id: int, content: str, version: int = 1):
        """保存章节内容到文件，更新元数据"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT novel_id, number, content_path FROM chapters WHERE id = ?",
                (chapter_id,)
            ).fetchone()
            
            if not row:
                raise ValueError(f"Chapter {chapter_id} not found")
            
            # 写入文件
            content_path = Path(row["content_path"]) / f"v{version}.md"
            content_path.write_text(content, encoding="utf-8")
            
            # 更新数据库
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            conn.execute(
                """UPDATE chapters 
                   SET content_hash = ?, version = ?, updated_at = unixepoch()
                   WHERE id = ?""",
                (content_hash, version, chapter_id)
            )
            conn.commit()
    
    def get_chapter_content(self, chapter_id: int, version: Optional[int] = None) -> str:
        """读取章节内容"""
        with self._get_connection() as conn:
            if version is None:
                row = conn.execute(
                    "SELECT content_path, version FROM chapters WHERE id = ?",
                    (chapter_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT content_path, ? as version FROM chapters WHERE id = ?",
                    (version, chapter_id)
                ).fetchone()
            
            if not row:
                raise ValueError(f"Chapter {chapter_id} not found")
            
            content_path = Path(row["content_path"]) / f"v{row['version']}.md"
            if content_path.exists():
                return content_path.read_text(encoding="utf-8")
            return ""
```

---

## 第二阶段：任务管理层重构（2-3周）

### 2.1 可视化任务管理

```python
# src/deepnovel/task/visual_manager.py
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict
from datetime import datetime
import asyncio

class TaskStatus(Enum):
    PENDING = "pending"       # 等待执行
    QUEUED = "queued"        # 已入队
    RUNNING = "running"      # 执行中
    PAUSED = "paused"        # 已暂停（用户操作）
    COMPLETED = "completed"  # 完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 取消

class TaskType(Enum):
    GENERATE_CHAPTER = "generate_chapter"
    GENERATE_SCENE = "generate_scene"      # 更细粒度
    GENERATE_DIALOGUE = "generate_dialogue" # 对话生成
    REVISE_CHAPTER = "revise_chapter"
    EXPAND_SCENE = "expand_scene"
    BRIDGE_SCENES = "bridge_scenes"        # 场景过渡
    CHECK_CONSISTENCY = "check_consistency"
    UPDATE_CONTEXT = "update_context"

@dataclass
class GenerationStep:
    """生成步骤（细粒度）"""
    name: str                          # 步骤名称
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0              # 0-100
    
    # 执行信息
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None   # 秒
    
    # 输入输出
    input_data: Dict = field(default_factory=dict)
    output_data: Dict = field(default_factory=dict)
    
    # 错误信息
    error: Optional[str] = None
    
    # 可中断点
    can_pause: bool = True
    can_resume: bool = True
    
    # 回调
    on_progress: Optional[Callable] = None
    on_complete: Optional[Callable] = None

@dataclass
class GenerationTask:
    """生成任务（可暂停、可恢复）"""
    id: str
    novel_id: int
    chapter_id: Optional[int]
    task_type: TaskType
    
    # 任务配置
    config: Dict = field(default_factory=dict)
    
    # 执行状态
    status: TaskStatus = TaskStatus.PENDING
    overall_progress: float = 0.0
    
    # 步骤分解（细粒度控制）
    steps: List[GenerationStep] = field(default_factory=list)
    current_step_index: int = 0
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 资源使用
    tokens_used: int = 0
    api_calls: int = 0
    
    # 依赖
    dependencies: List[str] = field(default_factory=list)
    
    # 用户交互
    user_notes: str = ""
    priority: int = 3  # 1-5
    
    # 检查点（用于恢复）
    checkpoint_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "novel_id": self.novel_id,
            "chapter_id": self.chapter_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": self.overall_progress,
            "steps": [
                {
                    "name": step.name,
                    "status": step.status.value,
                    "progress": step.progress,
                    "duration": step.duration,
                    "error": step.error
                }
                for step in self.steps
            ],
            "current_step": self.current_step_index,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tokens_used": self.tokens_used,
            "api_calls": self.api_calls,
            "dependencies": self.dependencies,
            "priority": self.priority
        }

class VisualTaskManager:
    """可视化任务管理器"""
    
    def __init__(self, dao):
        self.dao = dao
        self.tasks: Dict[str, GenerationTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._observers: List[Callable] = []
        
        # 从数据库恢复未完成的任务
        self._restore_tasks()
    
    def _restore_tasks(self):
        """启动时恢复未完成的任务"""
        unfinished = self.dao.get_tasks_by_status(["pending", "running", "paused"])
        for task_data in unfinished:
            task = self._deserialize_task(task_data)
            self.tasks[task.id] = task
            
            # 如果是暂停状态，保持暂停
            if task.status == TaskStatus.PAUSED:
                print(f"恢复暂停任务: {task.id}")
    
    def add_observer(self, callback: Callable):
        """添加状态观察器（用于UI更新）"""
        self._observers.append(callback)
    
    def _notify_observers(self, task: GenerationTask):
        """通知所有观察者"""
        for callback in self._observers:
            try:
                callback(task)
            except Exception as e:
                print(f"Observer error: {e}")
    
    def create_task(self, 
                   novel_id: int,
                   task_type: TaskType,
                   chapter_id: Optional[int] = None,
                   config: Dict = None,
                   steps: List[str] = None) -> GenerationTask:
        """创建新任务"""
        
        task_id = f"task_{novel_id}_{task_type.value}_{int(datetime.now().timestamp())}"
        
        # 默认步骤
        if steps is None:
            steps = self._get_default_steps(task_type)
        
        task = GenerationTask(
            id=task_id,
            novel_id=novel_id,
            chapter_id=chapter_id,
            task_type=task_type,
            config=config or {},
            steps=[GenerationStep(name=step) for step in steps]
        )
        
        # 保存到内存和数据库
        self.tasks[task_id] = task
        self.dao.save_task(task.to_dict())
        
        self._notify_observers(task)
        return task
    
    def _get_default_steps(self, task_type: TaskType) -> List[str]:
        """获取任务类型的默认步骤"""
        steps_map = {
            TaskType.GENERATE_CHAPTER: [
                "analyze_context",      # 分析上下文
                "retrieve_references",  # 检索参考
                "generate_outline",     # 生成细纲
                "generate_scenes",      # 生成场景
                "generate_dialogues",   # 生成对话
                "weave_narrative",      # 编织叙事
                "polish_prose",         # 润色文字
                "check_consistency",    # 一致性检查
                "update_context",       # 更新上下文
                "save_checkpoint"       # 保存检查点
            ],
            TaskType.GENERATE_SCENE: [
                "analyze_scene_requirement",
                "retrieve_character_states",
                "generate_setting",
                "generate_action",
                "generate_dialogue",
                "integrate_emotion",
                "polish_scene",
                "update_character_states"
            ],
            TaskType.REVISE_CHAPTER: [
                "analyze_issues",
                "retrieve_original",
                "plan_revisions",
                "execute_revisions",
                "verify_improvements"
            ]
        }
        return steps_map.get(task_type, ["execute"])
    
    async def start_task(self, task_id: str) -> bool:
        """启动任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.PAUSED]:
            print(f"任务 {task_id} 状态 {task.status} 不允许启动")
            return False
        
        # 检查依赖
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                print(f"等待依赖任务: {dep_id}")
                return False
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # 创建异步任务
        asyncio_task = asyncio.create_task(self._execute_task(task))
        self.running_tasks[task_id] = asyncio_task
        
        self.dao.update_task_status(task_id, "running")
        self._notify_observers(task)
        
        return True
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务（在可暂停点）"""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        # 标记为暂停请求
        task.status = TaskStatus.PAUSED
        
        # 等待当前步骤完成（如果可暂停）
        current_step = task.steps[task.current_step_index]
        if current_step.can_pause:
            # 保存检查点
            task.checkpoint_data = {
                "step_index": task.current_step_index,
                "step_progress": current_step.progress,
                "timestamp": datetime.now().isoformat()
            }
            
            self.dao.update_task_status(task_id, "paused", checkpoint=task.checkpoint_data)
            self._notify_observers(task)
            return True
        
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        # 从检查点恢复
        checkpoint = task.checkpoint_data
        if checkpoint:
            task.current_step_index = checkpoint.get("step_index", 0)
            # 恢复步骤进度
            if task.current_step_index < len(task.steps):
                task.steps[task.current_step_index].progress = checkpoint.get("step_progress", 0)
        
        return await self.start_task(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # 取消异步任务
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        task.status = TaskStatus.CANCELLED
        self.dao.update_task_status(task_id, "cancelled")
        self._notify_observers(task)
        
        return True
    
    async def _execute_task(self, task: GenerationTask):
        """执行任务"""
        try:
            for i, step in enumerate(task.steps[task.current_step_index:], 
                                      start=task.current_step_index):
                
                # 检查是否被暂停
                if task.status == TaskStatus.PAUSED:
                    print(f"任务 {task.id} 在步骤 {step.name} 被暂停")
                    return
                
                # 检查是否被取消
                if task.status == TaskStatus.CANCELLED:
                    return
                
                task.current_step_index = i
                step.status = TaskStatus.RUNNING
                step.started_at = datetime.now()
                
                self._notify_observers(task)
                
                # 执行步骤
                try:
                    await self._execute_step(task, step)
                    step.status = TaskStatus.COMPLETED
                    step.completed_at = datetime.now()
                    step.duration = (step.completed_at - step.started_at).total_seconds()
                except Exception as e:
                    step.status = TaskStatus.FAILED
                    step.error = str(e)
                    task.status = TaskStatus.FAILED
                    raise
                
                # 更新整体进度
                task.overall_progress = (i + 1) / len(task.steps) * 100
                self._notify_observers(task)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.dao.update_task_status(task.id, "completed")
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            self.dao.update_task_status(task.id, "cancelled")
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.steps[task.current_step_index].error = str(e)
            self.dao.update_task_status(task.id, "failed", error=str(e))
        finally:
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
            
            self._notify_observers(task)
    
    async def _execute_step(self, task: GenerationTask, step: GenerationStep):
        """执行单个步骤"""
        # 这里调用具体的生成逻辑
        # 每个步骤都是一个小型生成任务
        
        step_handlers = {
            "analyze_context": self._step_analyze_context,
            "retrieve_references": self._step_retrieve_references,
            "generate_outline": self._step_generate_outline,
            "generate_scenes": self._step_generate_scenes,
            "check_consistency": self._step_check_consistency,
            "update_context": self._step_update_context,
        }
        
        handler = step_handlers.get(step.name)
        if handler:
            await handler(task, step)
        else:
            # 默认步骤：模拟执行
            await asyncio.sleep(1)
            step.progress = 100
    
    async def _step_analyze_context(self, task: GenerationTask, step: GenerationStep):
        """分析上下文步骤"""
        # 从数据库读取当前状态
        novel = self.dao.get_novel(task.novel_id)
        chapter = self.dao.get_chapter(task.chapter_id) if task.chapter_id else None
        
        # 分析需要的上下文
        step.input_data = {
            "novel_status": novel.status if novel else None,
            "chapter_status": chapter.status if chapter else None,
        }
        
        # 模拟进度
        for progress in [25, 50, 75, 100]:
            step.progress = progress
            await asyncio.sleep(0.5)
            self._notify_observers(task)
    
    async def _step_retrieve_references(self, task: GenerationTask, step: GenerationStep):
        """检索参考步骤"""
        # 调用向量检索
        # ...
        step.progress = 100
    
    async def _step_generate_outline(self, task: GenerationTask, step: GenerationStep):
        """生成细纲步骤"""
        # 调用LLM生成
        # ...
        step.progress = 100
    
    async def _step_generate_scenes(self, task: GenerationTask, step: GenerationStep):
        """生成场景步骤"""
        # ...
        step.progress = 100
    
    async def _step_check_consistency(self, task: GenerationTask, step: GenerationStep):
        """一致性检查步骤"""
        # ...
        step.progress = 100
    
    async def _step_update_context(self, task: GenerationTask, step: GenerationStep):
        """更新上下文步骤"""
        # 保存生成结果到数据库
        # 更新角色状态
        # 添加新的上下文片段
        # ...
        step.progress = 100
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态（供UI查询）"""
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_all_tasks(self, novel_id: Optional[int] = None) -> List[Dict]:
        """获取所有任务"""
        tasks = self.tasks.values()
        if novel_id:
            tasks = [t for t in tasks if t.novel_id == novel_id]
        return [t.to_dict() for t in tasks]
    
    def modify_task_config(self, task_id: str, config_updates: Dict) -> bool:
        """动态修改任务配置（暂停时可用）"""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        task.config.update(config_updates)
        self.dao.update_task_config(task_id, task.config)
        self._notify_observers(task)
        return True
```

### 2.2 可视化数据结构（供前端使用）

```json
{
  "tasks": [
    {
      "id": "task_123_generate_chapter_1714300000",
      "novel_id": 123,
      "chapter_id": 5,
      "task_type": "generate_chapter",
      "status": "running",
      "progress": 45.5,
      "current_step": 4,
      "steps": [
        {
          "name": "analyze_context",
          "status": "completed",
          "progress": 100,
          "duration": 2.5
        },
        {
          "name": "retrieve_references",
          "status": "completed",
          "progress": 100,
          "duration": 5.0
        },
        {
          "name": "generate_outline",
          "status": "completed",
          "progress": 100,
          "duration": 15.0
        },
        {
          "name": "generate_scenes",
          "status": "running",
          "progress": 60,
          "duration": null
        },
        {
          "name": "generate_dialogues",
          "status": "pending",
          "progress": 0
        }
      ],
      "tokens_used": 5000,
      "api_calls": 3,
      "created_at": "2024-04-28T10:00:00",
      "started_at": "2024-04-28T10:05:00",
      "can_pause": true,
      "can_cancel": true,
      "user_notes": "重点描写主角心理变化"
    }
  ],
  "statistics": {
    "total_tasks": 10,
    "running": 1,
    "completed": 5,
    "failed": 1,
    "paused": 1,
    "pending": 2
  }
}
```

---

## 第三阶段：任务调度层重构（2周）

### 3.1 调度器设计

```python
# src/deepnovel/scheduler/intelligent_scheduler.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
import heapq
import asyncio

class PriorityLevel(Enum):
    CRITICAL = 1    # 用户主动触发，阻塞操作
    HIGH = 2        # 重要更新
    NORMAL = 3      # 常规生成
    LOW = 4         # 后台优化
    BACKGROUND = 5  # 索引更新、清理

@dataclass(order=True)
class ScheduledTask:
    """可调度任务"""
    priority: int
    created_at: float
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)
    novel_id: int = field(compare=False)
    
    # 资源预估
    estimated_tokens: int = 1000
    estimated_duration: float = 30.0
    
    # 依赖
    dependencies: List[str] = field(default_factory=list)
    
    # 资源需求
    required_context_window: int = 4000
    
    def __post_init__(self):
        # 用于堆排序
        self._sort_key = (self.priority, self.created_at)

class IntelligentScheduler:
    """智能任务调度器"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 任务队列（优先级堆）
        self.task_queue: List[ScheduledTask] = []
        
        # 正在执行的任务
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # 资源限制
        self.max_concurrent = config.get("max_concurrent", 1)  # 单机默认1
        self.max_tokens_per_minute = config.get("max_tpm", 10000)
        self.token_bucket = TokenBucket(self.max_tokens_per_minute)
        
        # 调度策略
        self.strategy = config.get("strategy", "quality_first")
        
        # 回调
        self.on_task_start: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
    
    def submit_task(self, task: ScheduledTask) -> bool:
        """提交任务到队列"""
        # 检查是否已存在
        if any(t.task_id == task.task_id for t in self.task_queue):
            return False
        
        # 根据策略调整优先级
        task = self._apply_strategy(task)
        
        # 加入优先级队列
        heapq.heappush(self.task_queue, task)
        
        # 触发调度
        asyncio.create_task(self._schedule())
        
        return True
    
    def _apply_strategy(self, task: ScheduledTask) -> ScheduledTask:
        """应用调度策略"""
        
        if self.strategy == "quality_first":
            # 质量优先：降低并发，增加思考时间
            task.estimated_duration *= 1.5
            
        elif self.strategy == "speed_first":
            # 速度优先：允许更高并发
            task.estimated_duration *= 0.8
            
        elif self.strategy == "token_efficient":
            # Token效率优先：优先使用短上下文任务
            if task.estimated_tokens > 2000:
                task.priority += 1  # 降低优先级
                
        elif self.strategy == "continuity_first":
            # 连续性优先：同一小说的任务连续执行
            # 检查队列中是否有同小说任务
            same_novel_tasks = [t for t in self.task_queue if t.novel_id == task.novel_id]
            if same_novel_tasks:
                task.priority = min(t.priority for t in same_novel_tasks) - 1
        
        return task
    
    async def _schedule(self):
        """调度循环"""
        while self.task_queue and len(self.running_tasks) < self.max_concurrent:
            # 获取最高优先级任务
            task = heapq.heappop(self.task_queue)
            
            # 检查依赖
            if task.dependencies:
                # 检查依赖是否完成
                # ...
                pass
            
            # 检查Token限制
            if not await self.token_bucket.consume(task.estimated_tokens):
                # Token不足，放回队列
                heapq.heappush(self.task_queue, task)
                await asyncio.sleep(1)
                continue
            
            # 启动任务
            await self._start_task(task)
    
    async def _start_task(self, task: ScheduledTask):
        """启动任务"""
        # 创建异步任务
        asyncio_task = asyncio.create_task(self._execute_task(task))
        self.running_tasks[task.task_id] = asyncio_task
        
        if self.on_task_start:
            self.on_task_start(task)
    
    async def _execute_task(self, task: ScheduledTask):
        """执行任务包装"""
        try:
            # 实际执行
            result = await self._run_task_logic(task)
            
            if self.on_task_complete:
                self.on_task_complete(task, result)
                
        except Exception as e:
            if self.on_task_complete:
                self.on_task_complete(task, None, error=e)
        finally:
            del self.running_tasks[task.task_id]
            # 触发下一轮调度
            asyncio.create_task(self._schedule())
    
    async def _run_task_logic(self, task: ScheduledTask):
        """实际任务逻辑（由子类或回调实现）"""
        pass
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            "queued": len(self.task_queue),
            "running": len(self.running_tasks),
            "max_concurrent": self.max_concurrent,
            "strategy": self.strategy,
            "token_bucket": self.token_bucket.get_status()
        }

class TokenBucket:
    """Token桶限流"""
    
    def __init__(self, rate: int, capacity: Optional[int] = None):
        self.rate = rate  # 每秒补充速率
        self.capacity = capacity or rate  # 桶容量
        self.tokens = capacity or rate
        self.last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int) -> bool:
        """消费Token"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_update
            
            # 补充Token
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict:
        return {
            "available": self.tokens,
            "capacity": self.capacity,
            "rate": self.rate
        }
```

---

## 第四阶段：消息通信模块重构（1-2周）

### 4.1 事件驱动架构

```python
# src/deepnovel/messaging/event_bus.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
import asyncio
import json

class EventType(Enum):
    # 任务事件
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PAUSED = "task.paused"
    TASK_RESUMED = "task.resumed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_PROGRESS = "task.progress"
    
    # 生成事件
    GENERATION_STEP_START = "generation.step_start"
    GENERATION_STEP_COMPLETE = "generation.step_complete"
    GENERATION_CHUNK = "generation.chunk"
    GENERATION_COMPLETE = "generation.complete"
    
    # 数据事件
    CHAPTER_CREATED = "chapter.created"
    CHAPTER_UPDATED = "chapter.updated"
    CHARACTER_UPDATED = "character.updated"
    CONTEXT_UPDATED = "context.updated"
    
    # 系统事件
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"

@dataclass
class Event:
    type: EventType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    correlation_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id
        }, default=str)

class EventBus:
    """事件总线 - 单机版"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        
        # 异步队列
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅特定事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def subscribe_all(self, handler: Callable):
        """订阅所有事件"""
        self._global_subscribers.append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
    
    async def publish(self, event: Event):
        """发布事件"""
        # 加入历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # 加入异步队列
        await self._queue.put(event)
    
    async def start(self):
        """启动事件处理循环"""
        self._running = True
        while self._running:
            event = await self._queue.get()
            await self._process_event(event)
            self._queue.task_done()
    
    async def _process_event(self, event: Event):
        """处理事件"""
        # 调用特定订阅者
        handlers = self._subscribers.get(event.type, [])
        
        # 调用全局订阅者
        handlers.extend(self._global_subscribers)
        
        # 异步执行所有处理器
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(event)))
            else:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Event handler error: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_history(self, event_type: Optional[EventType] = None, 
                   limit: int = 100) -> List[Event]:
        """获取事件历史"""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]
    
    def stop(self):
        """停止事件总线"""
        self._running = False

# 使用示例
class NovelGenerationPipeline:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._setup_handlers()
    
    def _setup_handlers(self):
        """设置事件处理器"""
        self.event_bus.subscribe(EventType.TASK_STARTED, self._on_task_started)
        self.event_bus.subscribe(EventType.GENERATION_CHUNK, self._on_generation_chunk)
        self.event_bus.subscribe(EventType.CHAPTER_UPDATED, self._on_chapter_updated)
    
    async def _on_task_started(self, event: Event):
        """任务开始处理"""
        print(f"任务开始: {event.payload['task_id']}")
        # 可以在这里更新UI、记录日志等
    
    async def _on_generation_chunk(self, event: Event):
        """生成片段处理（流式输出）"""
        chunk = event.payload.get("text", "")
        # 发送到前端（WebSocket）
        # await websocket.send(chunk)
    
    async def _on_chapter_updated(self, event: Event):
        """章节更新处理"""
        # 更新缓存
        # 通知相关组件
        pass
```

### 4.2 流式通信（WebSocket）

```python
# src/deepnovel/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

class ConnectionManager:
    """WebSocket连接管理"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.novel_subscriptions: Dict[int, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        del self.active_connections[client_id]
        # 清理订阅
        for novel_id, subscribers in self.novel_subscriptions.items():
            subscribers.discard(client_id)
    
    def subscribe_novel(self, client_id: str, novel_id: int):
        if novel_id not in self.novel_subscriptions:
            self.novel_subscriptions[novel_id] = set()
        self.novel_subscriptions[novel_id].add(client_id)
    
    async def send_to_client(self, client_id: str, message: Dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def broadcast_to_novel(self, novel_id: int, message: Dict):
        subscribers = self.novel_subscriptions.get(novel_id, set())
        for client_id in subscribers:
            await self.send_to_client(client_id, message)
    
    async def broadcast_task_update(self, task: Dict):
        """广播任务更新"""
        message = {
            "type": "task_update",
            "data": task
        }
        
        novel_id = task.get("novel_id")
        if novel_id:
            await self.broadcast_to_novel(novel_id, message)
        else:
            # 广播给所有连接
            for client_id in self.active_connections:
                await self.send_to_client(client_id, message)

# FastAPI路由
from fastapi import APIRouter

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # 处理客户端消息
            if data["type"] == "subscribe_novel":
                manager.subscribe_novel(client_id, data["novel_id"])
            elif data["type"] == "pause_task":
                # 处理暂停请求
                pass
            elif data["type"] == "resume_task":
                # 处理恢复请求
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

---

## 第五阶段：上下文管理层重构（3-4周）

### 5.1 上下文架构（重中之重）

```
┌─────────────────────────────────────────────────────────────┐
│                    上下文管理系统                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  上下文构建器  │  │  上下文窗口   │  │  上下文检索   │      │
│  │  ContextBuilder│  │  WindowManager│  │  Retriever   │      │
│  │              │  │              │  │              │      │
│  │ • 收集片段    │  │ • 优先级排序  │  │ • 向量检索    │      │
│  │ • 重要性评估  │  │ • 空间分配   │  │ • 关系遍历    │      │
│  │ • 冲突解决   │  │ • 动态调整   │  │ • 时序过滤    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         └──────────────────┼──────────────────┘               │
│                            │                                │
│                   ┌────────┴────────┐                        │
│                   │   上下文存储      │                        │
│                   │  ContextStore     │                        │
│                   │                  │                        │
│                   │ • 热缓存 (内存)   │                        │
│                   │ • 温存储 (SQLite) │                        │
│                   │ • 冷归档 (文件)   │                        │
│                   └─────────────────┘                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  上下文更新器  │  │  一致性检查器  │  │  上下文可视化  │      │
│  │  Updater      │  │  Consistency │  │  Visualizer   │      │
│  │              │  │              │  │              │      │
│  │ • 增量更新    │  │ • 冲突检测    │  │ • 结构展示    │      │
│  │ • 版本管理    │  │ • 修复建议    │  │ • 关系图谱    │      │
│  │ • 回滚机制    │  │ • 自动修复    │  │ • 时间线      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 上下文片段定义

```python
# src/deepnovel/context/models.py
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime

class FragmentType(Enum):
    CHAPTER_SUMMARY = "chapter_summary"      # 章节摘要
    SCENE_DESCRIPTION = "scene_description" # 场景描述
    CHARACTER_STATE = "character_state"      # 角色状态
    CHARACTER_PROFILE = "character_profile"    # 角色档案
    DIALOGUE_SAMPLE = "dialogue_sample"      # 对话样本
    WORLD_FACT = "world_fact"               # 世界设定
    PLOT_POINT = "plot_point"               # 情节点
    THEME_EXPRESSION = "theme_expression"    # 主题表达
    STYLE_SAMPLE = "style_sample"           # 风格样本
    FORESHADOWING = "foreshadowing"         # 伏笔
    CALLBACK = "callback"                   # 呼应

class FragmentPriority(Enum):
    CRITICAL = 1    # 必须包含（当前章节直接相关）
    HIGH = 2        # 重要（主要角色当前状态）
    NORMAL = 3      # 一般（背景信息）
    LOW = 4         # 次要（历史参考）
    OPTIONAL = 5    # 可选（扩展阅读）

@dataclass
class ContextFragment:
    """上下文片段 - 最小检索单元"""
    
    id: str
    type: FragmentType
    content: str
    
    # 来源信息
    source_novel_id: int
    source_chapter_id: Optional[int]
    source_character_id: Optional[int]
    
    # 元数据（用于过滤和排序）
    metadata: Dict = field(default_factory=dict)
    
    # 重要性
    importance: float = 0.5  # 0-1
    priority: FragmentPriority = FragmentPriority.NORMAL
    
    # 时效性
    created_at: datetime = field(default_factory=datetime.now)
    last_retrieved: Optional[datetime] = None
    retrieval_count: int = 0
    
    # 关联
    related_fragments: List[str] = field(default_factory=list)
    
    # 向量ID（Qdrant）
    vector_id: Optional[str] = None
    
    # 验证状态
    verified: bool = False
    verification_notes: str = ""
    
    def to_prompt_text(self) -> str:
        """转换为提示文本"""
        headers = {
            FragmentType.CHAPTER_SUMMARY: "【前文摘要】",
            FragmentType.CHARACTER_STATE: "【角色状态】",
            FragmentType.WORLD_FACT: "【世界设定】",
            FragmentType.PLOT_POINT: "【情节点】",
            FragmentType.DIALOGUE_SAMPLE: "【对话样本】",
            FragmentType.STYLE_SAMPLE: "【风格参考】",
        }
        
        header = headers.get(self.type, f"【{self.type.value}】")
        return f"{header}\n{self.content}\n"
    
    def update_retrieval_stats(self):
        """更新检索统计"""
        self.last_retrieved = datetime.now()
        self.retrieval_count += 1

@dataclass
class ContextWindow:
    """上下文窗口 - 最终送入LLM的上下文"""
    
    # 窗口配置
    max_tokens: int = 8000
    reserved_tokens: int = 2000  # 预留给生成回复
    
    # 片段列表（已排序和截断）
    fragments: List[ContextFragment] = field(default_factory=list)
    
    # 系统提示（固定）
    system_prompt: str = ""
    
    # 用户提示（当前请求）
    user_prompt: str = ""
    
    # 统计
    total_tokens: int = 0
    fragment_count: int = 0
    
    # 被排除的片段（用于调试）
    excluded_fragments: List[ContextFragment] = field(default_factory=list)
    
    def build_prompt(self) -> str:
        """构建完整提示"""
        parts = []
        
        if self.system_prompt:
            parts.append(self.system_prompt)
        
        for fragment in self.fragments:
            parts.append(fragment.to_prompt_text())
        
        if self.user_prompt:
            parts.append(f"【当前任务】\n{self.user_prompt}")
        
        return "\n\n".join(parts)
```

### 5.3 上下文检索器

```python
# src/deepnovel/context/retriever.py
from typing import List, Dict, Optional, Tuple
import numpy as np

class ContextRetriever:
    """上下文检索器 - 多策略检索"""
    
    def __init__(self, 
                 qdrant_client,
                 sqlite_dao,
                 embedder,
                 config: Dict):
        self.qdrant = qdrant_client
        self.dao = sqlite_dao
        self.embedder = embedder
        self.config = config
        
        # 检索策略权重
        self.weights = {
            "semantic": 0.4,      # 语义相似度
            "temporal": 0.2,      # 时间邻近性
            "structural": 0.2,    # 结构重要性
            "frequency": 0.1,   # 使用频率
            "recency": 0.1        # 最近使用
        }
    
    async def retrieve(self, 
                      novel_id: int,
                      current_chapter_id: Optional[int],
                      query: str,
                      required_types: Optional[List[FragmentType]] = None,
                      max_results: int = 20) -> List[ContextFragment]:
        """检索上下文片段"""
        
        # 1. 生成查询向量
        query_embedding = await self.embedder.embed(query)
        
        # 2. 向量检索（Qdrant）
        vector_results = await self._vector_search(
            novel_id, query_embedding, max_results * 2
        )
        
        # 3. 结构化检索（SQLite）
        struct_results = await self._structured_search(
            novel_id, current_chapter_id, required_types
        )
        
        # 4. 合并结果
        merged = self._merge_results(vector_results, struct_results)
        
        # 5. 重排序
        reranked = await self._rerank(merged, query, novel_id, current_chapter_id)
        
        # 6. 更新统计
        for fragment in reranked:
            fragment.update_retrieval_stats()
            self.dao.update_fragment_retrieval_stats(fragment.id)
        
        return reranked[:max_results]
    
    async def _vector_search(self, 
                           novel_id: int,
                           query_embedding: List[float],
                           limit: int) -> List[Tuple[ContextFragment, float]]:
        """向量检索"""
        
        results = self.qdrant.search(
            collection_name="context_fragments",
            query_vector=query_embedding,
            query_filter={
                "must": [
                    {"key": "novel_id", "match": {"value": novel_id}}
                ]
            },
            limit=limit,
            with_payload=True
        )
        
        fragments = []
        for result in results:
            fragment = ContextFragment(
                id=result.payload["fragment_id"],
                type=FragmentType(result.payload["type"]),
                content=result.payload["content"],
                source_novel_id=novel_id,
                source_chapter_id=result.payload.get("chapter_id"),
                source_character_id=result.payload.get("character_id"),
                metadata=result.payload.get("metadata", {}),
                importance=result.payload.get("importance", 0.5),
                vector_id=result.id
            )
            fragments.append((fragment, result.score))
        
        return fragments
    
    async def _structured_search(self,
                                novel_id: int,
                                current_chapter_id: Optional[int],
                                required_types: Optional[List[FragmentType]]) -> List[ContextFragment]:
        """结构化检索（基于规则）"""
        
        fragments = []
        
        # 获取当前章节之前的所有章节摘要
        if current_chapter_id:
            chapter_summaries = self.dao.get_chapter_summaries_before(
                novel_id, current_chapter_id, limit=5
            )
            for summary in chapter_summaries:
                fragments.append(ContextFragment(
                    id=f"summary_{summary['id']}",
                    type=FragmentType.CHAPTER_SUMMARY,
                    content=summary["summary"],
                    source_novel_id=novel_id,
                    source_chapter_id=summary["id"],
                    priority=FragmentPriority.HIGH
                ))
        
        # 获取主要角色当前状态
        characters = self.dao.get_active_characters(novel_id)
        for char in characters:
            if char["importance"] >= 4:  # 主要角色
                fragments.append(ContextFragment(
                    id=f"char_state_{char['id']}",
                    type=FragmentType.CHARACTER_STATE,
                    content=f"{char['name']}: {json.dumps(char['attributes'])}",
                    source_novel_id=novel_id,
                    source_character_id=char["id"],
                    priority=FragmentPriority.CRITICAL
                ))
        
        # 获取相关世界设定
        world_facts = self.dao.get_relevant_world_facts(novel_id, current_chapter_id)
        for fact in world_facts:
            fragments.append(ContextFragment(
                id=f"world_{fact['id']}",
                type=FragmentType.WORLD_FACT,
                content=f"{fact['name']}: {fact['description']}",
                source_novel_id=novel_id,
                priority=FragmentPriority.NORMAL
            ))
        
        return fragments
    
    def _merge_results(self,
                      vector_results: List[Tuple[ContextFragment, float]],
                      struct_results: List[ContextFragment]) -> List[ContextFragment]:
        """合并向量检索和结构化检索结果"""
        
        # 去重（基于ID）
        seen_ids = set()
        merged = []
        
        # 优先加入结构化结果（更精确）
        for fragment in struct_results:
            if fragment.id not in seen_ids:
                seen_ids.add(fragment.id)
                merged.append(fragment)
        
        # 加入向量结果（补充）
        for fragment, score in vector_results:
            if fragment.id not in seen_ids:
                seen_ids.add(fragment.id)
                # 将相似度分数作为重要性参考
                fragment.importance = max(fragment.importance, score)
                merged.append(fragment)
        
        return merged
    
    async def _rerank(self,
                     fragments: List[ContextFragment],
                     query: str,
                     novel_id: int,
                     current_chapter_id: Optional[int]) -> List[ContextFragment]:
        """重排序"""
        
        scored_fragments = []
        
        for fragment in fragments:
            score = 0.0
            
            # 语义分数（如果有向量检索分数）
            if fragment.importance > 0.5:
                score += fragment.importance * self.weights["semantic"]
            
            # 时间邻近性
            if current_chapter_id and fragment.source_chapter_id:
                distance = abs(current_chapter_id - fragment.source_chapter_id)
                temporal_score = 1.0 / (1.0 + distance * 0.1)
                score += temporal_score * self.weights["temporal"]
            
            # 结构重要性
            priority_scores = {
                FragmentPriority.CRITICAL: 1.0,
                FragmentPriority.HIGH: 0.8,
                FragmentPriority.NORMAL: 0.5,
                FragmentPriority.LOW: 0.3,
                FragmentPriority.OPTIONAL: 0.1
            }
            score += priority_scores.get(fragment.priority, 0.5) * self.weights["structural"]
            
            # 使用频率（越常用越重要）
            freq_score = min(fragment.retrieval_count / 10.0, 1.0)
            score += freq_score * self.weights["frequency"]
            
            # 最近使用
            if fragment.last_retrieved:
                hours_ago = (datetime.now() - fragment.last_retrieved).total_seconds() / 3600
                recency_score = 1.0 / (1.0 + hours_ago * 0.1)
                score += recency_score * self.weights["recency"]
            
            scored_fragments.append((fragment, score))
        
        # 按分数排序
        scored_fragments.sort(key=lambda x: x[1], reverse=True)
        
        return [f for f, _ in scored_fragments]
```

### 5.4 上下文窗口管理

```python
# src/deepnovel/context/window_manager.py
class WindowManager:
    """上下文窗口管理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.tokenizer = TokenCounter()  # 需要实现
    
    async def build_window(self,
                          fragments: List[ContextFragment],
                          system_prompt: str,
                          user_prompt: str,
                          max_tokens: int = 8000) -> ContextWindow:
        """构建上下文窗口"""
        
        window = ContextWindow(
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # 计算预留空间
        system_tokens = self.tokenizer.count(system_prompt)
        user_tokens = self.tokenizer.count(user_prompt)
        available_tokens = max_tokens - system_tokens - user_tokens - window.reserved_tokens
        
        # 按优先级分组
        priority_groups = {
            FragmentPriority.CRITICAL: [],
            FragmentPriority.HIGH: [],
            FragmentPriority.NORMAL: [],
            FragmentPriority.LOW: [],
            FragmentPriority.OPTIONAL: []
        }
        
        for fragment in fragments:
            priority_groups[fragment.priority].append(fragment)
        
        # 逐级填充
        current_tokens = 0
        selected_fragments = []
        
        for priority in [FragmentPriority.CRITICAL, FragmentPriority.HIGH, 
                        FragmentPriority.NORMAL, FragmentPriority.LOW]:
            for fragment in priority_groups[priority]:
                fragment_tokens = self.tokenizer.count(fragment.to_prompt_text())
                
                if current_tokens + fragment_tokens <= available_tokens:
                    selected_fragments.append(fragment)
                    current_tokens += fragment_tokens
                else:
                    # 尝试截断
                    truncated = self._truncate_fragment(fragment, 
                                                       available_tokens - current_tokens)
                    if truncated:
                        selected_fragments.append(truncated)
                        current_tokens += self.tokenizer.count(truncated.to_prompt_text())
                    else:
                        window.excluded_fragments.append(fragment)
        
        window.fragments = selected_fragments
        window.total_tokens = current_tokens + system_tokens + user_tokens
        window.fragment_count = len(selected_fragments)
        
        return window
    
    def _truncate_fragment(self, fragment: ContextFragment, 
                          max_tokens: int) -> Optional[ContextFragment]:
        """截断片段以适应窗口"""
        
        text = fragment.content
        tokens = self.tokenizer.count(text)
        
        if tokens <= max_tokens:
            return fragment
        
        # 尝试智能截断
        # 保留开头和结尾，中间用省略号
        head_tokens = max_tokens // 3
        tail_tokens = max_tokens // 3
        
        head_text = self.tokenizer.truncate(text, head_tokens)
        tail_text = self.tokenizer.truncate(text[-1000:], tail_tokens)  # 从末尾
        
        truncated_content = f"{head_text}\n...（省略中间部分）...\n{tail_text}"
        
        return ContextFragment(
            id=f"{fragment.id}_truncated",
            type=fragment.type,
            content=truncated_content,
            source_novel_id=fragment.source_novel_id,
            source_chapter_id=fragment.source_chapter_id,
            importance=fragment.importance * 0.8,  # 降低重要性
            priority=fragment.priority
        )
```

### 5.5 上下文更新器

```python
# src/deepnovel/context/updater.py
class ContextUpdater:
    """上下文更新器 - 生成后更新上下文"""
    
    def __init__(self, dao, qdrant_client, embedder):
        self.dao = dao
        self.qdrant = qdrant_client
        self.embedder = embedder
    
    async def update_after_generation(self,
                                     novel_id: int,
                                     chapter_id: int,
                                     generated_content: str,
                                     generation_metadata: Dict):
        """生成后更新上下文"""
        
        updates = []
        
        # 1. 提取并更新章节摘要
        chapter_summary = await self._extract_chapter_summary(generated_content)
        updates.append(self._create_fragment(
            novel_id, chapter_id, None,
            FragmentType.CHAPTER_SUMMARY,
            chapter_summary,
            FragmentPriority.HIGH
        ))
        
        # 2. 提取角色状态变化
        character_changes = await self._extract_character_changes(generated_content)
        for char_id, state_change in character_changes.items():
            updates.append(self._create_fragment(
                novel_id, chapter_id, char_id,
                FragmentType.CHARACTER_STATE,
                json.dumps(state_change),
                FragmentPriority.CRITICAL
            ))
            
            # 更新角色数据库状态
            self.dao.update_character_state(char_id, state_change)
        
        # 3. 提取对话样本
        dialogues = self._extract_dialogues(generated_content)
        for dialogue in dialogues:
            updates.append(self._create_fragment(
                novel_id, chapter_id, dialogue["speaker_id"],
                FragmentType.DIALOGUE_SAMPLE,
                dialogue["text"],
                FragmentPriority.NORMAL
            ))
        
        # 4. 提取情节点
        plot_points = await self._extract_plot_points(generated_content)
        for plot in plot_points:
            updates.append(self._create_fragment(
                novel_id, chapter_id, None,
                FragmentType.PLOT_POINT,
                plot["description"],
                FragmentPriority.HIGH
            ))
        
        # 5. 提取世界设定使用
        world_usage = self._extract_world_usage(generated_content)
        for usage in world_usage:
            updates.append(self._create_fragment(
                novel_id, chapter_id, None,
                FragmentType.WORLD_FACT,
                usage,
                FragmentPriority.NORMAL
            ))
        
        # 6. 批量保存到数据库和向量库
        await self._save_fragments(updates)
        
        return updates
    
    async def _save_fragments(self, fragments: List[ContextFragment]):
        """批量保存片段"""
        
        # 保存到SQLite
        for fragment in fragments:
            self.dao.save_context_fragment(fragment)
        
        # 生成向量并保存到Qdrant
        texts = [f.content for f in fragments]
        embeddings = await self.embedder.embed_batch(texts)
        
        points = []
        for fragment, embedding in zip(fragments, embeddings):
            fragment.vector_id = f"vec_{fragment.id}"
            points.append({
                "id": fragment.vector_id,
                "vector": embedding,
                "payload": {
                    "fragment_id": fragment.id,
                    "novel_id": fragment.source_novel_id,
                    "type": fragment.type.value,
                    "chapter_id": fragment.source_chapter_id,
                    "character_id": fragment.source_character_id,
                    "importance": fragment.importance,
                    "content": fragment.content[:1000]  # 存储前1000字用于展示
                }
            })
        
        self.qdrant.upsert(
            collection_name="context_fragments",
            points=points
        )
    
    async def _extract_chapter_summary(self, content: str) -> str:
        """提取章节摘要（使用LLM）"""
        prompt = f"请为以下内容生成200字以内的摘要：\n\n{content[:3000]}"
        summary = await self.llm.generate(prompt, max_tokens=300)
        return summary
    
    async def _extract_character_changes(self, content: str) -> Dict[int, Dict]:
        """提取角色状态变化"""
        # 使用LLM或规则提取
        # 返回 {character_id: {location, mood, health, ...}}
        pass
    
    def _extract_dialogues(self, content: str) -> List[Dict]:
        """提取对话样本"""
        # 正则提取对话
        pass
    
    async def _extract_plot_points(self, content: str) -> List[Dict]:
        """提取情节点"""
        prompt = "请从以下内容中提取关键情节点："
        # ...
        pass
    
    def _extract_world_usage(self, content: str) -> List[str]:
        """提取世界设定使用"""
        # 匹配世界设定关键词
        pass
    
    def _create_fragment(self, novel_id, chapter_id, character_id,
                        fragment_type, content, priority) -> ContextFragment:
        """创建片段"""
        return ContextFragment(
            id=f"frag_{novel_id}_{chapter_id}_{fragment_type.value}_{int(time.time())}",
            type=fragment_type,
            content=content,
            source_novel_id=novel_id,
            source_chapter_id=chapter_id,
            source_character_id=character_id,
            priority=priority
        )
```

---

## 实施路线图

### Phase 1: 数据层重构（2-3周）
- [ ] 设计SQLite schema
- [ ] 实现基础DAO层
- [ ] 迁移现有数据
- [ ] 集成Qdrant本地模式
- [ ] 文件存储结构实现

### Phase 2: 任务管理层（2-3周）
- [ ] 设计任务状态机
- [ ] 实现可暂停/恢复的任务执行
- [ ] 细粒度步骤分解
- [ ] 检查点保存/恢复
- [ ] WebSocket实时状态推送

### Phase 3: 任务调度层（2周）
- [ ] 优先级队列实现
- [ ] Token桶限流
- [ ] 调度策略（质量优先）
- [ ] 依赖管理
- [ ] 资源预估

### Phase 4: 消息通信（1-2周）
- [ ] 事件总线实现
- [ ] WebSocket连接管理
- [ ] 流式生成输出
- [ ] 事件持久化

### Phase 5: 上下文管理（3-4周）
- [ ] 上下文片段定义
- [ ] 向量检索实现
- [ ] 混合检索策略
- [ ] 窗口管理
- [ ] 上下文更新器
- [ ] 一致性检查

---

## 关键技术决策

1. **SQLite + WAL模式**：支持读写并发，足够单机使用
2. **Qdrant本地模式**：无需Docker，直接嵌入
3. **文件存储大文本**：避免数据库膨胀
4. **细粒度生成步骤**：每步可暂停、可恢复
5. **强制检索-生成-更新循环**：保证上下文一致性
6. **流式输出**：实时看到生成进度

---

*文档版本: v1.0*
*更新日期: 2026-04-28*
*作者: 小R*
