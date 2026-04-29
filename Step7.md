# Step 7: 小说配置补全模块重构 - 类型安全+LLM驱动的动态配置系统

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step1-6
> 目标: 构建类型安全、LLM驱动、模板化的小说配置系统

---

## 1. 设计哲学

### 1.1 核心转变

```
从：字典+字符串的配置     → 到：Pydantic类型安全模型
从：静态Prompt字符串      → 到：Jinja2动态模板引擎
从：规则-based配置扩展    → 到：LLM-driven智能补全
从：硬编码genre枚举       → 到：可扩展配置预设库
从：单文件配置管理       → 到：分层配置继承系统
从：LLM输出JSON手动解析   → 到：结构化生成强制合规
```

### 1.2 设计原则

1. **类型即文档**: Pydantic模型即配置规范，IDE自动补全，运行时验证
2. **模糊输入→精确配置**: 用户说"写一个修仙小说"→LLM补全完整世界观+角色+大纲配置
3. **模板即代码**: Prompt模板使用Jinja2，支持变量、条件、循环、宏
4. **配置可继承**: 基础配置 → 预设 → 用户输入 → LLM补全，层层叠加
5. **生成即合规**: 使用结构化生成（Structured Generation）强制LLM输出符合Schema
6. **预设可组合**: Genre + Style + Tone + POV 四维组合，自动推导兼容配置

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **Pydantic Settings** (v2) | 类型安全配置、环境变量注入、验证器 | Python配置管理 |
| **Hydra** (Meta) | 分层配置组合、命令行覆盖、配置组 | 复杂实验配置 |
| **OmegaConf** | 结构化配置、类型安全、配置合并 | ML流水线配置 |
| **Jinja2** | 模板继承、宏、条件、过滤器 | Prompt模板引擎 |
| **LangChain PromptTemplate** | 变量插值、部分填充、示例选择 | LLM Prompt管理 |
| **Instructor / Outlines** | 结构化生成、Pydantic输出 | LLM输出合规 |
| **DSPy** | 声明式LLM编程、自动优化Prompt | LLM程序优化 |
| **Django Settings** | 环境分离、懒加载、本地覆盖 | 多环境部署 |

---

## 2. 现状诊断

### 2.1 当前组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| ConfigEnhancerAgent | `agents/config_enhancer.py` | 纯规则扩展，**从未调用LLM**；Schema有拼写错误（`" POV"` `"yOUNG_ADULT"`）；字符串匹配路由 | **严重** |
| ConfigManager | `config/manager.py` | 懒加载逻辑**重复3次**；环境配置路径可能不存在 | **中** |
| AINovelsSchemas | `config/validator.py` | 数据库Schema**要求所有4个DB必填**；novel配置无Schema | **中** |
| Prompt Presets | `config/prompts/presets.json` | 只有3个简单预设，无组合逻辑 | **中** |
| Generation Templates | `config/prompts/templates/generation_templates.json` | 静态JSON，**无变量替换系统** | **严重** |
| System Prompts | `config/prompts/system_prompts/*.py` | 纯Python字符串常量，无模板化 | **中** |
| WorldBuilder | `agents/world_builder.py` | JSON提取脆弱（`find('{')`），fallback硬编码英文 | **严重** |
| CharacterGenerator | `agents/character_generator.py` | 同上，Character dataclass大小写不一致 | **中** |
| ContentGenerator | `agents/content_generator.py` | StyleConstraint引用不存在的枚举值 | **严重** |

### 2.2 核心问题总结

```
1. 无类型安全          → 配置错误在运行时才发现
2. 无LLM驱动补全       → 用户输入"修仙小说"不会自动扩展世界观
3. 无模板引擎          → Prompt是静态字符串，无法动态注入变量
4. Schema不统一        → config_enhancer.py和validator.py各自为政
5. 无结构化生成        → LLM输出JSON需要手动解析，容易出错
6. 预设系统简陋        → 只有3个预设，无组合推导
7. 配置无继承          → 每个配置从头写，无法复用基础设定
8. 多语言支持混乱      → 中文小说用英文配置键和fallback模板
```

---

## 3. 架构总览

### 3.1 配置系统四层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 4: 应用层 (Application)                                        │
│  • NovelConfigService    - 小说配置服务入口                          │
│  • ConfigPresetsUI       - 前端预设选择界面                          │
│  • ConfigWizard          - 交互式配置引导                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 配置引擎层 (Config Engine)                                  │
│  • ConfigComposer        - 配置组合（基础→预设→用户→LLM补全）        │
│  • LLMConfigCompleter    - LLM驱动的智能补全                         │
│  • StructuredGenerator   - 结构化生成（强制Schema合规）              │
│  • ConfigValidator       - Pydantic+JSON Schema双验证                │
│  • PresetManager         - 预设库管理（组合推导）                     │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 模板引擎层 (Template Engine)                                │
│  • PromptTemplateEngine  - Jinja2模板引擎                            │
│  • TemplateRegistry      - 模板注册中心                              │
│  • DynamicPromptBuilder  - 动态Prompt构建器                          │
│  • ExampleSelector       - 少样本示例选择器                          │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 数据模型层 (Data Models)                                    │
│  • NovelConfig (Pydantic) - 小说配置模型                             │
│  • WorldConfig (Pydantic) - 世界配置模型                             │
│  • CharacterConfig (Pydantic) - 角色配置模型                         │
│  • OutlineConfig (Pydantic) - 大纲配置模型                           │
│  • PromptTemplate (Pydantic) - 模板模型                              │
│  • ConfigPreset (Pydantic) - 预设模型                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 配置补全流程

```
用户输入: "我想写一个修仙小说，主角叫林凡"
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. 输入解析 (Input Parser)                                    │
│    - 提取已知字段: genre="修仙", protagonist_name="林凡"      │
│    - 识别意图: 创建新小说配置                                  │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. 预设匹配 (Preset Matcher)                                  │
│    - Genre="修仙" → 匹配 xianxia preset                        │
│    - 加载预设默认值: world_type="东方玄幻", power_system="灵气" │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. 配置组合 (Config Composer)                                 │
│    - 基础默认值                                               │
│    - + 预设覆盖 (xianxia)                                     │
│    - + 用户输入 (genre, protagonist_name)                     │
│    = 部分填充的NovelConfig                                    │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. LLM智能补全 (LLM Completer)                                │
│    - 识别缺失字段: world_setting, protagonist_background...    │
│    - 构建补全Prompt（含已知上下文）                            │
│    - 调用LLM生成缺失配置                                       │
│    - 结构化解析为Pydantic模型                                  │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. 验证与修正 (Validation)                                    │
│    - Pydantic模型验证                                          │
│    - 自定义业务规则验证                                        │
│    - 一致性检查（如：修仙小说不应有科技元素）                  │
│    - 如有错误，反馈给LLM重新生成                               │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. 配置固化 (Persistence)                                     │
│    - 保存到数据库                                              │
│    - 生成配置版本ID                                            │
│    - 返回完整配置给用户                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 核心组件设计

### 4.1 Pydantic配置模型层

**职责**: 定义类型安全的小说配置数据模型

```python
# src/deepnovel/config/models/novel.py

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator, field_validator
from enum import Enum
from datetime import datetime


class GenreType(str, Enum):
    """小说类型枚举"""
    ROMANCE = "romance"
    SCI_FI = "sci-fi"
    FANTASY = "fantasy"
    MYSTERY = "mystery"
    DRAMA = "drama"
    ADVENTURE = "adventure"
    HISTORY = "history"
    XIUXIA = "xianxia"           # 修仙
    WUXIA = "wuxia"              # 武侠
    URBAN_FANTASY = "urban_fantasy"
    HORROR = "horror"
    THRILLER = "thriller"
    OTHER = "other"


class ToneType(str, Enum):
    """基调类型"""
    DARK = "dark"
    LIGHT = "light"
    SERIOUS = "serious"
    HUMOROUS = "humorous"
    EPIC = "epic"
    INTIMATE = "intimate"
    MELANCHOLIC = "melancholic"
    HOPEFUL = "hopeful"


class PaceType(str, Enum):
    """节奏类型"""
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class POVType(str, Enum):
    """视角类型"""
    FIRST_PERSON = "first_person"
    THIRD_PERSON_LIMITED = "third_person_limited"
    THIRD_PERSON_OMNISCIENT = "third_person_omniscient"
    SECOND_PERSON = "second_person"


class TargetAudience(str, Enum):
    """目标受众"""
    CHILDREN = "children"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    ALL_AGES = "all_ages"


class StyleType(str, Enum):
    """叙事风格"""
    DESCRIPTIVE = "descriptive"           # 描写型
    CONCISE = "concise"                   # 简洁型
    POETIC = "poetic"                     # 诗意型
    DIALOGUE_HEAVY = "dialogue_heavy"     # 对话型
    STREAM_OF_CONSCIOUSNESS = "stream_of_consciousness"  # 意识流
    REPORTER = "reporter"                 # 报道型


class PowerSystemType(str, Enum):
    """力量体系类型"""
    MAGIC = "magic"                       # 魔法
    QI_CULTIVATION = "qi_cultivation"     # 灵气修炼
    TECHNOLOGY = "technology"             # 科技
    PSIONIC = "psionic"                   # 灵能
    DIVINE = "divine"                     # 神力
    NONE = "none"


# ───────────────────────────────────────────────
# 嵌套配置模型
# ───────────────────────────────────────────────

class WorldConfig(BaseModel):
    """世界配置"""
    world_name: Optional[str] = Field(None, description="世界名称")
    world_description: Optional[str] = Field(None, description="世界描述")
    geography: Optional[str] = Field(None, description="地理环境")
    cultures: List[str] = Field(default_factory=list, description="文化体系")
    factions: List[str] = Field(default_factory=list, description="势力/门派")
    power_system: PowerSystemType = Field(PowerSystemType.NONE, description="力量体系")
    power_system_details: Optional[str] = Field(None, description="力量体系详细设定")
    historical_events: List[str] = Field(default_factory=list, description="历史事件")
    rules: List[str] = Field(default_factory=list, description="世界规则")
    technology_level: Optional[str] = Field(None, description="科技水平")


class CharacterArcConfig(BaseModel):
    """角色弧线配置"""
    arc_type: Literal["growth", "fall", "circular", "flat"] = "growth"
    initial_state: Optional[str] = None
    turning_points: List[str] = Field(default_factory=list)
    final_state: Optional[str] = None


class CharacterConfig(BaseModel):
    """角色配置"""
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    char_type: Literal["protagonist", "antagonist", "supporting", "mentor", "foil"] = "supporting"
    age: Optional[int] = Field(None, ge=0, le=1000)
    gender: Optional[Literal["male", "female", "non_binary", "unknown"]] = None
    appearance: Optional[str] = Field(None, description="外貌描述")
    personality: List[str] = Field(default_factory=list, description="性格特征")
    background: Optional[str] = Field(None, description="背景故事")
    goals: List[str] = Field(default_factory=list, description="目标")
    fears: List[str] = Field(default_factory=list, description="恐惧")
    secrets: List[str] = Field(default_factory=list, description="秘密")
    skills: List[str] = Field(default_factory=list, description="技能/能力")
    relationships: Dict[str, str] = Field(default_factory=dict, description="与其他角色的关系")
    arc: Optional[CharacterArcConfig] = None
    voice_style: Optional[str] = Field(None, description="说话风格")


class ChapterConfig(BaseModel):
    """章节配置"""
    chapter_number: int = Field(..., ge=1)
    title: Optional[str] = None
    word_count_target: int = Field(3000, ge=500, le=50000)
    plot_points: List[str] = Field(default_factory=list)
    characters_present: List[str] = Field(default_factory=list)
    setting: Optional[str] = None
    tone_shift: Optional[str] = None
    cliffhanger: bool = False


class ThreeActStructure(BaseModel):
    """三幕结构"""
    act_1_chapters: int = Field(3, ge=1, description="第一幕章节数")
    act_2_chapters: int = Field(10, ge=1, description="第二幕章节数")
    act_3_chapters: int = Field(3, ge=1, description="第三幕章节数")
    inciting_incident_chapter: Optional[int] = None
    first_plot_point_chapter: Optional[int] = None
    midpoint_chapter: Optional[int] = None
    second_plot_point_chapter: Optional[int] = None
    climax_chapter: Optional[int] = None


class EmotionalArcConfig(BaseModel):
    """情感弧线配置"""
    stage_name: str
    intensity: int = Field(5, ge=1, le=10)
    description: Optional[str] = None


class OutlineConfig(BaseModel):
    """大纲配置"""
    three_act_structure: ThreeActStructure = Field(default_factory=ThreeActStructure)
    emotional_arc: List[EmotionalArcConfig] = Field(default_factory=list)
    chapters: List[ChapterConfig] = Field(default_factory=list)
    main_plot_threads: List[str] = Field(default_factory=list)
    subplot_threads: List[str] = Field(default_factory=list)
    foreshadowing_points: List[str] = Field(default_factory=list)
    twists: List[str] = Field(default_factory=list)


# ───────────────────────────────────────────────
# 主配置模型
# ───────────────────────────────────────────────

class NovelConfig(BaseModel):
    """
    小说完整配置

    这是核心配置模型，所有小说生成任务的基础。
    """
    # 基础信息
    novel_id: Optional[str] = Field(None, description="小说唯一ID")
    title: str = Field(..., min_length=1, max_length=100, description="小说标题")
    genre: GenreType = Field(..., description="小说类型")
    subtitle: Optional[str] = Field(None, description="副标题")
    description: Optional[str] = Field(None, description="简介")

    # 叙事参数
    style: StyleType = Field(StyleType.DESCRIPTIVE, description="叙事风格")
    tone: ToneType = Field(ToneType.SERIOUS, description="基调")
    pace: PaceType = Field(PaceType.MEDIUM, description="节奏")
    pov: POVType = Field(POVType.THIRD_PERSON_LIMITED, description="视角")
    target_audience: TargetAudience = Field(TargetAudience.ADULT, description="目标受众")
    language: str = Field("zh-CN", description="语言")

    # 结构参数
    max_chapters: int = Field(50, ge=1, le=1000, description="最大章节数")
    word_count_per_chapter: int = Field(3000, ge=500, le=50000, description="每章目标字数")
    total_word_count_target: Optional[int] = Field(None, description="总目标字数")

    # 世界观
    world: WorldConfig = Field(default_factory=WorldConfig)

    # 角色
    characters: List[CharacterConfig] = Field(default_factory=list)

    # 大纲
    outline: OutlineConfig = Field(default_factory=OutlineConfig)

    # 主题与标签
    themes: List[str] = Field(default_factory=list, description="主题")
    tags: List[str] = Field(default_factory=list, description="标签")
    tropes: List[str] = Field(default_factory=list, description="套路/桥段")

    # 写作约束
    writing_constraints: Dict[str, Any] = Field(default_factory=dict, description="写作约束")
    forbidden_elements: List[str] = Field(default_factory=list, description="禁止元素")
    required_elements: List[str] = Field(default_factory=list, description="必须包含元素")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = Field("1.0", description="配置版本")
    preset_name: Optional[str] = Field(None, description="使用的预设名称")

    # 运行时配置
    llm_override: Optional[Dict[str, Any]] = Field(None, description="LLM参数覆盖")
    rag_enabled: bool = Field(True, description="是否启用RAG")
    auto_save: bool = Field(True, description="是否自动保存")

    @field_validator("total_word_count_target")
    @classmethod
    def validate_total_word_count(cls, v, info):
        """验证总字数目标是否合理"""
        if v is not None:
            data = info.data
            max_chapters = data.get("max_chapters", 50)
            word_per_ch = data.get("word_count_per_chapter", 3000)
            expected = max_chapters * word_per_ch
            if v > expected * 2 or v < expected * 0.5:
                raise ValueError(f"总字数目标({v})与章节配置不匹配，预期范围: {expected * 0.5:.0f} - {expected * 2:.0f}")
        return v

    @field_validator("characters")
    @classmethod
    def validate_protagonist_exists(cls, v):
        """验证至少有一个主角"""
        if v and not any(c.char_type == "protagonist" for c in v):
            raise ValueError("至少需要一个主角(protagonist)")
        return v

    def get_protagonist(self) -> Optional[CharacterConfig]:
        """获取主角"""
        for char in self.characters:
            if char.char_type == "protagonist":
                return char
        return None

    def estimate_total_word_count(self) -> int:
        """估算总字数"""
        return self.max_chapters * self.word_count_per_chapter

    def to_generation_context(self) -> Dict[str, Any]:
        """转换为生成上下文（供Prompt模板使用）"""
        return {
            "title": self.title,
            "genre": self.genre.value,
            "genre_display": self._get_genre_display(),
            "style": self.style.value,
            "tone": self.tone.value,
            "pace": self.pace.value,
            "pov": self.pov.value,
            "pov_display": self._get_pov_display(),
            "max_chapters": self.max_chapters,
            "word_count_per_chapter": self.word_count_per_chapter,
            "world_name": self.world.world_name,
            "world_description": self.world.world_description,
            "power_system": self.world.power_system.value,
            "protagonist_name": self.get_protagonist().name if self.get_protagonist() else "主角",
            "protagonist_background": self.get_protagonist().background if self.get_protagonist() else "",
            "themes": ", ".join(self.themes) if self.themes else "未指定",
            "language": "中文" if self.language.startswith("zh") else "English",
        }

    def _get_genre_display(self) -> str:
        """获取类型显示名称"""
        genre_names = {
            GenreType.XIUXIA: "修仙",
            GenreType.WUXIA: "武侠",
            GenreType.ROMANCE: "言情",
            GenreType.FANTASY: "奇幻",
            GenreType.SCI_FI: "科幻",
            GenreType.MYSTERY: "悬疑",
            GenreType.HISTORY: "历史",
        }
        return genre_names.get(self.genre, self.genre.value)

    def _get_pov_display(self) -> str:
        """获取视角显示名称"""
        pov_names = {
            POVType.FIRST_PERSON: "第一人称",
            POVType.THIRD_PERSON_LIMITED: "第三人称有限",
            POVType.THIRD_PERSON_OMNISCIENT: "第三人称全知",
        }
        return pov_names.get(self.pov, self.pov.value)

    class Config:
        """Pydantic配置"""
        use_enum_values = True
        validate_assignment = True
```

### 4.2 模板引擎层

**职责**: Jinja2模板引擎，支持变量替换、条件、循环、继承

```python
# src/deepnovel/config/templates/engine.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import json

from jinja2 import Environment, FileSystemLoader, BaseLoader, Template as JinjaTemplate
from jinja2.exceptions import TemplateNotFound

from src.deepnovel.utils import get_logger

logger = get_logger()


@dataclass
class PromptTemplate:
    """Prompt模板定义"""
    name: str
    description: str
    template_text: str
    input_variables: List[str]
    output_format: Optional[Dict[str, Any]] = None
    example_inputs: Optional[List[Dict]] = None
    tags: List[str] = None
    version: str = "1.0"


class PromptTemplateEngine:
    """
    Prompt模板引擎

    基于Jinja2，支持：
    1. 变量插值: {{ variable }}
    2. 条件渲染: {% if condition %}...{% endif %}
    3. 循环渲染: {% for item in items %}...{% endfor %}
    4. 模板继承: {% extends "base" %}
    5. 宏定义: {% macro name() %}...{% endmacro %}
    6. 自定义过滤器
    """

    def __init__(self, template_dir: str = "config/prompts"):
        self._template_dir = Path(template_dir)
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=False
        )
        self._register_filters()
        self._in_memory_templates: Dict[str, PromptTemplate] = {}

    def _register_filters(self):
        """注册自定义Jinja2过滤器"""

        def json_pretty(value):
            """JSON格式化"""
            return json.dumps(value, ensure_ascii=False, indent=2)

        def join_comma(value):
            """逗号连接列表"""
            if isinstance(value, list):
                return "、".join(str(v) for v in value)
            return str(value)

        def bullet_list(value):
            """项目符号列表"""
            if isinstance(value, list):
                return "\n".join(f"- {v}" for v in value)
            return str(value)

        def numbered_list(value):
            """编号列表"""
            if isinstance(value, list):
                return "\n".join(f"{i+1}. {v}" for i, v in enumerate(value))
            return str(value)

        def chinese_number(value):
            """数字转中文"""
            num_map = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
                      6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
            return num_map.get(value, str(value))

        self._env.filters["json_pretty"] = json_pretty
        self._env.filters["join_comma"] = join_comma
        self._env.filters["bullet_list"] = bullet_list
        self._env.filters["numbered_list"] = numbered_list
        self._env.filters["chinese_number"] = chinese_number

    def load_template(self, name: str) -> PromptTemplate:
        """从文件加载模板"""
        try:
            jinja_template = self._env.get_template(f"{name}.j2")

            # 尝试加载元数据
            meta_path = self._template_dir / f"{name}.json"
            metadata = {}
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

            return PromptTemplate(
                name=name,
                description=metadata.get("description", ""),
                template_text=jinja_template.source if hasattr(jinja_template, 'source') else "",
                input_variables=metadata.get("input_variables", []),
                output_format=metadata.get("output_format"),
                example_inputs=metadata.get("example_inputs"),
                tags=metadata.get("tags", []),
                version=metadata.get("version", "1.0")
            )
        except TemplateNotFound:
            raise ValueError(f"Template not found: {name}")

    def register_in_memory(self, template: PromptTemplate):
        """注册内存模板"""
        self._in_memory_templates[template.name] = template
        self._env.loader.loaders.append(
            DictLoader({template.name: template.template_text})
        )

    def render(self, template_name: str, **variables) -> str:
        """渲染模板"""
        try:
            template = self._env.get_template(f"{template_name}.j2")
            return template.render(**variables)
        except TemplateNotFound:
            # 尝试内存模板
            if template_name in self._in_memory_templates:
                t = self._in_memory_templates[template_name]
                jt = JinjaTemplate(t.template_text)
                return jt.render(**variables)
            raise

    def render_string(self, template_text: str, **variables) -> str:
        """渲染字符串模板"""
        template = JinjaTemplate(template_text)
        return template.render(**variables)


class DictLoader(BaseLoader):
    """字典模板加载器"""

    def __init__(self, templates: Dict[str, str]):
        self.templates = templates

    def get_source(self, environment, template):
        if template in self.templates:
            return self.templates[template], None, lambda: True
        raise TemplateNotFound(template)
```

#### 模板示例（Jinja2）

```jinja2
{# config/prompts/novel_generation/world_building.j2 #}
【世界观生成任务】

请为以下小说生成详细的世界观设定：

小说标题：{{ title }}
类型：{{ genre_display }}
基调：{{ tone }}
力量体系：{{ power_system }}

{% if world_description %}
已有世界描述：{{ world_description }}
{% endif %}

{% if themes %}
主题：{{ themes | join_comma }}
{% endif %}

请生成以下内容：
1. 世界名称与概述
2. 地理环境（主要地点、地形、气候）
3. 文化体系（宗教、习俗、价值观）
4. 势力/门派分布
5. {{ power_system }}的详细设定
6. 关键历史事件（3-5个）
7. 世界规则与限制

{% if language == "中文" %}
请使用中文生成，注重东方美学的描写风格。
{% else %}
Please generate in English with vivid descriptions.
{% endif %}

输出格式要求：
{{ output_format | json_pretty }}
```

### 4.3 预设管理层

**职责**: 管理配置预设，支持组合推导

```python
# src/deepnovel/config/presets.py

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
from pathlib import Path

from .models.novel import NovelConfig, GenreType, StyleType, ToneType, PaceType, POVType, PowerSystemType


class ConfigPreset(BaseModel):
    """配置预设"""
    name: str
    description: str
    category: str  # "genre", "style", "tone", "pace", "pov", "combined"
    icon: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    config_delta: Dict[str, Any] = Field(default_factory=dict, description="配置增量（覆盖默认值）")
    incompatible_with: List[str] = Field(default_factory=list, description="不兼容的预设")
    requires: List[str] = Field(default_factory=list, description="需要的预设")
    popularity: int = Field(0, ge=0, description=" popularity score")


class PresetManager:
    """
    预设管理器

    管理所有配置预设，支持：
    1. 按类别查找预设
    2. 预设组合验证（检查兼容性）
    3. 自动推导互补预设
    4. 用户自定义预设CRUD
    """

    def __init__(self, presets_dir: str = "config/presets"):
        self._presets_dir = Path(presets_dir)
        self._presets: Dict[str, ConfigPreset] = {}
        self._load_builtin_presets()

    def _load_builtin_presets(self):
        """加载内置预设"""
        builtins = [
            # === 类型预设 ===
            ConfigPreset(
                name="xianxia",
                description="修仙小说：东方玄幻，灵气修炼，长生不老",
                category="genre",
                tags=["东方", "玄幻", "修炼", "仙侠"],
                config_delta={
                    "genre": "xianxia",
                    "world": {
                        "power_system": "qi_cultivation",
                        "power_system_details": "通过吸收天地灵气修炼，境界分为炼气、筑基、金丹、元婴、化神、渡劫、大乘",
                        "cultures": ["修真文明", "世俗王朝", "魔道宗门"],
                        "factions": ["正道联盟", "魔教", "散修", "妖族"]
                    },
                    "themes": ["逆天改命", "长生追求", "正邪之争", "师徒情义"],
                    "style": "descriptive",
                    "tone": "epic"
                }
            ),
            ConfigPreset(
                name="wuxia",
                description="武侠小说：江湖恩怨，快意恩仇",
                category="genre",
                tags=["武侠", "江湖", "功夫", "侠义"],
                config_delta={
                    "genre": "wuxia",
                    "world": {
                        "power_system": "martial_arts",
                        "power_system_details": "内功心法与外家功夫结合，以轻功、剑法、掌法为主",
                        "cultures": ["江湖文化", "门派文化", "朝廷势力"],
                        "factions": ["少林", "武当", "峨眉", "丐帮", "明教"]
                    },
                    "themes": ["侠义精神", "江湖恩怨", "正邪之争", "家国情怀"],
                    "style": "concise",
                    "tone": "serious"
                }
            ),
            ConfigPreset(
                name="cyberpunk",
                description="赛博朋克：高科技低生活， corporations统治",
                category="genre",
                tags=["科幻", "赛博朋克", "未来", "反乌托邦"],
                config_delta={
                    "genre": "sci-fi",
                    "world": {
                        "power_system": "technology",
                        "power_system_details": "义体改造、神经网络接入、AI辅助",
                        "technology_level": "近未来高科技",
                        "cultures": ["corporate文化", "街头文化", "黑客文化"],
                        "factions": [" megaCorp", "黑客组织", "政府", "街头帮派"]
                    },
                    "themes": ["人性与机器", "阶级分化", "监控与自由", "身份认同"],
                    "style": "concise",
                    "tone": "dark"
                }
            ),
            # === 风格预设 ===
            ConfigPreset(
                name="literary",
                description="文学风格：注重心理描写和语言美感",
                category="style",
                tags=["文学", "严肃", "心理"],
                config_delta={
                    "style": "poetic",
                    "tone": "melancholic",
                    "pace": "slow",
                    "writing_constraints": {
                        "dialogue_percentage": 0.35,
                        "description_min_ratio": 0.4,
                        "use_metaphor": True
                    }
                }
            ),
            ConfigPreset(
                name="page_turner",
                description=" page-turner：快节奏，悬念驱动",
                category="style",
                tags=["快节奏", "悬疑", "通俗"],
                config_delta={
                    "style": "concise",
                    "tone": "serious",
                    "pace": "fast",
                    "writing_constraints": {
                        "dialogue_percentage": 0.5,
                        "chapter_hook_required": True,
                        "cliffhanger_frequency": "every_chapter"
                    }
                }
            ),
            # === 基调预设 ===
            ConfigPreset(
                name="grimdark",
                description="黑暗残酷：道德模糊，世界残酷",
                category="tone",
                tags=["黑暗", "残酷", "现实主义"],
                config_delta={
                    "tone": "dark",
                    "writing_constraints": {
                        "moral_ambiguity": True,
                        "character_death_allowed": True,
                        "happy_ending_not_guaranteed": True
                    }
                }
            ),
        ]

        for preset in builtins:
            self._presets[preset.name] = preset

    def get_preset(self, name: str) -> Optional[ConfigPreset]:
        """获取预设"""
        return self._presets.get(name)

    def list_presets(self, category: str = None, tags: List[str] = None) -> List[ConfigPreset]:
        """列出预设"""
        results = list(self._presets.values())
        if category:
            results = [p for p in results if p.category == category]
        if tags:
            results = [p for p in results if any(t in p.tags for t in tags)]
        return sorted(results, key=lambda p: p.popularity, reverse=True)

    def apply_presets(self, base_config: NovelConfig, preset_names: List[str]) -> NovelConfig:
        """
        应用预设到配置

        Args:
            base_config: 基础配置
            preset_names: 预设名称列表

        Returns:
            应用后的配置
        """
        config_dict = base_config.model_dump()

        for name in preset_names:
            preset = self._presets.get(name)
            if not preset:
                continue

            # 合并配置增量（深度合并）
            self._deep_merge(config_dict, preset.config_delta)

        return NovelConfig(**config_dict)

    def check_compatibility(self, preset_names: List[str]) -> tuple[bool, List[str]]:
        """
        检查预设兼容性

        Returns:
            (是否兼容, 冲突信息列表)
        """
        conflicts = []
        presets = [self._presets.get(n) for n in preset_names if n in self._presets]

        for p1 in presets:
            for p2 in presets:
                if p1.name == p2.name:
                    continue
                if p2.name in p1.incompatible_with:
                    conflicts.append(f"'{p1.name}' 与 '{p2.name}' 不兼容")
                if p2.name in p1.requires and p2.name not in preset_names:
                    conflicts.append(f"'{p1.name}' 需要 '{p2.name}'")

        return len(conflicts) == 0, conflicts

    def suggest_complementary(self, preset_names: List[str]) -> List[ConfigPreset]:
        """
        推荐互补预设

        例如：选择了 genre=xianxia，推荐 style=descriptive, tone=epic
        """
        suggestions = []
        current_categories = {self._presets[n].category for n in preset_names if n in self._presets}

        # 推荐缺失类别的预设
        for preset in self._presets.values():
            if preset.category not in current_categories and preset.category in ["style", "tone", "pace"]:
                suggestions.append(preset)

        return suggestions[:5]

    def _deep_merge(self, base: Dict, delta: Dict):
        """深度合并字典"""
        for key, value in delta.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def add_preset(self, preset: ConfigPreset) -> bool:
        """添加自定义预设"""
        self._presets[preset.name] = preset
        return True

    def save_presets(self, path: str = None):
        """保存预设到文件"""
        save_path = path or str(self._presets_dir / "custom_presets.json")
        data = {name: preset.model_dump() for name, preset in self._presets.items()}
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

### 4.4 LLM配置补全器

**职责**: 用LLM智能补全缺失的配置字段

```python
# src/deepnovel/config/completion/llm_completer.py

from typing import Dict, Any, List, Optional, Type
import json

from ..models.novel import NovelConfig
from ..templates.engine import PromptTemplateEngine
from src.deepnovel.llm.base import BaseLLMClient
from src.deepnovel.utils import get_logger

logger = get_logger()


class LLMConfigCompleter:
    """
    LLM驱动的配置补全器

    使用LLM根据已有配置智能补全缺失字段。
    支持两种模式：
    1. 结构化生成模式：使用Instructor/Outlines强制输出符合Schema
    2. 标准模式：LLM输出JSON，手动解析验证
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        template_engine: PromptTemplateEngine,
        use_structured_generation: bool = False
    ):
        self._llm = llm_client
        self._templates = template_engine
        self._use_structured = use_structured_generation
        self._max_retries = 3

    async def complete(
        self,
        partial_config: NovelConfig,
        fields_to_complete: List[str] = None,
        context: str = ""
    ) -> NovelConfig:
        """
        补全配置

        Args:
            partial_config: 部分填充的配置
            fields_to_complete: 需要补全的字段列表，None则自动检测缺失字段
            context: 额外上下文（用户原始输入）

        Returns:
            补全后的配置
        """
        # 检测缺失字段
        if fields_to_complete is None:
            fields_to_complete = self._detect_missing_fields(partial_config)

        if not fields_to_complete:
            return partial_config

        logger.info(f"Completing fields: {fields_to_complete}")

        # 构建补全Prompt
        prompt = self._build_completion_prompt(partial_config, fields_to_complete, context)

        # 调用LLM
        for attempt in range(self._max_retries):
            try:
                if self._use_structured:
                    result = await self._structured_complete(prompt, fields_to_complete)
                else:
                    result = await self._standard_complete(prompt)

                # 合并结果
                merged = self._merge_completion(partial_config, result, fields_to_complete)

                # 验证
                validated = NovelConfig(**merged)
                return validated

            except Exception as e:
                logger.warning(f"Completion attempt {attempt + 1} failed: {e}")
                if attempt == self._max_retries - 1:
                    raise

        return partial_config

    def _detect_missing_fields(self, config: NovelConfig) -> List[str]:
        """检测缺失的关键字段"""
        missing = []
        config_dict = config.model_dump()

        # 关键字段检查
        critical_fields = {
            "title": lambda v: not v,
            "description": lambda v: not v,
            "world.world_description": lambda v: not v,
            "world.geography": lambda v: not v,
            "world.cultures": lambda v: len(v) == 0,
            "world.factions": lambda v: len(v) == 0,
            "world.power_system_details": lambda v: not v,
            "characters": lambda v: len(v) == 0,
            "outline.three_act_structure": lambda v: v.act_1_chapters == 3 and v.act_2_chapters == 10,
            "themes": lambda v: len(v) == 0,
        }

        for field_path, check in critical_fields.items():
            value = self._get_nested_value(config_dict, field_path)
            if check(value):
                missing.append(field_path)

        return missing

    def _build_completion_prompt(
        self,
        config: NovelConfig,
        fields: List[str],
        context: str
    ) -> str:
        """构建补全Prompt"""
        known_fields = config.to_generation_context()

        template_vars = {
            "title": config.title or "未命名",
            "genre": config.genre.value if config.genre else "未知",
            "genre_display": config._get_genre_display() if hasattr(config, '_get_genre_display') else str(config.genre),
            "known_config": json.dumps(known_fields, ensure_ascii=False, indent=2),
            "missing_fields": "\n".join(f"- {f}" for f in fields),
            "user_context": context,
            "language": "中文" if config.language.startswith("zh") else "English"
        }

        return self._templates.render("config_completion", **template_vars)

    async def _standard_complete(self, prompt: str) -> Dict[str, Any]:
        """标准补全（LLM输出JSON）"""
        system_prompt = "你是一个专业的小说配置补全助手。请根据已有信息生成缺失的配置字段，输出严格的JSON格式。"

        response = await self._llm.generate(prompt, system_prompt=system_prompt)

        # 提取JSON
        json_str = self._extract_json(response)
        return json.loads(json_str)

    async def _structured_complete(self, prompt: str, fields: List[str]) -> Dict[str, Any]:
        """结构化生成补全"""
        # 使用Instructor或类似库强制输出符合Schema
        # 这里为简化展示核心逻辑
        try:
            import instructor
            from openai import OpenAI

            # 创建instructor客户端
            client = instructor.from_openai(OpenAI())

            # 根据fields构建响应模型
            response_model = self._build_response_model(fields)

            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是一个专业的小说配置补全助手。"},
                    {"role": "user", "content": prompt}
                ],
                response_model=response_model
            )

            return result.model_dump()

        except ImportError:
            logger.warning("Instructor not available, falling back to standard completion")
            return await self._standard_complete(prompt)

    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        # 寻找JSON代码块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()

        # 寻找花括号
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]

        raise ValueError("No JSON found in response")

    def _merge_completion(
        self,
        base: NovelConfig,
        completion: Dict[str, Any],
        fields: List[str]
    ) -> Dict[str, Any]:
        """合并补全结果到基础配置"""
        base_dict = base.model_dump()

        for field in fields:
            if field in completion:
                self._set_nested_value(base_dict, field, completion[field])

        return base_dict

    def _get_nested_value(self, d: Dict, path: str) -> Any:
        """获取嵌套字典值"""
        keys = path.split(".")
        value = d
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _set_nested_value(self, d: Dict, path: str, value: Any):
        """设置嵌套字典值"""
        keys = path.split(".")
        current = d
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _build_response_model(self, fields: List[str]):
        """构建Pydantic响应模型（用于结构化生成）"""
        from pydantic import create_model

        field_definitions = {}
        for field in fields:
            # 简化：所有字段视为Optional[str]
            field_name = field.replace(".", "_")
            field_definitions[field_name] = (Optional[str], None)

        return create_model("CompletionResponse", **field_definitions)
```

### 4.5 配置组合器

**职责**: 组合多层配置（默认→预设→用户→LLM补全）

```python
# src/deepnovel/config/composer.py

from typing import Dict, Any, List, Optional
from pydantic import ValidationError

from .models.novel import NovelConfig
from .presets import PresetManager
from .completion.llm_completer import LLMConfigCompleter
from src.deepnovel.utils import get_logger

logger = get_logger()


class ConfigComposer:
    """
    配置组合器（已弃用 - 使用Step10的ProfileMerger替代）

    ⚠️ **DEPRECATED**: 本类功能与Step10的ProfileMerger重复。
    请使用 `from src.deepnovel.config.loader import ProfileMerger` 替代。

    保留目的：向后兼容，直到所有调用方迁移完成。

    按照优先级组合多层配置：
    1. 系统默认值
    2. 预设覆盖
    3. 用户输入
    4. LLM智能补全
    5. 运行时覆盖
    """

    def __init__(
        self,
        preset_manager: PresetManager,
        llm_completer: Optional[LLMConfigCompleter] = None
    ):
        self._presets = preset_manager
        self._completer = llm_completer

    async def compose(
        self,
        user_input: Dict[str, Any],
        preset_names: List[str] = None,
        enable_llm_completion: bool = True,
        context: str = ""
    ) -> NovelConfig:
        """
        组合完整配置

        Args:
            user_input: 用户输入的配置字段
            preset_names: 预设名称列表
            enable_llm_completion: 是否启用LLM补全
            context: 额外上下文

        Returns:
            完整的NovelConfig
        """
        # Step 1: 从系统默认值开始
        config = NovelConfig(
            title=user_input.get("title", "未命名小说"),
            genre=user_input.get("genre", "other")
        )

        # Step 2: 应用预设
        if preset_names:
            is_compatible, conflicts = self._presets.check_compatibility(preset_names)
            if not is_compatible:
                logger.warning(f"Preset conflicts detected: {conflicts}")
                # 过滤冲突的预设
                preset_names = self._resolve_conflicts(preset_names, conflicts)

            config = self._presets.apply_presets(config, preset_names)

        # Step 3: 应用用户输入
        config = self._apply_user_input(config, user_input)

        # Step 4: LLM智能补全
        if enable_llm_completion and self._completer:
            try:
                config = await self._completer.complete(config, context=context)
            except Exception as e:
                logger.error(f"LLM completion failed: {e}")
                # LLM补全失败不影响已有配置

        return config

    def _apply_user_input(self, config: NovelConfig, user_input: Dict[str, Any]) -> NovelConfig:
        """应用用户输入（覆盖已有配置）"""
        config_dict = config.model_dump()

        # 安全地更新字段
        for key, value in user_input.items():
            if key in config_dict or "." in key:
                try:
                    self._set_nested_value(config_dict, key, value)
                except Exception as e:
                    logger.warning(f"Failed to set {key}: {e}")

        try:
            return NovelConfig(**config_dict)
        except ValidationError as e:
            logger.error(f"Validation error after applying user input: {e}")
            # 返回原始配置，不应用无效输入
            return config

    def _resolve_conflicts(self, preset_names: List[str], conflicts: List[str]) -> List[str]:
        """解析预设冲突（简单策略：保留第一个，移除冲突的）"""
        resolved = preset_names.copy()
        for conflict in conflicts:
            # 解析冲突信息，移除后出现的预设
            if "与" in conflict:
                parts = conflict.split("'")
                if len(parts) >= 4:
                    p1, p2 = parts[1], parts[3]
                    idx1 = resolved.index(p1) if p1 in resolved else -1
                    idx2 = resolved.index(p2) if p2 in resolved else -1
                    if idx1 != -1 and idx2 != -1:
                        # 移除后出现的一个
                        resolved.pop(max(idx1, idx2))
        return resolved

    def _set_nested_value(self, d: Dict, path: str, value: Any):
        """设置嵌套值"""
        keys = path.split(".")
        current = d
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
```

---

## 5. 与Step1-6的对接

### 5.1 对接Step1（数据层）

| Step1组件 | 对接方式 | 用途 |
|-----------|---------|------|
| FactManager | NovelConfig.world → 世界事实 | 配置即事实，生成时自动同步 |
| CharacterMind | NovelConfig.characters → 角色心智 | 角色配置直接驱动心智初始化 |
| EventManager | NovelConfig.outline → 事件规划 | 大纲配置生成初始事件序列 |

### 5.2 对接Step2（记忆系统）

| Step2组件 | 对接方式 | 用途 |
|-----------|---------|------|
| 三级记忆 | NovelConfig持久化 → 长期记忆 | 小说配置作为长期记忆存储 |
| MemoryManager | 配置版本管理 | 支持配置的版本回溯 |

### 5.3 对接Step3（LLM层）

| Step3组件 | 对接方式 | 用途 |
|-----------|---------|------|
| LLMRouter | LLMConfigCompleter注入 | 补全器使用LLMRouter选择模型 |
| 多模型配置 | NovelConfig.llm_override | 小说级LLM参数覆盖 |

### 5.4 对接Step4（Agent层）

| Step4组件 | 对接方式 | 用途 |
|-----------|---------|------|
| BaseAgent | 配置通过共享状态传递 | Agent读取NovelConfig执行任务 |
| ToolRegistry | RAG工具 + Config工具 | 新增配置查询工具 |

### 5.5 对接Step5（调度层）

| Step5组件 | 对接方式 | 用途 |
|-----------|---------|------|
| TaskScheduler | NovelConfig作为任务输入 | 小说生成任务以NovelConfig初始化 |
| CheckpointManager | 配置版本保存 | 每个checkpoint保存对应配置版本 |

### 5.6 对接Step6（RAG层）

| Step6组件 | 对接方式 | 用途 |
|-----------|---------|------|
| RAG检索器 | NovelConfig作为检索上下文 | 配置内容注入RAG检索Prompt |
| Embedding | 配置文本向量化 | 世界设定、角色档案入向量库 |

---

## 6. 详细实施计划

### 6.1 文件变更清单

#### 新增文件

| 文件 | 职责 | 行数估计 |
|------|------|---------|
| `src/deepnovel/config/models/__init__.py` | 模型包初始化 | 20 |
| `src/deepnovel/config/models/novel.py` | NovelConfig等Pydantic模型 | 350 |
| `src/deepnovel/config/models/world.py` | 世界配置子模型 | 80 |
| `src/deepnovel/config/models/character.py` | 角色配置子模型 | 100 |
| `src/deepnovel/config/templates/__init__.py` | 模板包初始化 | 20 |
| `src/deepnovel/config/templates/engine.py` | Jinja2模板引擎 | 200 |
| `src/deepnovel/config/presets.py` | 预设管理器 | 250 |
| `src/deepnovel/config/composer.py` | 配置组合器 | 150 |
| `src/deepnovel/config/completion/__init__.py` | 补全包初始化 | 20 |
| `src/deepnovel/config/completion/llm_completer.py` | LLM配置补全 | 250 |
| `config/prompts/config_completion.j2` | 配置补全Prompt模板 | 80 |
| `config/prompts/world_building.j2` | 世界观生成模板 | 100 |
| `config/prompts/character_generation.j2` | 角色生成模板 | 80 |
| `config/presets/builtin.json` | 内置预设JSON | 150 |

#### 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/deepnovel/config/manager.py` | 集成Pydantic模型 | ConfigManager返回NovelConfig对象 |
| `src/deepnovel/config/validator.py` | 增强验证 | 添加NovelConfig验证支持 |
| `src/deepnovel/agents/config_enhancer.py` | 重构 | 使用ConfigComposer+LLM补全 |
| `src/deepnovel/agents/world_builder.py` | 模板化 | 使用Jinja2模板引擎 |
| `src/deepnovel/agents/character_generator.py` | 模板化 | 使用Jinja2模板引擎 |
| `src/deepnovel/agents/content_generator.py` | 模板化 | 使用Jinja2模板引擎 |
| `src/deepnovel/api/routes.py` | 新增端点 | /config/compose, /config/presets |
| `requirements.txt` | 新增依赖 | jinja2, pydantic-settings |

#### 删除文件

| 文件 | 说明 |
|------|------|
| `config/prompts/system_prompts/*.py` | 迁移到Jinja2模板 |
| `config/prompts/user_prompts/templates/*.json` | 迁移到Jinja2模板+元数据JSON |

### 6.2 实施阶段

#### Phase 1: Pydantic模型层（Day 1-2）

```
Day 1: 核心模型
- NovelConfig主模型
- WorldConfig / CharacterConfig / OutlineConfig 子模型
- 字段验证器（总字数、主角存在性等）
- 单元测试

Day 2: 模型工具方法
- to_generation_context() 转换
- 配置序列化/反序列化
- 配置差异计算（diff）
- 单元测试
```

#### Phase 2: 模板引擎（Day 3-4）

```
Day 3: Jinja2引擎
- PromptTemplateEngine实现
- 自定义过滤器（json_pretty, bullet_list, chinese_number等）
- 模板加载（文件+内存）
- 单元测试

Day 4: 模板迁移
- 将现有Python字符串Prompt迁移到Jinja2
- 创建模板元数据JSON
- 渲染测试（所有模板）
```

#### Phase 3: 预设系统（Day 5-6）

```
Day 5: PresetManager
- 内置预设定义（xianxia, wuxia, cyberpunk等）
- 预设组合与兼容性检查
- 互补预设推荐
- 单元测试

Day 6: ConfigComposer
- 配置组合流水线（默认→预设→用户→LLM）
- 冲突解决策略
- 与PresetManager集成
- 端到端测试
```

#### Phase 4: LLM补全（Day 7-8）

```
Day 7: LLMConfigCompleter
- 缺失字段检测
- 补全Prompt构建
- 标准模式（JSON解析）
- 单元测试

Day 8: 结构化生成
- Instructor集成（可选）
- 重试机制
- 错误处理与降级
- 集成测试
```

#### Phase 5: Agent改造（Day 9-11）

```
Day 9: ConfigEnhancerAgent重构
- 使用ConfigComposer替代硬编码规则
- LLM驱动扩展替代规则扩展
- 集成测试

Day 10: WorldBuilder/CharacterGenerator模板化
- 迁移到Jinja2模板
- NovelConfig驱动生成
- 集成测试

Day 11: ContentGenerator模板化
- 动态Prompt构建
- 配置注入上下文
- 集成测试
```

#### Phase 6: API与前端（Day 12-14）

```
Day 12: API端点
- POST /config/compose（配置组合）
- GET /config/presets（预设列表）
- POST /config/complete（LLM补全）
- GET /config/schema（配置Schema）

Day 13: 前端配置向导
- 预设选择界面
- 配置表单（动态生成）
- 实时预览

Day 14: 集成测试
- 端到端配置流程测试
- 性能测试
- 文档编写
```

### 6.3 关键里程碑

| 里程碑 | 日期 | 验收标准 |
|--------|------|---------|
| M1: 模型可用 | Day 2 | NovelConfig可创建、验证、序列化 |
| M2: 模板引擎 | Day 4 | 所有Prompt模板Jinja2化，渲染正确 |
| M3: 预设系统 | Day 6 | 5+预设可用，组合冲突检测正常工作 |
| M4: LLM补全 | Day 8 | 从"修仙小说"输入生成完整配置 |
| M5: Agent改造 | Day 11 | 所有Agent使用新配置系统 |
| M6: 生产就绪 | Day 14 | API完整，前端可用，文档齐全 |

---

## 7. 量化验收标准

### 7.1 功能验收

| 编号 | 功能 | 验收标准 |
|------|------|---------|
| F1 | 类型安全 | NovelConfig使用Pydantic，非法字段在IDE和运行时都报错 |
| F2 | 配置验证 | 必填字段缺失、字数不合理等错误自动检测 |
| F3 | 模板引擎 | Jinja2支持变量、条件、循环，自定义过滤器正常工作 |
| F4 | 预设系统 | 5+内置预设，可组合，冲突检测正确 |
| F5 | 智能补全 | 用户输入"修仙小说"可生成完整世界观+角色+大纲 |
| F6 | 结构化生成 | LLM输出可强制符合Pydantic Schema（如使用Instructor） |
| F7 | 配置继承 | 默认→预设→用户→LLM补全，层层叠加不丢失 |
| F8 | Agent集成 | 所有Agent使用NovelConfig驱动，不再硬编码 |
| F9 | 多语言 | 中文/英文配置自动切换模板语言 |
| F10 | 配置版本 | 配置可保存版本，支持diff和回滚 |
| F11 | API完整 | /config/compose, /presets, /complete端点可用 |
| F12 | 前端向导 | 用户可通过界面选择预设、填写配置、预览结果 |

### 7.2 质量验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 配置合法性 | >95% LLM补全配置通过验证 | 100次补全测试 |
| 补全相关性 | >80% 补全内容与用户意图匹配 | 人工评估 |
| 模板渲染成功率 | >99% | 所有模板渲染测试 |
| 预设组合合法性 | 100% 兼容预设组合可通过验证 | 所有组合测试 |

### 7.3 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 配置验证 | <10ms | 1000次验证取平均 |
| 模板渲染 | <50ms | 1000次渲染取平均 |
| 预设应用 | <20ms | 1000次应用取平均 |
| LLM补全 | <30s | 端到端补全流程 |

---

## 8. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| LLM补全质量不稳定 | 高 | 高 | 多重验证+回退到预设默认值 |
| Pydantic模型过于严格 | 中 | 中 | 使用Optional字段+宽松验证模式 |
| 模板迁移工作量大 | 中 | 低 | 分阶段迁移，先核心Agent |
| 用户输入与预设冲突 | 中 | 低 | 用户输入优先级高于预设，明确提示 |
| 结构化生成依赖外部库 | 低 | 中 | 标准JSON解析作为降级方案 |

---

## 9. 附录

### A. 配置补全Prompt模板

```jinja2
{# config/prompts/config_completion.j2 #}
你是一位专业的小说策划助手。请根据以下已有信息，生成缺失的小说配置字段。

【已有信息】：
```json
{{ known_config | json_pretty }}
```

【用户原始输入】：
{{ user_context }}

【需要补全的字段】：
{{ missing_fields | bullet_list }}

请生成这些字段的内容，要求：
1. 与已有信息保持一致（如类型、基调）
2. 内容具体、有创意，避免泛泛而谈
3. 符合{{ genre_display }}类型的常见套路和设定
4. 输出严格的JSON格式

输出格式：
```json
{
  {% for field in missing_fields %}
  "{{ field }}": "..."
  {% endfor %}
}
```
```

### B. 依赖清单

```
# Python新增依赖
jinja2>=3.1.0              # 模板引擎
pydantic-settings>=2.0.0   # Pydantic配置管理
instructor>=0.4.0          # 结构化生成（可选）
python-dotenv>=1.0.0       # 环境变量（已存在）
```

### C. API端点设计

```python
# 新增FastAPI端点

@router.post("/config/compose")
async def compose_config(request: ConfigComposeRequest):
    """
    组合完整小说配置

    - user_input: 用户输入字段
    - presets: 预设名称列表
    - enable_llm_completion: 是否启用LLM补全
    """
    config = await composer.compose(
        user_input=request.user_input,
        preset_names=request.presets,
        enable_llm_completion=request.enable_llm_completion,
        context=request.context
    )
    return config

@router.get("/config/presets")
async def list_presets(category: str = None, tags: List[str] = None):
    """获取配置预设列表"""
    return preset_manager.list_presets(category=category, tags=tags)

@router.post("/config/complete")
async def complete_config(request: ConfigCompleteRequest):
    """LLM补全配置"""
    partial = NovelConfig(**request.partial_config)
    completed = await llm_completer.complete(
        partial,
        fields_to_complete=request.fields,
        context=request.context
    )
    return completed

@router.get("/config/schema")
async def get_config_schema():
    """获取配置Schema（供前端动态表单）"""
    return NovelConfig.model_json_schema()
```

---

> **文档结束**
>
> 下一步：按Phase 1开始实施，优先搭建Pydantic配置模型层和Jinja2模板引擎。
