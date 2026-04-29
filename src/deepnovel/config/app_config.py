"""
统一应用配置 — Pydantic Settings v2

替代旧的 ConfigManager/Settings，提供：
- 类型安全的配置模型
- 环境变量自动注入
- 分层覆盖（默认值 → .env → 环境变量）
- 敏感信息脱敏

@file: config/app_config.py
@date: 2026-04-29
"""

from functools import lru_cache
from typing import Any, Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """数据库配置"""

    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = Field(
        default="postgresql+asyncpg://deepnovel:deepnovel_pass@localhost:5432/deepnovel",
        description="数据库连接URL",
    )
    pool_size: int = Field(default=10, ge=1, description="连接池大小")
    max_overflow: int = Field(default=20, ge=0, description="连接池溢出")
    pool_pre_ping: bool = Field(default=True, description="连接前ping检测")
    pool_recycle: int = Field(default=300, ge=0, description="连接回收时间(秒)")
    echo: bool = Field(default=False, description="SQL语句回显")


class RedisConfig(BaseSettings):
    """Redis配置"""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL",
    )
    stream_key: str = Field(default="deepnovel:events", description="事件流键名")
    consumer_group: str = Field(default="deepnovel:consumers", description="消费者组名")


class LLMProviderConfig(BaseSettings):
    """单个LLM提供商配置"""

    provider: str = Field(..., description="提供商标识")
    model: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="自定义Base URL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(default=4096, ge=1, description="最大生成token数")
    timeout: float = Field(default=30.0, ge=1.0, description="请求超时（秒）")
    retry_times: int = Field(default=3, ge=0, description="重试次数")
    enabled: bool = Field(default=True, description="是否启用")


class LLMConfig(BaseSettings):
    """LLM全局配置"""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    default_provider: str = Field(default="ollama", description="默认提供商")
    providers: Dict[str, LLMProviderConfig] = Field(
        default_factory=dict, description="提供商列表"
    )
    fallback_enabled: bool = Field(default=True, description="是否启用降级")
    embedding_provider: Optional[str] = Field(default=None, description="默认嵌入提供商")


class LogConfig(BaseSettings):
    """日志配置"""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = Field(default="INFO", description="日志级别")
    json_format: bool = Field(default=False, description="JSON格式输出")
    service_name: str = Field(default="deepnovel-ai", description="服务名称")
    environment: str = Field(default="development", description="环境名称")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"日志级别必须是其中之一: {valid}")
        return upper


class AppConfig(BaseSettings):
    """应用统一配置根模型

    所有配置通过此类统一管理，支持：
    - 环境变量自动映射（前缀见各子配置）
    - .env 文件加载
    - 类型安全验证
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="APP_",
        env_nested_delimiter="__",
    )

    # 应用基础
    app_name: str = Field(default="deepnovel-ai", description="应用名称")
    app_version: str = Field(default="2.0.0", description="应用版本")
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")

    # 服务器
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="监听端口")

    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    log: LogConfig = Field(default_factory=LogConfig)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid = {"development", "test", "staging", "production"}
        if v not in valid:
            raise ValueError(f"环境必须是其中之一: {valid}")
        return v

    def to_safe_dict(self) -> Dict[str, Any]:
        """导出脱敏后的配置字典（用于日志/监控）"""
        data = self.model_dump()
        # 脱敏所有 api_key
        self._mask_api_keys(data)
        return data

    def _mask_api_keys(self, data: Dict[str, Any]) -> None:
        """递归脱敏 API 密钥"""
        for key, value in data.items():
            if isinstance(value, dict):
                self._mask_api_keys(value)
            elif key == "api_key" and isinstance(value, str) and value:
                data[key] = f"{value[:4]}****{value[-4:]}" if len(value) > 8 else "****"

    def __repr__(self) -> str:
        return f"AppConfig(env={self.environment}, debug={self.debug}, port={self.port})"


@lru_cache
def get_config() -> AppConfig:
    """获取全局配置单例

    使用 lru_cache 确保全进程只有一个实例。
    首次调用时从环境变量和 .env 文件加载。
    """
    return AppConfig()


def reload_config() -> AppConfig:
    """重新加载配置（用于热更新场景）"""
    get_config.cache_clear()
    return get_config()
