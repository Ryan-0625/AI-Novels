# Step 6: 向量化检索重构 - RAG架构驱动的语义增强生成

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step1 (数据层), Step2 (记忆系统), Step3 (LLM层), Step4 (Agent层), Step5 (调度层)
> 目标: 构建面向小说生成的RAG架构，实现语义增强检索，提升生成质量与一致性

---

## 1. 核心概念澄清：RAG是什么？

### 1.1 向量语义增强检索 = RAG的核心组件

**是的，向量语义增强检索正是RAG（Retrieval-Augmented Generation，检索增强生成）架构的核心组成部分。**

但完整的RAG架构远不止向量检索本身，它是一个完整的**检索-增强-生成**流水线：

```
传统LLM生成:
用户Query → LLM → 输出
                    ↑
              (仅依赖模型参数知识)

RAG增强生成:
用户Query → Query理解 → 多路检索 → 重排序 → 上下文组装 → Prompt注入 → LLM → 输出
                              ↑                                    ↑
                        (向量+关键词+图谱检索)              (检索结果作为上下文)
```

### 1.2 RAG对小说生成的独特价值

| 问题 | 纯LLM的局限 | RAG的解决方案 |
|------|-----------|-------------|
| **角色一致性** | 长文本中角色性格漂移 | 检索角色历史记忆、性格描述注入Prompt |
| **世界观一致** | 遗忘早期设定的世界规则 | 检索世界知识库，确保新内容符合设定 |
| **风格统一** | 不同章节风格突变 | 检索作者风格范例，保持叙事风格一致 |
| **情节连贯** | 丢失伏笔、前后矛盾 | 检索前文摘要、伏笔记录，确保逻辑连贯 |
| **知识时效** | 模型知识有截止日期 | 检索最新参考资料（历史、文化、科学） |
| **幻觉控制** | 生成不存在的人物/事件 | 检索已确认事实，约束生成范围 |

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **LlamaIndex** (2024) | 多索引策略、Agentic RAG、递归检索 | 复杂文档检索 |
| **LangChain RAG** (2024) | 灵活链式组合、LCEL表达式 | 快速原型搭建 |
| **Microsoft GraphRAG** (2024) | 知识图谱增强、社区发现、全局推理 | 大规模知识库 |
| **Self-RAG** (ACL 2024) | 自适应检索决策、反思令牌 | 检索质量不确定场景 |
| **Corrective RAG** (2024) | 检索质量评估、网络搜索修正 | 检索结果不足时自动扩展 |
| **RAG-Fusion** (2024) | 多查询生成、RRF融合排序 | 查询歧义消解 |
| **Hybrid Search** (2024) | 向量+关键词+过滤组合 | 精确匹配+语义理解 |
| **ColBERT v2** (2024) | 晚期交互、token级相似度 | 细粒度语义匹配 |
| **Vercel AI SDK RAG** (2024) | 流式检索、前端集成 | 实时应用 |
| **RAGFlow** (2024) | 深度文档理解、模板化RAG | 企业级RAG引擎 |

---

## 2. 现状诊断

### 2.1 当前组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| ChromaVectorStore | `vector_store/chroma_store.py` | `import ChromaDB` 拼写错误（应为`chromadb`），会直接导致ImportError | **致命** |
| ChromaDBClient | `database/chromadb_client.py` | 使用MD5哈希假Embedding（语义无意义）；`disconnect()`调用`reset()`删除所有数据 | **致命** |
| EmbeddingClient | `llm/base.py` | 纯抽象类，**零实现** — 所有LLM适配器均未实现 | **致命** |
| HashEmbeddingFunction | `database/chromadb_client.py:112` | MD5哈希生成32维向量，毫无语义表达能力 | **致命** |
| HookGeneratorAgent | `agents/hook_generator.py` | 绕过ChromaDB，在内存dict上做手动cosine similarity | **严重** |
| LangChain | `requirements.txt` | 已安装但**零使用**，未用于任何RAG操作 | **中** |
| Qdrant | Step1提及 | 在Step1架构中声明使用Qdrant，但**代码中完全未实现** | **中** |
| 检索方法 | `database/chromadb_client.py:488` | `search_character_memories`等方法存在，但**从未被Agent调用**来增强生成 | **严重** |

### 2.2 核心问题总结

```
当前状态：有向量存储的"壳"，没有RAG的"魂"

1. 无真正的语义Embedding → 检索结果是随机的
2. 无RAG Pipeline → 检索结果从未进入LLM Prompt
3. 无领域专用检索器 → 无法针对小说场景优化检索
4. 无检索质量评估 → 不知道检索结果是否有用
5. 无混合检索 → 只有向量检索，缺少关键词补充
6. 无重排序 → 检索Top-K直接送入LLM，质量参差
7. Agent无检索工具 → Step4的Agent无法调用检索能力
```

---

## 3. 架构总览

### 3.1 RAG六层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 6: 应用层 (Application)                                        │
│  • NovelRAGService       - 小说生成RAG服务入口                        │
│  • RetrieverTools        - Agent可调用的检索工具（MCP兼容）            │
│  • RAGEvalPipeline       - 检索质量评估与反馈                         │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 5: 领域检索层 (Domain Retrievers)                              │
│  • WorldKnowledgeRetriever   - 世界观/规则/设定检索                   │
│  • CharacterMemoryRetriever  - 角色记忆/性格/关系检索                 │
│  • StyleReferenceRetriever   - 风格范例/修辞/叙事模式检索             │
│  • PlotContinuityRetriever   - 情节连贯/伏笔/前文摘要检索             │
│  • WritingCraftRetriever     - 写作技巧/经典片段/文化参考检索         │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: RAG引擎层 (RAG Engine)                                      │
│  • QueryTransformer      - 查询改写/扩展/多查询生成                   │
│  • HybridRetriever       - 混合检索（向量+关键词+过滤）               │
│  • Reranker              - 重排序（Cross-Encoder/ColBERT）            │
│  • ContextAssembler      - 上下文组装/去重/截断                       │
│  • PromptAugmenter       - Prompt注入与模板管理                       │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 检索策略层 (Retrieval Strategy)                             │
│  • VectorSearch          - 向量相似度检索                            │
│  • BM25Search            - 稀疏向量关键词检索                         │
│  • GraphSearch           - 知识图谱关系检索（Neo4j）                  │
│  • MetadataFilter        - 元数据过滤（角色ID/章节/时间范围）          │
│  • MultiIndexFusion      - 多索引结果融合（RRF）                      │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: Embedding层 (Embedding Engine)                              │
│  • LocalEmbedding        - 本地模型（SentenceTransformers）           │
│  • APIEmbedding          - 云端API（OpenAI/Qwen/MiniMax）             │
│  • EmbeddingRouter       - 路由选择（按质量/速度/成本）               │
│  • EmbeddingCache        - 向量缓存（避免重复计算）                    │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 向量存储层 (Vector Store)                                    │
│  • ChromaDBStore         - 默认向量存储（本地/远程）                  │
│  • QdrantStore           - 可选高性能向量存储                         │
│  • IndexManager          - 索引管理（创建/更新/删除/优化）             │
│  • CollectionSchema      - 集合Schema定义与迁移                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 RAG数据流

```
┌─────────────┐     ┌──────────────────────────────────────────────────────────┐
│  Agent请求  │────→│  RAG Pipeline（每次LLM调用前自动执行）                      │
│  生成场景   │     │                                                          │
└─────────────┘     │  ┌─────────────┐                                        │
                    │  │Query理解    │  识别查询意图、提取实体、补全上下文      │
                    │  │& 改写       │                                        │
                    │  └──────┬──────┘                                        │
                    │         │                                               │
                    │         ▼                                               │
                    │  ┌─────────────┐     ┌─────────────┐     ┌──────────┐  │
                    │  │ 向量检索     │     │ BM25检索    │     │图谱检索  │  │
                    │  │(语义相似)   │     │(关键词匹配) │     │(关系推理)│  │
                    │  └──────┬──────┘     └──────┬──────┘     └────┬─────┘  │
                    │         │                   │                 │        │
                    │         └───────────────────┼─────────────────┘        │
                    │                             ▼                          │
                    │                    ┌─────────────┐                     │
                    │                    │ MultiIndex  │  RRF融合排序         │
                    │                    │ Fusion      │                     │
                    │                    └──────┬──────┘                     │
                    │                           ▼                            │
                    │                    ┌─────────────┐                     │
                    │                    │ Reranker    │  Cross-Encoder精排  │
                    │                    │(Top-K重排)  │                     │
                    │                    └──────┬──────┘                     │
                    │                           ▼                            │
                    │                    ┌─────────────┐                     │
                    │                    │Context      │  去重/截断/格式化   │
                    │                    │Assembler    │                     │
                    │                    └──────┬──────┘                     │
                    │                           │                            │
                    │                           ▼                            │
                    │                    ┌─────────────┐                     │
                    │                    │Prompt       │  注入检索上下文     │
                    │                    │Augmenter    │  构建增强Prompt    │
                    │                    └──────┬──────┘                     │
                    │                           │                            │
                    └───────────────────────────┼────────────────────────────┘
                                                ▼
                                         ┌─────────────┐
                                         │    LLM      │
                                         │  生成文本   │
                                         └─────────────┘
```

---

## 4. 核心组件设计

### 4.1 Embedding引擎层

**职责**: 提供统一的文本向量化能力，支持本地模型和云端API，带缓存和路由

```python
# src/deepnovel/rag/embeddings/engine.py

from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
import asyncio

from src.deepnovel.utils import get_logger

logger = get_logger()


class EmbeddingQuality(Enum):
    """Embedding质量等级"""
    HIGH = "high"       # 云端大模型（1536/3072维）
    MEDIUM = "medium"   # 本地高质量模型（768/1024维）
    FAST = "fast"       # 本地轻量模型（384/512维）


class EmbeddingProvider(Enum):
    """Embedding提供商"""
    OPENAI = "openai"           # text-embedding-3-large/small
    QWEN = "qwen"               # 阿里云百炼Embedding
    MINIMAX = "minimax"         # MiniMax Embedding
    OLLAMA = "ollama"           # 本地Ollama Embedding
    LOCAL = "local"             # SentenceTransformers本地模型


@dataclass
class EmbeddingConfig:
    """Embedding配置"""
    provider: EmbeddingProvider
    model: str
    dimensions: int
    quality: EmbeddingQuality
    batch_size: int = 32
    timeout: float = 30.0


class BaseEmbeddingEngine(ABC):
    """Embedding引擎基类"""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """单文本向量化"""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量向量化"""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """向量维度"""
        pass


class LocalEmbeddingEngine(BaseEmbeddingEngine):
    """
    本地Embedding引擎

    使用SentenceTransformers，无需网络，适合隐私敏感场景
    """

    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5", device: str = "cpu"):
        self.model_name = model_name
        self._model = None
        self._device = device
        self._dimensions = None

    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self._device)
            self._dimensions = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self.model_name} ({self._dimensions}d)")

    async def embed(self, text: str) -> List[float]:
        self._load_model()
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self._model.encode, text)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, texts)
        return embeddings.tolist()

    @property
    def dimensions(self) -> int:
        self._load_model()
        return self._dimensions


class OpenAIEmbeddingEngine(BaseEmbeddingEngine):
    """
    OpenAI Embedding引擎

    高质量云端Embedding，适合生产环境
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-large"):
        self.api_key = api_key
        self.model = model
        self._dimensions = 3072 if "large" in model else 1536
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def embed(self, text: str) -> List[float]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [d.embedding for d in response.data]

    @property
    def dimensions(self) -> int:
        return self._dimensions


class EmbeddingRouter:
    """
    Embedding路由引擎

    根据任务需求自动选择最优Embedding方案：
    - 质量优先 → OpenAI/Qwen云端大模型
    - 速度优先 → 本地轻量模型
    - 成本优先 → 本地模型
    - 隐私优先 → 本地模型
    """

    def __init__(self):
        self._engines: Dict[str, BaseEmbeddingEngine] = {}
        self._default_engine: Optional[str] = None
        self._cache: Dict[str, tuple] = {}  # text -> (embedding, timestamp)
        self._cache_ttl = 3600  # 缓存1小时
        self._cache_hits = 0
        self._cache_misses = 0

    def register_engine(self, name: str, engine: BaseEmbeddingEngine, default: bool = False):
        """注册Embedding引擎"""
        self._engines[name] = engine
        if default or self._default_engine is None:
            self._default_engine = name
        logger.info(f"Registered embedding engine: {name} ({engine.dimensions}d)")

    async def embed(self, text: str, engine_name: str = None, use_cache: bool = True) -> List[float]:
        """
        向量化文本

        Args:
            text: 输入文本
            engine_name: 指定引擎，None则使用默认
            use_cache: 是否使用缓存
        """
        # 缓存检查
        if use_cache and text in self._cache:
            embedding, timestamp = self._cache[text]
            if time.time() - timestamp < self._cache_ttl:
                self._cache_hits += 1
                return embedding

        # 选择引擎
        name = engine_name or self._default_engine
        engine = self._engines.get(name)
        if not engine:
            raise ValueError(f"Embedding engine not found: {name}")

        # 执行向量化
        embedding = await engine.embed(text)
        self._cache_misses += 1

        # 写入缓存
        if use_cache:
            self._cache[text] = (embedding, time.time())

        return embedding

    async def embed_batch(self, texts: List[str], engine_name: str = None) -> List[List[float]]:
        """批量向量化"""
        name = engine_name or self._default_engine
        engine = self._engines.get(name)
        if not engine:
            raise ValueError(f"Embedding engine not found: {name}")
        return await engine.embed_batch(texts)

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._cache_hits + self._cache_misses
        return {
            "cache_size": len(self._cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._cache_hits / total if total > 0 else 0
        }

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
```

### 4.2 向量存储层

**职责**: 提供统一的向量存储抽象，支持ChromaDB和Qdrant

```python
# src/deepnovel/rag/vector_store/base.py

from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class VectorStoreType(Enum):
    CHROMADB = "chromadb"
    QDRANT = "qdrant"


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class CollectionConfig:
    """集合配置"""
    name: str
    dimensions: int
    distance_metric: str = "cosine"  # cosine, euclidean, dot
    metadata_schema: Optional[Dict] = None


class BaseVectorStore(ABC):
    """向量存储基类"""

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        pass

    @abstractmethod
    async def create_collection(self, config: CollectionConfig) -> bool:
        """创建集合"""
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        pass

    @abstractmethod
    async def add(
        self,
        collection: str,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None
    ) -> bool:
        """添加向量"""
        pass

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """向量检索"""
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        collection: str,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """混合检索（向量+关键词）"""
        pass

    @abstractmethod
    async def delete(self, collection: str, ids: List[str]) -> bool:
        pass

    @abstractmethod
    async def get_stats(self, collection: str) -> Dict[str, Any]:
        pass


# src/deepnovel/rag/vector_store/chroma_store.py
import chromadb
from chromadb.config import Settings


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB向量存储实现

    修复原版的致命bug：
    1. import ChromaDB -> import chromadb
    2. disconnect() 不再调用 reset()
    3. 真正的Embedding注入，不再使用MD5假向量
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        persist_path: str = "./data/chromadb",
        embedding_engine: Optional['BaseEmbeddingEngine'] = None
    ):
        self.host = host
        self.port = port
        self.persist_path = persist_path
        self._embedding_engine = embedding_engine
        self._client = None
        self._collections: Dict[str, Any] = {}

    async def connect(self) -> bool:
        try:
            if self.host and self.port:
                # 远程模式
                settings = Settings(
                    chroma_server_host=self.host,
                    chroma_server_http_port=self.port
                )
                self._client = chromadb.Client(settings)
            else:
                # 本地持久化模式
                settings = Settings(
                    is_persistent=True,
                    persist_directory=self.persist_path
                )
                self._client = chromadb.Client(settings)

            logger.info(f"Connected to ChromaDB (host={self.host}, port={self.port})")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            return False

    async def disconnect(self) -> bool:
        """安全断开连接（不删除数据）"""
        try:
            if self._client:
                # 只持久化，不reset！
                # self._client.persist()  # ChromaDB 0.4+ 自动持久化
                self._client = None
                self._collections.clear()
            return True
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False

    async def create_collection(self, config: CollectionConfig) -> bool:
        try:
            collection = self._client.create_collection(
                name=config.name,
                metadata={
                    "hnsw:space": config.distance_metric,
                    "dimensions": config.dimensions
                }
            )
            self._collections[config.name] = collection
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    async def add(
        self,
        collection: str,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None
    ) -> bool:
        coll = self._get_collection(collection)
        coll.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts]
        )
        return True

    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        coll = self._get_collection(collection)

        where_clause = self._build_where_clause(filters) if filters else None

        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )

        return self._format_results(results)

    async def hybrid_search(
        self,
        collection: str,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        混合检索：向量检索 + 关键词BM25

        使用RRF (Reciprocal Rank Fusion) 融合排序
        """
        # 向量检索
        vector_results = await self.search(
            collection, query_embedding, top_k=top_k * 2, filters=filters
        )

        # 关键词检索（简化实现，可用BM25优化）
        keyword_results = await self._keyword_search(
            collection, query_text, top_k=top_k * 2, filters=filters
        )

        # RRF融合
        return self._reciprocal_rank_fusion(
            vector_results, keyword_results,
            weight_vector=vector_weight,
            weight_keyword=1 - vector_weight,
            k=60, top_k=top_k
        )

    async def _keyword_search(
        self,
        collection: str,
        query_text: str,
        top_k: int,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """关键词检索（基于ChromaDB的$contains操作）"""
        coll = self._get_collection(collection)

        # 分词
        keywords = query_text.split()

        results = []
        seen_ids = set()

        for keyword in keywords:
            if len(keyword) < 2:
                continue

            where_clause = {"$contains": keyword}
            if filters:
                where_clause = {"$and": [where_clause, self._build_where_clause(filters)]}

            try:
                batch = coll.query(
                    query_texts=[keyword],
                    n_results=min(top_k, 10),
                    where=where_clause
                )

                for i, doc_id in enumerate(batch["ids"][0]):
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        results.append(SearchResult(
                            id=doc_id,
                            text=batch["documents"][0][i],
                            score=batch["distances"][0][i] if batch.get("distances") else 0.5,
                            metadata=batch["metadatas"][0][i] if batch.get("metadatas") else {}
                        ))
            except Exception:
                continue

        return results[:top_k]

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        weight_vector: float,
        weight_keyword: float,
        k: int = 60,
        top_k: int = 5
    ) -> List[SearchResult]:
        """RRF融合排序"""
        scores = {}

        # 向量结果打分
        for rank, result in enumerate(vector_results):
            if result.id not in scores:
                scores[result.id] = {"score": 0, "result": result}
            scores[result.id]["score"] += weight_vector * (1.0 / (k + rank + 1))

        # 关键词结果打分
        for rank, result in enumerate(keyword_results):
            if result.id not in scores:
                scores[result.id] = {"score": 0, "result": result}
            scores[result.id]["score"] += weight_keyword * (1.0 / (k + rank + 1))

        # 排序
        fused = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["result"] for item in fused[:top_k]]

    def _get_collection(self, name: str):
        """获取集合（带缓存）"""
        if name not in self._collections:
            self._collections[name] = self._client.get_collection(name)
        return self._collections[name]

    def _build_where_clause(self, filters: Dict) -> Dict:
        """构建ChromaDB where条件"""
        # 简化实现，支持基本等于条件
        conditions = []
        for key, value in filters.items():
            conditions.append({key: value})

        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _format_results(self, raw_results: Dict) -> List[SearchResult]:
        """格式化结果"""
        results = []
        if not raw_results.get("ids"):
            return results

        for i, doc_ids in enumerate(raw_results["ids"]):
            for j, doc_id in enumerate(doc_ids):
                results.append(SearchResult(
                    id=doc_id,
                    text=raw_results["documents"][i][j] if raw_results.get("documents") else "",
                    score=raw_results["distances"][i][j] if raw_results.get("distances") else 0.0,
                    metadata=raw_results["metadatas"][i][j] if raw_results.get("metadatas") else {}
                ))
        return results

    async def delete(self, collection: str, ids: List[str]) -> bool:
        coll = self._get_collection(collection)
        coll.delete(ids=ids)
        return True

    async def get_stats(self, collection: str) -> Dict[str, Any]:
        coll = self._get_collection(collection)
        return {
            "name": collection,
            "count": coll.count()
        }


# src/deepnovel/rag/vector_store/qdrant_store.py
class QdrantVectorStore(BaseVectorStore):
    """
    Qdrant向量存储实现

    高性能替代方案，支持：
    - HNSW索引优化
    - 量化压缩（Scalar/Product/Binary）
    - 分布式部署
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        grpc_port: int = 6334
    ):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.grpc_port = grpc_port
        self._client = None

    async def connect(self) -> bool:
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                prefer_grpc=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return False

    async def disconnect(self) -> bool:
        # Qdrant client is stateless, no explicit disconnect needed
        self._client = None
        return True

    async def create_collection(self, config: CollectionConfig) -> bool:
        from qdrant_client.models import Distance, VectorParams

        distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT
        }

        self._client.create_collection(
            collection_name=config.name,
            vectors_config=VectorParams(
                size=config.dimensions,
                distance=distance_map.get(config.distance_metric, Distance.COSINE)
            )
        )
        return True

    async def add(
        self,
        collection: str,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None
    ) -> bool:
        from qdrant_client.models import PointStruct

        points = []
        for i, (doc_id, embedding, text) in enumerate(zip(ids, embeddings, texts)):
            payload = {"text": text}
            if metadatas and i < len(metadatas):
                payload.update(metadatas[i])

            points.append(PointStruct(
                id=doc_id,
                vector=embedding,
                payload=payload
            ))

        self._client.upsert(collection_name=collection, points=points)
        return True

    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            query_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=collection,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter
        )

        return [
            SearchResult(
                id=str(r.id),
                text=r.payload.get("text", ""),
                score=r.score,
                metadata={k: v for k, v in r.payload.items() if k != "text"}
            )
            for r in results
        ]

    # ... 其他方法类似实现
```

### 4.3 领域检索层（小说专用）

**职责**: 针对小说生成场景，提供五个专用检索器

```python
# src/deepnovel/rag/retrievers/world_knowledge.py

class WorldKnowledgeRetriever:
    """
    世界观知识检索器

    检索内容：世界规则、地理设定、历史事件、文化习俗、魔法/科技体系
    使用场景：WorldStateAgent确保生成内容符合世界设定
    """

    COLLECTION = "world_knowledge"

    def __init__(self, vector_store: BaseVectorStore, embedding_router: EmbeddingRouter):
        self._store = vector_store
        self._embedder = embedding_router

    async def add_knowledge(
        self,
        world_id: str,
        knowledge_type: str,  # "rule", "geography", "history", "culture", "system"
        text: str,
        importance: float = 1.0,
        tags: List[str] = None
    ) -> str:
        """添加世界观知识"""
        doc_id = f"{world_id}_{knowledge_type}_{uuid.uuid4().hex[:8]}"
        embedding = await self._embedder.embed(text)

        await self._store.add(
            collection=self.COLLECTION,
            ids=[doc_id],
            texts=[text],
            embeddings=[embedding],
            metadatas=[{
                "world_id": world_id,
                "knowledge_type": knowledge_type,
                "importance": importance,
                "tags": tags or [],
                "created_at": time.time()
            }]
        )
        return doc_id

    async def search(
        self,
        world_id: str,
        query: str,
        knowledge_types: List[str] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """检索世界观知识"""
        embedding = await self._embedder.embed(query)

        filters = {"world_id": world_id}
        if knowledge_types:
            # ChromaDB不支持in操作，需要多次查询或客户端过滤
            pass

        return await self._store.search(
            collection=self.COLLECTION,
            query_embedding=embedding,
            top_k=top_k,
            filters=filters
        )


# src/deepnovel/rag/retrievers/character_memory.py
class CharacterMemoryRetriever:
    """
    角色记忆检索器

    检索内容：角色过往经历、性格特征、人际关系、情感状态、决策模式
    使用场景：CharacterMindAgent保持角色行为一致性
    """

    COLLECTION = "character_memories"

    def __init__(self, vector_store: BaseVectorStore, embedding_router: EmbeddingRouter):
        self._store = vector_store
        self._embedder = embedding_router

    async def add_memory(
        self,
        char_id: str,
        memory_text: str,
        memory_type: str = "event",  # "event", "trait", "relationship", "emotion"
        importance: float = 1.0,
        chapter: Optional[int] = None,
        scene: Optional[str] = None
    ) -> str:
        """添加角色记忆"""
        doc_id = f"{char_id}_mem_{uuid.uuid4().hex[:8]}"
        embedding = await self._embedder.embed(memory_text)

        await self._store.add(
            collection=self.COLLECTION,
            ids=[doc_id],
            texts=[memory_text],
            embeddings=[embedding],
            metadatas=[{
                "char_id": char_id,
                "memory_type": memory_type,
                "importance": importance,
                "chapter": chapter,
                "scene": scene,
                "created_at": time.time()
            }]
        )
        return doc_id

    async def search_memories(
        self,
        char_id: str,
        query: str,
        memory_types: List[str] = None,
        min_importance: float = 0.0,
        top_k: int = 5
    ) -> List[SearchResult]:
        """检索角色记忆"""
        embedding = await self._embedder.embed(query)

        results = await self._store.search(
            collection=self.COLLECTION,
            query_embedding=embedding,
            top_k=top_k * 2,  # 多取一些用于客户端过滤
            filters={"char_id": char_id}
        )

        # 客户端过滤
        filtered = []
        for r in results:
            meta = r.metadata
            if memory_types and meta.get("memory_type") not in memory_types:
                continue
            if meta.get("importance", 1.0) < min_importance:
                continue
            filtered.append(r)

        return filtered[:top_k]


# src/deepnovel/rag/retrievers/style_reference.py
class StyleReferenceRetriever:
    """
    风格范例检索器

    检索内容：经典文学片段、作者风格样本、修辞手法、叙事节奏范例
    使用场景：StyleEnforcerAgent保持叙事风格一致性
    """

    COLLECTION = "style_references"

    def __init__(self, vector_store: BaseVectorStore, embedding_router: EmbeddingRouter):
        self._store = vector_store
        self._embedder = embedding_router

    async def add_reference(
        self,
        text: str,
        style_type: str,  # "dialogue", "description", "action", "monologue", "transition"
        genre: str,
        tone: str,  # "dark", "light", "dramatic", "humorous"
        author: Optional[str] = None,
        source: Optional[str] = None
    ) -> str:
        """添加风格范例"""
        doc_id = f"style_{style_type}_{uuid.uuid4().hex[:8]}"
        embedding = await self._embedder.embed(text)

        await self._store.add(
            collection=self.COLLECTION,
            ids=[doc_id],
            texts=[text],
            embeddings=[embedding],
            metadatas=[{
                "style_type": style_type,
                "genre": genre,
                "tone": tone,
                "author": author,
                "source": source,
                "created_at": time.time()
            }]
        )
        return doc_id

    async def search_similar_style(
        self,
        query_text: str,
        style_type: str = None,
        genre: str = None,
        tone: str = None,
        top_k: int = 3
    ) -> List[SearchResult]:
        """检索相似风格范例"""
        embedding = await self._embedder.embed(query_text)

        filters = {}
        if style_type:
            filters["style_type"] = style_type
        if genre:
            filters["genre"] = genre
        if tone:
            filters["tone"] = tone

        return await self._store.search(
            collection=self.COLLECTION,
            query_embedding=embedding,
            top_k=top_k,
            filters=filters if filters else None
        )


# src/deepnovel/rag/retrievers/plot_continuity.py
class PlotContinuityRetriever:
    """
    情节连贯检索器

    检索内容：前文摘要、伏笔记录、未解决冲突、角色目标、时间线事件
    使用场景：SceneWriterAgent确保情节前后连贯
    """

    COLLECTION = "plot_continuity"

    def __init__(self, vector_store: BaseVectorStore, embedding_router: EmbeddingRouter):
        self._store = vector_store
        self._embedder = embedding_router

    async def add_plot_element(
        self,
        novel_id: str,
        element_type: str,  # "summary", "foreshadow", "conflict", "goal", "timeline"
        text: str,
        chapter: int,
        status: str = "active",  # "active", "resolved", "abandoned"
    ) -> str:
        """添加情节元素"""
        doc_id = f"{novel_id}_{element_type}_ch{chapter}_{uuid.uuid4().hex[:8]}"
        embedding = await self._embedder.embed(text)

        await self._store.add(
            collection=self.COLLECTION,
            ids=[doc_id],
            texts=[text],
            embeddings=[embedding],
            metadatas=[{
                "novel_id": novel_id,
                "element_type": element_type,
                "chapter": chapter,
                "status": status,
                "created_at": time.time()
            }]
        )
        return doc_id

    async def search_relevant_context(
        self,
        novel_id: str,
        query: str,
        current_chapter: int,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        检索相关情节上下文

        策略：优先检索当前章节附近的内容 + 未解决的伏笔/冲突
        """
        embedding = await self._embedder.embed(query)

        # 检索所有相关结果（不过滤章节，在客户端排序）
        results = await self._store.search(
            collection=self.COLLECTION,
            query_embedding=embedding,
            top_k=top_k * 3,
            filters={"novel_id": novel_id}
        )

        # 排序：未解决的 > 近期章节 > 其他
        def sort_key(r: SearchResult):
            meta = r.metadata
            status_score = 100 if meta.get("status") == "active" else 0
            chapter_dist = abs(meta.get("chapter", 0) - current_chapter)
            return (-status_score, chapter_dist)

        results.sort(key=sort_key)
        return results[:top_k]


# src/deepnovel/rag/retrievers/writing_craft.py
class WritingCraftRetriever:
    """
    写作技巧检索器

    检索内容：修辞手法、叙事技巧、文化背景、历史事件、科学知识
    使用场景：为写作提供参考和灵感
    """

    COLLECTION = "writing_craft"

    def __init__(self, vector_store: BaseVectorStore, embedding_router: EmbeddingRouter):
        self._store = vector_store
        self._embedder = embedding_router

    async def add_craft_reference(
        self,
        text: str,
        craft_type: str,  # "rhetoric", "technique", "culture", "history", "science"
        category: str,
        description: str = ""
    ) -> str:
        """添加写作技巧参考"""
        doc_id = f"craft_{craft_type}_{uuid.uuid4().hex[:8]}"
        embedding = await self._embedder.embed(text + " " + description)

        await self._store.add(
            collection=self.COLLECTION,
            ids=[doc_id],
            texts=[text],
            embeddings=[embedding],
            metadatas=[{
                "craft_type": craft_type,
                "category": category,
                "description": description,
                "created_at": time.time()
            }]
        )
        return doc_id

    async def search_craft(
        self,
        query: str,
        craft_types: List[str] = None,
        top_k: int = 3
    ) -> List[SearchResult]:
        """检索写作技巧"""
        embedding = await self._embedder.embed(query)

        # 如果指定了craft_types，分别查询后合并
        if craft_types:
            all_results = []
            for craft_type in craft_types:
                results = await self._store.search(
                    collection=self.COLLECTION,
                    query_embedding=embedding,
                    top_k=top_k,
                    filters={"craft_type": craft_type}
                )
                all_results.extend(results)
            # 去重并排序
            seen = set()
            unique = []
            for r in sorted(all_results, key=lambda x: x.score, reverse=True):
                if r.id not in seen:
                    seen.add(r.id)
                    unique.append(r)
            return unique[:top_k]

        return await self._store.search(
            collection=self.COLLECTION,
            query_embedding=embedding,
            top_k=top_k
        )
```

### 4.4 RAG引擎层

**职责**: 编排完整的RAG流水线

```python
# src/deepnovel/rag/engine.py

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class RAGStrategy(Enum):
    """RAG策略"""
    STANDARD = "standard"           # 标准RAG：检索 -> 增强 -> 生成
    SELF_RAG = "self_rag"          # 自适应检索：先判断是否需要检索
    CORRECTIVE = "corrective"      # 修正RAG：评估检索质量，不足时扩展
    FUSION = "fusion"              # 融合RAG：多查询生成 + 融合排序
    MULTI_HOP = "multi_hop"        # 多跳RAG：链式检索，逐步深入


@dataclass
class RAGContext:
    """RAG上下文"""
    query: str
    retrieved_chunks: List[SearchResult] = field(default_factory=list)
    augmented_prompt: str = ""
    retrieval_time_ms: float = 0.0
    total_time_ms: float = 0.0
    strategy_used: RAGStrategy = RAGStrategy.STANDARD
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGEngine:
    """
    RAG引擎

    编排完整的检索增强生成流水线：
    Query -> 理解/改写 -> 多路检索 -> 重排序 -> 上下文组装 -> Prompt注入

    参考：LlamaIndex + LangChain RAG最佳实践
    """

    def __init__(
        self,
        embedding_router: EmbeddingRouter,
        vector_store: BaseVectorStore,
        retrievers: Dict[str, Any] = None,
        reranker: Optional['Reranker'] = None,
        strategy: RAGStrategy = RAGStrategy.STANDARD
    ):
        self._embedder = embedding_router
        self._store = vector_store
        self._retrievers = retrievers or {}
        self._reranker = reranker
        self._strategy = strategy
        self._logger = get_logger()

    async def retrieve(
        self,
        query: str,
        retriever_names: List[str] = None,
        top_k: int = 5,
        use_hybrid: bool = True,
        filters: Dict[str, Any] = None
    ) -> RAGContext:
        """
        执行检索

        Args:
            query: 查询文本
            retriever_names: 指定检索器，None则使用所有
            top_k: 返回数量
            use_hybrid: 是否使用混合检索
            filters: 元数据过滤
        """
        start_time = time.time()

        # 1. Query理解/改写
        transformed_query = await self._transform_query(query)

        # 2. 多路检索
        all_results = []
        names = retriever_names or list(self._retrievers.keys())

        for name in names:
            retriever = self._retrievers.get(name)
            if not retriever:
                continue

            try:
                if hasattr(retriever, 'search'):
                    results = await retriever.search(query=transformed_query, top_k=top_k * 2)
                elif hasattr(retriever, 'search_relevant_context'):
                    # PlotContinuityRetriever等自定义方法
                    results = await retriever.search_relevant_context(
                        novel_id=filters.get("novel_id", ""),
                        query=transformed_query,
                        current_chapter=filters.get("chapter", 0),
                        top_k=top_k * 2
                    )
                else:
                    continue

                # 标记来源
                for r in results:
                    r.metadata["retriever_source"] = name
                all_results.extend(results)

            except Exception as e:
                self._logger.error(f"Retriever {name} failed: {e}")

        # 3. 去重
        seen_texts = set()
        unique_results = []
        for r in all_results:
            text_hash = hashlib.md5(r.text.encode()).hexdigest()[:16]
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_results.append(r)

        # 4. 重排序
        if self._reranker and len(unique_results) > top_k:
            ranked_results = await self._reranker.rerank(
                query=transformed_query,
                results=unique_results,
                top_k=top_k
            )
        else:
            ranked_results = sorted(unique_results, key=lambda x: x.score, reverse=True)[:top_k]

        retrieval_time = (time.time() - start_time) * 1000

        return RAGContext(
            query=query,
            retrieved_chunks=ranked_results,
            retrieval_time_ms=retrieval_time,
            strategy_used=self._strategy
        )

    async def augment(
        self,
        context: RAGContext,
        prompt_template: str = None,
        max_context_length: int = 4000
    ) -> RAGContext:
        """
        组装增强Prompt

        Args:
            context: 检索上下文
            prompt_template: 自定义Prompt模板
            max_context_length: 最大上下文长度
        """
        start_time = time.time()

        # 默认模板
        template = prompt_template or """基于以下检索到的背景信息，回答问题：

{background}

问题：{query}

请确保你的回答与背景信息一致。如果背景信息不足以回答问题，请明确说明。"""

        # 组装背景信息
        background_parts = []
        current_length = 0

        for i, chunk in enumerate(context.retrieved_chunks):
            part = f"[{i+1}] {chunk.text}"
            if current_length + len(part) > max_context_length:
                break
            background_parts.append(part)
            current_length += len(part)

        background = "\n\n".join(background_parts)

        # 填充模板
        augmented = template.format(
            background=background,
            query=context.query
        )

        context.augmented_prompt = augmented
        context.total_time_ms = (time.time() - start_time) * 1000 + context.retrieval_time_ms

        return context

    async def _transform_query(self, query: str) -> str:
        """查询改写（可扩展为LLM驱动的查询扩展）"""
        # 基础实现：去除多余空格，统一标点
        return query.strip()

    async def self_rag_retrieve(
        self,
        query: str,
        llm_client: Any,
        retriever_names: List[str] = None,
        top_k: int = 5
    ) -> RAGContext:
        """
        Self-RAG：自适应检索

        先用LLM判断是否需要检索，如果需要才执行检索
        """
        # 判断是否需要检索
        decision_prompt = f"""判断以下问题是否需要额外的背景知识才能准确回答：

问题：{query}

如果需要检索背景知识，回答"需要"。如果可以直接回答，回答"不需要"。只回答这两个字。"""

        try:
            decision = await llm_client.generate(decision_prompt)
            needs_retrieval = "需要" in decision
        except Exception:
            needs_retrieval = True  # 默认需要检索

        if not needs_retrieval:
            return RAGContext(
                query=query,
                retrieved_chunks=[],
                augmented_prompt=query,
                strategy_used=RAGStrategy.SELF_RAG
            )

        return await self.retrieve(query, retriever_names, top_k)


class Reranker:
    """
    重排序器

    使用Cross-Encoder模型对初步检索结果进行精排
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        if self._model is None:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._model.eval()

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """重排序"""
        self._load_model()

        import torch

        pairs = [[query, r.text] for r in results]

        with torch.no_grad():
            inputs = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            )
            scores = self._model(**inputs).logits.squeeze(-1)

        # 更新分数
        for i, result in enumerate(results):
            result.score = float(scores[i])

        # 排序
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
```

### 4.5 Agent检索工具（内部封装层）

**职责**: 为Step8工具层提供RAG能力封装

> **边界说明（冲突C解决方案）**: 本节的 `RAGToolRegistry` 是**内部工具封装层**，
> 直接暴露给Agent的入口在 **Step8 工具层**。Step8的 `@tool` 装饰器工具内部调用本节的服务，
> 不做重复实现。Agent禁止直接调用本层的 `RAGToolRegistry`，必须通过 Step8 的 `ToolRegistry`。

**暴露给Step8的接口**:
```python
# Step8的工具内部调用方式
from src.deepnovel.rag.service import NovelRAGService

async def retrieve_world_knowledge(query: str, world_id: str) -> List[Document]:
    service = NovelRAGService()
    return await service.retrieve_world(query, world_id)
```

```python
# src/deepnovel/rag/tools.py

"""
RAG检索工具集

这些工具以MCP（Model Context Protocol）兼容格式暴露给Agent使用。
每个Agent可以在其配置中声明需要的检索工具。
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class RetrievalTool:
    """检索工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: callable


class RAGToolRegistry:
    """RAG工具注册中心"""

    def __init__(self, rag_engine: RAGEngine):
        self._engine = rag_engine
        self._tools: Dict[str, RetrievalTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认检索工具"""

        # 工具1：检索世界观知识
        self._tools["retrieve_world_knowledge"] = RetrievalTool(
            name="retrieve_world_knowledge",
            description="检索世界观设定、规则、历史等背景知识，确保生成内容符合世界设定",
            parameters={
                "query": {"type": "string", "description": "检索查询"},
                "world_id": {"type": "string", "description": "世界观ID"},
                "top_k": {"type": "integer", "default": 5}
            },
            handler=self._handle_world_knowledge
        )

        # 工具2：检索角色记忆
        self._tools["retrieve_character_memory"] = RetrievalTool(
            name="retrieve_character_memory",
            description="检索角色的过往经历、性格特征、人际关系等记忆，保持角色行为一致性",
            parameters={
                "query": {"type": "string", "description": "检索查询"},
                "char_id": {"type": "string", "description": "角色ID"},
                "memory_types": {"type": "array", "description": "记忆类型过滤"},
                "top_k": {"type": "integer", "default": 5}
            },
            handler=self._handle_character_memory
        )

        # 工具3：检索风格范例
        self._tools["retrieve_style_reference"] = RetrievalTool(
            name="retrieve_style_reference",
            description="检索相似风格范例，保持叙事风格一致性",
            parameters={
                "query_text": {"type": "string", "description": "要匹配风格的文本"},
                "style_type": {"type": "string", "description": "风格类型"},
                "genre": {"type": "string", "description": "小说类型"},
                "top_k": {"type": "integer", "default": 3}
            },
            handler=self._handle_style_reference
        )

        # 工具4：检索情节连贯性
        self._tools["retrieve_plot_continuity"] = RetrievalTool(
            name="retrieve_plot_continuity",
            description="检索前文情节、伏笔、未解决冲突，确保情节连贯",
            parameters={
                "query": {"type": "string", "description": "检索查询"},
                "novel_id": {"type": "string", "description": "小说ID"},
                "current_chapter": {"type": "integer", "description": "当前章节号"},
                "top_k": {"type": "integer", "default": 5}
            },
            handler=self._handle_plot_continuity
        )

        # 工具5：检索写作技巧
        self._tools["retrieve_writing_craft"] = RetrievalTool(
            name="retrieve_writing_craft",
            description="检索写作技巧、修辞手法、文化背景等参考",
            parameters={
                "query": {"type": "string", "description": "检索查询"},
                "craft_types": {"type": "array", "description": "技巧类型"},
                "top_k": {"type": "integer", "default": 3}
            },
            handler=self._handle_writing_craft
        )

        # 工具6：增强生成（完整RAG Pipeline）
        self._tools["augment_generation"] = RetrievalTool(
            name="augment_generation",
            description="执行完整RAG流程：检索相关知识并生成增强Prompt",
            parameters={
                "query": {"type": "string", "description": "生成任务描述"},
                "retrievers": {"type": "array", "description": "使用的检索器列表"},
                "top_k": {"type": "integer", "default": 5}
            },
            handler=self._handle_augment_generation
        )

    async def _handle_world_knowledge(self, **params) -> Dict:
        retriever = self._engine._retrievers.get("world_knowledge")
        if not retriever:
            return {"error": "World knowledge retriever not available"}
        results = await retriever.search(
            world_id=params["world_id"],
            query=params["query"],
            top_k=params.get("top_k", 5)
        )
        return {
            "tool": "retrieve_world_knowledge",
            "results": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
        }

    async def _handle_character_memory(self, **params) -> Dict:
        retriever = self._engine._retrievers.get("character_memory")
        if not retriever:
            return {"error": "Character memory retriever not available"}
        results = await retriever.search_memories(
            char_id=params["char_id"],
            query=params["query"],
            memory_types=params.get("memory_types"),
            top_k=params.get("top_k", 5)
        )
        return {
            "tool": "retrieve_character_memory",
            "results": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
        }

    async def _handle_style_reference(self, **params) -> Dict:
        retriever = self._engine._retrievers.get("style_reference")
        if not retriever:
            return {"error": "Style reference retriever not available"}
        results = await retriever.search_similar_style(
            query_text=params["query_text"],
            style_type=params.get("style_type"),
            genre=params.get("genre"),
            top_k=params.get("top_k", 3)
        )
        return {
            "tool": "retrieve_style_reference",
            "results": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
        }

    async def _handle_plot_continuity(self, **params) -> Dict:
        retriever = self._engine._retrievers.get("plot_continuity")
        if not retriever:
            return {"error": "Plot continuity retriever not available"}
        results = await retriever.search_relevant_context(
            novel_id=params["novel_id"],
            query=params["query"],
            current_chapter=params["current_chapter"],
            top_k=params.get("top_k", 5)
        )
        return {
            "tool": "retrieve_plot_continuity",
            "results": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
        }

    async def _handle_writing_craft(self, **params) -> Dict:
        retriever = self._engine._retrievers.get("writing_craft")
        if not retriever:
            return {"error": "Writing craft retriever not available"}
        results = await retriever.search_craft(
            query=params["query"],
            craft_types=params.get("craft_types"),
            top_k=params.get("top_k", 3)
        )
        return {
            "tool": "retrieve_writing_craft",
            "results": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
        }

    async def _handle_augment_generation(self, **params) -> Dict:
        context = await self._engine.retrieve(
            query=params["query"],
            retriever_names=params.get("retrievers"),
            top_k=params.get("top_k", 5)
        )
        context = await self._engine.augment(context)
        return {
            "tool": "augment_generation",
            "augmented_prompt": context.augmented_prompt,
            "retrieved_count": len(context.retrieved_chunks),
            "retrieval_time_ms": context.retrieval_time_ms,
            "sources": [r.metadata.get("retriever_source", "unknown") for r in context.retrieved_chunks]
        }

    def get_tool(self, name: str) -> Optional[RetrievalTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        """列出所有可用工具（MCP格式）"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(self, name: str, **params) -> Dict:
        """执行工具"""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Tool not found: {name}"}
        return await tool.handler(**params)
```

---

## 5. Agent集成方案

### 5.1 Step4 Agent的RAG改造

```python
# 示例：WorldStateAgent集成RAG

class WorldStateAgent(BaseAgent):
    """
    世界状态Agent - 集成RAG检索
    """

    # Agent配置中声明需要的RAG工具
    RAG_TOOLS = ["retrieve_world_knowledge", "augment_generation"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 从共享状态获取查询
        query = state.get("shared.query", "")
        world_id = state.get("world.id", "")

        # 2. 检索世界知识
        rag_result = await self._rag_tools.execute_tool(
            "retrieve_world_knowledge",
            query=query,
            world_id=world_id,
            top_k=5
        )

        # 3. 将检索结果注入上下文
        context = "\n".join([r["text"] for r in rag_result["results"]])

        # 4. 构建增强Prompt
        prompt = f"""基于以下世界设定，回答关于世界状态的问题：

{context}

问题：{query}

请确保回答严格符合上述世界设定。"""

        # 5. 调用LLM生成
        result = await self.llm.generate(prompt)

        # 6. 返回增量状态更新
        return {"world.facts": [{"query": query, "answer": result, "sources": rag_result["results"]}]}


# 示例：SceneWriterAgent集成风格检索

class SceneWriterAgent(BaseAgent):
    """
    场景写作Agent - 集成风格检索
    """

    RAG_TOOLS = ["retrieve_style_reference", "retrieve_plot_continuity", "augment_generation"]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        scene_description = state.get("shared.scene_description", "")
        genre = state.get("novel.genre", "")
        current_chapter = state.get("novel.current_chapter", 1)
        novel_id = state.get("novel.id", "")

        # 1. 检索风格范例
        style_results = await self._rag_tools.execute_tool(
            "retrieve_style_reference",
            query_text=scene_description,
            style_type="description",
            genre=genre,
            top_k=3
        )

        # 2. 检索情节连贯性
        plot_results = await self._rag_tools.execute_tool(
            "retrieve_plot_continuity",
            query=scene_description,
            novel_id=novel_id,
            current_chapter=current_chapter,
            top_k=5
        )

        # 3. 组装增强上下文
        style_examples = "\n\n".join([f"范例{i+1}：{r['text']}" for i, r in enumerate(style_results["results"])])
        plot_context = "\n".join([r["text"] for r in plot_results["results"]])

        prompt = f"""你是一位专业的小说家。请根据以下信息撰写场景：

【风格范例】（请模仿以下风格）：
{style_examples}

【情节上下文】（确保与以下前文连贯）：
{plot_context}

【场景要求】：
{scene_description}

请撰写场景，确保：
1. 风格与范例一致
2. 情节与前文连贯
3. 描写生动、有画面感
"""

        result = await self.llm.generate(prompt)
        return {"narrative.scene_text": result}
```

### 5.2 自动RAG注入模式

除了显式工具调用，还支持**自动RAG注入模式**——在Agent的LLM调用前自动执行检索：

```python
# src/deepnovel/rag/auto_inject.py

class AutoRAGInjector:
    """
    自动RAG注入器

    在Agent调用LLM前，自动根据Agent类型和执行上下文执行检索，
    并将检索结果注入到Prompt中。
    """

    # Agent类型到检索器的映射
    AGENT_RETRIEVER_MAP = {
        "WorldStateAgent": ["world_knowledge"],
        "CharacterMindAgent": ["character_memory"],
        "SceneWriterAgent": ["style_reference", "plot_continuity"],
        "DialogueWriterAgent": ["character_memory", "style_reference"],
        "NarrativePlannerAgent": ["plot_continuity", "writing_craft"],
    }

    def __init__(self, rag_engine: RAGEngine):
        self._engine = rag_engine

    async def inject(self, agent_name: str, prompt: str, context: Dict) -> str:
        """
        自动注入检索上下文

        Args:
            agent_name: Agent名称
            prompt: 原始Prompt
            context: 执行上下文

        Returns:
            增强后的Prompt
        """
        retriever_names = self.AGENT_RETRIEVER_MAP.get(agent_name, [])
        if not retriever_names:
            return prompt

        # 提取查询（简化实现：使用prompt的前100字）
        query = prompt[:200]

        # 执行检索
        rag_context = await self._engine.retrieve(
            query=query,
            retriever_names=retriever_names,
            top_k=3
        )
        rag_context = await self._engine.augment(rag_context)

        # 注入Prompt
        injected = f"""{rag_context.augmented_prompt}

---

【原始任务】：
{prompt}
"""
        return injected
```

---

## 6. 数据流与生命周期

### 6.1 索引构建流程

```
小说创作启动
    │
    ├──→ 世界设定录入 → WorldKnowledgeRetriever.add_knowledge()
    │                    (世界规则、地理、历史、文化)
    │
    ├──→ 角色档案录入 → CharacterMemoryRetriever.add_memory()
    │                    (性格、经历、关系、目标)
    │
    ├──→ 风格范例录入 → StyleReferenceRetriever.add_reference()
    │                    (经典片段、作者样本、修辞范例)
    │
    └──→ 情节大纲录入 → PlotContinuityRetriever.add_plot_element()
                       (章节摘要、伏笔、冲突)

章节写作中
    │
    ├──→ 每完成一个场景 → PlotContinuityRetriever.add_plot_element()
    │                    (更新摘要、记录新伏笔)
    │
    ├──→ 角色新行为 → CharacterMemoryRetriever.add_memory()
    │                (记录新经历、情感变化)
    │
    └──→ 新设定引入 → WorldKnowledgeRetriever.add_knowledge()
                    (扩展世界观)
```

### 6.2 检索触发时机

| Agent | 触发时机 | 检索内容 | 用途 |
|-------|---------|---------|------|
| DirectorAgent | 制定策略时 | 风格范例、写作技巧 | 确定创作方向 |
| WorldStateAgent | 验证设定时 | 世界观知识 | 确保设定一致 |
| CharacterMindAgent | 角色决策时 | 角色记忆、关系 | 保持角色一致性 |
| EventSimulatorAgent | 事件生成时 | 前文情节、世界规则 | 确保事件合理 |
| SceneWriterAgent | 场景写作时 | 风格范例、前文摘要 | 风格+情节一致 |
| DialogueWriterAgent | 对话写作时 | 角色记忆、风格范例 | 角色声音+风格 |
| StyleEnforcerAgent | 质量检查时 | 风格范例 | 风格一致性验证 |
| ConsistencyCheckerAgent | 审查时 | 全部知识库 | 全局一致性检查 |

---

## 7. 评估与优化

### 7.1 检索质量评估

```python
# src/deepnovel/rag/evaluation.py

class RAGEvaluator:
    """
    RAG质量评估器

    评估指标：
    1. 检索准确率：检索结果与人工标注的相关性
    2. 上下文利用率：LLM实际使用了多少检索内容
    3. 幻觉率：生成内容与检索内容矛盾的比例
    4. 一致性提升：使用RAG前后角色/情节一致性对比
    """

    async def evaluate_retrieval(
        self,
        queries: List[str],
        expected_docs: List[List[str]],
        retriever_name: str
    ) -> Dict[str, float]:
        """评估检索准确率"""
        precision_sum = 0.0
        recall_sum = 0.0

        for query, expected in zip(queries, expected_docs):
            results = await self._retrieve(query, retriever_name)
            retrieved = [r.text for r in results]

            # Precision @ K
            hits = sum(1 for r in retrieved if any(e in r for e in expected))
            precision = hits / len(retrieved) if retrieved else 0

            # Recall
            expected_hits = sum(1 for e in expected if any(e in r for r in retrieved))
            recall = expected_hits / len(expected) if expected else 0

            precision_sum += precision
            recall_sum += recall

        n = len(queries)
        return {
            "precision@k": precision_sum / n,
            "recall": recall_sum / n,
            "f1": 2 * (precision_sum / n) * (recall_sum / n) / (precision_sum / n + recall_sum / n)
            if (precision_sum + recall_sum) > 0 else 0
        }

    async def evaluate_generation_faithfulness(
        self,
        query: str,
        retrieved_chunks: List[str],
        generated_text: str,
        llm_client: Any
    ) -> float:
        """
        评估生成内容对检索结果的忠实度

        使用LLM作为评判者，检查生成内容是否与检索内容一致
        """
        prompt = f"""评估以下生成内容对参考信息的忠实度：

【参考信息】：
{chr(10).join(retrieved_chunks)}

【生成内容】：
{generated_text}

请判断生成内容是否与参考信息一致：
- 如果生成内容完全基于参考信息，回答"完全忠实"
- 如果有少量扩展但不矛盾，回答"基本忠实"
- 如果有明显矛盾或幻觉，回答"不忠实"

只回答这三个选项之一。"""

        result = await llm_client.generate(prompt)

        scores = {"完全忠实": 1.0, "基本忠实": 0.7, "不忠实": 0.0}
        for key, score in scores.items():
            if key in result:
                return score
        return 0.5
```

### 7.2 反馈循环

```
生成结果
    │
    ├──→ ConsistencyChecker评估一致性
    │
    ├──→ RAGEvaluator评估检索质量
    │
    └──→ 反馈聚合
              │
              ├──→ 检索结果差 → 调整检索策略/重排序模型
              │
              ├──→ 上下文未充分利用 → 优化Prompt模板
              │
              └──→ 幻觉严重 → 增强检索召回/调整temperature
```

---

## 8. 详细实施计划

### 8.1 文件变更清单

#### 新增文件

| 文件 | 职责 | 行数估计 |
|------|------|---------|
| `src/deepnovel/rag/__init__.py` | 包初始化 | 30 |
| `src/deepnovel/rag/embeddings/__init__.py` | Embedding包初始化 | 20 |
| `src/deepnovel/rag/embeddings/engine.py` | Embedding引擎+路由 | 250 |
| `src/deepnovel/rag/vector_store/__init__.py` | 向量存储包初始化 | 20 |
| `src/deepnovel/rag/vector_store/base.py` | 向量存储基类 | 100 |
| `src/deepnovel/rag/vector_store/chroma_store.py` | ChromaDB实现（修复版） | 250 |
| `src/deepnovel/rag/vector_store/qdrant_store.py` | Qdrant实现 | 200 |
| `src/deepnovel/rag/retrievers/__init__.py` | 检索器包初始化 | 20 |
| `src/deepnovel/rag/retrievers/world_knowledge.py` | 世界观检索器 | 120 |
| `src/deepnovel/rag/retrievers/character_memory.py` | 角色记忆检索器 | 120 |
| `src/deepnovel/rag/retrievers/style_reference.py` | 风格范例检索器 | 120 |
| `src/deepnovel/rag/retrievers/plot_continuity.py` | 情节连贯检索器 | 150 |
| `src/deepnovel/rag/retrievers/writing_craft.py` | 写作技巧检索器 | 100 |
| `src/deepnovel/rag/engine.py` | RAG引擎（Query→检索→重排→组装） | 300 |
| `src/deepnovel/rag/reranker.py` | Cross-Encoder重排序 | 100 |
| `src/deepnovel/rag/tools.py` | Agent检索工具（MCP兼容） | 250 |
| `src/deepnovel/rag/auto_inject.py` | 自动RAG注入 | 80 |
| `src/deepnovel/rag/evaluation.py` | RAG质量评估 | 150 |
| `src/deepnovel/rag/ingestion.py` | 数据摄入管道 | 200 |

#### 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/deepnovel/llm/base.py` | EmbeddingClient新增async方法 | 向后兼容 |
| `src/deepnovel/llm/openai_adapter.py` | 实现EmbeddingClient | 新增embed/embed_batch |
| `src/deepnovel/llm/qwen_adapter.py` | 实现EmbeddingClient | 同上 |
| `src/deepnovel/llm/minimax_adapter.py` | 实现EmbeddingClient | 同上 |
| `src/deepnovel/llm/ollama_adapter.py` | 实现EmbeddingClient | 同上 |
| `src/deepnovel/agents/base.py` | 集成RAG工具注册 | AgentConfig添加rag_tools字段 |
| `src/deepnovel/api/routes.py` | 新增RAG管理端点 | 知识库CRUD、检索测试 |

#### 删除文件

| 文件 | 说明 |
|------|------|
| `src/deepnovel/vector_store/chroma_store.py` | 被新实现替代 |
| `src/deepnovel/vector_store/base.py` | 被新基类替代 |
| `src/deepnovel/database/chromadb_client.py` | 功能合并到新ChromaVectorStore |
| `src/deepnovel/database/chromadb_crud.py` | 冗余 |

### 8.2 实施阶段

#### Phase 1: 基础设施搭建（Day 1-3）

```
Day 1: Embedding引擎
- 实现BaseEmbeddingEngine + LocalEmbeddingEngine + OpenAIEmbeddingEngine
- 实现EmbeddingRouter（路由+缓存）
- 为所有LLM适配器实现EmbeddingClient
- 单元测试

Day 2: 向量存储修复
- 重写ChromaVectorStore（修复import和disconnect）
- 实现QdrantVectorStore
- 统一BaseVectorStore接口
- 混合检索（向量+BM25+RRF）
- 单元测试

Day 3: 数据摄入管道
- 实现RAGIngestionPipeline
- 世界知识/角色记忆/风格范例/情节元素的批量导入
- 索引构建与优化
- 单元测试
```

#### Phase 2: 领域检索器（Day 4-6）

```
Day 4: 世界+角色检索器
- WorldKnowledgeRetriever（世界观知识CRUD+检索）
- CharacterMemoryRetriever（角色记忆CRUD+检索）
- 集成测试

Day 5: 风格+情节检索器
- StyleReferenceRetriever（风格范例管理）
- PlotContinuityRetriever（情节连贯性管理）
- WritingCraftRetriever（写作技巧管理）
- 集成测试

Day 6: RAG引擎
- RAGEngine（Query理解→多路检索→RRF融合）
- Reranker（Cross-Encoder精排）
- ContextAssembler + PromptAugmenter
- 端到端RAG Pipeline测试
```

#### Phase 3: Agent工具集成（Day 7-9）

```
Day 7: RAG工具注册中心
- RAGToolRegistry（6个检索工具）
- MCP兼容格式
- 工具执行与结果格式化
- 单元测试

Day 8: Agent集成
- BaseAgent添加rag_tools支持
- 改造WorldStateAgent + CharacterMindAgent
- 改造SceneWriterAgent + DialogueWriterAgent
- 集成测试

Day 9: 自动RAG注入
- AutoRAGInjector实现
- Agent类型到检索器的映射配置
- 显式工具调用 vs 自动注入对比测试
```

#### Phase 4: 评估优化（Day 10-12）

```
Day 10: 评估体系
- RAGEvaluator实现
- 检索准确率测试集构建
- 生成忠实度评估
- 人工标注流程

Day 11: 性能优化
- Embedding缓存命中率优化
- 向量索引HNSW参数调优
- 批量检索优化
- 并发检索测试

Day 12: 反馈循环
- 检索质量自动反馈
- 索引自动更新策略
- Prompt模板A/B测试
- 整体RAG效果对比（有RAG vs 无RAG）
```

#### Phase 5: API与前端（Day 13-15）

```
Day 13: RAG管理API
- /rag/collections CRUD
- /rag/search 通用检索端点
- /rag/ingest 批量导入
- /rag/evaluate 质量评估

Day 14: 知识库管理前端
- 知识库浏览器（查看/搜索向量库内容）
- 批量导入界面
- 检索测试工具

Day 15: 集成测试与文档
- 端到端小说生成测试（有RAG vs 无RAG）
- API文档更新
- RAG使用手册
```

### 8.3 关键里程碑

| 里程碑 | 日期 | 验收标准 |
|--------|------|---------|
| M1: Embedding可用 | Day 1 | 文本向量化成功，本地模型+云端API均可使用 |
| M2: 向量存储修复 | Day 2 | ChromaDB/Qdrant可正常CRUD，混合检索可用 |
| M3: 检索器可用 | Day 5 | 5个领域检索器均可正常检索，结果有语义相关性 |
| M4: RAG Pipeline | Day 6 | 完整Query→检索→重排→组装→Prompt流程跑通 |
| M5: Agent集成 | Day 9 | Agent可通过工具调用RAG，生成质量有提升 |
| M6: 评估优化 | Day 12 | 检索准确率>70%，幻觉率降低>30% |
| M7: 生产就绪 | Day 15 | 端到端测试通过，文档完整 |

---

## 9. 量化验收标准

### 9.1 功能验收

| 编号 | 功能 | 验收标准 |
|------|------|---------|
| F1 | 真实Embedding | 使用真实模型（非MD5），语义相似文本的向量余弦相似度>0.8 |
| F2 | 多Embedding源 | 支持至少2种本地模型+2种云端API |
| F3 | 向量存储修复 | ChromaDB import错误修复，disconnect不删除数据 |
| F4 | 混合检索 | 向量检索+关键词检索融合，RRF排序正确 |
| F5 | 元数据过滤 | 支持按角色ID/章节/类型等元数据过滤检索 |
| F6 | 领域检索器 | 5个领域检索器均可独立工作 |
| F7 | RAG Pipeline | Query→检索→重排→组装→Prompt完整流程跑通 |
| F8 | Agent工具 | Agent可调用检索工具，工具返回结果正确 |
| F9 | 自动注入 | Agent LLM调用前自动注入检索上下文 |
| F10 | 数据摄入 | 支持批量导入世界设定/角色/风格/情节数据 |
| F11 | 检索评估 | 可计算Precision@K、Recall、F1 |
| F12 | 生成评估 | 可评估生成内容对检索结果的忠实度 |

### 9.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 向量化速度 | >50 texts/sec（本地模型） | 批量向量化1000条文本 |
| 检索延迟 | <200ms（单集合，10万文档） | 1000次查询取平均 |
| 混合检索延迟 | <500ms | 向量+关键词融合查询 |
| 重排序延迟 | <300ms（Top-20重排） | Cross-Encoder推理 |
| 索引构建速度 | >100 docs/sec | 批量导入1万条文档 |
| 缓存命中率 | >50% | 重复查询测试 |

### 9.3 质量验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 检索Precision@5 | >70% | 人工标注测试集 |
| 检索Recall@10 | >60% | 人工标注测试集 |
| 生成忠实度 | >80% | LLM评判+人工抽查 |
| 角色一致性提升 | >30% | 有RAG vs 无RAG对比 |
| 情节连贯性提升 | >25% | 有RAG vs 无RAG对比 |
| 风格一致性提升 | >20% | 有RAG vs 无RAG对比 |

---

## 10. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| Embedding模型过大 | 中 | 中 | 提供轻量模型选项（384维），按需加载 |
| 向量存储性能瓶颈 | 低 | 高 | 支持Qdrant切换，HNSW参数调优 |
| 检索结果质量不稳定 | 中 | 高 | 混合检索+重排序，Self-RAG自适应 |
| 数据隐私（云端Embedding） | 中 | 中 | 默认使用本地模型，云端可选 |
| 索引构建耗时 | 中 | 低 | 异步后台构建，增量更新 |
| 多模型维度不一致 | 低 | 高 | 统一768维，不匹配的模型投影 |

---

## 11. 附录

### A. 集合Schema定义

```python
# 预定义集合配置
RAG_COLLECTIONS = {
    "world_knowledge": CollectionConfig(
        name="world_knowledge",
        dimensions=768,
        distance_metric="cosine",
        metadata_schema={
            "world_id": "string",
            "knowledge_type": "string",  # rule, geography, history, culture, system
            "importance": "float",
            "tags": "list[string]"
        }
    ),
    "character_memories": CollectionConfig(
        name="character_memories",
        dimensions=768,
        distance_metric="cosine",
        metadata_schema={
            "char_id": "string",
            "memory_type": "string",  # event, trait, relationship, emotion
            "importance": "float",
            "chapter": "integer",
            "scene": "string"
        }
    ),
    "style_references": CollectionConfig(
        name="style_references",
        dimensions=768,
        distance_metric="cosine",
        metadata_schema={
            "style_type": "string",  # dialogue, description, action, monologue
            "genre": "string",
            "tone": "string",
            "author": "string"
        }
    ),
    "plot_continuity": CollectionConfig(
        name="plot_continuity",
        dimensions=768,
        distance_metric="cosine",
        metadata_schema={
            "novel_id": "string",
            "element_type": "string",  # summary, foreshadow, conflict, goal
            "chapter": "integer",
            "status": "string"  # active, resolved, abandoned
        }
    ),
    "writing_craft": CollectionConfig(
        name="writing_craft",
        dimensions=768,
        distance_metric="cosine",
        metadata_schema={
            "craft_type": "string",  # rhetoric, technique, culture, history
            "category": "string"
        }
    )
}
```

### B. 依赖清单

```
# Python新增依赖
sentence-transformers>=2.5.0   # 本地Embedding模型
qdrant-client>=1.7.0           # Qdrant向量存储
transformers>=4.36.0           # Cross-Encoder重排序
torch>=2.1.0                   # PyTorch（重排序模型）
croniter>=2.0.0                # 定时任务（如需要）

# 可选依赖（云端Embedding）
# openai 已存在
# dashscope 已存在（Qwen）
```

### C. RAG Prompt模板示例

```python
# 场景写作增强Prompt模板
SCENE_WRITING_RAG_TEMPLATE = """你是一位专业小说家。请根据以下参考信息撰写场景：

【风格范例】（请严格模仿以下叙事风格）：
{style_references}

【前文情节】（确保与以下情节连贯）：
{plot_context}

【角色状态】（角色当前的状态和记忆）：
{character_context}

【世界设定】（故事发生的世界背景）：
{world_context}

【写作要求】：
{scene_requirement}

请撰写场景，要求：
1. 叙事风格与【风格范例】一致
2. 情节与【前文情节】自然衔接
3. 角色行为符合【角色状态】
4. 场景描写符合【世界设定】
5. 描写生动，有画面感和沉浸感
"""
```

---

> **文档结束**
>
> **关于RAG的回答**：向量语义增强检索确实是RAG架构的核心组成部分。完整的RAG = 检索（Retrieval）+ 增强（Augmented）+ 生成（Generation）。当前项目只有"壳"（ChromaDB存储）没有"魂"（Embedding、Pipeline、Agent集成），Step6的设计将补全这一完整链条。
>
> 下一步：按Phase 1开始实施，优先搭建Embedding引擎和修复向量存储。
