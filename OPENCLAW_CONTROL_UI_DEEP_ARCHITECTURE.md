# OpenClaw Control UI - 核心引擎深度架构

## 第一部分：上下文管理系统（Context Management System）

### 1.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Context Management Engine                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Context    │  │   Context    │  │   Context    │         │
│  │   Builder    │  │   Window     │  │   Compressor │         │
│  │              │  │   Manager    │  │              │         │
│  │ - 构建上下文 │  │ - 窗口滑动   │  │ - 语义压缩   │         │
│  │ - 优先级排序 │  │ - 动态调整   │  │ - 层级摘要   │         │
│  │ - 关联检索   │  │ - 溢出处理   │  │ - 增量更新   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐          │
│  │              Context Store (Multi-Tier)            │          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │          │
│  │  │  Hot     │ │  Warm    │ │  Cold    │         │          │
│  │  │ (Redis)  │ │ (PG)     │ │ (S3)     │         │          │
│  │  │ < 1h     │ │ < 24h    │ │ > 24h    │         │          │
│  │  └──────────┘ └──────────┘ └──────────┘         │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心数据模型

```typescript
// types/context.ts

/**
 * 上下文片段 - 最小的语义单元
 */
interface ContextFragment {
  id: string;
  type: FragmentType;
  content: string;
  metadata: FragmentMetadata;
  vector: number[];           // 嵌入向量
  importance: number;         // 重要性评分 (0-1)
  timestamp: Date;
  ttl?: number;              // 生存时间
}

type FragmentType = 
  | 'user_message'      // 用户消息
  | 'assistant_message' // AI回复
  | 'system_prompt'     // 系统提示
  | 'tool_call'        // 工具调用
  | 'tool_result'      // 工具结果
  | 'memory_recall'    // 记忆召回
  | 'knowledge_inject' // 知识注入
  | 'summary'          // 摘要
  | 'thinking'         // 思考过程
  | 'fact';            // 事实断言

interface FragmentMetadata {
  sessionId: string;
  turnId: number;
  agentId?: string;
  model?: string;
  tokens: number;
  latency?: number;
  source?: string;         // 来源：direct, retrieved, generated
  confidence?: number;     // 置信度
  tags?: string[];
  relations?: string[];    // 关联的片段ID
}

/**
 * 上下文窗口 - 完整的对话上下文
 */
interface ContextWindow {
  id: string;
  sessionId: string;
  fragments: ContextFragment[];
  
  // 窗口管理
  maxTokens: number;
  currentTokens: number;
  compressionRatio: number;
  
  // 语义结构
  topics: TopicSegment[];
  entities: EntityReference[];
  intents: IntentHistory[];
  
  // 时间线
  createdAt: Date;
  updatedAt: Date;
  lastAccessedAt: Date;
}

/**
 * 主题段 - 连续的语义主题
 */
interface TopicSegment {
  id: string;
  name: string;
  startFragmentId: string;
  endFragmentId: string;
  fragmentIds: string[];
  vector: number[];
  coherence: number;        // 内部一致性
  importance: number;
}

/**
 * 实体引用 - 跟踪提到的实体
 */
interface EntityReference {
  id: string;
  name: string;
  type: string;
  firstMentionId: string;
  lastMentionId: string;
  mentionCount: number;
  currentState?: any;
}

/**
 * 意图历史 - 用户意图演变
 */
interface IntentHistory {
  turnId: number;
  primaryIntent: string;
  secondaryIntents: string[];
  confidence: number;
  transition: string;       // 从上一个意图的转换
}
```

### 1.3 上下文构建器

```typescript
// context/ContextBuilder.ts
export class ContextBuilder {
  constructor(
    private vectorStore: VectorStore,
    private memoryManager: MemoryManager,
    private knowledgeBase: KnowledgeBase,
    private config: ContextConfig
  ) {}

  /**
   * 构建完整的上下文窗口
   * 
   * 策略：
   * 1. 保留系统提示（必须）
   * 2. 保留最近的对话（高保真）
   * 3. 检索相关记忆（语义匹配）
   * 4. 注入相关知识（RAG）
   * 5. 压缩历史（摘要替代）
   */
  async build(sessionId: string, userMessage: string): Promise<ContextWindow> {
    const startTime = Date.now();
    
    // 1. 获取基础窗口
    const baseWindow = await this.getBaseWindow(sessionId);
    
    // 2. 编码用户消息
    const messageVector = await this.encodeMessage(userMessage);
    
    // 3. 并行检索
    const [relevantMemories, relevantKnowledge, relatedFacts] = await Promise.all([
      this.retrieveMemories(sessionId, messageVector, userMessage),
      this.retrieveKnowledge(messageVector, userMessage),
      this.retrieveFacts(sessionId, userMessage)
    ]);
    
    // 4. 组装上下文
    const window = await this.assembleContext({
      baseWindow,
      userMessage,
      messageVector,
      memories: relevantMemories,
      knowledge: relevantKnowledge,
      facts: relatedFacts
    });
    
    // 5. 优化窗口大小
    const optimized = await this.optimizeWindow(window);
    
    // 6. 记录指标
    this.recordMetrics('context_build', {
      duration: Date.now() - startTime,
      fragments: optimized.fragments.length,
      tokens: optimized.currentTokens,
      compressionRatio: optimized.compressionRatio
    });
    
    return optimized;
  }

  /**
   * 智能上下文组装
   */
  private async assembleContext(params: AssemblyParams): Promise<ContextWindow> {
    const fragments: ContextFragment[] = [];
    let tokenCount = 0;
    
    // 1. 系统提示（最高优先级）
    const systemPrompt = await this.getSystemPrompt(params.baseWindow.sessionId);
    if (systemPrompt) {
      fragments.push(this.createFragment('system_prompt', systemPrompt, {
        priority: 1.0,
        immutable: true
      }));
      tokenCount += systemPrompt.tokens;
    }
    
    // 2. 相关事实（高优先级）
    for (const fact of params.facts) {
      if (tokenCount >= this.config.maxTokens * 0.3) break;
      
      fragments.push(this.createFragment('fact', fact.content, {
        priority: 0.9,
        source: 'fact_store',
        confidence: fact.confidence
      }));
      tokenCount += fact.tokens;
    }
    
    // 3. 相关知识（中优先级）
    for (const knowledge of params.knowledge) {
      if (tokenCount >= this.config.maxTokens * 0.5) break;
      
      fragments.push(this.createFragment('knowledge_inject', knowledge.content, {
        priority: 0.7,
        source: 'knowledge_base',
        relevance: knowledge.score
      }));
      tokenCount += knowledge.tokens;
    }
    
    // 4. 相关记忆（中优先级）
    for (const memory of params.memories) {
      if (tokenCount >= this.config.maxTokens * 0.7) break;
      
      fragments.push(this.createFragment('memory_recall', memory.content, {
        priority: 0.6,
        source: 'memory_store',
        recency: memory.recencyScore,
        relevance: memory.relevanceScore
      }));
      tokenCount += memory.tokens;
    }
    
    // 5. 历史对话（动态压缩）
    const historyBudget = this.config.maxTokens - tokenCount;
    const historyFragments = await this.prepareHistory(
      params.baseWindow,
      historyBudget,
      params.messageVector
    );
    fragments.push(...historyFragments);
    
    // 6. 当前用户消息
    fragments.push(this.createFragment('user_message', params.userMessage, {
      priority: 1.0,
      turnId: params.baseWindow.fragments.length + 1
    }));
    
    return {
      id: generateId(),
      sessionId: params.baseWindow.sessionId,
      fragments,
      maxTokens: this.config.maxTokens,
      currentTokens: fragments.reduce((sum, f) => sum + f.metadata.tokens, 0),
      compressionRatio: this.calculateCompressionRatio(fragments),
      topics: params.baseWindow.topics,
      entities: params.baseWindow.entities,
      intents: params.baseWindow.intents,
      createdAt: new Date(),
      updatedAt: new Date(),
      lastAccessedAt: new Date()
    };
  }

  /**
   * 历史对话准备 - 智能压缩
   */
  private async prepareHistory(
    window: ContextWindow,
    budget: number,
    queryVector: number[]
  ): Promise<ContextFragment[]> {
    const history = window.fragments.filter(f => 
      f.type === 'user_message' || f.type === 'assistant_message'
    );
    
    if (history.length === 0) return [];
    
    // 计算每个历史片段的相关性
    const scored = await Promise.all(
      history.map(async (fragment) => ({
        fragment,
        relevance: await this.calculateRelevance(fragment.vector, queryVector),
        recency: this.calculateRecency(fragment),
        importance: fragment.importance
      }))
    );
    
    // 综合评分排序
    scored.sort((a, b) => {
      const scoreA = a.relevance * 0.4 + a.recency * 0.3 + a.importance * 0.3;
      const scoreB = b.relevance * 0.4 + b.recency * 0.3 + b.importance * 0.3;
      return scoreB - scoreA;
    });
    
    // 贪心选择，直到预算耗尽
    const selected: ContextFragment[] = [];
    let usedTokens = 0;
    
    for (const { fragment } of scored) {
      if (usedTokens + fragment.metadata.tokens > budget) {
        // 尝试压缩或摘要
        const compressed = await this.compressFragment(fragment, budget - usedTokens);
        if (compressed) {
          selected.push(compressed);
          usedTokens += compressed.metadata.tokens;
        }
        break;
      }
      
      selected.push(fragment);
      usedTokens += fragment.metadata.tokens;
    }
    
    // 按时间排序
    selected.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
    
    return selected;
  }

  /**
   * 片段压缩 - 保留语义核心
   */
  private async compressFragment(
    fragment: ContextFragment,
    maxTokens: number
  ): Promise<ContextFragment | null> {
    // 如果已经够小，直接返回
    if (fragment.metadata.tokens <= maxTokens) return fragment;
    
    // 生成摘要
    const summary = await this.summarize(fragment.content, maxTokens);
    
    if (!summary || summary.tokens > maxTokens) return null;
    
    return {
      ...fragment,
      id: generateId(),
      type: 'summary',
      content: summary.text,
      metadata: {
        ...fragment.metadata,
        tokens: summary.tokens,
        originalId: fragment.id,
        compressionType: 'summary'
      }
    };
  }

  /**
   * 上下文优化 - 动态调整
   */
  private async optimizeWindow(window: ContextWindow): Promise<ContextWindow> {
    // 如果仍然超出预算，进行激进压缩
    while (window.currentTokens > window.maxTokens) {
      const overage = window.currentTokens - window.maxTokens;
      
      // 找到可压缩的片段（排除不可变的）
      const compressible = window.fragments.filter(f => 
        !f.metadata.immutable && f.type !== 'user_message'
      );
      
      if (compressible.length === 0) break;
      
      // 选择重要性最低的片段进行压缩或移除
      const target = compressible.reduce((min, f) => 
        f.importance < min.importance ? f : min
      );
      
      if (target.importance > 0.7) {
        // 重要片段尝试压缩
        const compressed = await this.compressFragment(target, target.metadata.tokens * 0.5);
        if (compressed) {
          window.fragments = window.fragments.map(f => 
            f.id === target.id ? compressed : f
          );
        } else {
          // 移除最低重要性的
          window.fragments = window.fragments.filter(f => f.id !== target.id);
        }
      } else {
        // 低重要性直接移除
        window.fragments = window.fragments.filter(f => f.id !== target.id);
      }
      
      window.currentTokens = window.fragments.reduce((sum, f) => sum + f.metadata.tokens, 0);
    }
    
    window.compressionRatio = this.calculateCompressionRatio(window.fragments);
    
    return window;
  }
}

/**
 * 上下文配置
 */
interface ContextConfig {
  maxTokens: number;
  maxFragments: number;
  
  // 预算分配
  budgetAllocation: {
    systemPrompt: number;    // 0.1 = 10%
    facts: number;
    knowledge: number;
    memories: number;
    history: number;
  };
  
  // 压缩策略
  compression: {
    enabled: boolean;
    threshold: number;       // 超过多少开始压缩
    method: 'summary' | 'extract' | 'hybrid';
    preserveQuotes: boolean;
    preserveFacts: boolean;
  };
  
  // 检索策略
  retrieval: {
    memoryTopK: number;
    knowledgeTopK: number;
    factTopK: number;
    minRelevance: number;
  };
}
```

### 1.4 上下文窗口管理器

```typescript
// context/WindowManager.ts
export class WindowManager {
  private windows: Map<string, ContextWindow> = new Map();
  private stats: WindowStats = new WindowStats();
  
  constructor(
    private store: ContextStore,
    private compressor: ContextCompressor,
    private config: WindowConfig
  ) {}

  /**
   * 创建新窗口
   */
  async create(sessionId: string, initialConfig?: Partial<WindowConfig>): Promise<ContextWindow> {
    const window: ContextWindow = {
      id: generateId(),
      sessionId,
      fragments: [],
      maxTokens: initialConfig?.maxTokens || this.config.maxTokens,
      currentTokens: 0,
      compressionRatio: 1.0,
      topics: [],
      entities: [],
      intents: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      lastAccessedAt: new Date()
    };
    
    this.windows.set(window.id, window);
    await this.store.save(window);
    
    return window;
  }

  /**
   * 添加片段到窗口
   */
  async addFragment(windowId: string, fragment: ContextFragment): Promise<AddResult> {
    const window = this.windows.get(windowId);
    if (!window) throw new Error('Window not found');
    
    // 检查溢出
    const projectedTokens = window.currentTokens + fragment.metadata.tokens;
    
    if (projectedTokens > window.maxTokens) {
      // 需要处理溢出
      const overflowResult = await this.handleOverflow(window, fragment);
      
      if (overflowResult.action === 'compress') {
        // 压缩现有片段
        await this.compressWindow(window, overflowResult.targetTokens);
      } else if (overflowResult.action === 'evict') {
        // 驱逐低优先级片段
        await this.evictFragments(window, overflowResult.evictCount);
      }
    }
    
    // 添加新片段
    window.fragments.push(fragment);
    window.currentTokens += fragment.metadata.tokens;
    window.updatedAt = new Date();
    window.lastAccessedAt = new Date();
    
    // 更新语义结构
    await this.updateSemanticStructure(window, fragment);
    
    // 持久化
    await this.store.save(window);
    
    this.stats.recordAdd(fragment.metadata.tokens);
    
    return {
      success: true,
      window,
      overflow: projectedTokens > window.maxTokens ? overflowResult : null
    };
  }

  /**
   * 处理窗口溢出
   */
  private async handleOverflow(
    window: ContextWindow, 
    newFragment: ContextFragment
  ): Promise<OverflowResult> {
    const overflow = window.currentTokens + newFragment.metadata.tokens - window.maxTokens;
    const overflowRatio = overflow / window.maxTokens;
    
    // 策略选择
    if (overflowRatio < 0.1) {
      // 轻微溢出：压缩最低重要性片段
      return { action: 'compress', targetTokens: window.maxTokens - newFragment.metadata.tokens };
    } else if (overflowRatio < 0.3) {
      // 中度溢出：驱逐 + 压缩
      return { 
        action: 'evict', 
        evictCount: Math.ceil(window.fragments.length * 0.2),
        thenCompress: true 
      };
    } else {
      // 严重溢出：激进压缩，生成摘要
      return { 
        action: 'compress', 
        targetTokens: window.maxTokens * 0.5,
        aggressive: true 
      };
    }
  }

  /**
   * 压缩窗口
   */
  private async compressWindow(window: ContextWindow, targetTokens: number): Promise<void> {
    const current = window.currentTokens;
    const needToSave = current - targetTokens;
    
    // 按重要性排序（低到高）
    const sorted = [...window.fragments].sort((a, b) => a.importance - b.importance);
    
    let saved = 0;
    const compressed: ContextFragment[] = [];
    
    for (const fragment of sorted) {
      if (saved >= needToSave) {
        compressed.push(fragment);
        continue;
      }
      
      // 尝试压缩
      if (fragment.type === 'assistant_message' && !fragment.metadata.immutable) {
        const summary = await this.compressor.summarize(fragment, {
          maxTokens: Math.floor(fragment.metadata.tokens * 0.3),
          preserveKeyPoints: true
        });
        
        if (summary) {
          saved += fragment.metadata.tokens - summary.tokens;
          compressed.push({
            ...fragment,
            id: generateId(),
            type: 'summary',
            content: summary.text,
            metadata: {
              ...fragment.metadata,
              tokens: summary.tokens,
              originalId: fragment.id,
              compressionType: 'summary'
            }
          });
          continue;
        }
      }
      
      compressed.push(fragment);
    }
    
    window.fragments = compressed;
    window.currentTokens = compressed.reduce((sum, f) => sum + f.metadata.tokens, 0);
    window.compressionRatio = window.currentTokens / current;
  }

  /**
   * 驱逐片段
   */
  private async evictFragments(window: ContextWindow, count: number): Promise<void> {
    // 按重要性排序，移除最低的
    const sorted = [...window.fragments].sort((a, b) => a.importance - b.importance);
    const toEvict = sorted.slice(0, count).filter(f => !f.metadata.immutable);
    
    // 保存到冷存储
    await this.store.archive(window.id, toEvict);
    
    // 从窗口移除
    const evictIds = new Set(toEvict.map(f => f.id));
    window.fragments = window.fragments.filter(f => !evictIds.has(f.id));
    window.currentTokens = window.fragments.reduce((sum, f) => sum + f.metadata.tokens, 0);
  }

  /**
   * 更新语义结构
   */
  private async updateSemanticStructure(
    window: ContextWindow, 
    fragment: ContextFragment
  ): Promise<void> {
    // 更新主题
    if (fragment.type === 'user_message' || fragment.type === 'assistant_message') {
      const topic = await this.detectTopic(fragment);
      
      // 检查是否延续现有主题
      const lastTopic = window.topics[window.topics.length - 1];
      if (lastTopic && await this.isTopicContinuation(lastTopic, topic)) {
        lastTopic.endFragmentId = fragment.id;
        lastTopic.fragmentIds.push(fragment.id);
        lastTopic.coherence = await this.calculateCoherence(lastTopic);
      } else {
        window.topics.push({
          id: generateId(),
          name: topic.name,
          startFragmentId: fragment.id,
          endFragmentId: fragment.id,
          fragmentIds: [fragment.id],
          vector: topic.vector,
          coherence: 1.0,
          importance: topic.importance
        });
      }
    }
    
    // 更新实体
    const entities = await this.extractEntities(fragment);
    for (const entity of entities) {
      const existing = window.entities.find(e => e.id === entity.id);
      if (existing) {
        existing.lastMentionId = fragment.id;
        existing.mentionCount++;
      } else {
        window.entities.push({
          ...entity,
          firstMentionId: fragment.id,
          lastMentionId: fragment.id,
          mentionCount: 1
        });
      }
    }
    
    // 更新意图
    if (fragment.type === 'user_message') {
      const intent = await this.detectIntent(fragment);
      const lastIntent = window.intents[window.intents.length - 1];
      
      window.intents.push({
        turnId: fragment.metadata.turnId || window.intents.length + 1,
        primaryIntent: intent.primary,
        secondaryIntents: intent.secondary,
        confidence: intent.confidence,
        transition: lastIntent ? `${lastIntent.primaryIntent} -> ${intent.primary}` : 'start'
      });
    }
  }
}
```

---

## 第二部分：向量化检索系统（Vector Retrieval System）

### 2.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Vector Retrieval Engine                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Embedder   │  │   Index      │  │   Search     │         │
│  │              │  │   Manager    │  │   Engine     │         │
│  │ - 文本编码   │  │ - 索引构建   │  │ - 相似度搜索 │         │
│  │ - 多模态编码 │  │ - 增量更新   │  │ - 混合检索   │         │
│  │ - 缓存优化   │  │ - 分区管理   │  │ - 重排序     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐          │
│  │              Vector Store (Qdrant/Pinecone)        │          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │          │
│  │  │  Dense   │ │  Sparse  │ │  Hybrid  │         │          │
│  │  │ Vector   │ │ Vector   │ │ Search   │         │          │
│  │  │ 1536d    │ │ BM25     │ │ α=0.7    │         │          │
│  │  └──────────┘ └──────────┘ └──────────┘         │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 嵌入模型管理

```typescript
// vector/EmbedderManager.ts
export class EmbedderManager {
  private models: Map<string, EmbeddingModel> = new Map();
  private cache: EmbeddingCache;
  
  constructor(private config: EmbedderConfig) {
    this.cache = new EmbeddingCache(config.cacheSize);
  }

  /**
   * 注册嵌入模型
   */
  register(model: EmbeddingModel): void {
    this.models.set(model.name, model);
  }

  /**
   * 获取文本嵌入
   */
  async embed(text: string, options: EmbedOptions = {}): Promise<number[]> {
    const modelName = options.model || this.config.defaultModel;
    const model = this.models.get(modelName);
    
    if (!model) throw new Error(`Model ${modelName} not found`);
    
    // 检查缓存
    const cacheKey = this.generateCacheKey(text, modelName);
    const cached = this.cache.get(cacheKey);
    if (cached) return cached;
    
    // 编码
    const embedding = await model.encode(text, {
      normalize: true,
      ...options
    });
    
    // 缓存
    this.cache.set(cacheKey, embedding);
    
    return embedding;
  }

  /**
   * 批量编码
   */
  async embedBatch(texts: string[], options: EmbedOptions = {}): Promise<number[][]> {
    const modelName = options.model || this.config.defaultModel;
    const model = this.models.get(modelName);
    
    if (!model) throw new Error(`Model ${modelName} not found`);
    
    // 检查缓存
    const uncached: { index: number; text: string }[] = [];
    const results: (number[] | null)[] = new Array(texts.length).fill(null);
    
    for (let i = 0; i < texts.length; i++) {
      const cacheKey = this.generateCacheKey(texts[i], modelName);
      const cached = this.cache.get(cacheKey);
      
      if (cached) {
        results[i] = cached;
      } else {
        uncached.push({ index: i, text: texts[i] });
      }
    }
    
    // 批量编码未缓存的
    if (uncached.length > 0) {
      const embeddings = await model.encodeBatch(
        uncached.map(u => u.text),
        { normalize: true, ...options }
      );
      
      for (let i = 0; i < uncached.length; i++) {
        const { index } = uncached[i];
        results[index] = embeddings[i];
        
        // 缓存
        const cacheKey = this.generateCacheKey(uncached[i].text, modelName);
        this.cache.set(cacheKey, embeddings[i]);
      }
    }
    
    return results as number[][];
  }

  /**
   * 多模态编码
   */
  async embedMultimodal(
    content: MultimodalContent,
    options: EmbedOptions = {}
  ): Promise<number[]> {
    const modelName = options.model || this.config.defaultMultimodalModel;
    const model = this.models.get(modelName);
    
    if (!model || !model.supportsMultimodal) {
      throw new Error(`Multimodal model ${modelName} not available`);
    }
    
    return model.encodeMultimodal(content, options);
  }
}

/**
 * 嵌入模型接口
 */
interface EmbeddingModel {
  name: string;
  dimension: number;
  supportsMultimodal: boolean;
  maxSequenceLength: number;
  
  encode(text: string, options?: EncodeOptions): Promise<number[]>;
  encodeBatch(texts: string[], options?: EncodeOptions): Promise<number[][]>;
  encodeMultimodal?(content: MultimodalContent, options?: EncodeOptions): Promise<number[]>;
}

/**
 * OpenAI 嵌入模型
 */
class OpenAIEmbedder implements EmbeddingModel {
  name = 'text-embedding-3-large';
  dimension = 3072;
  supportsMultimodal = false;
  maxSequenceLength = 8191;
  
  constructor(private apiKey: string) {}
  
  async encode(text: string, options?: EncodeOptions): Promise<number[]> {
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: this.name,
        input: text,
        dimensions: options?.dimensions || this.dimension
      })
    });
    
    const data = await response.json();
    let embedding = data.data[0].embedding;
    
    // 归一化
    if (options?.normalize) {
      embedding = this.normalize(embedding);
    }
    
    return embedding;
  }
  
  async encodeBatch(texts: string[], options?: EncodeOptions): Promise<number[][]> {
    // OpenAI 支持批量
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: this.name,
        input: texts,
        dimensions: options?.dimensions || this.dimension
      })
    });
    
    const data = await response.json();
    
    return data.data.map((d: any) => {
      let emb = d.embedding;
      if (options?.normalize) emb = this.normalize(emb);
      return emb;
    });
  }
  
  private normalize(vector: number[]): number[] {
    const magnitude = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
    return vector.map(v => v / magnitude);
  }
}

/**
 * 本地嵌入模型（使用 Transformers.js）
 */
class LocalEmbedder implements EmbeddingModel {
  name = 'Xenova/all-MiniLM-L6-v2';
  dimension = 384;
  supportsMultimodal = false;
  maxSequenceLength = 512;
  
  private pipeline: any;
  
  async load(): Promise<void> {
    const { pipeline } = await import('@xenova/transformers');
    this.pipeline = await pipeline('feature-extraction', this.name);
  }
  
  async encode(text: string, options?: EncodeOptions): Promise<number[]> {
    if (!this.pipeline) await this.load();
    
    const output = await this.pipeline(text, {
      pooling: 'mean',
      normalize: options?.normalize
    });
    
    return Array.from(output.data);
  }
  
  async encodeBatch(texts: string[], options?: EncodeOptions): Promise<number[][]> {
    const results = await Promise.all(texts.map(t => this.encode(t, options)));
    return results;
  }
}
```

### 2.3 向量索引管理

```typescript
// vector/VectorIndex.ts
export class VectorIndex {
  constructor(
    private store: VectorStore,
    private embedder: EmbedderManager,
    private config: IndexConfig
  ) {}

  /**
   * 添加文档到索引
   */
  async addDocument(doc: Document): Promise<IndexResult> {
    // 分块
    const chunks = this.chunkDocument(doc);
    
    // 编码
    const texts = chunks.map(c => c.text);
    const embeddings = await this.embedder.embedBatch(texts);
    
    // 构建向量记录
    const points: VectorPoint[] = chunks.map((chunk, i) => ({
      id: generateId(),
      vector: embeddings[i],
      payload: {
        docId: doc.id,
        chunkIndex: chunk.index,
        text: chunk.text,
        metadata: {
          ...doc.metadata,
          chunkSize: chunk.text.length,
          startChar: chunk.start,
          endChar: chunk.end
        }
      }
    }));
    
    // 批量插入
    await this.store.upsert(this.config.collectionName, points);
    
    return {
      docId: doc.id,
      chunks: points.length,
      tokens: chunks.reduce((sum, c) => sum + c.tokens, 0)
    };
  }

  /**
   * 搜索相似文档
   */
  async search(query: string, options: SearchOptions = {}): Promise<SearchResult[]> {
    const startTime = Date.now();
    
    // 编码查询
    const queryVector = await this.embedder.embed(query);
    
    // 构建过滤条件
    const filter = this.buildFilter(options.filters);
    
    // 执行搜索
    const results = await this.store.search({
      collection: this.config.collectionName,
      vector: queryVector,
      limit: options.limit || 10,
      offset: options.offset || 0,
      filter,
      withPayload: true,
      withVectors: false
    });
    
    // 重排序（如果启用）
    let ranked = results;
    if (options.rerank) {
      ranked = await this.rerank(query, results);
    }
    
    // 记录指标
    this.recordMetrics('search', {
      duration: Date.now() - startTime,
      queryLength: query.length,
      results: ranked.length,
      collection: this.config.collectionName
    });
    
    return ranked.map(r => ({
      id: r.id,
      score: r.score,
      text: r.payload.text,
      metadata: r.payload.metadata,
      docId: r.payload.docId
    }));
  }

  /**
   * 混合搜索（向量 + 关键词）
   */
  async hybridSearch(query: string, options: HybridOptions = {}): Promise<SearchResult[]> {
    // 并行执行向量搜索和关键词搜索
    const [vectorResults, keywordResults] = await Promise.all([
      this.search(query, { ...options, limit: (options.limit || 10) * 2 }),
      this.keywordSearch(query, options)
    ]);
    
    // 融合结果
    const fused = this.fuseResults(vectorResults, keywordResults, {
      vectorWeight: options.vectorWeight || 0.7,
      keywordWeight: options.keywordWeight || 0.3
    });
    
    // 去重并限制数量
    const seen = new Set<string>();
    const unique: SearchResult[] = [];
    
    for (const result of fused) {
      if (!seen.has(result.docId)) {
        seen.add(result.docId);
        unique.push(result);
        
        if (unique.length >= (options.limit || 10)) break;
      }
    }
    
    return unique;
  }

  /**
   * 关键词搜索
   */
  private async keywordSearch(query: string, options: SearchOptions): Promise<SearchResult[]> {
    // 使用 BM25 或全文搜索
    const tokens = this.tokenize(query);
    
    const results = await this.store.scroll({
      collection: this.config.collectionName,
      filter: {
        must: tokens.map(token => ({
          key: 'text',
          match: { text: token }
        }))
      },
      limit: (options.limit || 10) * 2
    });
    
    // 计算 BM25 分数
    return results.map(r => ({
      id: r.id,
      score: this.calculateBM25(r.payload.text, tokens),
      text: r.payload.text,
      metadata: r.payload.metadata,
      docId: r.payload.docId
    }));
  }

  /**
   * 结果融合
   */
  private fuseResults(
    vectorResults: SearchResult[],
    keywordResults: SearchResult[],
    weights: { vectorWeight: number; keywordWeight: number }
  ): SearchResult[] {
    const scores = new Map<string, number>();
    const results = new Map<string, SearchResult>();
    
    // 归一化向量分数
    const maxVectorScore = Math.max(...vectorResults.map(r => r.score), 1);
    for (const result of vectorResults) {
      const normalizedScore = (result.score / maxVectorScore) * weights.vectorWeight;
      scores.set(result.id, (scores.get(result.id) || 0) + normalizedScore);
      results.set(result.id, result);
    }
    
    // 归一化关键词分数
    const maxKeywordScore = Math.max(...keywordResults.map(r => r.score), 1);
    for (const result of keywordResults) {
      const normalizedScore = (result.score / maxKeywordScore) * weights.keywordWeight;
      scores.set(result.id, (scores.get(result.id) || 0) + normalizedScore);
      if (!results.has(result.id)) {
        results.set(result.id, result);
      }
    }
    
    // 排序
    const fused = Array.from(scores.entries())
      .map(([id, score]) => ({ ...results.get(id)!, score }))
      .sort((a, b) => b.score - a.score);
    
    return fused;
  }

  /**
   * 重排序
   */
  private async rerank(query: string, results: VectorResult[]): Promise<VectorResult[]> {
    // 使用交叉编码器
    const pairs = results.map(r => ({
      query,
      document: r.payload.text
    }));
    
    const scores = await this.crossEncoder.score(pairs);
    
    return results
      .map((r, i) => ({ ...r, score: scores[i] }))
      .sort((a, b) => b.score - a.score);
  }

  /**
   * 文档分块
   */
  private chunkDocument(doc: Document): DocumentChunk[] {
    const chunks: DocumentChunk[] = [];
    const text = doc.content;
    
    if (this.config.chunking.strategy === 'fixed') {
      // 固定大小分块
      const size = this.config.chunking.size;
      const overlap = this.config.chunking.overlap;
      
      for (let i = 0; i < text.length; i += size - overlap) {
        const chunkText = text.slice(i, i + size);
        chunks.push({
          index: chunks.length,
          text: chunkText,
          start: i,
          end: Math.min(i + size, text.length),
          tokens: this.estimateTokens(chunkText)
        });
      }
    } else if (this.config.chunking.strategy === 'semantic') {
      // 语义分块
      chunks.push(...this.semanticChunk(text));
    } else if (this.config.chunking.strategy === 'hierarchical') {
      // 层次分块
      chunks.push(...this.hierarchicalChunk(text, doc.structure));
    }
    
    return chunks;
  }

  /**
   * 语义分块 - 基于语义边界
   */
  private semanticChunk(text: string): DocumentChunk[] {
    // 使用句子分割
    const sentences = this.splitSentences(text);
    const chunks: DocumentChunk[] = [];
    let currentChunk: string[] = [];
    let currentTokens = 0;
    
    for (const sentence of sentences) {
      const sentenceTokens = this.estimateTokens(sentence);
      
      if (currentTokens + sentenceTokens > this.config.chunking.size && currentChunk.length > 0) {
        // 保存当前块
        const chunkText = currentChunk.join(' ');
        chunks.push({
          index: chunks.length,
          text: chunkText,
          start: text.indexOf(currentChunk[0]),
          end: text.indexOf(currentChunk[currentChunk.length - 1]) + currentChunk[currentChunk.length - 1].length,
          tokens: currentTokens
        });
        
        // 开始新块，保留一些上下文
        currentChunk = currentChunk.slice(-2); // 保留最后2句
        currentTokens = currentChunk.reduce((sum, s) => sum + this.estimateTokens(s), 0);
      }
      
      currentChunk.push(sentence);
      currentTokens += sentenceTokens;
    }
    
    // 处理剩余
    if (currentChunk.length > 0) {
      const chunkText = currentChunk.join(' ');
      chunks.push({
        index: chunks.length,
        text: chunkText,
        start: text.indexOf(currentChunk[0]),
        end: text.length,
        tokens: currentTokens
      });
    }
    
    return chunks;
  }
}

/**
 * 向量存储接口
 */
interface VectorStore {
  upsert(collection: string, points: VectorPoint[]): Promise<void>;
  search(params: SearchParams): Promise<VectorResult[]>;
  scroll(params: ScrollParams): Promise<VectorResult[]>;
  delete(collection: string, ids: string[]): Promise<void>;
  createCollection(params: CollectionConfig): Promise<void>;
}

/**
 * Qdrant 实现
 */
class QdrantStore implements VectorStore {
  constructor(private client: QdrantClient) {}
  
  async upsert(collection: string, points: VectorPoint[]): Promise<void> {
    await this.client.upsert(collection, {
      points: points.map(p => ({
        id: p.id,
        vector: p.vector,
        payload: p.payload
      }))
    });
  }
  
  async search(params: SearchParams): Promise<VectorResult[]> {
    const results = await this.client.search(params.collection, {
      vector: params.vector,
      limit: params.limit,
      offset: params.offset,
      filter: params.filter,
      with_payload: params.withPayload,
      with_vector: params.withVectors
    });
    
    return results.map(r => ({
      id: r.id as string,
      score: r.score,
      payload: r.payload as Record<string, any>,
      vector: r.vector
    }));
  }
  
  async createCollection(params: CollectionConfig): Promise<void> {
    await this.client.createCollection(params.name, {
      vectors: {
        size: params.dimension,
        distance: params.distance || 'Cosine'
      }
    });
  }
}
```

---

## 第三部分：数据模型系统（Data Model System）

### 3.1 核心实体关系

```typescript
// models/core.ts

/**
 * 用户实体
 */
interface User {
  id: string;
  username: string;
  email: string;
  profile: UserProfile;
  preferences: UserPreferences;
  roles: Role[];
  apiKeys: APIKey[];
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt?: Date;
}

interface UserProfile {
  displayName?: string;
  avatar?: string;
  bio?: string;
  timezone: string;
  language: string;
}

interface UserPreferences {
  theme: string;
  fontSize: number;
  messageDensity: 'compact' | 'comfortable' | 'spacious';
  codeTheme: string;
  autoSave: boolean;
  notifications: NotificationPreferences;
  privacy: PrivacySettings;
}

/**
 * 会话实体
 */
interface Session {
  id: string;
  name: string;
  description?: string;
  status: SessionStatus;
  
  // 关联
  userId: string;
  user: User;
  agentId: string;
  agent: Agent;
  parentId?: string;
  parent?: Session;
  children: Session[];
  
  // 内容
  messages: Message[];
  contextWindow: ContextWindow;
  
  // 元数据
  tags: string[];
  metadata: SessionMetadata;
  
  // 统计
  stats: SessionStats;
  
  // 时间
  createdAt: Date;
  updatedAt: Date;
  endedAt?: Date;
}

type SessionStatus = 'active' | 'paused' | 'archived' | 'deleted';

interface SessionMetadata {
  source: string;
  topic?: string;
  goal?: string;
  context?: Record<string, any>;
}

interface SessionStats {
  messageCount: number;
  tokenCount: number;
  userTokenCount: number;
  assistantTokenCount: number;
  totalLatency: number;
  avgLatency: number;
  modelCalls: number;
  toolCalls: number;
}

/**
 * 消息实体
 */
interface Message {
  id: string;
  role: MessageRole;
  content: MessageContent;
  
  // 关联
  sessionId: string;
  session: Session;
  parentId?: string;
  parent?: Message;
  children: Message[];
  
  // 工具调用
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  
  // 模型信息
  model?: string;
  modelVersion?: string;
  
  // 性能
  latency?: number;
  tokens?: TokenUsage;
  
  // 反馈
  feedback?: MessageFeedback;
  
  // 元数据
  metadata: MessageMetadata;
  
  // 时间
  createdAt: Date;
  updatedAt?: Date;
  deletedAt?: Date;
}

type MessageRole = 'system' | 'user' | 'assistant' | 'tool';

interface MessageContent {
  type: 'text' | 'multimodal' | 'structured';
  text?: string;
  parts?: ContentPart[];
  structured?: Record<string, any>;
}

type ContentPart = 
  | { type: 'text'; text: string }
  | { type: 'image'; url: string; mimeType: string }
  | { type: 'file'; url: string; name: string; mimeType: string }
  | { type: 'code'; code: string; language: string }
  | { type: 'thinking'; thinking: string; signature?: string };

interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

interface ToolResult {
  toolCallId: string;
  content: string;
  isError?: boolean;
}

interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

interface MessageFeedback {
  rating: number;
  comment?: string;
  tags?: string[];
  createdAt: Date;
}

interface MessageMetadata {
  clientInfo?: ClientInfo;
  processingStages?: ProcessingStage[];
  edits?: MessageEdit[];
  reactions?: Reaction[];
}

/**
 * Agent 实体
 */
interface Agent {
  id: string;
  name: string;
  description?: string;
  avatar?: string;
  
  // 配置
  config: AgentConfig;
  systemPrompt: string;
  
  // 能力
  capabilities: Capability[];
  tools: ToolPermission[];
  
  // 模型
  model: ModelConfig;
  fallbackModels: ModelConfig[];
  
  // 记忆
  memory: MemoryConfig;
  
  // 知识
  knowledgeBases: KnowledgeBaseLink[];
  
  // 版本
  version: string;
  versions: AgentVersion[];
  
  // 统计
  stats: AgentStats;
  
  // 时间
  createdAt: Date;
  updatedAt: Date;
  publishedAt?: Date;
}

interface AgentConfig {
  temperature: number;
  maxTokens: number;
  topP: number;
  frequencyPenalty: number;
  presencePenalty: number;
  stopSequences: string[];
  responseFormat?: 'text' | 'json' | 'structured';
  jsonSchema?: Record<string, any>;
}

interface ModelConfig {
  provider: string;
  model: string;
  version?: string;
  endpoint?: string;
}

interface MemoryConfig {
  enabled: boolean;
  type: 'session' | 'user' | 'global';
  maxMessages: number;
  summarizationThreshold: number;
  vectorStore?: string;
}

interface AgentStats {
  totalSessions: number;
  totalMessages: number;
  totalTokens: number;
  avgResponseTime: number;
  satisfactionRate: number;
  errorRate: number;
  lastUsedAt?: Date;
}

/**
 * 插件实体
 */
interface Plugin {
  id: string;
  manifest: PluginManifest;
  
  // 状态
  status: PluginStatus;
  
  // 配置
  config: PluginConfig;
  
  // 钩子
  hooks: PluginHook[];
  
  // 权限
  permissions: string[];
  
  // 统计
  stats: PluginStats;
  
  // 时间
  installedAt: Date;
  updatedAt: Date;
  lastUsedAt?: Date;
}

interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  homepage?: string;
  repository?: string;
  
  // 入口
  entry: string;
  
  // 能力
  capabilities: string[];
  
  // 依赖
  dependencies: PluginDependency[];
  
  // 钩子声明
  hooks: HookDeclaration[];
  
  // 权限声明
  permissions: string[];
  
  // 配置 schema
  configSchema: JSONSchema;
}

type PluginStatus = 'installed' | 'active' | 'inactive' | 'error' | 'updating';

/**
 * 知识库实体
 */
interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  
  // 类型
  type: 'documents' | 'webpages' | 'database' | 'api';
  
  // 源
  sources: KnowledgeSource[];
  
  // 索引
  index: VectorIndex;
  
  // 同步
  syncConfig: SyncConfig;
  lastSyncAt?: Date;
  
  // 统计
  stats: KnowledgeStats;
  
  // 时间
  createdAt: Date;
  updatedAt: Date;
}

interface KnowledgeSource {
  id: string;
  type: 'file' | 'url' | 'database' | 'api';
  location: string;
  metadata: Record<string, any>;
  lastIndexedAt?: Date;
  documentCount: number;
  status: 'pending' | 'indexing' | 'ready' | 'error';
}

/**
 * 工具实体
 */
interface Tool {
  id: string;
  name: string;
  description: string;
  
  // 定义
  definition: ToolDefinition;
  
  // 实现
  implementation: ToolImplementation;
  
  // 权限
  permissions: ToolPermission[];
  
  // 统计
  stats: ToolStats;
  
  // 时间
  createdAt: Date;
  updatedAt: Date;
}

interface ToolDefinition {
  type: 'function' | 'retrieval' | 'code' | 'mcp';
  function?: {
    name: string;
    description: string;
    parameters: JSONSchema;
  };
  retrieval?: {
    knowledgeBaseId: string;
    maxResults: number;
  };
}

interface ToolImplementation {
  type: 'native' | 'plugin' | 'webhook' | 'mcp';
  code?: string;
  pluginId?: string;
  webhookUrl?: string;
  mcpServer?: string;
}
```

### 3.2 数据库 Schema

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    profile JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    role VARCHAR(20) DEFAULT 'user',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- API 密钥表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '{}',
    rate_limit JSONB DEFAULT '{}',
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent 表
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    avatar_url TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    system_prompt TEXT,
    model_provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_config JSONB DEFAULT '{}',
    memory_config JSONB DEFAULT '{}',
    capabilities JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'draft',
    version VARCHAR(50) DEFAULT '1.0.0',
    stats JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Agent 版本表
CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    system_prompt TEXT,
    change_log TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 会话表
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    user_id UUID NOT NULL REFERENCES users(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    parent_id UUID REFERENCES sessions(id),
    context_window JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    stats JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content JSONB NOT NULL,
    content_text TEXT GENERATED ALWAYS AS (content->>'text') STORED,
    tool_calls JSONB DEFAULT '[]',
    tool_results JSONB DEFAULT '[]',
    model VARCHAR(100),
    model_version VARCHAR(50),
    latency_ms INTEGER,
    tokens JSONB DEFAULT '{}',
    feedback JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    parent_id UUID REFERENCES messages(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- 消息内容全文搜索索引
CREATE INDEX idx_messages_content_search ON messages USING gin(to_tsvector('english', content_text));
CREATE INDEX idx_messages_content_search_zh ON messages USING gin(to_tsvector('chinese', content_text));

-- 插件表
CREATE TABLE plugins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manifest JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'installed',
    config JSONB DEFAULT '{}',
    hooks JSONB DEFAULT '[]',
    permissions TEXT[] DEFAULT '{}',
    stats JSONB DEFAULT '{}',
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- 知识库表
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    config JSONB DEFAULT '{}',
    sync_config JSONB DEFAULT '{}',
    index_config JSONB DEFAULT '{}',
    stats JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ
);

-- 知识源表
CREATE TABLE knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    location TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    document_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    last_indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 工具表
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    implementation JSONB NOT NULL,
    permissions JSONB DEFAULT '[]',
    stats JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 记忆表
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id UUID REFERENCES sessions(id),
    agent_id UUID REFERENCES agents(id),
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    content_vector vector(1536),
    metadata JSONB DEFAULT '{}',
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- 记忆向量索引
CREATE INDEX idx_memories_vector ON memories USING ivfflat (content_vector vector_cosine_ops);

-- 审计日志表
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建分区表（按时间）
CREATE TABLE audit_logs_2024 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- 索引
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_session_id ON memories(session_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

---

## 第四部分：可视化界面系统（Visualization System）

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Visualization Engine                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Layout     │  │   Component  │  │   Animation  │         │
│  │   Manager    │  │   Library    │  │   Engine     │         │
│  │              │  │              │  │              │         │
│  │ - 响应式布局 │  │ - 图表组件   │  │ - 过渡动画   │         │
│  │ - 网格系统   │  │ - 数据面板   │  │ - 交互反馈   │         │
│  │ - 拖拽调整   │  │ - 状态指示   │  │ - 性能优化   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐          │
│  │              Data Flow Layer                       │          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │          │
│  │  │  Realtime│ │  Batch   │ │  Cached  │         │          │
│  │  │  Stream  │ │  Query   │ │  Data    │         │          │
│  │  └──────────┘ └──────────┘ └──────────┘         │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 核心可视化组件

```typescript
// components/visualization/SessionGraph.tsx
/**
 * 会话关系图 - 展示会话间的关联
 */
export function SessionGraph({ sessions, onSelect }: SessionGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  
  // 使用 D3.js 力导向图
  useEffect(() => {
    if (!svgRef.current || sessions.length === 0) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // 构建节点和边
    const nodes: Node[] = sessions.map(s => ({
      id: s.id,
      name: s.name,
      status: s.status,
      messageCount: s.stats.messageCount,
      radius: Math.sqrt(s.stats.messageCount) * 2 + 10
    }));
    
    const links: Link[] = [];
    for (const session of sessions) {
      if (session.parentId) {
        links.push({
          source: session.parentId,
          target: session.id,
          type: 'parent-child'
        });
      }
      // 添加语义关联
      for (const other of sessions) {
        if (session.id !== other.id) {
          const similarity = calculateSimilarity(session, other);
          if (similarity > 0.7) {
            links.push({
              source: session.id,
              target: other.id,
              type: 'semantic',
              strength: similarity
            });
          }
        }
      }
    }
    
    // 创建力模拟
    const simulation = d3.forceSimulation<Node>(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(dimensions.width / 2, dimensions.height / 2))
      .force('collision', d3.forceCollide().radius(d => d.radius + 5));
    
    // 绘制边
    const linkElements = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => d.type === 'parent-child' ? '#94a3b8' : '#cbd5e1')
      .attr('stroke-width', d => d.type === 'parent-child' ? 2 : 1)
      .attr('stroke-dasharray', d => d.type === 'semantic' ? '5,5' : 'none')
      .attr('opacity', d => d.strength || 0.5);
    
    // 绘制节点
    const nodeElements = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, Node>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );
    
    // 节点圆形
    nodeElements.append('circle')
      .attr('r', d => d.radius)
      .attr('fill', d => getStatusColor(d.status))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9);
    
    // 节点标签
    nodeElements.append('text')
      .text(d => d.name)
      .attr('text-anchor', 'middle')
      .attr('dy', d => d.radius + 15)
      .attr('font-size', 12)
      .attr('fill', '#475569');
    
    // 消息数指示
    nodeElements.append('text')
      .text(d => d.messageCount.toString())
      .attr('text-anchor', 'middle')
      .attr('dy', 4)
      .attr('font-size', 10)
      .attr('fill', '#fff');
    
    // 点击事件
    nodeElements.on('click', (event, d) => {
      onSelect?.(d.id);
    });
    
    // 更新位置
    simulation.on('tick', () => {
      linkElements
        .attr('x1', d => (d.source as Node).x!)
        .attr('y1', d => (d.source as Node).y!)
        .attr('x2', d => (d.target as Node).x!)
        .attr('y2', d => (d.target as Node).y!);
      
      nodeElements.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    return () => {
      simulation.stop();
    };
  }, [sessions, dimensions]);
  
  return (
    <div className="session-graph">
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
      />
      
      <GraphLegend />
      
      <GraphControls
        onZoomIn={() => {/* 放大 */}}
        onZoomOut={() => {/* 缩小 */}}
        onReset={() => {/* 重置 */}}
      />
    </div>
  );
}

// components/visualization/TokenFlow.tsx
/**
 * Token 流向可视化 - 展示 Token 的使用情况
 */
export function TokenFlow({ data }: TokenFlowProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [granularity, setGranularity] = useState<Granularity>('hour');
  
  // 聚合数据
  const aggregated = useMemo(() => {
    return aggregateTokenData(data, timeRange, granularity);
  }, [data, timeRange, granularity]);
  
  return (
    <div className="token-flow">
      <Card>
        <CardHeader>
          <CardTitle>Token 使用流向</CardTitle>
          <CardDescription>
            监控 Token 的消耗模式和成本分析
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <div className="controls">
            <TimeRangeSelector
              value={timeRange}
              onChange={setTimeRange}
              options={['1h', '24h', '7d', '30d']}
            />
            
            <GranularitySelector
              value={granularity}
              onChange={setGranularity}
              options={['minute', 'hour', 'day']}
            />
          </div>
          
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={aggregated}>
              <defs>
                <linearGradient id="promptGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="completionGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={(ts) => formatDate(ts, granularity)}
              />
              <YAxis />
              <Tooltip 
                content={<TokenTooltip />}
              />
              <Legend />
              
              <Area
                type="monotone"
                dataKey="promptTokens"
                name="Prompt Tokens"
                stroke="#3b82f6"
                fill="url(#promptGradient)"
                stackId="1"
              />
              
              <Area
                type="monotone"
                dataKey="completionTokens"
                name="Completion Tokens"
                stroke="#10b981"
                fill="url(#completionGradient)"
                stackId="1"
              />
            </AreaChart>
          </ResponsiveContainer>
          
          <TokenStatsSummary data={aggregated} />
        </CardContent>
      </Card>
    </div>
  );
}

// components/visualization/ContextWindowViewer.tsx
/**
 * 上下文窗口可视化 - 展示上下文组成
 */
export function ContextWindowViewer({ window }: ContextWindowViewerProps) {
  const [selectedFragment, setSelectedFragment] = useState<string | null>(null);
  const [hoveredType, setHoveredType] = useState<string | null>(null);
  
  // 按类型分组
  const byType = useMemo(() => {
    const groups = new Map<string, ContextFragment[]>();
    for (const fragment of window.fragments) {
      if (!groups.has(fragment.type)) {
        groups.set(fragment.type, []);
      }
      groups.get(fragment.type)!.push(fragment);
    }
    return groups;
  }, [window.fragments]);
  
  // 计算各类型占比
  const typeStats = useMemo(() => {
    return Array.from(byType.entries()).map(([type, fragments]) => ({
      type,
      count: fragments.length,
      tokens: fragments.reduce((sum, f) => sum + f.metadata.tokens, 0),
      percentage: fragments.reduce((sum, f) => sum + f.metadata.tokens, 0) / window.currentTokens * 100,
      color: getFragmentTypeColor(type)
    }));
  }, [byType, window.currentTokens]);
  
  return (
    <div className="context-window-viewer">
      <Card>
        <CardHeader>
          <CardTitle>上下文窗口组成</CardTitle>
          <div className="window-stats">
            <Badge variant="outline">
              {window.currentTokens.toLocaleString()} / {window.maxTokens.toLocaleString()} tokens
            </Badge>
            <Badge variant="outline">
              压缩率: {(window.compressionRatio * 100).toFixed(1)}%
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent>
          {/* 组成饼图 */}
          <div className="composition-chart">
            <ResponsiveContainer width={300} height={300}>
              <PieChart>
                <Pie
                  data={typeStats}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="tokens"
                  onMouseEnter={(_, index) => setHoveredType(typeStats[index].type)}
                  onMouseLeave={() => setHoveredType(null)}
                >
                  {typeStats.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.color}
                      opacity={hoveredType === null || hoveredType === entry.type ? 1 : 0.3}
                    />
                  ))}
                </Pie>
                <Tooltip content={<TypeTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            
            <div className="type-legend">
              {typeStats.map(stat => (
                <div 
                  key={stat.type}
                  className={cn("legend-item", hoveredType === stat.type && "highlighted")}
                  onMouseEnter={() => setHoveredType(stat.type)}
                  onMouseLeave={() => setHoveredType(null)}
                >
                  <div className="color-dot" style={{ backgroundColor: stat.color }} />
                  <span className="type-name">{formatFragmentType(stat.type)}</span>
                  <span className="token-count">{stat.tokens.toLocaleString()} tokens</span>
                  <span className="percentage">{stat.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* 片段列表 */}
          <div className="fragment-list">
            <h4>片段详情</h4>
            {window.fragments.map((fragment, index) => (
              <ContextFragmentCard
                key={fragment.id}
                fragment={fragment}
                index={index}
                isSelected={selectedFragment === fragment.id}
                isDimmed={hoveredType !== null && hoveredType !== fragment.type}
                onClick={() => setSelectedFragment(fragment.id)}
              />
            ))}
          </div>
          
          {/* 选中片段详情 */}
          {selectedFragment && (
            <FragmentDetailModal
              fragment={window.fragments.find(f => f.id === selectedFragment)!}
              onClose={() => setSelectedFragment(null)}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// components/visualization/VectorSpaceExplorer.tsx
/**
 * 向量空间探索器 - 可视化高维向量
 */
export function VectorSpaceExplorer({ vectors, labels }: VectorSpaceExplorerProps) {
  const [projection, setProjection] = useState<'pca' | 'tsne' | 'umap'>('umap');
  const [dimensions, setDimensions] = useState<2 | 3>(2);
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null);
  
  // 降维
  const projected = useMemo(() => {
    switch (projection) {
      case 'pca':
        return computePCA(vectors, dimensions);
      case 'tsne':
        return computeTSNE(vectors, dimensions);
      case 'umap':
        return computeUMAP(vectors, dimensions);
      default:
        return computePCA(vectors, dimensions);
    }
  }, [vectors, projection, dimensions]);
  
  // 聚类
  const clusters = useMemo(() => {
    return performClustering(projected, 5);
  }, [projected]);
  
  if (dimensions === 3) {
    return (
      <div className="vector-space-3d">
        <Canvas>
          <OrbitControls />
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} />
          
          {projected.map((point, i) => (
            <mesh
              key={i}
              position={[point[0], point[1], point[2]]}
              onClick={() => setSelectedPoint(i)}
            >
              <sphereGeometry args={[0.05, 16, 16]} />
              <meshStandardMaterial 
                color={getClusterColor(clusters[i])}
                opacity={selectedPoint === null || selectedPoint === i ? 1 : 0.3}
              />
            </mesh>
          ))}
        </Canvas>
        
        <VectorControls
          projection={projection}
          onProjectionChange={setProjection}
          dimensions={dimensions}
          onDimensionsChange={setDimensions}
        />
      </div>
    );
  }
  
  return (
    <div className="vector-space-2d">
      <ResponsiveContainer width="100%" height={600}>
        <ScatterChart>
          <CartesianGrid />
          <XAxis type="number" dataKey="x" name="X" />
          <YAxis type="number" dataKey="y" name="Y" />
          <Tooltip 
            cursor={{ strokeDasharray: '3 3' }}
            content={<VectorTooltip labels={labels} />}
          />
          
          {/* 按聚类绘制 */}
          {Array.from(new Set(clusters)).map(clusterId => (
            <Scatter
              key={clusterId}
              name={`Cluster ${clusterId}`}
              data={projected
                .map((p, i) => ({ x: p[0], y: p[1], index: i }))
                .filter((_, i) => clusters[i] === clusterId)
              }
              fill={getClusterColor(clusterId)}
              opacity={selectedPoint === null ? 0.7 : 0.3}
              onClick={(data) => setSelectedPoint(data.index)}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
      
      <VectorControls
        projection={projection}
        onProjectionChange={setProjection}
        dimensions={dimensions}
        onDimensionsChange={setDimensions}
      />
      
      {selectedPoint !== null && (
        <VectorDetailPanel
          vector={vectors[selectedPoint]}
          label={labels?.[selectedPoint]}
          similar={findSimilarVectors(vectors, selectedPoint, 5)}
          onClose={() => setSelectedPoint(null)}
        />
      )}
    </div>
  );
}

// components/visualization/KnowledgeGraph.tsx
/**
 * 知识图谱可视化
 */
export function KnowledgeGraph({ knowledgeBase }: KnowledgeGraphProps) {
  const [filter, setFilter] = useState<string>('');
  const [layout, setLayout] = useState<'force' | 'hierarchical' | 'circular'>('force');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  
  // 构建图数据
  const graphData = useMemo(() => {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    
    // 添加文档节点
    for (const source of knowledgeBase.sources) {
      nodes.push({
        id: source.id,
        type: 'document',
        label: source.location.split('/').pop() || source.location,
        size: Math.sqrt(source.documentCount) * 5 + 10,
        color: '#3b82f6'
      });
    }
    
    // 添加实体节点（从索引中提取）
    const entities = extractEntities(knowledgeBase);
    for (const entity of entities) {
      nodes.push({
        id: entity.id,
        type: 'entity',
        label: entity.name,
        size: entity.mentionCount * 3 + 8,
        color: getEntityTypeColor(entity.type)
      });
      
      // 连接到相关文档
      for (const docId of entity.sourceIds) {
        edges.push({
          source: docId,
          target: entity.id,
          type: 'contains',
          strength: entity.mentionCount / 10
        });
      }
    }
    
    // 添加关系边
    for (const relation of extractRelations(knowledgeBase)) {
      edges.push({
        source: relation.from,
        target: relation.to,
        type: relation.type,
        label: relation.label,
        strength: relation.confidence
      });
    }
    
    return { nodes, edges };
  }, [knowledgeBase]);
  
  // 过滤
  const filtered = useMemo(() => {
    if (!filter) return graphData;
    
    const filteredNodes = graphData.nodes.filter(n => 
      n.label.toLowerCase().includes(filter.toLowerCase())
    );
    
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = graphData.edges.filter(e => 
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );
    
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, filter]);
  
  return (
    <div className="knowledge-graph">
      <Card>
        <CardHeader>
          <CardTitle>知识图谱</CardTitle>
          <div className="graph-controls">
            <Input
              placeholder="搜索节点..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            
            <Select value={layout} onValueChange={(v) => setLayout(v as any)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="force">力导向</SelectItem>
                <SelectItem value="hierarchical">层次</SelectItem>
                <SelectItem value="circular">圆形</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        
        <CardContent>
          <GraphCanvas
            data={filtered}
            layout={layout}
            onNodeClick={setSelectedNode}
            selectedNode={selectedNode}
          />
          
          <GraphLegend />
        </CardContent>
      </Card>
      
      {selectedNode && (
        <NodeDetailPanel
          node={graphData.nodes.find(n => n.id === selectedNode)!}
          relatedEdges={graphData.edges.filter(e => 
            e.source === selectedNode || e.target === selectedNode
          )}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
```

### 4.3 仪表盘组件

```typescript
// components/dashboard/SystemDashboard.tsx
/**
 * 系统仪表盘 - 全局状态监控
 */
export function SystemDashboard() {
  const { data: metrics, isLoading } = useSystemMetrics();
  const [timeRange, setTimeRange] = useState('1h');
  
  if (isLoading) return <DashboardSkeleton />;
  
  return (
    <div className="system-dashboard">
      {/* 关键指标卡片 */}
      <div className="kpi-grid">
        <KPICard
          title="活跃会话"
          value={metrics.activeSessions}
          change={metrics.sessionChange}
          icon={<MessageSquare />}
          color="blue"
        />
        
        <KPICard
          title="Token 消耗"
          value={formatNumber(metrics.tokenUsage)}
          change={metrics.tokenChange}
          icon={<Zap />}
          color="green"
          subtitle="本月累计"
        />
        
        <KPICard
          title="平均延迟"
          value={`${metrics.avgLatency}ms`}
          change={metrics.latencyChange}
          icon={<Clock />}
          color="yellow"
          trend={metrics.latencyChange > 0 ? 'down' : 'up'}
        />
        
        <KPICard
          title="错误率"
          value={`${(metrics.errorRate * 100).toFixed(2)}%`}
          change={metrics.errorChange}
          icon={<AlertTriangle />}
          color={metrics.errorRate > 0.05 ? 'red' : 'green'}
          trend={metrics.errorChange > 0 ? 'down' : 'up'}
        />
      </div>
      
      {/* 图表区域 */}
      <div className="charts-grid">
        <Card className="chart-card">
          <CardHeader>
            <CardTitle>请求趋势</CardTitle>
            <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          </CardHeader>
          <CardContent>
            <RequestTrendChart data={metrics.requestTrend} />
          </CardContent>
        </Card>
        
        <Card className="chart-card">
          <CardHeader>
            <CardTitle>模型分布</CardTitle>
          </CardHeader>
          <CardContent>
            <ModelDistributionChart data={metrics.modelDistribution} />
          </CardContent>
        </Card>
        
        <Card className="chart-card wide">
          <CardHeader>
            <CardTitle>实时流量</CardTitle>
          </CardHeader>
          <CardContent>
            <RealtimeTrafficChart />
          </CardContent>
        </Card>
      </div>
      
      {/* 底部区域 */}
      <div className="bottom-grid">
        <RecentSessionsList />
        <SystemHealthStatus />
        <ActiveAlerts />
      </div>
    </div>
  );
}

// components/dashboard/AgentPerformanceDashboard.tsx
/**
 * Agent 性能仪表盘
 */
export function AgentPerformanceDashboard({ agentId }: { agentId: string }) {
  const { data: performance } = useAgentPerformance(agentId);
  const [comparisonPeriod, setComparisonPeriod] = useState('7d');
  
  return (
    <div className="agent-performance-dashboard">
      <div className="performance-header">
        <AgentInfo agentId={agentId} />
        
        <ComparisonSelector
          value={comparisonPeriod}
          onChange={setComparisonPeriod}
          options={['24h', '7d', '30d', '90d']}
        />
      </div>
      
      <div className="performance-metrics">
        <MetricCard
          title="响应质量"
          value={performance.qualityScore}
          max={100}
          chart={<Sparkline data={performance.qualityHistory} />}
        />
        
        <MetricCard
          title="用户满意度"
          value={performance.satisfactionRate}
          format="percent"
          chart={<Sparkline data={performance.satisfactionHistory} />}
        />
        
        <MetricCard
          title="成本效率"
          value={performance.costPerSession}
          format="currency"
          trend={performance.costTrend}
        />
      </div>
      
      <div className="performance-details">
        <Card>
          <CardHeader>
            <CardTitle>响应时间分布</CardTitle>
          </CardHeader>
          <CardContent>
            <LatencyDistributionChart data={performance.latencyDistribution} />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>工具调用分析</CardTitle>
          </CardHeader>
          <CardContent>
            <ToolUsageChart data={performance.toolUsage} />
          </CardContent>
        </Card>
      </div>
      
      <div className="feedback-analysis">
        <Card>
          <CardHeader>
            <CardTitle>用户反馈分析</CardTitle>
          </CardHeader>
          <CardContent>
            <FeedbackWordCloud feedback={performance.feedback} />
            <FeedbackTrendChart data={performance.feedbackTrend} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

---

## 第五部分：性能优化与行业领先特性

### 5.1 虚拟化与增量渲染

```typescript
// components/virtualization/VirtualMessageList.tsx
/**
 * 虚拟消息列表 - 处理大量消息
 */
export function VirtualMessageList({ messages }: VirtualMessageListProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  
  // 使用虚拟列表
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: useCallback((index: number) => {
      // 根据消息内容估算高度
      const message = messages[index];
      const baseHeight = 80;
      const contentHeight = Math.ceil(message.content.length / 50) * 20;
      return Math.min(baseHeight + contentHeight, 400);
    }, [messages]),
    overscan: 5
  });
  
  // 滚动到最新消息
  useEffect(() => {
    if (messages.length > 0) {
      virtualizer.scrollToIndex(messages.length - 1, { align: 'end' });
    }
  }, [messages.length]);
  
  return (
    <div ref={parentRef} className="virtual-message-list">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative'
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`
            }}
          >
            <MessageBubble
              message={messages[virtualItem.index]}
              isNew={virtualItem.index === messages.length - 1}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// hooks/useIncrementalRender.ts
/**
 * 增量渲染 Hook
 */
export function useIncrementalRender<T>(
  items: T[],
  batchSize: number = 10,
  delay: number = 16
): T[] {
  const [rendered, setRendered] = useState<T[]>([]);
  const [index, setIndex] = useState(0);
  
  useEffect(() => {
    if (index >= items.length) return;
    
    const timer = setTimeout(() => {
      const next = Math.min(index + batchSize, items.length);
      setRendered(items.slice(0, next));
      setIndex(next);
    }, delay);
    
    return () => clearTimeout(timer);
  }, [index, items, batchSize, delay]);
  
  // 重置当 items 变化
  useEffect(() => {
    setRendered(items.slice(0, Math.min(batchSize, items.length)));
    setIndex(Math.min(batchSize, items.length));
  }, [items.length]);
  
  return rendered;
}
```

### 5.2 智能预加载

```typescript
// hooks/usePredictivePrefetch.ts
/**
 * 预测性预加载
 */
export function usePredictivePrefetch() {
  const router = useRouter();
  const prefetchQueue = useRef<string[]>([]);
  
  // 基于用户行为预测下一步
  const predictNextRoutes = useCallback((currentRoute: string, history: string[]) => {
    // 简单的马尔可夫链预测
    const transitions = new Map<string, Map<string, number>>();
    
    for (let i = 0; i < history.length - 1; i++) {
      const from = history[i];
      const to = history[i + 1];
      
      if (!transitions.has(from)) {
        transitions.set(from, new Map());
      }
      
      const counts = transitions.get(from)!;
      counts.set(to, (counts.get(to) || 0) + 1);
    }
    
    const currentTransitions = transitions.get(currentRoute);
    if (!currentTransitions) return [];
    
    // 返回概率最高的几个
    return Array.from(currentTransitions.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([route]) => route);
  }, []);
  
  // 预加载预测的路由
  const prefetchPredicted = useCallback((currentRoute: string, history: string[]) => {
    const predicted = predictNextRoutes(currentRoute, history);
    
    for (const route of predicted) {
      if (!prefetchQueue.current.includes(route)) {
        prefetchQueue.current.push(route);
        router.prefetch(route);
      }
    }
    
    // 限制队列大小
    if (prefetchQueue.current.length > 10) {
      prefetchQueue.current = prefetchQueue.current.slice(-10);
    }
  }, [predictNextRoutes, router]);
  
  return { prefetchPredicted };
}

// hooks/useDataPrefetch.ts
/**
 * 数据预加载
 */
export function useDataPrefetch<T>(
  queryKey: string,
  fetcher: () => Promise<T>,
  condition: boolean
) {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    if (!condition) return;
    
    // 在后台预加载
    const prefetch = async () => {
      await queryClient.prefetchQuery({
        queryKey: [queryKey],
        queryFn: fetcher,
        staleTime: 5 * 60 * 1000 // 5分钟
      });
    };
    
    // 使用 requestIdleCallback 在空闲时预加载
    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(() => prefetch(), { timeout: 2000 });
    } else {
      setTimeout(prefetch, 100);
    }
  }, [condition, queryKey, fetcher, queryClient]);
}
```

### 5.3 边缘计算优化

```typescript
// edge/EdgeWorker.ts
/**
 * 边缘计算 Worker
 */
export class EdgeWorker {
  private cache: EdgeCache;
  
  constructor() {
    this.cache = new EdgeCache();
  }
  
  /**
   * 边缘渲染
   */
  async renderAtEdge(request: RenderRequest): Promise<RenderResult> {
    // 检查缓存
    const cached = await this.cache.get(request.cacheKey);
    if (cached) return cached;
    
    // 执行轻量级渲染
    const result = await this.executeRender(request);
    
    // 缓存结果
    await this.cache.set(request.cacheKey, result, request.ttl);
    
    return result;
  }
  
  /**
   * 边缘数据聚合
   */
  async aggregateAtEdge(sources: DataSource[]): Promise<AggregatedData> {
    // 并行获取数据
    const results = await Promise.all(
      sources.map(async source => {
        // 检查边缘缓存
        const cached = await this.cache.get(source.key);
        if (cached) return cached;
        
        // 从源获取
        const data = await fetch(source.url, {
          cf: {
            cacheTtl: source.cacheTtl,
            cacheEverything: true
          }
        });
        
        const result = await data.json();
        
        // 缓存
        await this.cache.set(source.key, result, source.cacheTtl);
        
        return result;
      })
    );
    
    // 合并结果
    return this.mergeResults(results);
  }
}

// 边缘缓存实现
class EdgeCache {
  async get(key: string): Promise<any | null> {
    // 使用 Cloudflare Cache API
    const cache = caches.default;
    const request = new Request(`https://cache.internal/${key}`);
    const response = await cache.match(request);
    
    if (response) {
      return response.json();
    }
    
    return null;
  }
  
  async set(key: string, value: any, ttl: number): Promise<void> {
    const cache = caches.default;
    const request = new Request(`https://cache.internal/${key}`);
    const response = new Response(JSON.stringify(value), {
      headers: {
        'Cache-Control': `max-age=${ttl}`,
        'Content-Type': 'application/json'
      }
    });
    
    await cache.put(request, response);
  }
}
```

---

## 总结

这份深度架构涵盖了四个核心方向：

### 上下文管理
- **智能窗口管理**：动态压缩、优先级排序、语义保留
- **多级缓存**：Hot/Warm/Cold 分层存储
- **溢出处理**：智能驱逐和压缩策略
- **语义结构**：主题段、实体引用、意图追踪

### 向量化检索
- **多模型嵌入**：OpenAI、本地模型、多模态
- **混合搜索**：向量 + 关键词 + 重排序
- **智能分块**：固定、语义、层次分块
- **高性能索引**：Qdrant/Pinecone 集成

### 数据模型
- **完整实体关系**：用户、会话、消息、Agent、插件、知识库
- **灵活 Schema**：JSONB 扩展、向量字段
- **审计追踪**：完整操作日志
- **性能优化**：分区表、全文索引、向量索引

### 可视化界面
- **关系图谱**：D3.js 力导向图
- **数据流向**：Token 使用、请求趋势
- **向量空间**：PCA/t-SNE/UMAP 降维
- **知识图谱**：实体关系可视化
- **仪表盘**：KPI、实时监控、性能分析

### 行业领先特性
1. **预测性预加载**：基于行为的智能预取
2. **边缘计算**：CDN 级别的渲染和数据聚合
3. **虚拟化渲染**：10万+ 消息流畅滚动
4. **增量加载**：渐进式内容展示
5. **实时流式**：WebSocket + SSE 双通道

这套架构不仅功能完善，更在性能、扩展性和用户体验上达到行业前列水平。

---

*文档版本: v2.0*
*更新日期: 2026-04-28*
*作者: 小R (AI Assistant)*
