# Step 3: LLM层重构 - 多模型工厂架构

## 1. 设计哲学

### 核心转变

```
从：单一模型硬编码 → 到：多模型动态路由
从：统一配置 → 到：Agent独立LLM配置
从：简单适配器 → 到：功能分级+模型匹配
从：同步阻塞 → 到：异步流式+并发控制
```

### 设计原则

1. **模型即能力**：不同模型有不同特长，匹配任务需求
2. **Agent独立配置**：每个Agent可指定自己的LLM参数
3. **工厂模式初始化**：统一接口，动态创建
4. **流式优先**：实时反馈，降低延迟感知
5. **容错降级**：主模型失败时自动切换备用

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    LLM 路由层 (Router)                  │
│  • 任务分析 → 模型选择 → 负载均衡 → 结果聚合            │
├─────────────────────────────────────────────────────────┤
│                    LLM 工厂 (Factory)                    │
│  • 配置解析 → 实例创建 → 连接池管理 → 健康检查           │
├─────────────────────────────────────────────────────────┤
│                    LLM 适配器层 (Adapters)                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│  │  OpenAI │ │ Claude  │ │  Qwen   │ │  Local  │     │
│  │  GPT-4  │ │  Opus   │ │  Max    │ │  LLaMA  │     │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│  │ Gemini  │ │  Kimi   │ │ DeepSeek│ │  GLM-4  │     │
│  │ Pro 1.5 │ │ k1.5    │ │  V3     │ │ 9B/32B  │     │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
├─────────────────────────────────────────────────────────┤
│                    功能分级层 (Capability Tiers)         │
│  Tier 1: 推理/创意  Tier 2: 对话/生成  Tier 3: 简单任务 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Agent独立配置

```python
# Agent配置示例
AGENT_LLM_CONFIG = {
    "world_builder": {
        "primary": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tier": "creative"
        },
        "fallback": {
            "provider": "anthropic",
            "model": "claude-3-opus-20240229",
            "temperature": 0.7
        }
    },
    "character_mind": {
        "primary": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.9,  # 更高温度增加多样性
            "max_tokens": 2048,
            "tier": "emotional"
        },
        "fallback": {
            "provider": "local",
            "model": "qwen2.5-14b",
            "temperature": 0.9
        }
    },
    "causal_reasoning": {
        "primary": {
            "provider": "openai",
            "model": "o1-preview",  # 推理专用模型
            "temperature": 0.3,     # 低温度保证确定性
            "max_tokens": 8192,
            "tier": "reasoning"
        },
        "fallback": {
            "provider": "deepseek",
            "model": "deepseek-reasoner",
            "temperature": 0.3
        }
    },
    "narrative_record": {
        "primary": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.8,
            "max_tokens": 8192,
            "tier": "creative"
        },
        "stream": True  # 流式输出
    },
    "quality_checker": {
        "primary": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.2,  # 低温度保证一致性
            "tier": "analytical"
        }
    }
}
```

---

## 3. 工厂模式实现

### 3.1 LLM接口基类

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ModelTier(Enum):
    """模型能力分级"""
    REASONING = "reasoning"      # 推理/逻辑
    CREATIVE = "creative"       # 创意/生成
    EMOTIONAL = "emotional"      # 情感/对话
    ANALYTICAL = "analytical"    # 分析/评估
    SIMPLE = "simple"            # 简单任务

@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 60
    retry_count: int = 3
    stream: bool = False
    tier: ModelTier = ModelTier.SIMPLE
    
    # 高级参数
    response_format: Optional[Dict] = None  # JSON模式
    tools: Optional[List[Dict]] = None       # 函数调用
    seed: Optional[int] = None               # 确定性输出

@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    latency: float
    finish_reason: str
    metadata: Dict[str, Any]

class BaseLLM(ABC):
    """LLM接口基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.model_name = config.model
        self._client = None
        self._health_status = True
        self._last_used = 0
    
    @abstractmethod
    async def initialize(self):
        """初始化连接"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """生成响应（同步）"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """获取能力列表"""
        pass
    
    async def close(self):
        """关闭连接"""
        pass
```

### 3.2 具体适配器实现

```python
# OpenAI适配器
class OpenAILLM(BaseLLM):
    """OpenAI GPT适配器"""
    
    async def initialize(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.api_base,
            timeout=self.config.timeout
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        import time
        start = time.time()
        
        # 构建消息
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        
        # 调用API
        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            response_format=self.config.response_format,
            tools=self.config.tools,
            seed=self.config.seed,
            **kwargs
        )
        
        latency = time.time() - start
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            latency=latency,
            finish_reason=response.choices[0].finish_reason,
            metadata={"provider": "openai"}
        )
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        
        stream = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def health_check(self) -> bool:
        try:
            await self._client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False
    
    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "streaming": True,
            "function_calling": True,
            "json_mode": True,
            "vision": "vision" in self.config.model,
            "reasoning": self.config.model in ["o1-preview", "o1-mini"]
        }

# Anthropic适配器
class AnthropicLLM(BaseLLM):
    """Anthropic Claude适配器"""
    
    async def initialize(self):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.api_base,
            timeout=self.config.timeout
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        import time
        start = time.time()
        
        # Claude使用不同的消息格式
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        
        response = await self._client.messages.create(
            model=self.config.model,
            messages=messages,
            system=system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            **kwargs
        )
        
        latency = time.time() - start
        
        return LLMResponse(
            content=response.content[0].text,
            model=self.config.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            latency=latency,
            finish_reason=response.stop_reason,
            metadata={"provider": "anthropic"}
        )
    
    async def generate_stream(self, prompt, system_prompt=None, messages=None, **kwargs):
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        
        async with self._client.messages.stream(
            model=self.config.model,
            messages=messages,
            system=system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False
    
    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "streaming": True,
            "function_calling": True,
            "json_mode": False,  # Claude不原生支持JSON模式
            "vision": True,  # Claude支持vision
            "reasoning": self.config.model in ["claude-3-opus"]
        }

# 本地模型适配器（支持vLLM/llama.cpp等）
class LocalLLM(BaseLLM):
    """本地模型适配器"""
    
    async def initialize(self):
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._api_url = self.config.api_base or "http://localhost:8000/v1"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        import time
        start = time.time()
        
        # 兼容OpenAI格式
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        
        async with self._session.post(
            f"{self._api_url}/chat/completions",
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": False
            }
        ) as response:
            data = await response.json()
        
        latency = time.time() - start
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=self.config.model,
            usage=data.get("usage", {}),
            latency=latency,
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            metadata={"provider": "local"}
        )
    
    async def generate_stream(self, prompt, system_prompt=None, messages=None, **kwargs):
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        
        async with self._session.post(
            f"{self._api_url}/chat/completions",
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True
            }
        ) as response:
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    if "choices" in data and data["choices"]:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
    
    async def health_check(self) -> bool:
        try:
            async with self._session.get(f"{self._api_url}/models") as resp:
                return resp.status == 200
        except Exception:
            return False
    
    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "streaming": True,
            "function_calling": False,  # 本地模型通常不支持
            "json_mode": False,
            "vision": False,
            "reasoning": False
        }

# 更多适配器...
class QwenLLM(BaseLLM):
    """阿里云Qwen适配器"""
    pass

class KimiLLM(BaseLLM):
    """Moonshot Kimi适配器"""
    pass

class DeepSeekLLM(BaseLLM):
    """DeepSeek适配器"""
    pass

class GeminiLLM(BaseLLM):
    """Google Gemini适配器"""
    pass
```

### 3.3 LLM工厂

```python
class LLMFactory:
    """
    LLM工厂 - 动态创建LLM实例
    
    功能：
    1. 配置解析
    2. 实例创建
    3. 连接池管理
    4. 健康检查
    5. 负载均衡
    """
    
    _registry: Dict[str, Type[BaseLLM]] = {
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
        "local": LocalLLM,
        "qwen": QwenLLM,
        "kimi": KimiLLM,
        "deepseek": DeepSeekLLM,
        "gemini": GeminiLLM,
    }
    
    _instances: Dict[str, BaseLLM] = {}  # 实例缓存
    _configs: Dict[str, LLMConfig] = {}   # 配置缓存
    
    @classmethod
    def register_provider(cls, name: str, adapter_class: Type[BaseLLM]):
        """注册新的提供商"""
        cls._registry[name] = adapter_class
    
    @classmethod
    async def create(
        cls,
        config: Union[LLMConfig, Dict, str],
        agent_name: Optional[str] = None
    ) -> BaseLLM:
        """
        创建LLM实例
        
        输入：
        - config: 配置对象/字典/配置文件路径
        - agent_name: Agent名称（用于独立配置）
        
        输出：
        - LLM实例
        """
        # 解析配置
        if isinstance(config, str):
            config = cls._load_config_from_file(config)
        elif isinstance(config, dict):
            config = LLMConfig(**config)
        
        # Agent独立配置
        if agent_name and agent_name in AGENT_LLM_CONFIG:
            agent_config = AGENT_LLM_CONFIG[agent_name]
            # 合并配置（Agent配置覆盖全局配置）
            config = cls._merge_config(config, agent_config["primary"])
        
        # 创建缓存键
        cache_key = f"{config.provider}:{config.model}:{agent_name or 'default'}"
        
        # 检查缓存
        if cache_key in cls._instances:
            instance = cls._instances[cache_key]
            # 健康检查
            if await instance.health_check():
                return instance
            # 不健康，移除缓存
            del cls._instances[cache_key]
        
        # 创建新实例
        adapter_class = cls._registry.get(config.provider)
        if not adapter_class:
            raise ValueError(f"Unknown provider: {config.provider}")
        
        instance = adapter_class(config)
        await instance.initialize()
        
        # 健康检查
        if not await instance.health_check():
            # 尝试备用配置
            if agent_name and agent_name in AGENT_LLM_CONFIG:
                fallback_config = AGENT_LLM_CONFIG[agent_name].get("fallback")
                if fallback_config:
                    fallback = LLMConfig(**fallback_config)
                    instance = adapter_class(fallback)
                    await instance.initialize()
        
        # 缓存实例
        cls._instances[cache_key] = instance
        cls._configs[cache_key] = config
        
        return instance
    
    @classmethod
    async def get_or_create(
        cls,
        agent_name: str,
        task_type: Optional[str] = None
    ) -> BaseLLM:
        """
        获取或创建Agent专用的LLM实例
        
        支持任务类型覆盖：
        - 如果指定了task_type，使用对应tier的模型
        """
        # 获取Agent配置
        if agent_name not in AGENT_LLM_CONFIG:
            # 使用默认配置
            config = LLMConfig(
                provider="openai",
                model="gpt-4o-mini",
                tier=ModelTier.SIMPLE
            )
        else:
            agent_config = AGENT_LLM_CONFIG[agent_name]
            
            # 任务类型覆盖
            if task_type:
                # 根据任务类型选择模型
                task_config = cls._get_task_config(agent_name, task_type)
                if task_config:
                    config = LLMConfig(**task_config)
                else:
                    config = LLMConfig(**agent_config["primary"])
            else:
                config = LLMConfig(**agent_config["primary"])
        
        return await cls.create(config, agent_name)
    
    @classmethod
    def _get_task_config(cls, agent_name: str, task_type: str) -> Optional[Dict]:
        """获取任务类型对应的配置"""
        agent_config = AGENT_LLM_CONFIG.get(agent_name, {})
        task_overrides = agent_config.get("task_overrides", {})
        return task_overrides.get(task_type)
    
    @classmethod
    async def close_all(cls):
        """关闭所有实例"""
        for instance in cls._instances.values():
            await instance.close()
        cls._instances.clear()
    
    @classmethod
    async def health_check_all(cls) -> Dict[str, bool]:
        """检查所有实例健康状态"""
        results = {}
        for key, instance in cls._instances.items():
            results[key] = await instance.health_check()
        return results
```

---

## 4. 智能路由层

### 4.1 任务分析器

```python
class TaskAnalyzer:
    """
    任务分析器 - 分析任务需求，匹配模型能力
    """
    
    def analyze(self, prompt: str, context: Dict = None) -> TaskProfile:
        """
        分析任务特征
        
        返回：
        - 任务类型
        - 复杂度
        - 所需能力
        - 预期token数
        """
        profile = TaskProfile()
        
        # 1. 任务类型检测
        profile.task_type = self._detect_task_type(prompt)
        
        # 2. 复杂度评估
        profile.complexity = self._assess_complexity(prompt)
        
        # 3. 所需能力
        profile.required_capabilities = self._detect_required_capabilities(prompt)
        
        # 4. 预期token数
        profile.estimated_tokens = self._estimate_tokens(prompt)
        
        return profile
    
    def _detect_task_type(self, prompt: str) -> str:
        """检测任务类型"""
        # 关键词匹配
        reasoning_keywords = ["分析", "推理", "逻辑", "因果", "为什么", "如何"]
        creative_keywords = ["创作", "生成", "写", "描述", "故事", "场景"]
        emotional_keywords = ["情感", "感受", "心理", "情绪", "反应"]
        analytical_keywords = ["评估", "检查", "质量", "一致性", "评分"]
        
        if any(kw in prompt for kw in reasoning_keywords):
            return "reasoning"
        elif any(kw in prompt for kw in creative_keywords):
            return "creative"
        elif any(kw in prompt for kw in emotional_keywords):
            return "emotional"
        elif any(kw in prompt for kw in analytical_keywords):
            return "analytical"
        else:
            return "simple"
    
    def _assess_complexity(self, prompt: str) -> float:
        """评估复杂度（0-1）"""
        factors = {
            "length": min(len(prompt) / 1000, 1.0),
            "steps": prompt.count("然后") + prompt.count("接着") + prompt.count("最后"),
            "conditions": prompt.count("如果") + prompt.count("假设"),
            "entities": len(set(re.findall(r'[\u4e00-\u9fff]{2,4}', prompt))),  # 中文实体
        }
        
        complexity = (
            factors["length"] * 0.3 +
            min(factors["steps"] / 5, 1.0) * 0.3 +
            min(factors["conditions"] / 3, 1.0) * 0.2 +
            min(factors["entities"] / 10, 1.0) * 0.2
        )
        
        return min(1.0, complexity)
    
    def _detect_required_capabilities(self, prompt: str) -> List[str]:
        """检测所需能力"""
        capabilities = []
        
        if "图片" in prompt or "图像" in prompt or "vision" in prompt.lower():
            capabilities.append("vision")
        
        if "函数" in prompt or "工具" in prompt or "调用" in prompt:
            capabilities.append("function_calling")
        
        if "JSON" in prompt or "json" in prompt:
            capabilities.append("json_mode")
        
        if len(prompt) > 8000:
            capabilities.append("long_context")
        
        return capabilities
    
    def _estimate_tokens(self, prompt: str) -> int:
        """估算token数"""
        # 粗略估算：中文字符 ≈ 1.5 tokens，英文 ≈ 0.75 tokens
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', prompt))
        english_chars = len(re.findall(r'[a-zA-Z]', prompt))
        
        estimated = int(chinese_chars * 1.5 + english_chars * 0.75)
        return estimated
```

### 4.2 模型选择器

```python
class ModelSelector:
    """
    模型选择器 - 根据任务选择最佳模型
    """
    
    def __init__(self, factory: LLMFactory):
        self.factory = factory
        self.analyzer = TaskAnalyzer()
    
    async def select(
        self,
        prompt: str,
        agent_name: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> Tuple[BaseLLM, Dict]:
        """
        选择最佳模型
        
        返回：
        - LLM实例
        - 选择理由
        """
        # 1. 分析任务
        profile = self.analyzer.analyze(prompt)
        
        # 2. 如果指定了Agent，优先使用Agent配置
        if agent_name:
            llm = await self.factory.get_or_create(agent_name, profile.task_type)
            return llm, {
                "reason": f"Agent '{agent_name}' 专用配置",
                "task_type": profile.task_type,
                "model": llm.config.model
            }
        
        # 3. 如果指定了模型，直接使用
        if preferred_model:
            config = LLMConfig(model=preferred_model)
            llm = await self.factory.create(config)
            return llm, {
                "reason": "用户指定模型",
                "model": preferred_model
            }
        
        # 4. 智能选择
        candidates = await self._get_candidates(profile)
        
        # 5. 评分排序
        scored = []
        for llm in candidates:
            score = self._score_model(llm, profile)
            scored.append((score, llm))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        best_llm = scored[0][1]
        return best_llm, {
            "reason": f"任务类型: {profile.task_type}, 复杂度: {profile.complexity:.2f}",
            "task_type": profile.task_type,
            "model": best_llm.config.model,
            "score": scored[0][0]
        }
    
    def _score_model(self, llm: BaseLLM, profile: TaskProfile) -> float:
        """评分模型匹配度"""
        score = 0.0
        
        # 能力匹配
        capabilities = llm.get_capabilities()
        for cap in profile.required_capabilities:
            if capabilities.get(cap, False):
                score += 0.2
        
        # 任务类型匹配
        tier_scores = {
            ModelTier.REASONING: {"reasoning": 1.0, "creative": 0.6, "analytical": 0.8},
            ModelTier.CREATIVE: {"creative": 1.0, "emotional": 0.8, "reasoning": 0.5},
            ModelTier.EMOTIONAL: {"emotional": 1.0, "creative": 0.7, "simple": 0.8},
            ModelTier.ANALYTICAL: {"analytical": 1.0, "reasoning": 0.9, "simple": 0.7},
            ModelTier.SIMPLE: {"simple": 1.0, "analytical": 0.5, "creative": 0.3}
        }
        
        tier_score = tier_scores.get(llm.config.tier, {})
        score += tier_score.get(profile.task_type, 0.5) * 0.4
        
        # 复杂度匹配（复杂任务需要强模型）
        if profile.complexity > 0.7 and llm.config.tier in [ModelTier.REASONING, ModelTier.CREATIVE]:
            score += 0.2
        elif profile.complexity < 0.3 and llm.config.tier == ModelTier.SIMPLE:
            score += 0.2
        
        # 成本考虑（简单任务优先用便宜模型）
        if profile.task_type == "simple" and "mini" in llm.config.model:
            score += 0.1
        
        return score
```

---

## 5. Agent工具封装

### 5.1 LLMGenerateTool - 生成工具

```python
class LLMGenerateTool:
    """
    LLM生成工具 - Agent可直接调用
    
    功能：
    1. 智能模型选择
    2. 流式/非流式生成
    3. 自动重试
    4. 降级处理
    """
    
    def __init__(self, factory: LLMFactory, selector: ModelSelector):
        self.factory = factory
        self.selector = selector
    
    async def generate(
        self,
        prompt: str,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        preferred_model: Optional[str] = None,
        **kwargs
    ) -> Union[LLMResponse, AsyncIterator[str]]:
        """
        生成文本
        
        输入：
        - prompt: 提示词
        - agent_name: Agent名称（用于独立配置）
        - system_prompt: 系统提示
        - stream: 是否流式输出
        - preferred_model: 优先使用的模型
        
        输出：
        - 非流式: LLMResponse
        - 流式: AsyncIterator[str]
        """
        # 选择模型
        llm, selection_info = await self.selector.select(
            prompt, agent_name, preferred_model
        )
        
        try:
            if stream:
                return llm.generate_stream(prompt, system_prompt, **kwargs)
            else:
                return await llm.generate(prompt, system_prompt, **kwargs)
        
        except Exception as e:
            # 自动降级
            logger.warning(f"Primary model failed: {e}, trying fallback")
            
            if agent_name and agent_name in AGENT_LLM_CONFIG:
                fallback_config = AGENT_LLM_CONFIG[agent_name].get("fallback")
                if fallback_config:
                    fallback_llm = await self.factory.create(
                        LLMConfig(**fallback_config)
                    )
                    
                    if stream:
                        return fallback_llm.generate_stream(prompt, system_prompt, **kwargs)
                    else:
                        return await fallback_llm.generate(prompt, system_prompt, **kwargs)
            
            raise
    
    async def generate_json(
        self,
        prompt: str,
        schema: Dict,
        agent_name: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        生成JSON（结构化输出）
        
        输入：
        - prompt: 提示词
        - schema: JSON Schema
        - agent_name: Agent名称
        
        输出：
        - 解析后的JSON字典
        """
        # 选择支持JSON模式的模型
        llm, _ = await self.selector.select(prompt, agent_name)
        
        # 检查是否支持JSON模式
        if llm.get_capabilities().get("json_mode"):
            # 使用原生JSON模式
            response = await llm.generate(
                prompt,
                response_format={"type": "json_object"},
                **kwargs
            )
        else:
            # 手动约束（在prompt中要求JSON输出）
            json_prompt = f"""
{prompt}

请严格按照以下JSON Schema输出：
{json.dumps(schema, indent=2, ensure_ascii=False)}

只输出JSON，不要其他内容。
"""
            response = await llm.generate(json_prompt, **kwargs)
        
        # 解析JSON
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # 尝试提取JSON
            return self._extract_json(response.content)
    
    async def batch_generate(
        self,
        prompts: List[str],
        agent_name: Optional[str] = None,
        max_concurrency: int = 5
    ) -> List[LLMResponse]:
        """
        批量生成（并发控制）
        
        输入：
        - prompts: 提示词列表
        - agent_name: Agent名称
        - max_concurrency: 最大并发数
        
        输出：
        - 响应列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def generate_one(prompt):
            async with semaphore:
                return await self.generate(prompt, agent_name)
        
        tasks = [generate_one(p) for p in prompts]
        return await asyncio.gather(*tasks)
```

### 5.2 LLMChatTool - 对话工具

```python
class LLMChatTool:
    """
    LLM对话工具 - 支持多轮对话
    
    功能：
    1. 对话历史管理
    2. 上下文压缩
    3. 角色扮演
    """
    
    def __init__(self, generate_tool: LLMGenerateTool):
        self.generate = generate_tool
        self._sessions: Dict[str, List[Dict]] = {}  # 对话历史
    
    async def chat(
        self,
        session_id: str,
        message: str,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_history: int = 10
    ) -> str:
        """
        对话（自动管理历史）
        
        输入：
        - session_id: 会话ID
        - message: 用户消息
        - agent_name: Agent名称
        - system_prompt: 系统提示
        - max_history: 最大历史轮数
        
        输出：
        - 助手回复
        """
        # 获取或创建会话
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        history = self._sessions[session_id]
        
        # 添加用户消息
        history.append({"role": "user", "content": message})
        
        # 压缩历史（如果太长）
        if len(history) > max_history * 2:
            history = self._compress_history(history, max_history)
        
        # 生成回复
        response = await self.generate.generate(
            prompt=message,
            agent_name=agent_name,
            system_prompt=system_prompt,
            messages=history
        )
        
        # 添加助手回复到历史
        history.append({"role": "assistant", "content": response.content})
        
        return response.content
    
    def _compress_history(self, history: List[Dict], max_rounds: int) -> List[Dict]:
        """压缩对话历史"""
        # 保留最近N轮
        return history[-max_rounds * 2:]
    
    def clear_history(self, session_id: str):
        """清空对话历史"""
        self._sessions.pop(session_id, None)
```

---

## 6. 配置管理

### 6.1 配置文件格式

```yaml
# llm_config.yaml
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    api_base: "https://api.openai.com/v1"
    models:
      gpt-4o:
        tier: creative
        max_tokens: 8192
        cost_per_1k_tokens: 0.005
      gpt-4o-mini:
        tier: simple
        max_tokens: 4096
        cost_per_1k_tokens: 0.00015
      o1-preview:
        tier: reasoning
        max_tokens: 32768
        cost_per_1k_tokens: 0.015
  
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      claude-3-opus-20240229:
        tier: creative
        max_tokens: 4096
      claude-3-sonnet-20240229:
        tier: analytical
        max_tokens: 4096
  
  local:
    api_base: "http://localhost:8000/v1"
    models:
      qwen2.5-14b:
        tier: simple
        max_tokens: 4096
      llama3-70b:
        tier: creative
        max_tokens: 4096

# Agent独立配置
agents:
  world_builder:
    primary:
      provider: openai
      model: gpt-4o
      temperature: 0.7
    fallback:
      provider: anthropic
      model: claude-3-opus-20240229
    task_overrides:
      world_creation:
        temperature: 0.9
      rule_design:
        model: o1-preview
        temperature: 0.3
  
  character_mind:
    primary:
      provider: openai
      model: gpt-4o
      temperature: 0.9
    fallback:
      provider: local
      model: qwen2.5-14b
  
  causal_reasoning:
    primary:
      provider: openai
      model: o1-preview
      temperature: 0.3
    fallback:
      provider: deepseek
      model: deepseek-reasoner
  
  narrative_record:
    primary:
      provider: openai
      model: gpt-4o
      temperature: 0.8
      stream: true

# 全局设置
global:
  default_provider: openai
  default_model: gpt-4o-mini
  timeout: 60
  retry_count: 3
  max_concurrency: 10
```

---

## 7. 实施计划

### 7.1 删除旧LLM层（Day 1）

```bash
# 删除旧文件
rm src/deepnovel/llm/adapters/openai.py
rm src/deepnovel/llm/router.py
rm src/deepnovel/core/llm_router.py

# 保留接口（标记为deprecated）
```

### 7.2 创建新LLM层（Day 1-3）

```python
# 文件结构
llm/
├── __init__.py
├── base.py                    # LLM接口基类
├── factory.py                 # LLM工厂
├── router.py                  # 智能路由
├── analyzer.py               # 任务分析器
├── selector.py               # 模型选择器
├── config.py                 # 配置管理
├── adapters/                  # 适配器
│   ├── __init__.py
│   ├── openai.py             # OpenAI
│   ├── anthropic.py          # Anthropic
│   ├── local.py              # 本地模型
│   ├── qwen.py               # 阿里云
│   ├── kimi.py               # Moonshot
│   ├── deepseek.py           # DeepSeek
│   └── gemini.py             # Google
├── tools/                     # Agent工具
│   ├── __init__.py
│   ├── generate_tool.py      # 生成工具
│   └── chat_tool.py          # 对话工具
└── config.yaml               # 配置文件
```

### 7.3 集成测试（Day 3-4）

```python
# 测试场景
1. 工厂创建测试
   - 创建各种适配器
   - 验证健康检查
   
2. 路由测试
   - 任务分析准确性
   - 模型选择合理性
   
3. Agent配置测试
   - 独立配置生效
   - 降级切换正常
   
4. 流式测试
   - 流式输出正常
   - 中断处理
   
5. 并发测试
   - 并发控制有效
   - 资源不泄露
```

---

## 8. 验收标准

### 8.1 功能验收

| 功能 | 测试场景 | 通过标准 |
|------|---------|---------|
| 工厂创建 | 创建OpenAI适配器 | 成功初始化，健康检查通过 |
| 智能路由 | 分析创意任务 | 选择creative tier模型 |
| Agent配置 | world_builder调用 | 使用gpt-4o，temperature=0.7 |
| 降级切换 | 主模型失败 | 自动切换到fallback |
| 流式输出 | narrative生成 | 实时输出token |
| JSON模式 | 结构化生成 | 输出合法JSON |

### 8.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 初始化时间 | <1s | 创建10个实例 |
| 路由延迟 | <50ms | 100次路由 |
| 生成延迟 | <2s | 平均首次token时间 |
| 并发控制 | <10并发 | 20个请求同时发送 |

### 8.3 兼容性验收

| 提供商 | 基础功能 | 流式 | JSON模式 | 函数调用 |
|--------|---------|------|---------|---------|
| OpenAI | ✅ | ✅ | ✅ | ✅ |
| Anthropic | ✅ | ✅ | ❌ | ✅ |
| 本地模型 | ✅ | ✅ | ❌ | ❌ |
| Qwen | ✅ | ✅ | ✅ | ❌ |
| Kimi | ✅ | ✅ | ✅ | ❌ |
| DeepSeek | ✅ | ✅ | ✅ | ❌ |

---

## 9. 与Step 1/2的关联

### 9.1 数据层支持

```
Step 1 (数据层)          Step 3 (LLM层)
    │                        │
    ├─ facts ──────────────├─ 任务分析输入
    ├─ events ─────────────├─ 上下文构建
    └─ character_minds ────├─ 人格提示注入
```

### 9.2 记忆系统集成

```
Step 2 (记忆系统)        Step 3 (LLM层)
    │                        │
    ├─ 工作记忆 ───────────├─ 对话历史
    ├─ 长期记忆 ───────────├─ RAG上下文
    └─ 情感状态 ───────────├─ 情感提示
```

---

## 10. 实施状态追踪

| 日期 | 完成内容 | 状态 |
|------|---------|------|
| 2026-04-28 | 完成Step3.md设计文档 | ✅ |

---

*版本: v1.0*
*创建日期: 2026-04-28*
*负责人: Ryan + 小R*
*状态: 设计中*
*预计工期: 4天*
*同步状态: 本地文件（不同步GitHub）*
