# Step 10: 配置层重构 - 统一入口、统一封装、动态加载的配置中枢

> 版本: 1.1（已根据审查报告反向优化）
> 日期: 2026-04-28
> 依赖: Step1-9
> 目标: 构建类型安全、统一入口、动态感知、全生命周期管理的配置层  
> **全局路线图**: [OPTIMIZED_ROADMAP.md](OPTIMIZED_ROADMAP.md) — 本Step属于 **Phase 1: 基础设施加固**（最先实施）  
> **总装规范**: [INTEGRATION_SPEC.md](INTEGRATION_SPEC.md) — 模块边界与接口契约  
> **关键变更**: 整合Step7 NovelConfig（冲突A）、增加LLM Tier配置（冲突E）

---

## 1. 设计哲学

### 1.1 核心转变

```
从：字典+字符串的类型不安全配置          → 到：Pydantic v2 类型安全模型
从：配置文件散落各处                     → 到：统一配置中枢 + 单一入口
从：手动读取+硬编码默认值                → 到：声明式模型 + 自动验证 + 智能默认值
从：重启才能生效                         → 到：文件监听热加载 + 变更通知
从：明文存储API密钥                      → 到：ConfigVault加密 + 环境变量隔离
从：开发/生产配置混为一谈                → 到：Profile隔离 + 分层覆盖
从：多处重复懒加载逻辑                   → 到：统一ConfigProvider + DI注入
从：配置与代码紧耦合                     → 到：配置即契约 + 自动文档生成
```

### 1.2 设计原则

1. **类型即契约**：Pydantic模型即配置规范，IDE自动补全，运行时验证，失败早暴露
2. **单点即入口**：所有配置通过 `ConfigHub` 唯一入口获取，禁止分散import
3. **来源即透明**：配置文件、环境变量、命令行、远程配置统一抽象为ConfigSource
4. **变更即通知**：配置修改自动触发监听回调，组件无感热更新
5. **敏感即加密**：API密钥、密码等敏感信息走Vault加密存储，不落明文
6. **环境即隔离**：dev/test/prod配置严格隔离，禁止交叉污染
7. **层级即覆盖**：默认值 → 文件 → 环境变量 → 命令行，层层覆盖优先级清晰

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **Pydantic Settings v2** (2024) | `BaseSettings` + `Field` + `ConfigDict`、环境变量自动注入 | Python类型安全配置 |
| **Hydra** (Meta) | 分层配置组合、命令行覆盖、配置组 `@package` | 复杂实验配置 |
| **OmegaConf** | `DictConfig` + 结构化、类型安全、不可变模式 | ML流水线配置 |
| **Dynaconf** (2024) | 多格式、多环境、验证器、Redis远程加载 | 企业级配置管理 |
| **python-decouple** | 设置与代码分离、`.env`文件、类型转换 | 12-Factor App |
| **Traitlets** (Jupyter) | 类型化配置、观察回调、交叉验证 | 交互式应用 |
| **Spring Boot Config** | Profile分层、外部化配置、Actuator端点 | 云原生微服务 |
| **HashiCorp Vault** | 动态密钥、租约管理、加密即服务 | 敏感配置安全 |
| **AWS Parameter Store** | 层级参数、版本控制、安全字符串 | 云环境配置 |

---

## 2. 现状诊断

### 2.1 当前组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| `ConfigManager` | `config/manager.py` | 基础功能完整，但无类型安全、无热加载 | **中** |
| `Settings` 单例 | `config/manager.py:276` | 单例实现正确，但**懒加载逻辑重复3次**（get_llm/get_database/get_agent各行280+行） | **严重** |
| `ConfigLoader` | `config/loader.py` | 支持JSON/YAML，但无缓存、无监听 | **中** |
| `ConfigValidator` | `config/validator.py` | JSON Schema验证，但Schema要求**所有4个DB必填**（即使未使用） | **严重** |
| `utils/config_loader.py` | `utils/config_loader.py` | **功能重复**（deep_merge/expand_env_vars与config/loader.py重复） | **中** |
| `config/settings.py` | `config/settings.py` | 只是重新导出，增加import混乱 | **低** |
| `.env` | `config/.env` | Docker专用，与代码中的环境变量解析不统一 | **中** |
| 配置分散引用 | 全代码库 | `settings.get()` / `os.environ` / `config.get()` 混用，无统一入口 | **严重** |
| 敏感信息 | 多处 | API密钥在配置文件中明文存储 | **严重** |
| 环境隔离 | 不完善 | 只有dev/test/prod文件路径，无运行时常量区分 | **中** |
| 配置文档 | 不存在 | 无自动生成配置文档机制 | **低** |

### 2.2 核心问题总结

```
当前状态：配置"可用"但"不可治理"

1. 类型不安全          → 配置错误在运行时才发现，IDE无补全
2. 懒加载重复3次       → get_llm/get_database/get_agent各有一份独立懒加载
3. 数据库Schema全必填   → 只想用SQLite也被要求配MySQL/Neo4j/MongoDB
4. utils/config_loader  → 与config/loader.py功能重复，维护两份
5. 敏感信息明文         → API密钥写在JSON配置文件里，可进git
6. 无热加载            → 改配置必须重启服务
7. 无变更通知          → 配置改了，已初始化的组件不知道
8. 入口不统一          → 有的用settings.get()，有的用os.environ，有的直接读文件
9. 无配置Profile        → dev/prod只能通过文件名区分，无运行时强隔离
10. 无配置文档          → 新开发者靠读源码猜配置项含义
```

---

## 3. 架构总览

### 3.1 配置层六层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 6: 应用层 (Application)                                        │
│  • ConfigAdminAPI        - RESTful配置管理接口                      │
│  • ConfigDocsGenerator   - 自动生成配置文档(Markdown/OpenAPI)        │
│  • ConfigHealthCheck     - 配置健康检查（敏感项/必填项/过期项）      │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 5: 安全治理层 (Security & Governance)                          │
│  • ConfigVault           - 敏感配置加密存储                          │
│  • SecretResolver        - 密钥解析（${vault:xxx} / ${env:XXX}）    │
│  • ConfigAuditLog        - 配置变更审计日志                          │
│  • AccessControl         - 配置访问权限控制                          │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: 生命周期层 (Lifecycle)                                      │
│  • ConfigHub             - 统一配置入口（唯一门面）                  │
│  • ConfigWatcher         - 文件系统监听热加载                        │
│  • ChangePublisher       - 配置变更发布订阅                          │
│  • ConfigCache           - 配置值缓存（避免重复解析）                 │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 加载解析层 (Loader & Resolver)                              │
│  • UnifiedLoader         - 统一加载器（JSON/YAML/TOML/INI/Properties）│
│  • SourceResolver        - 多来源解析（文件/环境变量/命令行/远程）    │
│  • ProfileMerger         - Profile分层合并（default → dev → local） │
│  • EnvVarInterpolator    - 环境变量插值（${ENV_VAR:default}）       │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 模型验证层 (Model & Validation)                             │
│  • AppConfig (Pydantic)  - 根配置模型                                │
│  • LLMConfig (Pydantic)  - LLM配置模型                               │
│  • DBConfig (Pydantic)   - 数据库配置模型                            │
│  • AgentConfig (Pydantic)- Agent配置模型                             │
│  • NovelConfig (Pydantic)- 小说业务配置模型                          │
│  • ConfigValidator       - 跨模型联合验证                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 来源层 (Sources)                                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ FileSource  │ │ EnvSource   │ │ CLISource   │ │ RemoteSource│   │
│  │ *.json      │ │ os.environ  │ │ argparse    │ │ Redis/Consul│   │
│  │ *.yaml      │ │ .env文件    │ │ click       │ │ HTTP API    │   │
│  │ *.toml      │ │             │ │             │ │             │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 配置加载数据流

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              配置加载流程                                       │
│                                                                               │
│  命令行参数 ──→┐                                                               │
│  环境变量  ────→┼──→ SourceResolver ──→ 原始配置字典 ──→ ProfileMerger        │
│  .env文件  ────→┤                          ↑                              │
│  config/*.json ─→┘                          │ 分层覆盖                        │
│  config/*.yaml ─→                            │ (default → profile → local)    │
│                                              ↓                              │
│                                    EnvVarInterpolator                        │
│                                    (${MYSQL_HOST:localhost})                 │
│                                              │                              │
│                                              ↓                              │
│                                    SecretResolver                            │
│                                    (${vault:api_key} → 解密)                  │
│                                              │                              │
│                                              ↓                              │
│                                    Pydantic模型验证                           │
│                                    (AppConfig.parse_obj)                     │
│                                              │                              │
│                                              ↓                              │
│                                    ConfigHub（统一入口）                      │
│                                    ├─ config.llm.default.provider            │
│                                    ├─ config.database.sqlite.path            │
│                                    ├─ config.agents.world_builder.model      │
│                                    └─ config.novel.default_genre             │
│                                              │                              │
│                          ┌───────────────────┼───────────────────┐          │
│                          ↓                   ↓                   ↓          │
│                   ConfigWatcher        ChangePublisher        ConfigCache   │
│                   (文件监听)            (变更通知)            (值缓存)      │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 核心组件设计

### 4.1 Pydantic类型安全配置模型

**职责**: 用Pydantic v2定义所有配置模型，提供类型安全、自动验证、IDE补全

```python
# src/deepnovel/config/models/base.py

from typing import Any, Dict, List, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pathlib import Path
import os


class ConfigBase(BaseModel):
    """
    配置模型基类

    所有配置模型继承此类，获得：
    - 环境变量自动映射（env_prefix）
    - 严格模式（禁止额外字段）
    - 自定义JSON编码
    """
    model_config = ConfigDict(
        extra="forbid",           # 禁止未定义的字段
        populate_by_name=True,     # 允许用字段名赋值
        str_strip_whitespace=True, # 自动去除字符串首尾空格
        validate_assignment=True,  # 赋值时验证
    )


# ===== 嵌套配置模型 =====

class LogLevel(str, Literal):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Literal):
    """运行环境"""
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProviderConfig(ConfigBase):
    """单个LLM提供商配置"""
    provider: str = Field(..., description="提供商标识")
    model: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="自定义Base URL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(default=4096, ge=1, description="最大生成token数")
    timeout: float = Field(default=30.0, ge=1.0, description="请求超时（秒）")
    retry_times: int = Field(default=3, ge=0, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, description="重试间隔（秒）")
    embedding_model: Optional[str] = Field(default=None, description="嵌入模型（默认与生成模型相同）")
    embedding_dimensions: Optional[int] = Field(default=None, description="嵌入维度")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("api_key")
    @classmethod
    def mask_api_key_in_repr(cls, v: Optional[str]) -> Optional[str]:
        """API密钥在repr中脱敏"""
        return v

    def __repr__(self) -> str:
        """脱敏显示"""
        kwargs = []
        for k, v in self.model_dump().items():
            if k == "api_key" and v:
                v = v[:4] + "****" + v[-4:] if len(v) > 8 else "****"
            kwargs.append(f"{k}={v!r}")
        return f"{self.__class__.__name__}({', '.join(kwargs)})"


class LLMConfig(ConfigBase):
    """LLM全局配置"""
    default_provider: str = Field(default="ollama", description="默认提供商")
    providers: Dict[str, LLMProviderConfig] = Field(default_factory=dict, description="提供商列表")
    routing_strategy: Literal["round_robin", "priority", "health_check"] = Field(
        default="priority", description="路由策略"
    )
    fallback_enabled: bool = Field(default=True, description="是否启用降级")
    embedding_provider: Optional[str] = Field(default=None, description="默认嵌入提供商")

    # 功能分级配置（整合Step3的ModelTier）
    default_tier: str = Field(default="simple", description="默认功能分级: simple/reasoning/creative/emotional/analytical")
    tier_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "simple": "ollama",
            "reasoning": "openai",
            "creative": "openai",
            "emotional": "openai",
            "analytical": "openai"
        },
        description="功能分级到提供商的映射"
    )

    @model_validator(mode="after")
    def check_default_provider_exists(self) -> "LLMConfig":
        """验证默认提供商在providers中存在"""
        if self.default_provider and self.default_provider not in self.providers:
            raise ValueError(f"默认提供商 '{self.default_provider}' 不在providers列表中")
        if self.embedding_provider and self.embedding_provider not in self.providers:
            raise ValueError(f"嵌入提供商 '{self.embedding_provider}' 不在providers列表中")
        return self


class SQLiteConfig(ConfigBase):
    """SQLite配置"""
    path: str = Field(default="data/app.db", description="数据库文件路径")
    wal_mode: bool = Field(default=True, description="启用WAL模式")
    pragmas: Dict[str, Any] = Field(default_factory=lambda: {"journal_mode": "WAL"})


class MySQLConfig(ConfigBase):
    """MySQL配置"""
    host: str = Field(default="localhost", description="主机地址")
    port: int = Field(default=3306, ge=1, le=65535, description="端口")
    user: str = Field(default="root", description="用户名")
    password: str = Field(default="", description="密码")
    database: str = Field(default="ai_novels", description="数据库名")
    charset: str = Field(default="utf8mb4", description="字符集")
    pool_size: int = Field(default=10, ge=1, description="连接池大小")
    max_overflow: int = Field(default=20, ge=0, description="最大溢出连接")


class Neo4jConfig(ConfigBase):
    """Neo4j配置"""
    uri: str = Field(default="bolt://localhost:7687", description="连接URI")
    user: str = Field(default="neo4j", description="用户名")
    password: str = Field(default="", description="密码")
    database: str = Field(default="neo4j", description="数据库名")


class MongoDBConfig(ConfigBase):
    """MongoDB配置"""
    host: str = Field(default="localhost", description="主机地址")
    port: int = Field(default=27017, ge=1, le=65535, description="端口")
    user: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    database: str = Field(default="ai_novels", description="数据库名")
    auth_source: str = Field(default="admin", description="认证数据库")


class ChromaDBConfig(ConfigBase):
    """ChromaDB配置"""
    host: Optional[str] = Field(default=None, description="远程主机（None则使用本地）")
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="远程端口")
    path: str = Field(default="data/chromadb", description="本地存储路径")
    collection_prefix: str = Field(default="novel_", description="集合名前缀")


class DatabaseConfig(ConfigBase):
    """数据库总配置 - 所有子项可选，按需启用"""
    sqlite: Optional[SQLiteConfig] = Field(default=None, description="SQLite配置")
    mysql: Optional[MySQLConfig] = Field(default=None, description="MySQL配置")
    neo4j: Optional[Neo4jConfig] = Field(default=None, description="Neo4j配置")
    mongodb: Optional[MongoDBConfig] = Field(default=None, description="MongoDB配置")
    chromadb: Optional[ChromaDBConfig] = Field(default=None, description="ChromaDB配置")

    @property
    def active_connections(self) -> List[str]:
        """获取已配置的数据库连接列表"""
        active = []
        for name in ["sqlite", "mysql", "neo4j", "mongodb", "chromadb"]:
            if getattr(self, name) is not None:
                active.append(name)
        return active


class AgentLLMOverride(ConfigBase):
    """Agent级LLM覆盖配置"""
    provider: Optional[str] = Field(default=None, description="覆盖提供商")
    model: Optional[str] = Field(default=None, description="覆盖模型")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="覆盖温度")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="覆盖最大token")
    system_prompt: Optional[str] = Field(default=None, description="覆盖系统提示词")
    timeout: Optional[float] = Field(default=None, ge=1.0, description="覆盖超时")


class AgentConfigModel(ConfigBase):
    """Agent配置"""
    name: str = Field(..., description="Agent标识名")
    description: str = Field(default="", description="Agent描述")
    enabled: bool = Field(default=True, description="是否启用")
    llm_override: Optional[AgentLLMOverride] = Field(default=None, description="LLM覆盖配置")
    tools: List[str] = Field(default_factory=list, description="可用工具列表")
    max_history: int = Field(default=100, ge=0, description="最大历史消息数")
    retry_times: int = Field(default=3, ge=0, description="重试次数")
    timeout: float = Field(default=60.0, ge=1.0, description="执行超时")
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="自定义参数")


class RAGConfig(ConfigBase):
    """RAG配置"""
    enabled: bool = Field(default=True, description="是否启用RAG")
    default_retriever: str = Field(default="hybrid", description="默认检索器")
    top_k: int = Field(default=5, ge=1, le=50, description="检索Top-K")
    rerank_enabled: bool = Field(default=True, description="是否重排序")
    rerank_top_k: int = Field(default=10, ge=1, le=100, description="重排序候选数")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相似度阈值")
    embedding_cache_enabled: bool = Field(default=True, description="嵌入缓存")
    embedding_cache_ttl: int = Field(default=3600, ge=0, description="缓存TTL（秒）")


class WorkflowConfig(ConfigBase):
    """工作流配置"""
    enabled: bool = Field(default=True, description="是否启用工作流")
    max_concurrent_tasks: int = Field(default=10, ge=1, description="最大并发任务数")
    default_timeout: float = Field(default=300.0, ge=1.0, description="默认任务超时")
    checkpoint_interval: float = Field(default=30.0, ge=1.0, description="检查点间隔")
    retry_max_attempts: int = Field(default=3, ge=0, description="最大重试次数")


class GenerationConfig(ConfigBase):
    """内容生成配置"""
    default_word_count: int = Field(default=3000, ge=100, description="默认章节字数")
    min_word_count: int = Field(default=500, ge=100, description="最小章节字数")
    max_word_count: int = Field(default=10000, ge=500, description="最大章节字数")
    default_genre: str = Field(default="fantasy", description="默认小说类型")
    output_dir: str = Field(default="output", description="输出目录")
    auto_save: bool = Field(default=True, description="是否自动保存")
    quality_check_enabled: bool = Field(default=True, description="是否启用质量检查")


class LoggingConfig(ConfigBase):
    """日志配置"""
    level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    format: str = Field(
        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        description="日志格式"
    )
    file_enabled: bool = Field(default=True, description="是否写入文件")
    file_path: str = Field(default="logs/app.log", description="日志文件路径")
    file_max_bytes: int = Field(default=10 * 1024 * 1024, description="单文件最大字节")
    file_backup_count: int = Field(default=5, description="备份文件数")
    console_enabled: bool = Field(default=True, description="是否输出到控制台")
    structured: bool = Field(default=False, description="是否结构化日志（JSON）")


class SecurityConfig(ConfigBase):
    """安全配置"""
    secret_key: Optional[str] = Field(default=None, description="应用密钥（用于JWT等）")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_expire_hours: int = Field(default=24, ge=1, description="JWT过期时间（小时）")
    password_min_length: int = Field(default=8, ge=4, description="密码最小长度")
    rate_limit_enabled: bool = Field(default=True, description="是否启用限流")
    rate_limit_requests: int = Field(default=100, ge=1, description="限流请求数/分钟")


class APIConfig(ConfigBase):
    """API服务配置"""
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="监听端口")
    workers: int = Field(default=1, ge=1, description="工作进程数")
    cors_origins: List[str] = Field(default_factory=list, description="CORS允许来源")
    docs_enabled: bool = Field(default=True, description="是否启用API文档")


# ===== 根配置模型 =====

class AppConfig(ConfigBase):
    """
    应用根配置模型

    这是唯一的配置入口，所有子配置都挂载在此模型下。
    """
    model_config = ConfigDict(
        extra="forbid",
        env_prefix="AINOVELS_",      # 环境变量前缀：AINOVELS_DATABASE__MYSQL__HOST
        env_nested_delimiter="__",    # 嵌套分隔符
    )

    app_name: str = Field(default="AI-Novels", description="应用名称")
    version: str = Field(default="1.0.0", description="应用版本")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")
    debug: bool = Field(default=False, description="调试模式")

    # 子配置
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="数据库配置")
    agents: Dict[str, AgentConfigModel] = Field(default_factory=dict, description="Agent配置")
    rag: RAGConfig = Field(default_factory=RAGConfig, description="RAG配置")
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig, description="工作流配置")
    generation: GenerationConfig = Field(default_factory=GenerationConfig, description="生成配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="安全配置")
    api: APIConfig = Field(default_factory=APIConfig, description="API配置")

    # 小说业务配置（整合Step7的NovelConfig）
    novel: Optional["NovelConfig"] = Field(default=None, description="当前小说配置")
    novel_presets: Dict[str, "NovelConfig"] = Field(default_factory=dict, description="小说配置预设")

    # 扩展配置（插件/自定义）
    plugins: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="插件配置")
    custom: Dict[str, Any] = Field(default_factory=dict, description="自定义配置")

    @model_validator(mode="after")
    def validate_environment_consistency(self) -> "AppConfig":
        """环境一致性验证"""
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                raise ValueError("生产环境不能开启debug模式")
            if not self.security.secret_key:
                raise ValueError("生产环境必须设置secret_key")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    def get_agent(self, name: str) -> Optional[AgentConfigModel]:
        """获取Agent配置"""
        return self.agents.get(name)

    def get_llm_provider(self, name: Optional[str] = None) -> Optional[LLMProviderConfig]:
        """获取LLM提供商配置"""
        name = name or self.llm.default_provider
        return self.llm.providers.get(name)

    def dump_sensitive_masked(self) -> Dict[str, Any]:
        """导出配置（敏感字段脱敏），用于日志/展示"""
        data = self.model_dump()

        def mask_recursive(obj: Any, key_hint: str = "") -> Any:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    hint = f"{key_hint}.{k}" if key_hint else k
                    if any(s in k.lower() for s in ["password", "secret", "api_key", "token"]):
                        result[k] = "****"
                    else:
                        result[k] = mask_recursive(v, hint)
                return result
            elif isinstance(obj, list):
                return [mask_recursive(item, key_hint) for item in obj]
            return obj

        return mask_recursive(data)
```

### 4.2 统一配置中枢 - ConfigHub

**职责**: 唯一配置入口门面，整合加载、验证、访问、监听、热加载

```python
# src/deepnovel/config/hub.py

import os
import json
import time
import threading
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from pydantic import ValidationError

from .models.base import AppConfig, Environment
from .loader import UnifiedConfigLoader
from .vault import ConfigVault

T = TypeVar('T')


class ConfigChangeEvent:
    """配置变更事件"""
    def __init__(self, key: str, old_value: Any, new_value: Any, source: str):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source
        self.timestamp = time.time()


class ConfigHub:
    """
    配置中枢 - 统一入口

    单例模式，提供：
    1. 配置加载与初始化
    2. 类型安全访问
    3. 变更监听
    4. 热加载
    5. 配置导出

    用法：
        from src.deepnovel.config import ConfigHub

        hub = ConfigHub()
        hub.initialize()  # 启动时调用一次

        # 访问配置
        provider = hub.config.llm.default_provider
        api_key = hub.config.get_llm_provider("openai").api_key

        # 监听变更
        hub.watch("llm.default_provider", on_provider_change)

        # 热加载
        hub.reload()
    """

    _instance: Optional['ConfigHub'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._config: Optional[AppConfig] = None
                    cls._instance._loader: Optional[UnifiedConfigLoader] = None
                    cls._instance._vault: Optional[ConfigVault] = None
                    cls._instance._watcher: Optional['ConfigFileWatcher'] = None
                    cls._instance._listeners: Dict[str, List[Callable]] = {}
                    cls._instance._global_listeners: List[Callable] = []
                    cls._instance._cache: Dict[str, Any] = {}
        return cls._instance

    def initialize(
        self,
        config_dir: str = "config",
        profile: Optional[str] = None,
        env_file: str = "config/.env",
        vault_key: Optional[str] = None
    ) -> bool:
        """
        初始化配置中枢

        Args:
            config_dir: 配置目录
            profile: 运行环境profile（dev/test/prod），None则自动检测
            env_file: .env文件路径
            vault_key: Vault加密密钥

        Returns:
            是否成功
        """
        try:
            # 1. 检测Profile
            profile = profile or self._detect_profile()

            # 2. 初始化Vault
            self._vault = ConfigVault(key=vault_key)

            # 3. 初始化加载器
            self._loader = UnifiedConfigLoader(
                config_dir=config_dir,
                profile=profile,
                env_file=env_file,
                vault=self._vault
            )

            # 4. 加载并验证配置
            raw_config = self._loader.load()
            self._config = AppConfig.model_validate(raw_config)

            # 5. 启动文件监听（仅开发环境）
            if self._config.is_development:
                self._start_watcher(config_dir)

            self._initialized = True
            return True

        except ValidationError as e:
            print(f"[ConfigHub] 配置验证失败:\n{e}")
            return False
        except Exception as e:
            print(f"[ConfigHub] 初始化失败: {e}")
            return False

    def _detect_profile(self) -> str:
        """自动检测运行环境"""
        # 优先级：环境变量 > 文件标记 > 默认development
        env = os.environ.get("AINOVELS_ENV")
        if env:
            return env.lower()

        # 检查配置文件标记
        for profile in ["production", "staging", "test", "development"]:
            if os.path.exists(f"config/.{profile}"):
                return profile

        return "development"

    @property
    def config(self) -> AppConfig:
        """获取配置实例（类型安全）"""
        if not self._initialized or self._config is None:
            raise RuntimeError("ConfigHub未初始化，请先调用initialize()")
        return self._config

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def get(self, key: str, default: Any = None) -> Any:
        """
        点号路径获取配置值

        Args:
            key: 配置路径，如 "llm.providers.openai.temperature"
            default: 默认值

        Returns:
            配置值
        """
        try:
            keys = key.split(".")
            value = self.config
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                elif isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        except Exception:
            return default

    def get_required(self, key: str) -> Any:
        """获取必需配置值，不存在则抛异常"""
        value = self.get(key)
        if value is None:
            raise KeyError(f"Required config key '{key}' not found")
        return value

    def watch(self, key: str, callback: Callable[[ConfigChangeEvent], None]):
        """
        监听配置变更

        Args:
            key: 配置路径，如 "llm.default_provider"
            callback: 变更回调函数
        """
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)

    def watch_all(self, callback: Callable[[ConfigChangeEvent], None]):
        """监听所有配置变更"""
        self._global_listeners.append(callback)

    def unwatch(self, key: str, callback: Optional[Callable] = None):
        """取消监听"""
        if key in self._listeners:
            if callback:
                self._listeners[key] = [cb for cb in self._listeners[key] if cb != callback]
            else:
                del self._listeners[key]

    def reload(self) -> bool:
        """
        重新加载配置（热加载）

        Returns:
            是否成功
        """
        if not self._loader:
            return False

        try:
            old_config = self._config
            raw_config = self._loader.load()
            self._config = AppConfig.model_validate(raw_config)

            # 对比变更并通知
            if old_config:
                changes = self._diff_config(old_config, self._config)
                for change in changes:
                    self._notify_change(change)

            return True
        except Exception as e:
            print(f"[ConfigHub] 热加载失败: {e}")
            return False

    def _diff_config(self, old: AppConfig, new: AppConfig) -> List[ConfigChangeEvent]:
        """对比配置差异"""
        changes = []
        old_dict = old.model_dump()
        new_dict = new.model_dump()

        def compare(path: str, old_val: Any, new_val: Any):
            if old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    for k in set(old_val.keys()) | set(new_val.keys()):
                        sub_path = f"{path}.{k}" if path else k
                        compare(sub_path, old_val.get(k), new_val.get(k))
                else:
                    changes.append(ConfigChangeEvent(path, old_val, new_val, "reload"))

        compare("", old_dict, new_dict)
        return changes

    def _notify_change(self, event: ConfigChangeEvent):
        """通知配置变更"""
        # 精确匹配监听
        for key, callbacks in self._listeners.items():
            if event.key == key or event.key.startswith(key + "."):
                for cb in callbacks:
                    try:
                        cb(event)
                    except Exception as e:
                        print(f"[ConfigHub] 监听回调出错: {e}")

        # 全局监听
        for cb in self._global_listeners:
            try:
                cb(event)
            except Exception as e:
                print(f"[ConfigHub] 全局监听回调出错: {e}")

    def _start_watcher(self, config_dir: str):
        """启动配置文件监听"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class ConfigFileHandler(FileSystemEventHandler):
                def __init__(self, hub: ConfigHub):
                    self.hub = hub
                    self._last_reload = 0

                def on_modified(self, event):
                    if event.is_directory:
                        return
                    if event.src_path.endswith(('.json', '.yaml', '.yml', '.toml', '.env')):
                        now = time.time()
                        if now - self._last_reload > 1:  # 防抖
                            self._last_reload = now
                            print(f"[ConfigHub] 检测到配置文件变更: {event.src_path}")
                            self.hub.reload()

            self._watcher = Observer()
            self._watcher.schedule(ConfigFileHandler(self), config_dir, recursive=True)
            self._watcher.start()

        except ImportError:
            print("[ConfigHub] watchdog未安装，文件监听功能不可用")

    def export_docs(self, output_path: str = "CONFIG_REFERENCE.md"):
        """
        自动生成配置文档

        生成Markdown格式的配置参考文档，包含所有字段说明。
        """
        lines = [
            "# AI-Novels 配置参考文档",
            "",
            > 自动生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 概述",
            "",
            "本文档列出AI-Novels的所有可配置项。配置可通过以下方式设置：",
            "",
            "1. **配置文件**: `config/config.yaml`（基础配置）",
            "2. **环境配置**: `config/config.{profile}.yaml`（环境覆盖）",
            "3. **环境变量**: `AINOVELS_` 前缀，如 `AINOVELS_LLM__DEFAULT_PROVIDER=openai`",
            "4. **.env文件**: 项目根目录或 `config/.env`",
            "",
            "优先级：环境变量 > 环境配置 > 基础配置 > 默认值",
            "",
            "## 配置项列表",
            "",
        ]

        # 递归生成文档
        def document_model(model_cls, prefix="", level=2):
            for field_name, field_info in model_cls.model_fields.items():
                key = f"{prefix}{field_name}" if prefix else field_name
                desc = field_info.description or ""
                default = field_info.default
                annotation = field_info.annotation

                lines.append(f"{'#' * level} `{key}`")
                lines.append("")
                lines.append(f"- **类型**: {annotation}")
                lines.append(f"- **默认值**: `{default}`")
                lines.append(f"- **说明**: {desc}")

                # 环境变量名
                env_var = f"AINOVELS_{key.upper().replace('.', '__')}"
                lines.append(f"- **环境变量**: `{env_var}`")
                lines.append("")

                # 如果是嵌套模型，递归
                if hasattr(annotation, "model_fields"):
                    document_model(annotation, f"{key}.", level + 1)

        document_model(AppConfig)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"[ConfigHub] 配置文档已生成: {output_path}")

    def health_check(self) -> Dict[str, Any]:
        """配置健康检查"""
        issues = []

        # 检查必填敏感项
        if self.config.is_production:
            if not self.config.security.secret_key:
                issues.append({"level": "error", "message": "生产环境未设置secret_key"})

        # 检查LLM配置
        if not self.config.llm.providers:
            issues.append({"level": "warning", "message": "未配置任何LLM提供商"})

        # 检查数据库配置
        active_dbs = self.config.database.active_connections
        if not active_dbs:
            issues.append({"level": "warning", "message": "未配置任何数据库连接"})

        return {
            "status": "healthy" if not issues else "issues_found",
            "issues": issues,
            "profile": self.config.environment.value,
            "active_databases": active_dbs,
            "llm_providers": list(self.config.llm.providers.keys()),
            "agents": list(self.config.agents.keys())
        }


# 全局便捷访问函数
def get_config() -> AppConfig:
    """获取配置实例"""
    return ConfigHub().config


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return ConfigHub().get(key, default)
```

### 4.3 统一加载器 - UnifiedConfigLoader

**职责**: 从多来源、多格式加载配置，按优先级合并

```python
# src/deepnovel/config/loader.py（重构版）

import os
import json
import yaml
import toml
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from dotenv import load_dotenv

from .vault import ConfigVault


class ConfigSource:
    """配置来源抽象基类"""

    def load(self) -> Dict[str, Any]:
        raise NotImplementedError


class FileConfigSource(ConfigSource):
    """文件配置来源"""

    def __init__(self, path: str):
        self.path = path
        self._mtime = 0

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {}

        self._mtime = os.path.getmtime(self.path)

        with open(self.path, 'r', encoding='utf-8') as f:
            content = f.read()

        ext = os.path.splitext(self.path)[1].lower()

        if ext == '.json':
            return json.loads(content)
        elif ext in ('.yaml', '.yml'):
            return yaml.safe_load(content) or {}
        elif ext == '.toml':
            return toml.loads(content)
        elif ext == '.ini' or ext == '.properties':
            return self._parse_ini(content)
        else:
            # 尝试JSON再YAML
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return yaml.safe_load(content) or {}

    def _parse_ini(self, content: str) -> Dict[str, Any]:
        import configparser
        parser = configparser.ConfigParser()
        parser.read_string(content)
        result = {}
        for section in parser.sections():
            result[section] = dict(parser[section])
        return result

    @property
    def is_modified(self) -> bool:
        if not os.path.exists(self.path):
            return False
        return os.path.getmtime(self.path) > self._mtime


class EnvConfigSource(ConfigSource):
    """环境变量配置来源"""

    def __init__(self, prefix: str = "AINOVELS_", delimiter: str = "__"):
        self.prefix = prefix
        self.delimiter = delimiter

    def load(self) -> Dict[str, Any]:
        result = {}

        for key, value in os.environ.items():
            if not key.startswith(self.prefix):
                continue

            # 去掉前缀
            config_key = key[len(self.prefix):]

            # 按分隔符分割为嵌套路径
            parts = config_key.split(self.delimiter)

            # 构建嵌套字典
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # 设置值（尝试类型转换）
            current[parts[-1]] = self._convert_type(value)

        return result

    def _convert_type(self, value: str) -> Any:
        """智能类型转换"""
        # 布尔值
        lower = value.lower()
        if lower in ('true', 'yes', '1', 'on'):
            return True
        if lower in ('false', 'no', '0', 'off'):
            return False

        # 空值
        if lower in ('null', 'none', ''):
            return None

        # 整数
        try:
            return int(value)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # JSON对象/数组
        if value.startswith(('{', '[')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # 字符串
        return value


class DotEnvSource(ConfigSource):
    """.env文件配置来源"""

    def __init__(self, path: str = ".env"):
        self.path = path

    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            load_dotenv(self.path, override=False)
        return {}  # .env直接写入os.environ，由EnvSource读取


class UnifiedConfigLoader:
    """
    统一配置加载器

    加载优先级（从低到高）：
    1. 内置默认值（Pydantic模型定义）
    2. config/config.yaml（基础配置）
    3. config/config.{profile}.yaml（环境配置）
    4. config/config.local.yaml（本地覆盖，gitignore）
    5. .env文件
    6. 环境变量 AINOVELS_*
    7. 运行时覆盖（程序内修改）
    """

    def __init__(
        self,
        config_dir: str = "config",
        profile: str = "development",
        env_file: str = "config/.env",
        vault: Optional[ConfigVault] = None
    ):
        self.config_dir = config_dir
        self.profile = profile
        self.env_file = env_file
        self.vault = vault
        self._sources: List[ConfigSource] = []

    def load(self) -> Dict[str, Any]:
        """加载并合并所有来源的配置"""
        config = {}

        # 1. 基础配置
        base_files = [
            os.path.join(self.config_dir, "config.yaml"),
            os.path.join(self.config_dir, "config.yml"),
            os.path.join(self.config_dir, "config.json"),
        ]
        for f in base_files:
            if os.path.exists(f):
                source = FileConfigSource(f)
                config = self._deep_merge(config, source.load())
                break

        # 2. 环境配置
        profile_files = [
            os.path.join(self.config_dir, f"config.{self.profile}.yaml"),
            os.path.join(self.config_dir, f"config.{self.profile}.yml"),
            os.path.join(self.config_dir, f"config.{self.profile}.json"),
        ]
        for f in profile_files:
            if os.path.exists(f):
                source = FileConfigSource(f)
                config = self._deep_merge(config, source.load())
                break

        # 3. 本地覆盖（不提交到git）
        local_file = os.path.join(self.config_dir, "config.local.yaml")
        if os.path.exists(local_file):
            source = FileConfigSource(local_file)
            config = self._deep_merge(config, source.load())

        # 4. .env文件
        if os.path.exists(self.env_file):
            DotEnvSource(self.env_file).load()

        # 5. 环境变量
        env_config = EnvConfigSource().load()
        config = self._deep_merge(config, env_config)

        # 6. 解析Vault引用
        if self.vault:
            config = self._resolve_vault_refs(config)

        # 7. 解析环境变量插值
        config = self._interpolate_env_vars(config)

        return config

    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并"""
        if not overlay:
            return base

        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _interpolate_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析 ${ENV_VAR:default} 格式的环境变量插值"""
        import re

        def process(value: Any) -> Any:
            if isinstance(value, str):
                pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

                def replace(match):
                    var_name = match.group(1)
                    default = match.group(2) or ""
                    return os.environ.get(var_name, default)

                return re.sub(pattern, replace, value)
            elif isinstance(value, dict):
                return {k: process(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process(item) for item in value]
            return value

        return process(config)

    def _resolve_vault_refs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析 ${vault:key} 格式的Vault引用"""
        import re

        def process(value: Any) -> Any:
            if isinstance(value, str):
                pattern = r'\$\{vault:([^}]+)\}'
                match = re.search(pattern, value)
                if match:
                    key = match.group(1)
                    decrypted = self.vault.get(key)
                    return re.sub(pattern, lambda m: decrypted or "", value)
            elif isinstance(value, dict):
                return {k: process(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process(item) for item in value]
            return value

        return process(config)
```

### 4.4 配置安全Vault

**职责**: 加密存储和读取敏感配置（API密钥、密码等）

```python
# src/deepnovel/config/vault.py

import os
import base64
import hashlib
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigVault:
    """
    配置保险箱

    用于安全存储敏感配置项（API密钥、密码等）。

    支持两种模式：
    1. 主密钥模式：提供主密钥加密/解密
    2. 环境变量模式：从环境变量读取密钥

    用法：
        vault = ConfigVault(key="my-master-key")
        vault.set("openai_api_key", "sk-xxx")

        # 在配置文件中存储：
        # api_key: "${vault:openai_api_key}"
    """

    def __init__(self, key: Optional[str] = None, vault_file: str = "config/.vault"):
        self.vault_file = vault_file
        self._key = self._derive_key(key or os.environ.get("AINOVELS_VAULT_KEY", ""))
        self._cache: Dict[str, str] = {}
        self._load()

    def _derive_key(self, password: str) -> bytes:
        """从密码派生加密密钥"""
        if not password:
            # 无密码时使用默认（仅开发环境）
            return Fernet.generate_key()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ai_novels_vault_salt",  # 实际应使用随机salt并存储
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _get_fernet(self) -> Fernet:
        return Fernet(self._key)

    def set(self, key: str, value: str):
        """存储敏感值"""
        self._cache[key] = value
        self._save()

    def get(self, key: str) -> Optional[str]:
        """获取敏感值"""
        return self._cache.get(key)

    def delete(self, key: str):
        """删除敏感值"""
        if key in self._cache:
            del self._cache[key]
            self._save()

    def _save(self):
        """保存到文件（加密）"""
        f = self._get_fernet()
        data = {}
        for k, v in self._cache.items():
            data[k] = f.encrypt(v.encode()).decode()

        os.makedirs(os.path.dirname(self.vault_file), exist_ok=True)
        with open(self.vault_file, 'w') as file:
            import json
            json.dump(data, file)

    def _load(self):
        """从文件加载（解密）"""
        if not os.path.exists(self.vault_file):
            return

        try:
            f = self._get_fernet()
            with open(self.vault_file, 'r') as file:
                import json
                data = json.load(file)

            for k, v in data.items():
                try:
                    self._cache[k] = f.decrypt(v.encode()).decode()
                except Exception:
                    pass  # 解密失败则跳过
        except Exception:
            pass

    def rotate_key(self, new_password: str):
        """轮换加密密钥"""
        # 解密所有数据
        plaintext = dict(self._cache)

        # 更新密钥
        self._key = self._derive_key(new_password)

        # 重新加密保存
        self._cache = plaintext
        self._save()
```

### 4.5 依赖注入集成

**职责**: 让配置自动注入到需要它的组件中，与Step8的工具层和Step4的DI容器打通

```python
# src/deepnovel/config/injector.py

from typing import Type, TypeVar, Optional, Any
from functools import wraps

from .hub import ConfigHub
from src.deepnovel.core.di_container import DIContainer, Lifecycle

T = TypeVar('T')


class ConfigInjector:
    """
    配置依赖注入集成

    将ConfigHub与DI容器打通，实现配置自动注入。

    用法：
        # 在DI容器注册时
        container = DIContainer()
        ConfigInjector.register_with_container(container)

        # 在类中注入配置
        class MyService:
            config: AppConfig = ConfigInject()  # 自动注入
    """

    @staticmethod
    def register_with_container(container: DIContainer):
        """向DI容器注册配置相关服务"""
        hub = ConfigHub()

        # 注册ConfigHub单例
        container.register_singleton(object, lambda p: hub)  # ConfigHub类型

        # 注册AppConfig（每次从Hub获取最新）
        container.register_singleton(object, lambda p: hub.config)  # AppConfig类型

    @staticmethod
    def inject_config(cls: Type[T]) -> Type[T]:
        """
        类装饰器：自动为类注入配置

        用法：
            @inject_config
            class LLMService:
                def __init__(self):
                    self.provider = self.config.llm.default_provider
        """
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            self.config = ConfigHub().config
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls


class ConfigInject:
    """
    配置注入描述符

    用法：
        class MyService:
            config = ConfigInject()  # 注入AppConfig
            llm_config = ConfigInject("llm")  # 注入LLMConfig子集
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self._value = None

    def __get__(self, instance, owner):
        if instance is None:
            return self

        hub = ConfigHub()
        if not hub.is_initialized:
            raise RuntimeError("ConfigHub未初始化")

        if self.path:
            return hub.get(self.path)
        return hub.config

    def __set__(self, instance, value):
        raise AttributeError("配置是只读的，请通过ConfigHub修改")
```

---

## 5. 配置目录结构

```
config/
├── config.yaml                    # 基础配置（提交到git）
├── config.development.yaml        # 开发环境覆盖
├── config.production.yaml         # 生产环境覆盖
├── config.local.yaml              # 本地覆盖（.gitignore）
├── .env                           # Docker环境变量
├── .env.example                   # .env模板（提交到git）
├── .vault                         # 加密敏感配置（.gitignore）
├── .development                   # 环境标记文件（空文件即可）
└── schemas/                       # 自定义JSON Schema（可选）
    └── custom_validation.yaml
```

### 5.1 配置示例

```yaml
# config/config.yaml
app_name: "AI-Novels"
version: "1.0.0"
debug: false

llm:
  default_provider: "ollama"
  embedding_provider: "ollama"
  providers:
    ollama:
      provider: "ollama"
      model: "qwen2.5-14b"
      base_url: "http://localhost:11434"
      temperature: 0.7
      max_tokens: 8192
    openai:
      provider: "openai"
      model: "gpt-4o"
      api_key: "${vault:openai_api_key}"
      temperature: 0.7
      max_tokens: 4096

database:
  sqlite:
    path: "data/app.db"
    wal_mode: true

agents:
  world_builder:
    name: "world_builder"
    description: "世界观构建"
    llm_override:
      provider: "ollama"
      model: "qwen2.5-14b"
      temperature: 0.8
    tools: ["fact_query", "retrieve_world_knowledge"]
  content_generator:
    name: "content_generator"
    description: "内容生成"
    llm_override:
      provider: "openai"
      temperature: 0.9
    tools: ["retrieve_character_memory", "retrieve_plot_continuity"]

rag:
  enabled: true
  top_k: 5
  similarity_threshold: 0.7

generation:
  default_word_count: 3000
  output_dir: "output"

logging:
  level: "INFO"
  file_enabled: true
  file_path: "logs/app.log"

api:
  host: "0.0.0.0"
  port: 8000
```

---

## 6. 与现有系统的集成

### 6.1 向后兼容

```python
# src/deepnovel/config/compat.py
"""向后兼容层，让旧代码逐步迁移"""

from .hub import ConfigHub, get_config, get_config_value

# 旧接口兼容
class Settings:
    """兼容旧的Settings单例"""

    def __init__(self):
        self._hub = ConfigHub()

    def get(self, key: str, default=None):
        return get_config_value(key, default)

    def get_llm(self, provider=None):
        config = get_config()
        if provider:
            return config.llm.providers.get(provider, {})
        return config.llm.providers.get(config.llm.default_provider, {})

    def get_database(self, name):
        db = getattr(get_config().database, name, None)
        return db.model_dump() if db else {}

    def get_agent(self, name):
        agent = get_config().get_agent(name)
        return agent.model_dump() if agent else {}


# 全局实例（兼容旧代码）
settings = Settings()
```

### 6.2 迁移路径

| 旧代码 | 新代码 |
|--------|--------|
| `from src.deepnovel.config import settings` | `from src.deepnovel.config import ConfigHub, get_config` |
| `settings.get("llm.default")` | `ConfigHub().config.llm.default_provider` |
| `settings.get("database.mysql.host")` | `ConfigHub().config.database.mysql.host` |
| `settings.get_agent("world_builder")` | `ConfigHub().config.get_agent("world_builder")` |
| `os.environ.get("OPENAI_API_KEY")` | `ConfigHub().config.llm.providers["openai"].api_key` |
| `config.get("key", default)` | `ConfigHub().get("key", default)` |

---

## 7. 实施计划

### Phase 1: 模型定义（第1-3天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 根配置模型 | `config/models/base.py` | AppConfig + 所有子配置Pydantic模型 |
| 模型验证器 | `config/models/validators.py` | 跨模型联合验证逻辑 |
| 模型文档 | `config/models/__init__.py` | 统一导出 |

**验收标准**:
- 所有配置项有类型注解和Field描述
- `AppConfig.model_validate()`能验证通过示例配置
- IDE能自动补全 `config.llm.providers.openai.temperature`

### Phase 2: 加载器重构（第4-5天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 统一加载器 | `config/loader.py` | UnifiedConfigLoader（重构） |
| 多来源支持 | `config/sources.py` | FileSource/EnvSource/DotEnvSource |
| 合并逻辑 | `config/merger.py` | Profile分层合并 + 环境变量插值 |

**验收标准**:
- 支持JSON/YAML/TOML/INI格式
- 环境变量 `AINOVELS_LLM__DEFAULT_PROVIDER` 正确映射到 `llm.default_provider`
- `${ENV_VAR:default}` 插值正常工作

### Phase 3: 安全与Vault（第6-7天）

| 任务 | 文件 | 内容 |
|------|------|------|
| ConfigVault | `config/vault.py` | Fernet加密存储 |
| SecretResolver | `config/secrets.py` | `${vault:xxx}` 解析 |
| 敏感项脱敏 | `config/models/base.py` | `dump_sensitive_masked()` |

**验收标准**:
- API密钥加密存储在 `.vault` 文件
- 配置日志中敏感字段显示为 `****`
- Vault密钥支持轮换

### Phase 4: ConfigHub中枢（第8-10天）

| 任务 | 文件 | 内容 |
|------|------|------|
| ConfigHub | `config/hub.py` | 统一入口门面 |
| 文件监听 | `config/watcher.py` | watchdog热加载 |
| 变更通知 | `config/publisher.py` | 发布订阅模式 |
| 健康检查 | `config/health.py` | 配置项健康状态 |

**验收标准**:
- `ConfigHub().initialize()` 成功加载所有配置
- 修改 `config.yaml` 后自动热加载
- 监听回调在配置变更时触发

### Phase 5: 文档与兼容（第11-12天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 文档生成 | `config/docs.py` | 自动生成Markdown配置文档 |
| 向后兼容 | `config/compat.py` | Settings兼容层 |
| DI集成 | `config/injector.py` | 与DI容器集成 |

**验收标准**:
- `CONFIG_REFERENCE.md` 自动生成
- 旧代码 `settings.get()` 仍能工作（带弃用警告）

### Phase 6: 全量迁移（第13-15天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 迁移LLM模块 | `llm/*.py` | 使用新配置模型 |
| 迁移数据库模块 | `database/*.py` | 使用新配置模型 |
| 迁移Agent模块 | `agents/*.py` | 使用新配置模型 |
| 迁移API模块 | `api/*.py` | 使用新配置模型 |

**验收标准**:
- 所有模块通过 `ConfigHub().config` 访问配置
- 无直接 `os.environ.get()` 读取配置（除Vault密钥外）

### Phase 7: 清理旧代码（第16天）

| 任务 | 处置 |
|------|------|
| `config/manager.py` 旧 ConfigManager | 删除（功能由ConfigHub取代） |
| `config/validator.py` JSON Schema | 删除（Pydantic取代） |
| `config/settings.py` | 删除（由compat.py取代） |
| `utils/config_loader.py` | 删除（功能重复） |
| `config/loader.py` 旧版 | 替换为新版 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Pydantic v2迁移成本 | 旧代码大量使用dict访问 | 提供 `to_dict()` 兼容方法 + 渐进式迁移 |
| 配置文件格式不兼容 | 新旧格式混用导致加载失败 | 提供配置迁移工具 + 格式检测 |
| Vault密钥丢失 | 加密配置无法解密 | 密钥备份机制 + 支持明文fallback（仅开发） |
| 热加载引发状态不一致 | 运行中配置变更导致组件状态异常 | 变更通知 + 组件自行决定重载策略 |
| 环境变量命名冲突 | `AINOVELS_*` 与其他应用冲突 | 支持自定义前缀 + 文档说明 |

---

## 9. 成功指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|---------|
| 配置类型安全覆盖率 | 0% | 100% | Pydantic模型覆盖的配置项比例 |
| 配置入口统一度 | 30%（多处分散） | 100% | 通过ConfigHub访问的比例 |
| 敏感信息加密率 | 0% | 100% | Vault存储的敏感项/总敏感项 |
| 热加载响应时间 | N/A | <1s | 文件修改到配置生效的延迟 |
| 配置验证失败早暴露 | 运行时 | 启动时 | 配置错误在import阶段发现 |
| IDE自动补全支持 | 无 | 全配置路径 | IDE能否补全 `config.llm.providers` |
| 配置文档自动生成 | 无 | 每次部署生成 | CONFIG_REFERENCE.md存在且最新 |
| 旧代码兼容过渡期 | N/A | 2个Sprint | 旧 `settings.get()` 仍可工作 |
