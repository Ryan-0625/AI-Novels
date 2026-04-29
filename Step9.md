# Step 9: Prompt层重构 - 可组合、可评估、可优化的工程化Prompt系统

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step1-8
> 目标: 将Prompt从静态字符串升级为可组合、可评估、可优化的工程化资产

---

## 1. 设计哲学

### 1.1 核心转变

```
从：静态Python字符串常量                        → 到：可组合Prompt组件 + Jinja2模板引擎
从：单体大Prompt（2000+字）                     → 到：原子化组件按需组装
从：f-string硬编码拼接                          → 到：声明式模板变量注入
从：零少样本示例管理                           → 到：动态示例选择（Similarity-Based）
从：无Prompt版本控制                           → 到：Git版本化 + A/B测试框架
从：JSON提取靠find('{')                        → 到：结构化输出强制 + XML标签约束
从：无评估无优化                               → 到：自动化Prompt评分 + DSPy式优化
从：中英文混杂、风格不一                       → 到：统一中文Prompt规范 + 角色一致性
```

### 1.2 设计原则

1. **Prompt即代码**: 版本控制、单元测试、CI/CD流水线一视同仁
2. **组合优于继承**: 通过原子组件组装而非复制粘贴大Prompt
3. **上下文即精度**: 动态注入检索结果（RAG）、记忆状态、世界事实
4. **示例即质量**: 少样本示例的质量直接决定输出质量，需精心管理
5. **结构即约束**: XML标签、JSON Schema、TypeScript接口约束LLM输出
6. **评估即优化**: 无评估的Prompt调优是盲人摸象，必须建立评分体系
7. **链式即推理**: 复杂任务分解为多步Prompt链，每步专注单一职责

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **DSPy** (Stanford, 2024) | 声明式Prompt编程、自动Bootstrap示例、编译器优化 | Prompt系统工程化 |
| **LangChain Prompts** (2024) | PromptTemplate、ChatPromptTemplate、FewShotPromptTemplate | 快速模板组装 |
| **OpenAI Prompt Eng** (2024) | 清晰指令、分隔符、逐步思考、指定输出格式 | 通用最佳实践 |
| **Anthropic Prompt Eng** (2024) | XML标签结构化、<thinking>标签、角色扮演 | Claude系列优化 |
| **Google Prompt Eng** (2024) | System/Context/Instruction分离、示例前置 | Gemini系列优化 |
| **Chain-of-Thought** (2022) | 逐步推理、中间步骤显式化 | 逻辑推理任务 |
| **ReAct** (2023) | Thought → Action → Observation循环 | Agent工具调用 |
| **Tree of Thoughts** (2023) | 多路径探索、自我评估、最优路径选择 | 创意生成任务 |
| **PromptLayer** (2024) | Prompt版本管理、性能追踪、A/B测试 | 生产环境优化 |
| **Guardrails AI** (2024) | 结构化输出验证、自动重试修正 | 输出合规性保障 |
| **TextGrad** (2024) | 文本梯度下降自动优化Prompt | 自动化Prompt调优 |
| **OPRO** (Google, 2024) | LLM作为优化器，迭代优化Prompt | 自动Prompt工程 |

---

## 2. 现状诊断

### 2.1 当前组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| `WORLD_BUILDER_SYSTEM_PROMPT` | `config/prompts/system_prompts/world_builder.py` | 150行静态字符串，无变量注入 | **中** |
| `CHARACTER_GENERATOR_SYSTEM_PROMPT` | `config/prompts/system_prompts/character_generator.py` | 同上，角色类型硬编码 | **中** |
| `CONTENT_WRITER_SYSTEM_PROMPT` | `config/prompts/system_prompts/content_writer.py` | 150行，风格描述混杂英文单词 | **中** |
| `OUTLINE_PLANNER_SYSTEM_PROMPT` | `config/prompts/system_prompts/outline_planner.py` | 三幕结构纯文本描述，无参数化 | **中** |
| `QUALITY_REVIEWER_SYSTEM_PROMPT` | `config/prompts/system_prompts/quality_reviewer.py` | 评分标准静态，无法动态调整权重 | **中** |
| `generation_templates.json` | `config/prompts/user_prompts/templates/` | 纯元数据描述，无实际模板内容 | **严重** |
| `pacing_tension.json` | `config/prompts/dynamic_prompts/` | JSON配置式，无法运行时组合 | **中** |
| `presets.json` | `config/prompts/system_prompts/` | 仅3个预设，无Prompt组合逻辑 | **中** |
| `world_builder._generate_locations_with_llm()` | `agents/world_builder.py:388` | f-string硬编码Prompt，无复用 | **严重** |
| `content_generator._generate_content()` | `agents/content_generator.py` | Prompt在代码中拼接，无模板 | **严重** |
| JSON解析 | 多个Agent | `find('{')` / `find('[')` 脆弱解析 | **严重** |

### 2.2 核心问题总结

```
当前状态：Prompt是"文字资产"，不是"工程资产"

1. 静态字符串 → 无法动态注入上下文（角色状态、世界事实、前文摘要）
2. 单体大Prompt → 重复内容多（每个Agent都重复"你是一个专家"），修改困难
3. 代码内拼接 → Prompt与逻辑混杂，非技术人员无法修改
4. 无少样本管理 → LLM输出格式不稳定，每次随机
5. 无版本控制 → 改坏Prompt无法回滚，无法对比效果
6. 无评估体系 → 不知道哪个Prompt版本更好
7. 解析靠字符串操作 → JSON/XML提取失败率高
8. 无推理模式 → 复杂任务没有CoT/ReAct引导
9. 中英文混杂 → "conomy的表达"、"notable Practitioners"等错误
```

---

## 3. 架构总览

### 3.1 Prompt层七层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 7: 应用层 (Application)                                        │
│  • PromptStudio          - Prompt可视化编辑器                        │
│  • PromptDebugger        - Prompt调试工具（查看注入的上下文）         │
│  • PromptA/BTest         - A/B测试面板                               │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 6: 评估优化层 (Evaluation & Optimization)                      │
│  • PromptEvaluator       - 自动评分（相关性/准确性/风格一致性）       │
│  • PromptOptimizer       - DSPy式自动优化                            │
│  • PromptVersionManager  - 版本控制与回滚                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 5: 推理模式层 (Reasoning Patterns)                             │
│  • CoTTemplate           - 链式思考模板                              │
│  • ReActTemplate         - 推理-行动循环模板                         │
│  • ToTTemplate           - 树状思考模板                              │
│  • SelfConsistency       - 自一致性多采样                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: 少样本管理层 (Few-Shot Management)                          │
│  • ExampleBank           - 示例库（按任务/质量分类）                  │
│  • ExampleSelector       - 语义相似度示例选择                        │
│  • ExampleGenerator      - LLM自动生成示例                           │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: Prompt组合层 (Prompt Composition)                           │
│  • PromptComposer        - 原子组件组装器                            │
│  • ContextInjector       - RAG/记忆/事实动态注入                     │
│  • PromptChain           - 多步Prompt链编排                          │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 模板引擎层 (Template Engine)                                │
│  • Jinja2Engine          - Jinja2模板渲染                            │
│  • CustomFilters         - 自定义过滤器（中文排版、截断、格式化）       │
│  • SchemaValidator       - 输出Schema验证                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 原子组件层 (Atomic Components)                              │
│  • RoleComponents        - 角色定义组件（作家/编辑/评论家...）        │
│  • InstructionComponents - 指令组件（生成/评估/改写...）              │
│  • FormatComponents      - 格式组件（JSON/XML/Markdown...）          │
│  • ConstraintComponents  - 约束组件（字数/风格/禁忌...）              │
│  • ContextComponents     - 上下文组件（世界/角色/前文...）            │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Prompt组装数据流

```
用户请求: "生成第5章内容"
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. 加载基础组件                                               │
│    - Role: "专业小说作家"                                     │
│    - Instruction: "根据大纲生成章节内容"                       │
│    - Format: "JSON格式，含content/chaos_events/emotional_arc" │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. 动态上下文注入 (ContextInjector)                           │
│    ├─→ retrieve_character_memory(主角ID) → 角色当前状态       │
│    ├─→ retrieve_plot_continuity(第5章) → 前文摘要+伏笔        │
│    ├─→ retrieve_world_knowledge("灵气体系") → 世界规则        │
│    ├─→ retrieve_style_reference("战斗场景") → 风格范例        │
│    └─→ fact_query(subject="主角", predicate="当前位置") → 事实 │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. 选择少样本示例 (ExampleSelector)                           │
│    - 查询示例库中"战斗场景"类型的优质示例                      │
│    - 按与当前大纲的语义相似度排序                              │
│    - 选择Top-3作为少样本示例                                   │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. 组装完整Prompt (PromptComposer)                            │
│    ├─ System Prompt: Role + Instruction + Constraint          │
│    ├─ Few-Shot Examples: [示例1, 示例2, 示例3]               │
│    ├─ User Prompt: Context + Task + Format                    │
│    └─ 输出: 完整Prompt字符串                                   │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. 应用推理模式 (可选)                                        │
│    - CoT: 在Prompt末尾添加"让我们逐步思考..."                  │
│    - ReAct: 添加工具调用Schema到System Prompt                 │
│    - ToT: 要求生成3个不同版本并自评                            │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Jinja2模板渲染                                             │
│    - 变量替换                                                 │
│    - 条件渲染（如：修仙小说才渲染"灵气"相关段落）               │
│    - 过滤器应用（中文排版优化、自动截断）                      │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. 提交LLM生成                                               │
│    - 完整Prompt → LLM Router → 生成结果                       │
│    - 输出解析（XML/JSON Schema验证）                          │
│    - 失败时自动重试（带修正指令）                              │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 8. 记录与评估                                                 │
│    - 记录Prompt版本、注入的上下文、生成结果                   │
│    - 评估输出质量（结构化评分）                               │
│    - 反馈到PromptOptimizer用于后续优化                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 核心组件设计

### 4.1 原子组件层

**职责**: 定义最小可复用的Prompt片段，支持组合和参数化

```python
# src/deepnovel/prompts/components/base.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class ComponentType(str, Enum):
    """组件类型"""
    ROLE = "role"                    # 角色定义
    INSTRUCTION = "instruction"      # 任务指令
    FORMAT = "format"                # 输出格式
    CONSTRAINT = "constraint"        # 约束条件
    CONTEXT = "context"              # 上下文信息
    EXAMPLE = "example"              # 少样本示例
    REASONING = "reasoning"          # 推理模式
    META = "meta"                    # 元指令（如"深呼吸"）


@dataclass
class PromptComponent:
    """
    Prompt原子组件

    每个组件是一个带参数的模板片段，可独立渲染后组装。
    """
    name: str
    type: ComponentType
    template: str                          # Jinja2模板字符串
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)  # 默认参数
    required_params: List[str] = field(default_factory=list)
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)

    def render(self, **kwargs) -> str:
        """渲染组件"""
        from jinja2 import Template
        # 合并默认参数和传入参数
        params = {**self.parameters, **kwargs}
        # 检查必需参数
        for req in self.required_params:
            if req not in params:
                raise ValueError(f"Component '{self.name}' requires parameter '{req}'")
        template = Template(self.template, trim_blocks=True, lstrip_blocks=True)
        return template.render(**params)


# ===== 预定义组件库 =====

class RoleComponents:
    """角色定义组件"""

    WORLD_BUILDER = PromptComponent(
        name="world_builder_role",
        type=ComponentType.ROLE,
        template="""你是一个专业的小说世界观构建专家。你精通神话学、历史学、社会学和地理学，能够创造逻辑自洽、细节丰富、令人信服的虚构世界。

你的创作风格：
- 注重内在逻辑：魔法系统必须有代价和限制
- 文化独特性：避免简单套用现实文化模板
- 历史纵深：世界有真实的过去，而非静止的舞台背景
- 地理合理性：地形、气候、资源分布影响文明发展""",
        tags=["world", "setting", "creative"]
    )

    CHARACTER_DESIGNER = PromptComponent(
        name="character_designer_role",
        type=ComponentType.ROLE,
        template="""你是一个深谙人性的角色设计师。你创造的角色不是标签的堆砌，而是有血有肉、有矛盾有挣扎的真实个体。

你的设计原则：
- 动机至上：每个行为都有深层动机驱动
- 缺陷之美：完美角色是失败的，缺陷才是魅力的来源
- 成长弧线：角色在故事中必须经历变化
- 关系网络：角色通过关系定义自我""",
        tags=["character", "design", "creative"]
    )

    STORY_WRITER = PromptComponent(
        name="story_writer_role",
        type=ComponentType.ROLE,
        template="""你是一个技艺精湛的小说家，擅长{{ genre }}题材的叙事创作。你的文字既有文学性又有可读性，能够让读者沉浸其中。

你的写作特点：
- 节奏掌控：知道何时加速、何时放慢
- 情感真实：角色的喜怒哀乐令读者共鸣
- 画面感强：场景描写如在眼前
- 对话生动：每句对话都推动情节或揭示性格""",
        parameters={"genre": "奇幻"},
        required_params=["genre"],
        tags=["writing", "narrative", "creative"]
    )

    EDITOR = PromptComponent(
        name="editor_role",
        type=ComponentType.ROLE,
        template="""你是一个苛刻但公正的文学编辑。你的职责是把好作品变成杰作，而非摧毁作者的自信。

你的审查标准：
- 逻辑硬伤 > 风格偏好（先保证故事成立）
- 角色一致性 > 情节意外（角色行为不能出戏）
- 信息密度 > 文字华丽（每句话都要有存在的理由）
- 情感真实 > 戏剧冲突（强行制造冲突不如真实的人性挣扎）""",
        tags=["review", "quality", "critical"]
    )


class FormatComponents:
    """输出格式组件"""

    JSON_FORMAT = PromptComponent(
        name="json_format",
        type=ComponentType.FORMAT,
        template="""
你必须严格按照以下JSON Schema输出，不要包含任何其他文本：

```json
{
  "{{ root_key }}": {
    {% for field, desc in fields.items() %}
    "{{ field }}": "{{ desc }}"{% if not loop.last %},{% endif %}
    {% endfor %}
  }
}
```

重要规则：
1. 只输出JSON，不要markdown代码块标记
2. 确保JSON格式完全合法
3. 所有字段都必须填充，不能为空
4. 字符串值使用双引号""",
        parameters={"root_key": "result"},
        required_params=["fields"],
        tags=["json", "structured"]
    )

    XML_FORMAT = PromptComponent(
        name="xml_format",
        type=ComponentType.FORMAT,
        template="""
请使用以下XML标签结构组织你的输出：

<{{ root_tag }}>
  {% for tag, desc in tags.items() %}
  <{{ tag }}>{{ desc }}</{{ tag }}>
  {% endfor %}
</{{ root_tag }}>

注意：必须严格使用指定标签，不要添加额外标签。""",
        parameters={"root_tag": "output"},
        required_params=["tags"],
        tags=["xml", "structured"]
    )

    MARKDOWN_FORMAT = PromptComponent(
        name="markdown_format",
        type=ComponentType.FORMAT,
        template="""
请使用Markdown格式输出：
- 使用 # ## ### 表示标题层级
- 使用 - 或 1. 表示列表
- 使用 > 表示引用或重点
- 使用 **粗体** 强调关键词

{% if include_toc %}
请包含目录：
## 目录
- [第一部分](#第一部分)
- [第二部分](#第二部分)
{% endif %}""",
        parameters={"include_toc": False},
        tags=["markdown", "readable"]
    )


class ConstraintComponents:
    """约束条件组件"""

    WORD_COUNT = PromptComponent(
        name="word_count_constraint",
        type=ComponentType.CONSTRAINT,
        template="""
字数要求：
- 目标字数：{{ target_words }}字
- 允许偏差：±{{ tolerance }}%
- 当前字数统计方式：中文字符数（不含标点）
- 如果无法达到目标字数，请在末尾说明原因""",
        parameters={"tolerance": 10},
        required_params=["target_words"],
        tags=["constraint", "length"]
    )

    STYLE_GUIDE = PromptComponent(
        name="style_guide_constraint",
        type=ComponentType.CONSTRAINT,
        template="""
风格要求：
- 叙事视角：{{ pov }}
- 叙事距离：{{ narrative_distance }}
- 句式特点：{{ sentence_style }}
- 修辞风格：{{ rhetoric }}
- 对话占比：{{ dialogue_ratio }}%

禁止使用：
- 现代网络用语（如"666"、"绝了"）
- 英文单词（专有名词除外）
- 解释性旁白（"这是因为..."）
- 角色内心OS用括号"（）"""",
        parameters={
            "pov": "第三人称有限视角",
            "narrative_distance": "适中",
            "sentence_style": "长短句交错",
            "rhetoric": "适度比喻，避免堆砌",
            "dialogue_ratio": 30
        },
        tags=["constraint", "style"]
    )

    TONE_CONTROL = PromptComponent(
        name="tone_control",
        type=ComponentType.CONSTRAINT,
        template="""
语气基调：{{ tone }}

{% if tone == "紧张" %}
- 短句为主，加快节奏
- 感官细节聚焦听觉和触觉
- 环境描写暗示威胁
- 对话省略主语，制造紧迫感
{% elif tone == "悲伤" %}
- 长句、复合句，营造沉重感
- 感官细节聚焦视觉和嗅觉
- 环境描写与角色心境呼应
- 对话简短，留白多
{% elif tone == "欢快" %}
- 短句、感叹句
- 感官细节丰富多样
- 环境明亮温暖
- 对话活泼，节奏快
{% endif %}""",
        parameters={"tone": "紧张"},
        tags=["constraint", "tone"]
    )


class ReasoningComponents:
    """推理模式组件"""

    COT = PromptComponent(
        name="chain_of_thought",
        type=ComponentType.REASONING,
        template="""
在给出最终答案之前，请先逐步思考：
1. 分析任务的核心要求
2. 梳理已知信息和约束条件
3. 思考可能的方案及其优劣
4. 选择最佳方案并说明理由
5. 执行方案并验证结果

请用<thinking>标签包裹你的思考过程：
<thinking>
[你的逐步思考]
</thinking>

然后用<output>标签给出最终答案：
<output>
[最终答案]
</output>""",
        tags=["reasoning", "cot"]
    )

    REACT = PromptComponent(
        name="react_pattern",
        type=ComponentType.REASONING,
        template="""
你可以使用以下工具辅助完成任务。每次思考后，如果需要使用工具，请按以下格式输出：

<thinking>
[你的思考过程]
</thinking>

<action>
{
  "tool": "工具名称",
  "arguments": {"参数名": "参数值"}
}
</action>

工具执行后会返回结果，你可以继续思考并决定下一步行动。
当你认为任务完成时，输出：

<finish>
[最终答案]
</finish>""",
        tags=["reasoning", "react", "tools"]
    )

    SELF_CONSISTENCY = PromptComponent(
        name="self_consistency",
        type=ComponentType.REASONING,
        template="""
请生成{{ n_samples }}个不同的答案版本，然后：
1. 评估每个版本的优缺点
2. 选择最佳版本或综合各版本优点
3. 给出最终答案

请按以下格式输出：
<version_1>
[第一个版本]
</version_1>

<version_2>
[第二个版本]
</version_2>

...

<evaluation>
[各版本评估]
</evaluation>

<final>
[最终答案]
</final>""",
        parameters={"n_samples": 3},
        tags=["reasoning", "self_consistency"]
    )
```

### 4.2 Prompt组合器

**职责**: 将原子组件组装为完整Prompt，支持层级覆盖和条件渲染

```python
# src/deepnovel/prompts/composer.py

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import copy

from src.deepnovel.prompts.components.base import PromptComponent, ComponentType
from src.deepnovel.tools.decorator import tool, ToolCategory, ToolScope


class PromptSlot(str, Enum):
    """Prompt标准槽位"""
    SYSTEM = "system"          # System Prompt
    CONTEXT = "context"        # 动态上下文
    EXAMPLES = "examples"      # 少样本示例
    INSTRUCTION = "instruction" # 核心指令
    OUTPUT_FORMAT = "output_format"  # 输出格式
    CONSTRAINTS = "constraints"     # 约束条件
    REASONING = "reasoning"    # 推理模式
    META = "meta"              # 元指令


@dataclass
class PromptAssembly:
    """Prompt组装方案"""
    name: str
    description: str
    slots: Dict[PromptSlot, List[str]] = field(default_factory=dict)  # slot -> component names
    default_params: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"


class PromptComposer:
    """
    Prompt组合器

    将原子组件按槽位组装为完整Prompt，支持：
    1. 槽位级覆盖（如替换system prompt）
    2. 条件渲染（根据参数决定包含哪些组件）
    3. 参数级联（子组件继承父组件参数）
    4. 版本管理（记录每次组装的组件版本）
    """

    def __init__(self):
        self._components: Dict[str, PromptComponent] = {}
        self._assemblies: Dict[str, PromptAssembly] = {}
        self._component_registry = {
            # 自动注册所有预定义组件
            **{name: getattr(comp, name) for comp in [RoleComponents, FormatComponents, ConstraintComponents, ReasoningComponents]
               for name in dir(comp) if not name.startswith('_') and isinstance(getattr(comp, name), PromptComponent)}
        }

    def register_component(self, component: PromptComponent):
        """注册组件"""
        self._components[component.name] = component
        return self

    def register_assembly(self, assembly: PromptAssembly):
        """注册组装方案"""
        self._assemblies[assembly.name] = assembly
        return self

    def compose(
        self,
        assembly_name: str,
        params: Optional[Dict[str, Any]] = None,
        slot_overrides: Optional[Dict[PromptSlot, List[str]]] = None
    ) -> Dict[str, str]:
        """
        组装Prompt

        Args:
            assembly_name: 组装方案名称
            params: 渲染参数
            slot_overrides: 槽位覆盖（临时替换某些组件）

        Returns:
            {"system": "...", "user": "..."} 或 {"full": "..."}
        """
        assembly = self._assemblies.get(assembly_name)
        if not assembly:
            raise ValueError(f"Assembly '{assembly_name}' not found")

        params = {**assembly.default_params, **(params or {})}
        slots = copy.deepcopy(assembly.slots)

        # 应用槽位覆盖
        if slot_overrides:
            for slot, components in slot_overrides.items():
                slots[slot] = components

        # 按槽位渲染
        rendered_slots: Dict[str, str] = {}

        for slot, component_names in slots.items():
            slot_parts = []
            for name in component_names:
                component = self._get_component(name)
                if component:
                    try:
                        rendered = component.render(**params)
                        if rendered.strip():
                            slot_parts.append(rendered)
                    except ValueError as e:
                        # 参数缺失，跳过或报错
                        pass

            if slot_parts:
                rendered_slots[slot.value] = "\n\n".join(slot_parts)

        # 组装为最终格式
        return self._format_prompt(rendered_slots)

    def _get_component(self, name: str) -> Optional[PromptComponent]:
        """获取组件"""
        if name in self._components:
            return self._components[name]
        if name in self._component_registry:
            return self._component_registry[name]
        return None

    def _format_prompt(self, rendered_slots: Dict[str, str]) -> Dict[str, str]:
        """
        格式化Prompt为标准结构

        返回 {"system": "...", "user": "..."} 格式
        """
        system_parts = []
        user_parts = []

        # System部分：role + instruction + constraints + reasoning + meta
        for key in ["system", "constraints", "reasoning", "meta"]:
            if key in rendered_slots:
                system_parts.append(rendered_slots[key])

        # User部分：context + examples + instruction + output_format
        for key in ["context", "examples", "instruction", "output_format"]:
            if key in rendered_slots:
                user_parts.append(rendered_slots[key])

        return {
            "system": "\n\n".join(system_parts),
            "user": "\n\n".join(user_parts)
        }


# ===== 预定义组装方案 =====

class NovelPromptAssemblies:
    """小说生成专用Prompt组装方案"""

    WORLD_BUILDING = PromptAssembly(
        name="world_building",
        description="世界观构建专用Prompt",
        slots={
            PromptSlot.SYSTEM: ["world_builder_role"],
            PromptSlot.INSTRUCTION: ["world_build_instruction"],
            PromptSlot.OUTPUT_FORMAT: ["json_format"],
            PromptSlot.CONSTRAINTS: ["style_guide_constraint"]
        },
        default_params={
            "genre": "fantasy",
            "root_key": "world",
            "fields": {
                "name": "世界名称",
                "geography": "地理描述",
                "cultures": "文化列表",
                "magic_system": "魔法体系",
                "history": "历史概述"
            }
        }
    )

    CHARACTER_GENERATION = PromptAssembly(
        name="character_generation",
        description="角色生成专用Prompt",
        slots={
            PromptSlot.SYSTEM: ["character_designer_role"],
            PromptSlot.INSTRUCTION: ["character_gen_instruction"],
            PromptSlot.OUTPUT_FORMAT: ["json_format"],
            PromptSlot.CONSTRAINTS: ["style_guide_constraint"]
        },
        default_params={
            "genre": "fantasy",
            "root_key": "character",
            "pov": "第三人称有限视角"
        }
    )

    CHAPTER_WRITING = PromptAssembly(
        name="chapter_writing",
        description="章节写作专用Prompt",
        slots={
            PromptSlot.SYSTEM: ["story_writer_role"],
            PromptSlot.CONTEXT: ["chapter_context"],
            PromptSlot.INSTRUCTION: ["chapter_write_instruction"],
            PromptSlot.OUTPUT_FORMAT: ["markdown_format"],
            PromptSlot.CONSTRAINTS: ["word_count_constraint", "tone_control", "style_guide_constraint"]
        },
        default_params={
            "include_toc": False,
            "dialogue_ratio": 30
        }
    )

    QUALITY_REVIEW = PromptAssembly(
        name="quality_review",
        description="质量审查专用Prompt",
        slots={
            PromptSlot.SYSTEM: ["editor_role"],
            PromptSlot.INSTRUCTION: ["review_instruction"],
            PromptSlot.OUTPUT_FORMAT: ["json_format"],
            PromptSlot.REASONING: ["chain_of_thought"]
        },
        default_params={
            "root_key": "review",
            "fields": {
                "overall_score": "总分(1-10)",
                "plot_score": "情节得分",
                "character_score": "角色得分",
                "style_score": "风格得分",
                "issues": "问题列表",
                "suggestions": "改进建议"
            }
        }
    )
```

### 4.3 少样本示例管理器

**职责**: 管理示例库，支持基于语义相似度的动态示例选择

```python
# src/deepnovel/prompts/few_shot.py

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

from src.deepnovel.tools.embeddings import get_embedding_router


@dataclass
class FewShotExample:
    """少样本示例"""
    id: str
    task_type: str                    # 任务类型（如"chapter_writing"）
    input_text: str                   # 输入（Prompt）
    output_text: str                  # 输出（期望结果）
    quality_score: float = 0.0        # 质量评分（用于筛选）
    metadata: Dict[str, Any] = None   # 额外信息（genre, style等）
    embedding: Optional[List[float]] = None  # 预计算嵌入向量


class ExampleSelector:
    """
    少样本示例选择器

    策略：
    1. 相似度选择：基于输入query的语义相似度选择最相关的示例
    2. 多样性选择：在相似度基础上保证示例多样性（Maximal Marginal Relevance）
    3. 质量筛选：只选择质量分高于阈值的示例
    4. 动态数量：根据任务复杂度调整示例数量
    """

    def __init__(self, embedding_engine: str = "default"):
        self._examples: Dict[str, List[FewShotExample]] = {}  # task_type -> examples
        self._embedding_engine = embedding_engine
        self._min_quality = 0.6
        self._default_k = 3

    def add_example(self, example: FewShotExample):
        """添加示例"""
        if example.task_type not in self._examples:
            self._examples[example.task_type] = []
        self._examples[example.task_type].append(example)

    def select_examples(
        self,
        query: str,
        task_type: str,
        k: int = None,
        diversity_lambda: float = 0.5
    ) -> List[FewShotExample]:
        """
        选择示例（MMR算法）

        Args:
            query: 当前输入查询
            task_type: 任务类型
            k: 选择数量
            diversity_lambda: 多样性权重（0=纯相似度，1=纯多样性）

        Returns:
            选中的示例列表
        """
        k = k or self._default_k
        examples = self._examples.get(task_type, [])

        # 质量筛选
        examples = [e for e in examples if e.quality_score >= self._min_quality]

        if len(examples) <= k:
            return examples

        # 计算query的嵌入
        router = get_embedding_router()
        engine = router.get_engine(self._embedding_engine)
        query_embedding = np.array(engine.embed(query))

        # 确保所有示例都有嵌入
        for ex in examples:
            if ex.embedding is None:
                ex.embedding = engine.embed(ex.input_text)

        # MMR选择
        selected = []
        remaining = list(range(len(examples)))

        for _ in range(k):
            if not remaining:
                break

            # 计算每个候选的MMR分数
            mmr_scores = []
            for idx in remaining:
                ex_embedding = np.array(examples[idx].embedding)

                # 与query的相似度
                sim_to_query = self._cosine_similarity(query_embedding, ex_embedding)

                # 与已选示例的最大相似度
                if selected:
                    sim_to_selected = max(
                        self._cosine_similarity(np.array(examples[s].embedding), ex_embedding)
                        for s in selected
                    )
                else:
                    sim_to_selected = 0

                # MMR分数
                mmr_score = diversity_lambda * sim_to_query - (1 - diversity_lambda) * sim_to_selected
                mmr_scores.append((idx, mmr_score))

            # 选择MMR分数最高的
            best_idx, _ = max(mmr_scores, key=lambda x: x[1])
            selected.append(best_idx)
            remaining.remove(best_idx)

        return [examples[i] for i in selected]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def format_examples_for_prompt(self, examples: List[FewShotExample]) -> str:
        """将示例格式化为Prompt文本"""
        parts = ["## 示例\n"]
        for i, ex in enumerate(examples, 1):
            parts.append(f"### 示例{i}")
            parts.append(f"**输入：**\n{ex.input_text}")
            parts.append(f"**输出：**\n{ex.output_text}")
            parts.append("")
        return "\n".join(parts)
```

### 4.4 Prompt链与推理模式

**职责**: 将复杂任务分解为多步Prompt链，支持CoT/ReAct/ToT等推理模式

```python
# src/deepnovel/prompts/chain.py

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio

from src.deepnovel.prompts.composer import PromptComposer
from src.deepnovel.llm.base import BaseLLMClient


class ChainStepType(str, Enum):
    """链式步骤类型"""
    GENERATE = "generate"          # 生成内容
    EXTRACT = "extract"            # 提取信息
    TRANSFORM = "transform"        # 转换格式
    EVALUATE = "evaluate"          # 评估质量
    BRANCH = "branch"              # 条件分支
    MERGE = "merge"                # 合并多个输出


@dataclass
class ChainStep:
    """链式步骤"""
    id: str
    type: ChainStepType
    prompt_assembly: str           # 使用的Prompt组装方案
    prompt_params: Dict[str, Any] = None
    output_key: str = "output"     # 输出存储键
    condition: Optional[Callable] = None  # 条件（BRANCH类型用）
    depends_on: List[str] = None   # 依赖的前置步骤


@dataclass
class ChainExecutionResult:
    """链执行结果"""
    success: bool
    outputs: Dict[str, Any]        # 各步骤输出
    final_output: Any = None
    execution_log: List[Dict[str, Any]] = None
    total_tokens: int = 0
    total_time_ms: float = 0.0


class PromptChain:
    """
    Prompt链执行器

    将复杂任务分解为多个Prompt步骤，按依赖关系执行。
    支持：
    - 串行执行（一步接一步）
    - 并行执行（无依赖的步骤同时执行）
    - 条件分支（根据上一步输出决定下一步）
    - 结果合并（多路输出合并为一路）
    """

    def __init__(self, llm_client: BaseLLMClient, composer: PromptComposer):
        self._llm = llm_client
        self._composer = composer
        self._steps: List[ChainStep] = []

    def add_step(self, step: ChainStep):
        """添加步骤"""
        self._steps.append(step)
        return self

    async def execute(self, initial_params: Dict[str, Any]) -> ChainExecutionResult:
        """
        执行Prompt链

        Args:
            initial_params: 初始参数

        Returns:
            ChainExecutionResult
        """
        outputs = {"input": initial_params}
        execution_log = []
        completed_steps = set()
        total_tokens = 0
        total_time = 0.0

        while len(completed_steps) < len(self._steps):
            # 找到可以执行的步骤（依赖已满足）
            executable = [
                s for s in self._steps
                if s.id not in completed_steps
                and all(d in completed_steps for d in (s.depends_on or []))
            ]

            if not executable:
                break  # 死锁或无步骤可执行

            # 并行执行所有可执行的步骤
            tasks = [self._execute_step(step, outputs) for step in executable]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(executable, step_results):
                if isinstance(result, Exception):
                    return ChainExecutionResult(
                        success=False,
                        outputs=outputs,
                        execution_log=execution_log
                    )

                outputs[step.output_key] = result["output"]
                execution_log.append({
                    "step_id": step.id,
                    "type": step.type.value,
                    "tokens": result.get("tokens", 0),
                    "time_ms": result.get("time_ms", 0)
                })
                total_tokens += result.get("tokens", 0)
                total_time += result.get("time_ms", 0)
                completed_steps.add(step.id)

        # 最终输出为最后一个步骤的输出
        final_key = self._steps[-1].output_key if self._steps else "output"

        return ChainExecutionResult(
            success=True,
            outputs=outputs,
            final_output=outputs.get(final_key),
            execution_log=execution_log,
            total_tokens=total_tokens,
            total_time_ms=total_time
        )

    async def _execute_step(self, step: ChainStep, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        import time
        start = time.time()

        # 组装Prompt
        params = {**outputs.get("input", {}), **(step.prompt_params or {})}

        # 注入前置步骤的输出
        for dep_id in (step.depends_on or []):
            params[f"{dep_id}_output"] = outputs.get(dep_id)

        prompt = self._composer.compose(step.prompt_assembly, params)

        # 调用LLM
        response = await self._llm.generate_async(
            prompt=prompt["user"],
            system_prompt=prompt.get("system")
        )

        elapsed = (time.time() - start) * 1000

        return {
            "output": response,
            "tokens": len(response) // 4,  # 粗略估算
            "time_ms": elapsed
        }


# ===== 预定义Prompt链 =====

class NovelGenerationChains:
    """小说生成专用Prompt链"""

    @staticmethod
    def chapter_with_planning(llm_client, composer) -> PromptChain:
        """
        带规划的小说生成链

        Step1: 分析大纲，提取关键节拍
        Step2: 生成场景规划
        Step3: 生成章节内容
        Step4: 质量评估
        Step5: 如未通过，生成修订版
        """
        chain = PromptChain(llm_client, composer)

        chain.add_step(ChainStep(
            id="outline_analysis",
            type=ChainStepType.EXTRACT,
            prompt_assembly="outline_analysis",
            output_key="beats",
            prompt_params={"task": "从大纲提取关键节拍"}
        ))

        chain.add_step(ChainStep(
            id="scene_planning",
            type=ChainStepType.GENERATE,
            prompt_assembly="scene_planning",
            output_key="scenes",
            depends_on=["outline_analysis"],
            prompt_params={"beats": "{{outline_analysis_output}}"}
        ))

        chain.add_step(ChainStep(
            id="content_generation",
            type=ChainStepType.GENERATE,
            prompt_assembly="chapter_writing",
            output_key="draft",
            depends_on=["scene_planning"],
            prompt_params={"scenes": "{{scene_planning_output}}"}
        ))

        chain.add_step(ChainStep(
            id="quality_review",
            type=ChainStepType.EVALUATE,
            prompt_assembly="quality_review",
            output_key="review",
            depends_on=["content_generation"],
            prompt_params={"content": "{{content_generation_output}}"}
        ))

        return chain

    @staticmethod
    def react_with_tools(llm_client, composer) -> PromptChain:
        """
        ReAct推理链（用于Agent工具调用）

        循环：思考 -> 行动（工具调用）-> 观察 -> ... -> 完成
        """
        chain = PromptChain(llm_client, composer)

        # ReAct循环通过外部控制实现，此处定义单步
        chain.add_step(ChainStep(
            id="react_think",
            type=ChainStepType.GENERATE,
            prompt_assembly="react_step",
            output_key="thought_action",
            prompt_params={"mode": "think"}
        ))

        return chain
```

### 4.5 Prompt评估与优化

**职责**: 建立Prompt效果的量化评估体系，支持A/B测试和自动优化

```python
# src/deepnovel/prompts/evaluation.py

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import time


class EvaluationMetric(str, Enum):
    """评估指标"""
    RELEVANCE = "relevance"          # 相关性（输出与任务匹配度）
    COMPLETENESS = "completeness"    # 完整性（是否覆盖所有要求）
    STRUCTURE = "structure"          # 结构合规（JSON/XML格式正确）
    STYLE_CONSISTENCY = "style"      # 风格一致性
    CREATIVITY = "creativity"        # 创意度
    COHERENCE = "coherence"          # 连贯性
    LENGTH_ACCURACY = "length"       # 长度准确性
    FACTUAL_CONSISTENCY = "facts"    # 事实一致性（与设定不矛盾）


@dataclass
class PromptVersion:
    """Prompt版本"""
    id: str
    assembly_name: str
    component_versions: Dict[str, str]  # component -> version
    params: Dict[str, Any]
    created_at: float = 0.0
    score: float = 0.0                  # 综合评分
    evaluation_count: int = 0


@dataclass
class EvaluationResult:
    """评估结果"""
    prompt_version_id: str
    output: str
    metrics: Dict[EvaluationMetric, float]
    overall_score: float
    raw_eval_output: str = ""
    timestamp: float = 0.0


class PromptEvaluator:
    """
    Prompt评估器

    评估方法：
    1. 规则评估：结构化输出检查（JSON解析、字段完整性）
    2. LLM评估：用另一个LLM评判输出质量（类似GPT-4-as-judge）
    3. 语义评估：Embedding相似度（输出与期望的语义距离）
    4. 人工评估：人工打分（用于训练评估模型）
    """

    def __init__(self, judge_llm=None):
        self._judge_llm = judge_llm
        self._metric_weights = {
            EvaluationMetric.STRUCTURE: 0.2,
            EvaluationMetric.RELEVANCE: 0.2,
            EvaluationMetric.COMPLETENESS: 0.15,
            EvaluationMetric.STYLE_CONSISTENCY: 0.15,
            EvaluationMetric.COHERENCE: 0.15,
            EvaluationMetric.CREATIVITY: 0.1,
            EvaluationMetric.LENGTH_ACCURACY: 0.05
        }

    def evaluate(
        self,
        prompt_version: PromptVersion,
        output: str,
        expected: Optional[str] = None,
        task_type: str = ""
    ) -> EvaluationResult:
        """评估Prompt输出质量"""
        metrics = {}
        timestamp = time.time()

        # 1. 结构评估（规则-based）
        metrics[EvaluationMetric.STRUCTURE] = self._evaluate_structure(output, task_type)

        # 2. 长度评估
        metrics[EvaluationMetric.LENGTH_ACCURACY] = self._evaluate_length(output, prompt_version.params)

        # 3. LLM评估（相关性、完整性、风格等）
        if self._judge_llm:
            llm_metrics = self._evaluate_with_llm(output, expected, task_type)
            metrics.update(llm_metrics)

        # 4. 语义评估（如果有期望输出）
        if expected:
            metrics[EvaluationMetric.RELEVANCE] = self._evaluate_similarity(output, expected)

        # 计算综合分数
        overall = sum(
            metrics.get(m, 0) * self._metric_weights.get(m, 0)
            for m in self._metric_weights
        )

        return EvaluationResult(
            prompt_version_id=prompt_version.id,
            output=output,
            metrics=metrics,
            overall_score=overall,
            timestamp=timestamp
        )

    def _evaluate_structure(self, output: str, task_type: str) -> float:
        """评估输出结构合规性"""
        score = 1.0

        # JSON结构检查
        if task_type in ["world_building", "character_generation", "quality_review"]:
            try:
                json.loads(output)
            except json.JSONDecodeError:
                score -= 0.5

        return max(0, score)

    def _evaluate_length(self, output: str, params: Dict[str, Any]) -> float:
        """评估长度准确性"""
        target = params.get("target_words")
        if not target:
            return 1.0

        # 粗略字数统计
        word_count = len(output)
        deviation = abs(word_count - target) / target

        if deviation <= 0.1:
            return 1.0
        elif deviation <= 0.2:
            return 0.8
        elif deviation <= 0.3:
            return 0.6
        else:
            return 0.4

    def _evaluate_with_llm(
        self,
        output: str,
        expected: Optional[str],
        task_type: str
    ) -> Dict[EvaluationMetric, float]:
        """使用LLM评估"""
        # 简化实现：实际应调用Judge LLM
        # 返回模拟分数
        return {
            EvaluationMetric.RELEVANCE: 0.85,
            EvaluationMetric.COMPLETENESS: 0.80,
            EvaluationMetric.STYLE_CONSISTENCY: 0.75,
            EvaluationMetric.COHERENCE: 0.90,
            EvaluationMetric.CREATIVITY: 0.70
        }

    def _evaluate_similarity(self, output: str, expected: str) -> float:
        """评估语义相似度"""
        from src.deepnovel.tools.embeddings import get_embedding_router
        router = get_embedding_router()
        engine = router.get_engine(None)

        emb1 = engine.embed(output)
        emb2 = engine.embed(expected)

        # 余弦相似度
        import numpy as np
        a, b = np.array(emb1), np.array(emb2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


class PromptOptimizer:
    """
    Prompt优化器

    基于评估结果自动优化Prompt，参考DSPy和OPRO思路：
    1. 收集评估数据
    2. 识别低分指标
    3. LLM生成优化建议
    4. 生成新Prompt版本
    5. A/B测试验证
    """

    def __init__(self, evaluator: PromptEvaluator, optimizer_llm=None):
        self._evaluator = evaluator
        self._optimizer_llm = optimizer_llm
        self._evaluation_history: List[EvaluationResult] = []

    def add_evaluation(self, result: EvaluationResult):
        """添加评估结果到历史"""
        self._evaluation_history.append(result)

    def suggest_improvements(self, prompt_version: PromptVersion) -> List[Dict[str, Any]]:
        """
        基于历史评估生成优化建议

        Returns:
            [{"target": "component_name", "issue": "...", "suggestion": "..."}]
        """
        # 筛选该Prompt版本的评估
        version_evals = [
            e for e in self._evaluation_history
            if e.prompt_version_id == prompt_version.id
        ]

        if not version_evals:
            return []

        # 计算各指标平均分
        avg_metrics = {}
        for metric in EvaluationMetric:
            scores = [e.metrics.get(metric, 0) for e in version_evals if metric in e.metrics]
            if scores:
                avg_metrics[metric] = sum(scores) / len(scores)

        # 找出低分指标
        suggestions = []
        for metric, score in avg_metrics.items():
            if score < 0.7:
                suggestions.append({
                    "target": metric.value,
                    "issue": f"{metric.value}评分较低: {score:.2f}",
                    "suggestion": self._generate_suggestion(metric, score)
                })

        return suggestions

    def _generate_suggestion(self, metric: EvaluationMetric, score: float) -> str:
        """生成优化建议"""
        suggestions = {
            EvaluationMetric.STRUCTURE: "添加更明确的输出格式示例，使用XML标签强化结构",
            EvaluationMetric.RELEVANCE: "在指令中增加更多上下文信息，明确任务边界",
            EvaluationMetric.COMPLETENESS: "使用检查清单(checklist)确保所有要求被覆盖",
            EvaluationMetric.STYLE_CONSISTENCY: "增加风格示例，明确禁用词汇列表",
            EvaluationMetric.COHERENCE: "添加逻辑连接词要求，强调段落间过渡",
            EvaluationMetric.CREATIVITY: "减少过度约束，允许更多自由发挥空间",
            EvaluationMetric.LENGTH_ACCURACY: "明确字数统计方式，提供参考段落长度"
        }
        return suggestions.get(metric, "尝试调整指令措辞和约束条件")
```

### 4.6 上下文动态注入器

**职责**: 在Prompt组装时动态注入RAG检索结果、记忆状态、世界事实

```python
# src/deepnovel/prompts/context_injector.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.deepnovel.tools.domain.rag_tools import retrieve_world_knowledge, retrieve_character_memory
from src.deepnovel.tools.domain.world_tools import fact_query


@dataclass
class ContextSlice:
    """上下文片段"""
    source: str                      # 来源（rag/world/memory/config）
    content: str
    relevance_score: float = 1.0
    max_length: int = 500            # 最大长度（自动截断）


class ContextInjector:
    """
    上下文注入器

    根据当前任务自动检索和注入相关上下文：
    1. 世界知识：当前场景涉及的世界规则、地理、文化
    2. 角色状态：出场角色的当前状态、记忆、关系
    3. 情节连贯：前文摘要、伏笔、未解决冲突
    4. 风格参考：相似场景的风格范例
    5. 事实约束：世界事实图谱中的约束条件
    """

    def __init__(self, max_context_length: int = 4000):
        self._max_length = max_context_length
        self._retrieval_tools = {
            "world": retrieve_world_knowledge,
            "character": retrieve_character_memory,
            "fact": fact_query
        }

    async def inject(
        self,
        task_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        注入上下文

        Args:
            task_type: 任务类型（world_building/chapter_writing/...）
            params: 任务参数（含character_id, chapter_id等）

        Returns:
            {"world_context": "...", "character_context": "...", ...}
        """
        contexts = {}

        if task_type == "chapter_writing":
            contexts = await self._inject_for_chapter(params)
        elif task_type == "world_building":
            contexts = await self._inject_for_world(params)
        elif task_type == "character_generation":
            contexts = await self._inject_for_character(params)

        # 截断到最大长度
        for key, value in contexts.items():
            contexts[key] = self._truncate(value, self._max_length // len(contexts))

        return contexts

    async def _inject_for_chapter(self, params: Dict[str, Any]) -> Dict[str, str]:
        """为章节写作注入上下文"""
        contexts = {}
        chapter_id = params.get("chapter_id", "")
        genre = params.get("genre", "fantasy")

        # 1. 前文摘要（情节连贯）
        # contexts["plot_context"] = await retrieve_plot_continuity(...)

        # 2. 角色状态
        character_id = params.get("protagonist_id")
        if character_id:
            result = retrieve_character_memory(character_id, "当前状态和关系")
            contexts["character_context"] = str(result.get("memories", []))

        # 3. 世界规则
        if genre == "xianxia":
            result = retrieve_world_knowledge("修仙境界体系")
            contexts["world_context"] = str(result.get("results", []))

        # 4. 风格参考
        # contexts["style_reference"] = await retrieve_style_reference(...)

        return contexts

    async def _inject_for_world(self, params: Dict[str, Any]) -> Dict[str, str]:
        """为世界构建注入上下文"""
        return {}

    async def _inject_for_character(self, params: Dict[str, Any]) -> Dict[str, str]:
        """为角色生成注入上下文"""
        return {}

    def _truncate(self, text: str, max_length: int) -> str:
        """智能截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
```

---

## 5. Agent Prompt重构方案

### 5.1 WorldBuilderAgent Prompt重构

**当前**: `world_builder.py:388` f-string硬编码

```python
# 当前代码（问题）
llm_prompt = f"""Create detailed locations for a {self._current_genre} world..."""

# 重构后
prompt = composer.compose(
    "world_building",
    params={
        "genre": self._current_genre,
        "world_name": self._world_name,
        "scale": config.get("scale", "epic")
    },
    slot_overrides={
        PromptSlot.CONTEXT: ["genre_context"]  # 动态注入该类型世界构建的特定上下文
    }
)
response = llm.generate(prompt["user"], system_prompt=prompt["system"])
```

### 5.2 ContentGeneratorAgent Prompt重构

**当前**: 无统一Prompt，散落在各方法中

```python
# 重构后：使用Prompt链
chain = NovelGenerationChains.chapter_with_planning(llm_client, composer)
result = await chain.execute({
    "chapter_id": chapter_id,
    "outline": outline,
    "genre": context.genre,
    "target_words": target_words,
    "tone": context.tone,
    "style_config": style_config.to_dict()
})
draft = result.outputs.get("draft")
review = result.outputs.get("review")
```

### 5.3 各Agent Prompt组件映射

| Agent | System Role | 核心指令 | 动态上下文 | 少样本示例 |
|-------|------------|---------|-----------|-----------|
| WorldBuilder | world_builder_role | world_build_instruction | genre_context | 世界观示例 |
| CharacterGenerator | character_designer_role | character_gen_instruction | genre_context | 角色卡示例 |
| ContentGenerator | story_writer_role | chapter_write_instruction | plot+character+world | 章节示例 |
| OutlinePlanner | story_architect_role | outline_plan_instruction | genre+length | 大纲示例 |
| QualityChecker | editor_role | review_instruction | content | 审查报告示例 |
| ChapterSummary | summarizer_role | summary_instruction | previous_summaries | 摘要示例 |

---

## 6. Prompt模板文件结构

```
prompts/
├── components/                    # 原子组件库
│   ├── roles/                     # 角色定义组件
│   │   ├── writer.md              # 作家角色
│   │   ├── editor.md              # 编辑角色
│   │   ├── architect.md           # 架构师角色
│   │   └── critic.md              # 评论家角色
│   ├── instructions/              # 指令组件
│   │   ├── generate_world.md
│   │   ├── generate_character.md
│   │   ├── write_chapter.md
│   │   ├── review_content.md
│   │   └── revise_content.md
│   ├── formats/                   # 格式组件
│   │   ├── json_schema.md
│   │   ├── xml_structure.md
│   │   └── markdown.md
│   └── constraints/               # 约束组件
│       ├── word_count.md
│       ├── style_guide.md
│       └── tone_control.md
├── assemblies/                    # 组装方案
│   ├── world_building.yaml
│   ├── character_generation.yaml
│   ├── chapter_writing.yaml
│   └── quality_review.yaml
├── examples/                      # 少样本示例库
│   ├── chapters/                  # 章节示例（按genre分类）
│   │   ├── fantasy/
│   │   ├── xianxia/
│   │   └── sci-fi/
│   ├── characters/                # 角色卡示例
│   └── reviews/                   # 审查报告示例
├── chains/                        # Prompt链定义
│   ├── chapter_generation.yaml
│   ├── world_building.yaml
│   └── react_tool_use.yaml
└── versions/                      # Prompt版本历史
    ├── v1.0/
    ├── v1.1/
    └── v2.0/
```

---

## 7. 实施计划

### Phase 1: 基础设施（第1-3天）

| 任务 | 文件 | 内容 |
|------|------|------|
| PromptComponent基类 | `prompts/components/base.py` | 原子组件定义、Jinja2渲染 |
| 角色组件库 | `prompts/components/roles/*.md` | 6个核心角色定义 |
| 指令组件库 | `prompts/components/instructions/*.md` | 各Agent核心指令 |
| 格式组件库 | `prompts/components/formats/*.md` | JSON/XML/Markdown格式 |
| 约束组件库 | `prompts/components/constraints/*.md` | 字数/风格/语气约束 |

**验收标准**:
- 所有组件可用Jinja2渲染
- 组件可组合为完整Prompt
- 参数验证正常工作

### Phase 2: 组合器与引擎（第4-6天）

| 任务 | 文件 | 内容 |
|------|------|------|
| PromptComposer | `prompts/composer.py` | 槽位组装、参数级联、版本管理 |
| 组装方案定义 | `prompts/assemblies/*.yaml` | 各Agent的Prompt组装方案 |
| Jinja2引擎 | `prompts/engine.py` | 自定义过滤器、中文排版优化 |
| 上下文注入器 | `prompts/context_injector.py` | RAG/记忆/事实动态注入 |

**验收标准**:
- 组装方案可渲染为system+user Prompt
- 上下文注入可动态检索并注入
- YAML定义的组装方案可热加载

### Phase 3: 少样本与推理（第7-9天）

| 任务 | 文件 | 内容 |
|------|------|------|
| ExampleSelector | `prompts/few_shot.py` | MMR示例选择、语义相似度 |
| 示例库建设 | `prompts/examples/*` | 每个任务类型至少5个示例 |
| 推理模式 | `prompts/reasoning/*.py` | CoT/ReAct/ToT模板 |
| PromptChain | `prompts/chain.py` | 多步链式执行 |

**验收标准**:
- 示例选择基于语义相似度
- CoT模式可在任意Prompt后附加
- Prompt链可串行/并行执行

### Phase 4: 评估优化（第10-12天）

| 任务 | 文件 | 内容 |
|------|------|------|
| PromptEvaluator | `prompts/evaluation.py` | 多维度自动评分 |
| PromptOptimizer | `prompts/optimization.py` | DSPy式自动优化 |
| A/B测试框架 | `prompts/ab_test.py` | 版本对比、统计显著性 |
| 评估数据集 | `prompts/eval_data/` | 测试用例和期望输出 |

**验收标准**:
- 自动评估可给出结构分、相关分等
- A/B测试可比较两个Prompt版本
- 优化建议基于历史评估数据

### Phase 5: Agent迁移（第13-15天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 改造WorldBuilder | `agents/world_builder.py` | 使用PromptComposer |
| 改造ContentGenerator | `agents/content_generator.py` | 使用PromptChain |
| 改造CharacterGenerator | `agents/character_generator.py` | 使用PromptComposer |
| 改造其他Agent | `agents/*.py` | 统一迁移 |

**验收标准**:
- 所有Agent使用新的Prompt系统
- Prompt与代码逻辑分离
- 输出结构稳定性提升（JSON解析成功率>95%）

### Phase 6: 清理旧代码（第16天）

| 任务 | 处置 |
|------|------|
| `config/prompts/system_prompts/*.py` | 内容迁移到components后删除 |
| `config/prompts/user_prompts/templates/*.json` | 迁移到assemblies后删除 |
| Agent内的f-string Prompt | 全部替换为composer调用 |
| `find('{')` JSON解析 | 替换为结构化输出+Schema验证 |

---

## 8. 迁移策略

### 8.1 存量Prompt处理

| 当前文件 | 处理方式 | 迁移目标 |
|---------|---------|---------|
| `system_prompts/world_builder.py` | 解析 → 拆分组件 | `components/roles/writer.md` + `components/instructions/generate_world.md` |
| `system_prompts/character_generator.py` | 解析 → 拆分组件 | `components/instructions/generate_character.md` |
| `system_prompts/content_writer.py` | 解析 → 拆分组件 | `components/instructions/write_chapter.md` + `components/constraints/style_guide.md` |
| `system_prompts/outline_planner.py` | 解析 → 拆分组件 | `components/instructions/plan_outline.md` |
| `system_prompts/quality_reviewer.py` | 解析 → 拆分组件 | `components/instructions/review_content.md` |
| `generation_templates.json` | 解析 → 转为assemblies | `assemblies/*.yaml` |
| `pacing_tension.json` | 解析 → 转为constraints | `components/constraints/tone_control.md` |
| `presets.json` | 扩展 → 更多预设 | `assemblies/`中的default_params |

### 8.2 渐进式迁移路径

```
第1周: 基础设施 + 2个Agent试点
  └─ WorldBuilder + ContentGenerator 迁移到新Prompt系统
  └─ 其他Agent保持不动

第2周: 全部Agent迁移
  └─ 剩余Agent逐个迁移
  └─ 建立示例库

第3周: 评估优化
  └─ 运行A/B测试
  └─ 优化低分Prompt

第4周: 清理旧代码
  └─ 删除旧Prompt文件
  └─ 统一代码风格
```

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Jinja2模板语法错误 | 渲染失败 | 严格的模板验证 + 预编译检查 |
| 上下文注入过长 | 超出LLM上下文窗口 | Token预算管理 + 智能截断 |
| 少样本示例质量差 | 输出质量下降 | 人工审核示例库 + 质量分筛选 |
| Prompt版本混乱 | A/B测试结果不可信 | 严格的版本命名 + 哈希校验 |
| 动态Prompt不可预测 | 调试困难 | PromptDebugger记录每次渲染的完整上下文 |
| 组件过度拆分 | 性能下降 | 组件缓存 + 预编译模板 |

---

## 10. 成功指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|---------|
| JSON解析成功率 | ~60%（find('{')方式） | >95% | 解析成功次数/总调用次数 |
| Prompt可维护性 | 修改需改代码 | 修改只需改YAML/MD | 非技术人员能否修改 |
| 上下文注入覆盖率 | 0% | 100%（所有Agent） | 使用ContextInjector的Agent比例 |
| 少样本示例数量 | 0 | 50+ | 示例库计数 |
| Prompt评估覆盖率 | 0% | >80% | 有评估记录的Prompt比例 |
| System Prompt复用率 | 0%（每个Agent独立） | >60% | 共享组件使用次数/总组件数 |
| 输出结构一致性 | 低 | 高（标准差<0.1） | 同任务多次输出的结构相似度 |
