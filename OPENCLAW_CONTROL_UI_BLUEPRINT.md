# OpenClaw Control UI - 完整实现蓝图

## 第一部分：核心架构设计

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Control UI                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web App    │  │   Desktop    │  │   Mobile     │         │
│  │   (React)    │  │   (Electron) │  │   (React     │         │
│  │              │  │              │  │    Native)   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐          │
│  │              Unified API Client                    │          │
│  │         (REST + WebSocket + SSE)                  │          │
│  └─────────────────────────┬─────────────────────────┘          │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Gateway                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   REST API   │  │  WebSocket   │  │    SSE       │         │
│  │   Layer      │  │   Layer      │  │   Layer      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│  ┌─────────────────────────┴─────────────────────────┐          │
│  │              Core Controller                       │          │
│  │         (Auth + Routing + Middleware)             │          │
│  └─────────────────────────┬─────────────────────────┘          │
│                            │                                    │
│         ┌──────────────────┼──────────────────┐                 │
│         ▼                  ▼                  ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Session    │  │   Agent      │  │   Plugin     │         │
│  │   Manager    │  │   Manager    │  │   Manager    │         │
│  │              │  │              │  │              │         │
│  │ - CRUD       │  │ - Lifecycle  │  │ - Install    │         │
│  │ - Events     │  │ - Messaging  │  │ - Configure  │         │
│  │ - State      │  │ - Routing    │  │ - Monitor    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Memory     │  │   Tool       │  │   Config     │         │
│  │   Manager    │  │   Registry   │  │   Manager    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈选择

| 层级 | 技术 | 理由 |
|------|------|------|
| **Frontend** | React 18 + TypeScript | 类型安全，生态丰富 |
| **State Management** | Zustand + TanStack Query | 轻量，服务器状态同步 |
| **UI Components** | Radix UI + Tailwind CSS | 可访问性，定制灵活 |
| **Real-time** | Socket.io Client | 双向通信，自动重连 |
| **Desktop** | Electron + Vite | 快速打包，共享代码 |
| **Mobile** | React Native (Expo) | 跨平台，热更新 |
| **Backend** | Node.js + Fastify | 高性能，低开销 |
| **Database** | SQLite (local) + PostgreSQL (cloud) | 灵活部署 |
| **Cache** | Redis | 会话状态，实时数据 |

---

## 第二部分：前端详细设计

### 2.1 页面路由结构

```typescript
// router.config.ts
export const routes = [
  {
    path: '/',
    component: 'Layout',
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: 'DashboardPage',
        icon: 'LayoutDashboard',
        description: '系统概览和快速操作'
      },
      {
        path: 'sessions',
        name: 'Sessions',
        component: 'SessionsPage',
        icon: 'MessageSquare',
        description: '会话管理和监控'
      },
      {
        path: 'sessions/:id',
        name: 'SessionDetail',
        component: 'SessionDetailPage',
        hidden: true
      },
      {
        path: 'agents',
        name: 'Agents',
        component: 'AgentsPage',
        icon: 'Bot',
        description: '智能体管理和配置'
      },
      {
        path: 'agents/:id',
        name: 'AgentDetail',
        component: 'AgentDetailPage',
        hidden: true
      },
      {
        path: 'plugins',
        name: 'Plugins',
        component: 'PluginsPage',
        icon: 'Puzzle',
        description: '插件市场和已安装插件'
      },
      {
        path: 'plugins/:id',
        name: 'PluginDetail',
        component: 'PluginDetailPage',
        hidden: true
      },
      {
        path: 'memory',
        name: 'Memory',
        component: 'MemoryPage',
        icon: 'Brain',
        description: '记忆管理和搜索'
      },
      {
        path: 'tools',
        name: 'Tools',
        component: 'ToolsPage',
        icon: 'Wrench',
        description: '工具注册和配置'
      },
      {
        path: 'settings',
        name: 'Settings',
        component: 'SettingsPage',
        icon: 'Settings',
        description: '系统设置和配置'
      },
      {
        path: 'logs',
        name: 'Logs',
        component: 'LogsPage',
        icon: 'ScrollText',
        description: '日志查看和分析'
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: 'AnalyticsPage',
        icon: 'BarChart3',
        description: '使用统计和分析'
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: 'LoginPage',
    public: true
  }
];
```

### 2.2 核心组件设计

#### 2.2.1 会话管理组件

```typescript
// components/sessions/SessionList.tsx
interface SessionListProps {
  filter?: SessionFilter;
  onSelect?: (session: Session) => void;
  selectedId?: string;
}

interface Session {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'error' | 'closed';
  agentId: string;
  agentName: string;
  lastMessage: Message | null;
  messageCount: number;
  createdAt: Date;
  updatedAt: Date;
  tags: string[];
}

// 会话列表组件
export function SessionList({ filter, onSelect, selectedId }: SessionListProps) {
  const { data: sessions, isLoading } = useSessions(filter);
  const { mutate: closeSession } = useCloseSession();
  const { mutate: renameSession } = useRenameSession();
  
  return (
    <div className="session-list">
      <SessionListHeader 
        total={sessions?.length || 0}
        active={sessions?.filter(s => s.status === 'active').length || 0}
      />
      
      <div className="session-items">
        {sessions?.map(session => (
          <SessionCard
            key={session.id}
            session={session}
            isSelected={session.id === selectedId}
            onClick={() => onSelect?.(session)}
            onClose={() => closeSession(session.id)}
            onRename={(name) => renameSession({ id: session.id, name })}
          />
        ))}
      </div>
      
      {isLoading && <SessionListSkeleton />}
    </div>
  );
}

// 会话卡片组件
export function SessionCard({ 
  session, 
  isSelected, 
  onClick,
  onClose,
  onRename 
}: SessionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  
  return (
    <div 
      className={cn(
        "session-card",
        isSelected && "session-card--selected",
        `session-card--${session.status}`
      )}
      onClick={onClick}
    >
      <SessionStatusIndicator status={session.status} />
      
      <div className="session-card__content">
        {isEditing ? (
          <InlineEdit 
            value={session.name}
            onSave={onRename}
            onCancel={() => setIsEditing(false)}
          />
        ) : (
          <h4 onDoubleClick={() => setIsEditing(true)}>
            {session.name}
          </h4>
        )}
        
        <div className="session-card__meta">
          <AgentBadge agentId={session.agentId} name={session.agentName} />
          <MessageCount count={session.messageCount} />
          <TimeAgo date={session.updatedAt} />
        </div>
        
        {session.lastMessage && (
          <p className="session-card__preview">
            {truncate(session.lastMessage.content, 100)}
          </p>
        )}
      </div>
      
      <SessionActions 
        onClose={onClose}
        onRename={() => setIsEditing(true)}
      />
    </div>
  );
}
```

#### 2.2.2 实时消息组件

```typescript
// components/chat/MessageStream.tsx
interface MessageStreamProps {
  sessionId: string;
  onError?: (error: Error) => void;
}

export function MessageStream({ sessionId, onError }: MessageStreamProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  
  // 使用 WebSocket 接收实时消息
  const { messages, isConnected, error } = useSessionStream(sessionId);
  
  // 自动滚动到底部
  useEffect(() => {
    if (isAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isAutoScroll]);
  
  // 处理滚动事件
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setIsAutoScroll(isNearBottom);
  };
  
  if (error) {
    return <StreamError error={error} onRetry={() => window.location.reload()} />;
  }
  
  return (
    <div className="message-stream" onScroll={handleScroll}>
      <ConnectionStatus isConnected={isConnected} />
      
      <div className="messages">
        {messages.map((message, index) => (
          <MessageBubble
            key={message.id || index}
            message={message}
            isLast={index === messages.length - 1}
          />
        ))}
        
        {messages[messages.length - 1]?.role === 'user' && (
          <TypingIndicator />
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {!isAutoScroll && (
        <ScrollToBottomButton 
          onClick={() => {
            setIsAutoScroll(true);
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
          }}
        />
      )}
    </div>
  );
}

// 消息气泡组件
export function MessageBubble({ message, isLast }: MessageBubbleProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showActions, setShowActions] = useState(false);
  
  return (
    <div 
      className={cn(
        "message-bubble",
        `message-bubble--${message.role}`,
        isLast && "message-bubble--last"
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <Avatar role={message.role} agentId={message.agentId} />
      
      <div className="message-bubble__content">
        <MessageHeader 
          role={message.role}
          timestamp={message.timestamp}
          model={message.model}
        />
        
        <MessageBody 
          content={message.content}
          isExpanded={isExpanded}
          onToggle={() => setIsExpanded(!isExpanded)}
        />
        
        {message.toolCalls && (
          <ToolCallList toolCalls={message.toolCalls} />
        )}
        
        {message.attachments && (
          <AttachmentList attachments={message.attachments} />
        )}
        
        {showActions && (
          <MessageActions 
            onCopy={() => copyToClipboard(message.content)}
            onEdit={() => {/* 编辑消息 */}}
            onDelete={() => {/* 删除消息 */}}
          />
        )}
      </div>
    </div>
  );
}
```

#### 2.2.3 智能体配置组件

```typescript
// components/agents/AgentConfigurator.tsx
interface AgentConfiguratorProps {
  agentId: string;
  onSave?: (config: AgentConfig) => void;
}

export function AgentConfigurator({ agentId, onSave }: AgentConfiguratorProps) {
  const { data: agent, isLoading } = useAgent(agentId);
  const { mutate: updateAgent } = useUpdateAgent();
  
  const form = useForm<AgentConfig>({
    defaultValues: agent?.config
  });
  
  if (isLoading) return <AgentConfiguratorSkeleton />;
  
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSave || updateAgent)}>
        <Tabs defaultValue="basic">
          <TabsList>
            <TabsTrigger value="basic">基本信息</TabsTrigger>
            <TabsTrigger value="model">模型配置</TabsTrigger>
            <TabsTrigger value="tools">工具权限</TabsTrigger>
            <TabsTrigger value="memory">记忆设置</TabsTrigger>
            <TabsTrigger value="advanced">高级选项</TabsTrigger>
          </TabsList>
          
          <TabsContent value="basic">
            <BasicSettings form={form} />
          </TabsContent>
          
          <TabsContent value="model">
            <ModelSettings form={form} />
          </TabsContent>
          
          <TabsContent value="tools">
            <ToolPermissions form={form} />
          </TabsContent>
          
          <TabsContent value="memory">
            <MemorySettings form={form} />
          </TabsContent>
          
          <TabsContent value="advanced">
            <AdvancedSettings form={form} />
          </TabsContent>
        </Tabs>
        
        <div className="form-actions">
          <Button type="submit">保存配置</Button>
          <Button type="button" variant="outline" onClick={() => form.reset()}>
            重置
          </Button>
        </div>
      </form>
    </Form>
  );
}

// 模型配置子组件
function ModelSettings({ form }: { form: UseFormReturn<AgentConfig> }) {
  return (
    <div className="model-settings">
      <FormField
        control={form.control}
        name="model"
        render={({ field }) => (
          <FormItem>
            <FormLabel>模型选择</FormLabel>
            <Select onValueChange={field.onChange} defaultValue={field.value}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue placeholder="选择模型" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                <SelectItem value="claude-3-sonnet">Claude 3 Sonnet</SelectItem>
                <SelectItem value="qwen-max">Qwen Max</SelectItem>
                <SelectItem value="qwen-plus">Qwen Plus</SelectItem>
              </SelectContent>
            </Select>
            <FormDescription>
              选择智能体使用的基础模型
            </FormDescription>
          </FormItem>
        )}
      />
      
      <FormField
        control={form.control}
        name="temperature"
        render={({ field }) => (
          <FormItem>
            <FormLabel>温度 (Temperature)</FormLabel>
            <FormControl>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={[field.value]}
                onValueChange={([value]) => field.onChange(value)}
              />
            </FormControl>
            <FormDescription>
              控制输出的随机性: {field.value}
            </FormDescription>
          </FormItem>
        )}
      />
      
      <FormField
        control={form.control}
        name="maxTokens"
        render={({ field }) => (
          <FormItem>
            <FormLabel>最大 Token 数</FormLabel>
            <FormControl>
              <Input type="number" {...field} />
            </FormControl>
            <FormDescription>
              单次响应的最大长度
            </FormDescription>
          </FormItem>
        )}
      />
      
      <FormField
        control={form.control}
        name="systemPrompt"
        render={({ field }) => (
          <FormItem>
            <FormLabel>系统提示词</FormLabel>
            <FormControl>
              <Textarea 
                {...field} 
                rows={10}
                placeholder="输入系统提示词..."
              />
            </FormControl>
            <FormDescription>
              定义智能体的行为和角色
            </FormDescription>
          </FormItem>
        )}
      />
    </div>
  );
}
```

### 2.3 状态管理设计

```typescript
// stores/sessionStore.ts
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

interface SessionState {
  // 状态
  sessions: Session[];
  activeSessionId: string | null;
  isLoading: boolean;
  error: Error | null;
  
  // 动作
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
  removeSession: (id: string) => void;
  setActiveSession: (id: string | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: Error | null) => void;
  
  // 计算属性
  getActiveSession: () => Session | undefined;
  getSessionById: (id: string) => Session | undefined;
}

export const useSessionStore = create<SessionState>()(
  subscribeWithSelector((set, get) => ({
    sessions: [],
    activeSessionId: null,
    isLoading: false,
    error: null,
    
    setSessions: (sessions) => set({ sessions }),
    
    addSession: (session) => set((state) => ({
      sessions: [...state.sessions, session]
    })),
    
    updateSession: (id, updates) => set((state) => ({
      sessions: state.sessions.map(s => 
        s.id === id ? { ...s, ...updates } : s
      )
    })),
    
    removeSession: (id) => set((state) => ({
      sessions: state.sessions.filter(s => s.id !== id),
      activeSessionId: state.activeSessionId === id ? null : state.activeSessionId
    })),
    
    setActiveSession: (id) => set({ activeSessionId: id }),
    setLoading: (isLoading) => set({ isLoading }),
    setError: (error) => set({ error }),
    
    getActiveSession: () => {
      const { sessions, activeSessionId } = get();
      return sessions.find(s => s.id === activeSessionId);
    },
    
    getSessionById: (id) => {
      return get().sessions.find(s => s.id === id);
    }
  }))
);

// 实时同步 hook
export function useRealtimeSessions() {
  const { addSession, updateSession, removeSession } = useSessionStore();
  
  useEffect(() => {
    const socket = getSocket();
    
    socket.on('session:created', addSession);
    socket.on('session:updated', ({ id, updates }) => updateSession(id, updates));
    socket.on('session:deleted', ({ id }) => removeSession(id));
    
    return () => {
      socket.off('session:created');
      socket.off('session:updated');
      socket.off('session:deleted');
    };
  }, [addSession, updateSession, removeSession]);
}
```

---

## 第三部分：后端详细设计

### 3.1 API 设计

```typescript
// api/routes/sessions.ts
import { FastifyInstance } from 'fastify';

export async function sessionRoutes(fastify: FastifyInstance) {
  // 获取会话列表
  fastify.get('/sessions', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          status: { type: 'string', enum: ['active', 'idle', 'error', 'closed'] },
          agentId: { type: 'string' },
          tag: { type: 'string' },
          limit: { type: 'number', default: 20 },
          offset: { type: 'number', default: 0 }
        }
      },
      response: {
        200: {
          type: 'object',
          properties: {
            sessions: { type: 'array', items: { $ref: 'Session#' } },
            total: { type: 'number' },
            hasMore: { type: 'boolean' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const { status, agentId, tag, limit, offset } = request.query;
    
    const result = await sessionService.list({
      status,
      agentId,
      tag,
      limit,
      offset
    });
    
    return result;
  });
  
  // 创建会话
  fastify.post('/sessions', {
    schema: {
      body: {
        type: 'object',
        required: ['agentId'],
        properties: {
          agentId: { type: 'string' },
          name: { type: 'string' },
          initialMessage: { type: 'string' },
          metadata: { type: 'object' }
        }
      }
    }
  }, async (request, reply) => {
    const session = await sessionService.create(request.body);
    
    // 广播创建事件
    fastify.io.emit('session:created', session);
    
    reply.status(201);
    return session;
  });
  
  // 获取会话详情
  fastify.get('/sessions/:id', {
    schema: {
      params: {
        type: 'object',
        required: ['id'],
        properties: {
          id: { type: 'string' }
        }
      }
    }
  }, async (request, reply) => {
    const session = await sessionService.get(request.params.id);
    
    if (!session) {
      reply.status(404);
      throw new Error('Session not found');
    }
    
    return session;
  });
  
  // 发送消息（SSE 流式响应）
  fastify.post('/sessions/:id/messages', {
    schema: {
      params: {
        type: 'object',
        required: ['id'],
        properties: {
          id: { type: 'string' }
        }
      },
      body: {
        type: 'object',
        required: ['content'],
        properties: {
          content: { type: 'string' },
          attachments: { type: 'array' },
          options: { type: 'object' }
        }
      }
    }
  }, async (request, reply) => {
    const { id } = request.params;
    const { content, attachments, options } = request.body;
    
    // 设置 SSE 头
    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    });
    
    // 创建消息流
    const stream = await sessionService.sendMessage(id, {
      content,
      attachments,
      options
    });
    
    // 流式输出
    for await (const chunk of stream) {
      reply.raw.write(`data: ${JSON.stringify(chunk)}\n\n`);
    }
    
    reply.raw.end();
  });
  
  // WebSocket 处理实时消息
  fastify.io.on('connection', (socket) => {
    socket.on('session:subscribe', async (sessionId: string) => {
      socket.join(`session:${sessionId}`);
      
      // 发送当前会话状态
      const session = await sessionService.get(sessionId);
      socket.emit('session:state', session);
    });
    
    socket.on('session:send', async ({ sessionId, message }) => {
      const stream = await sessionService.sendMessage(sessionId, message);
      
      for await (const chunk of stream) {
        fastify.io.to(`session:${sessionId}`).emit('message:chunk', chunk);
      }
    });
  });
}
```

### 3.2 服务层设计

```typescript
// services/SessionService.ts
export class SessionService {
  constructor(
    private sessionRepo: SessionRepository,
    private agentService: AgentService,
    private llmRouter: LLMRouter,
    private eventBus: EventBus,
    private cache: CacheService
  ) {}
  
  async create(config: SessionConfig): Promise<Session> {
    // 验证 Agent 存在
    const agent = await this.agentService.get(config.agentId);
    if (!agent) {
      throw new Error(`Agent ${config.agentId} not found`);
    }
    
    // 创建会话
    const session = await this.sessionRepo.create({
      ...config,
      status: 'active',
      createdAt: new Date(),
      updatedAt: new Date()
    });
    
    // 缓存会话状态
    await this.cache.set(`session:${session.id}`, session, 3600);
    
    // 发布创建事件
    this.eventBus.publish('session:created', session);
    
    return session;
  }
  
  async sendMessage(
    sessionId: string, 
    message: UserMessage
  ): Promise<AsyncIterable<MessageChunk>> {
    // 获取会话
    const session = await this.get(sessionId);
    if (!session) {
      throw new Error('Session not found');
    }
    
    // 保存用户消息
    const userMessage = await this.saveMessage(sessionId, {
      role: 'user',
      content: message.content,
      timestamp: new Date()
    });
    
    // 获取历史消息
    const history = await this.getHistory(sessionId);
    
    // 获取 Agent 配置
    const agent = await this.agentService.get(session.agentId);
    
    // 创建 LLM 请求
    const request: LLMRequest = {
      model: agent.config.model,
      messages: [
        { role: 'system', content: agent.config.systemPrompt },
        ...history.map(m => ({ role: m.role, content: m.content })),
        { role: 'user', content: message.content }
      ],
      temperature: agent.config.temperature,
      maxTokens: agent.config.maxTokens,
      stream: true
    };
    
    // 流式生成响应
    const stream = this.llmRouter.stream(request);
    
    // 收集完整响应
    let fullResponse = '';
    
    // 转换并增强流
    return this.enhanceStream(stream, {
      onChunk: (chunk) => {
        fullResponse += chunk.content;
        
        // 实时广播
        this.eventBus.publish(`session:${sessionId}:chunk`, chunk);
      },
      onComplete: async () => {
        // 保存完整响应
        await this.saveMessage(sessionId, {
          role: 'assistant',
          content: fullResponse,
          timestamp: new Date(),
          model: agent.config.model
        });
        
        // 更新会话状态
        await this.sessionRepo.update(sessionId, {
          lastMessageAt: new Date(),
          messageCount: session.messageCount + 2
        });
      }
    });
  }
  
  private async enhanceStream(
    stream: AsyncIterable<LLMChunk>,
    handlers: StreamHandlers
  ): AsyncIterable<MessageChunk> {
    for await (const chunk of stream) {
      const enhanced: MessageChunk = {
        ...chunk,
        timestamp: new Date(),
        metadata: {
          latency: Date.now() - chunk.startTime,
          tokens: chunk.tokenCount
        }
      };
      
      handlers.onChunk?.(enhanced);
      yield enhanced;
    }
    
    handlers.onComplete?.();
  }
}
```

### 3.3 中间件设计

```typescript
// middleware/auth.ts
export async function authMiddleware(
  request: FastifyRequest,
  reply: FastifyReply
) {
  // 跳过公开路由
  if (request.routeOptions.config?.public) {
    return;
  }
  
  // 获取 Token
  const token = request.headers.authorization?.replace('Bearer ', '');
  
  if (!token) {
    reply.status(401);
    throw new Error('Authentication required');
  }
  
  // 验证 Token
  try {
    const decoded = await jwt.verify(token, process.env.JWT_SECRET);
    request.user = decoded;
  } catch (err) {
    reply.status(401);
    throw new Error('Invalid token');
  }
}

// middleware/rateLimit.ts
export function createRateLimit(options: RateLimitOptions) {
  const limiter = new RateLimiterRedis({
    storeClient: redisClient,
    keyPrefix: 'ratelimit',
    points: options.points,
    duration: options.duration
  });
  
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const key = `${request.user?.id || request.ip}:${request.routerPath}`;
    
    try {
      await limiter.consume(key);
    } catch (rejRes) {
      reply.status(429);
      reply.header('Retry-After', Math.round(rejRes.msBeforeNext / 1000));
      throw new Error('Rate limit exceeded');
    }
  };
}

// middleware/logging.ts
export async function loggingMiddleware(
  request: FastifyRequest,
  reply: FastifyReply
) {
  const startTime = Date.now();
  
  reply.raw.on('finish', () => {
    const duration = Date.now() - startTime;
    
    logger.info({
      method: request.method,
      url: request.url,
      statusCode: reply.statusCode,
      duration,
      userId: request.user?.id,
      ip: request.ip,
      userAgent: request.headers['user-agent']
    });
  });
}
```

---

## 第四部分：数据库设计

### 4.1 核心表结构

```sql
-- 会话表
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    agent_id UUID NOT NULL REFERENCES agents(id),
    user_id UUID NOT NULL REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    message_count INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}'
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_agent_id ON sessions(agent_id);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(50),
    tokens_used INTEGER,
    latency_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    parent_id UUID REFERENCES messages(id)
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Agent 表
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    avatar_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    config JSONB NOT NULL DEFAULT '{}',
    system_prompt TEXT,
    model VARCHAR(50) NOT NULL,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    tools TEXT[] DEFAULT '{}',
    memory_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_agents_status ON agents(status);

-- 插件表
CREATE TABLE plugins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    source VARCHAR(50) NOT NULL, -- 'marketplace', 'local', 'git'
    source_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'installed',
    config JSONB DEFAULT '{}',
    manifest JSONB NOT NULL,
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    preferences JSONB DEFAULT '{}',
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API 密钥表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '{}',
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 4.2 缓存设计

```typescript
// cache/sessionCache.ts
export class SessionCache {
  constructor(private redis: RedisClient) {}
  
  async get(sessionId: string): Promise<Session | null> {
    const data = await this.redis.get(`session:${sessionId}`);
    return data ? JSON.parse(data) : null;
  }
  
  async set(sessionId: string, session: Session, ttl: number = 3600): Promise<void> {
    await this.redis.setex(
      `session:${sessionId}`,
      ttl,
      JSON.stringify(session)
    );
  }
  
  async invalidate(sessionId: string): Promise<void> {
    await this.redis.del(`session:${sessionId}`);
  }
  
  async getActiveSessions(): Promise<Session[]> {
    const keys = await this.redis.keys('session:*');
    const sessions = await Promise.all(
      keys.map(key => this.redis.get(key))
    );
    return sessions
      .filter(Boolean)
      .map(s => JSON.parse(s!))
      .filter(s => s.status === 'active');
  }
}

// cache/agentCache.ts
export class AgentCache {
  constructor(private redis: RedisClient) {}
  
  async getConfig(agentId: string): Promise<AgentConfig | null> {
    const data = await this.redis.get(`agent:config:${agentId}`);
    return data ? JSON.parse(data) : null;
  }
  
  async setConfig(agentId: string, config: AgentConfig): Promise<void> {
    await this.redis.setex(
      `agent:config:${agentId}`,
      86400, // 24小时
      JSON.stringify(config)
    );
  }
  
  async getStats(agentId: string): Promise<AgentStats | null> {
    const data = await this.redis.hgetall(`agent:stats:${agentId}`);
    return data ? {
      totalRequests: parseInt(data.totalRequests || '0'),
      totalTokens: parseInt(data.totalTokens || '0'),
      avgLatency: parseFloat(data.avgLatency || '0'),
      errorRate: parseFloat(data.errorRate || '0')
    } : null;
  }
  
  async incrementStats(agentId: string, stats: Partial<AgentStats>): Promise<void> {
    const pipeline = this.redis.pipeline();
    
    if (stats.totalRequests) {
      pipeline.hincrby(`agent:stats:${agentId}`, 'totalRequests', stats.totalRequests);
    }
    if (stats.totalTokens) {
      pipeline.hincrby(`agent:stats:${agentId}`, 'totalTokens', stats.totalTokens);
    }
    
    await pipeline.exec();
  }
}
```

---

## 第五部分：实时通信设计

### 5.1 WebSocket 事件设计

```typescript
// events/sessionEvents.ts
export interface SessionEvents {
  // 客户端 -> 服务器
  'session:subscribe': (sessionId: string) => void;
  'session:unsubscribe': (sessionId: string) => void;
  'session:send': (data: {
    sessionId: string;
    content: string;
    attachments?: Attachment[];
  }) => void;
  'session:typing': (sessionId: string) => void;
  'session:read': (sessionId: string, messageId: string) => void;
  
  // 服务器 -> 客户端
  'session:state': (state: SessionState) => void;
  'message:chunk': (chunk: MessageChunk) => void;
  'message:complete': (message: Message) => void;
  'message:error': (error: { messageId: string; error: string }) => void;
  'agent:typing': (sessionId: string) => void;
  'session:updated': (updates: Partial<Session>) => void;
}

// events/systemEvents.ts
export interface SystemEvents {
  // 系统状态
  'system:status': (status: SystemStatus) => void;
  'system:metrics': (metrics: SystemMetrics) => void;
  
  // Agent 事件
  'agent:created': (agent: Agent) => void;
  'agent:updated': (agent: Agent) => void;
  'agent:deleted': (agentId: string) => void;
  'agent:status': (agentId: string, status: AgentStatus) => void;
  
  // 插件事件
  'plugin:installed': (plugin: Plugin) => void;
  'plugin:updated': (plugin: Plugin) => void;
  'plugin:uninstalled': (pluginId: string) => void;
  'plugin:error': (pluginId: string, error: string) => void;
}
```

### 5.2 SSE 流设计

```typescript
// streams/messageStream.ts
export class MessageStream {
  private encoder = new TextEncoder();
  
  constructor(
    private readable: ReadableStream,
    private onChunk?: (chunk: MessageChunk) => void
  ) {}
  
  async *generate(): AsyncGenerator<string> {
    const reader = this.readable.getReader();
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk: MessageChunk = {
          id: generateId(),
          content: value.content,
          role: 'assistant',
          timestamp: new Date(),
          metadata: {
            tokens: value.tokens,
            model: value.model,
            latency: value.latency
          }
        };
        
        this.onChunk?.(chunk);
        
        yield `data: ${JSON.stringify(chunk)}\n\n`;
      }
      
      // 发送完成标记
      yield `data: ${JSON.stringify({ type: 'done' })}\n\n`;
      
    } finally {
      reader.releaseLock();
    }
  }
}

// 使用示例
app.post('/api/sessions/:id/messages', async (req, res) => {
  const stream = await sessionService.sendMessage(req.params.id, req.body);
  
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  
  const messageStream = new MessageStream(stream, (chunk) => {
    // 可以在这里进行额外的处理
    console.log(`Chunk received: ${chunk.content.length} chars`);
  });
  
  for await (const data of messageStream.generate()) {
    res.write(data);
  }
  
  res.end();
});
```

---

## 第六部分：安全设计

### 6.1 认证授权

```typescript
// auth/strategies/jwt.ts
export class JWTStrategy implements AuthStrategy {
  constructor(private secret: string) {}
  
  async authenticate(token: string): Promise<User | null> {
    try {
      const decoded = jwt.verify(token, this.secret) as JWTPayload;
      
      // 验证 Token 是否被撤销
      const isRevoked = await tokenBlacklist.isRevoked(decoded.jti);
      if (isRevoked) return null;
      
      // 获取用户
      const user = await userService.getById(decoded.sub);
      return user;
    } catch {
      return null;
    }
  }
  
  async generateToken(user: User): Promise<string> {
    const payload: JWTPayload = {
      sub: user.id,
      username: user.username,
      role: user.role,
      jti: generateId(),
      iat: Date.now(),
      exp: Date.now() + 24 * 60 * 60 * 1000 // 24小时
    };
    
    return jwt.sign(payload, this.secret);
  }
}

// auth/permissions.ts
export const permissions = {
  session: {
    create: ['user', 'admin'],
    read: ['user', 'admin'],
    update: ['user', 'admin'],
    delete: ['admin'],
    manageAll: ['admin']
  },
  agent: {
    create: ['admin'],
    read: ['user', 'admin'],
    update: ['admin'],
    delete: ['admin'],
    configure: ['admin']
  },
  plugin: {
    install: ['admin'],
    uninstall: ['admin'],
    configure: ['admin'],
    view: ['user', 'admin']
  },
  system: {
    viewLogs: ['admin'],
    manageSettings: ['admin'],
    viewAnalytics: ['admin']
  }
};

// auth/guards.ts
export function requirePermission(resource: string, action: string) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user;
    if (!user) {
      reply.status(401);
      throw new Error('Authentication required');
    }
    
    const allowedRoles = permissions[resource]?.[action];
    if (!allowedRoles?.includes(user.role)) {
      reply.status(403);
      throw new Error('Permission denied');
    }
  };
}
```

### 6.2 输入验证

```typescript
// validation/schemas.ts
export const sessionSchemas = {
  create: z.object({
    agentId: z.string().uuid(),
    name: z.string().min(1).max(255).optional(),
    initialMessage: z.string().max(10000).optional(),
    metadata: z.record(z.unknown()).optional()
  }),
  
  sendMessage: z.object({
    content: z.string().min(1).max(100000),
    attachments: z.array(z.object({
      type: z.enum(['image', 'file', 'audio']),
      url: z.string().url(),
      name: z.string()
    })).max(10).optional(),
    options: z.object({
      temperature: z.number().min(0).max(2).optional(),
      maxTokens: z.number().min(1).max(100000).optional(),
      stream: z.boolean().optional()
    }).optional()
  })
};

// validation/sanitizer.ts
export function sanitizeInput(input: string): string {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: []
  });
}

export function validateFileUpload(file: FileUpload): void {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
  const maxSize = 10 * 1024 * 1024; // 10MB
  
  if (!allowedTypes.includes(file.mimetype)) {
    throw new Error('File type not allowed');
  }
  
  if (file.size > maxSize) {
    throw new Error('File too large');
  }
}
```

---

## 第七部分：部署架构

### 7.1 Docker 配置

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci

# 构建
COPY . .
RUN npm run build

# 生产镜像
FROM node:20-alpine

WORKDIR /app

# 只复制生产依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制构建产物
COPY --from=builder /app/dist ./dist

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

EXPOSE 3000

CMD ["node", "dist/main.js"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/openclaw
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=openclaw
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 7.2 Kubernetes 配置

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openclaw-ui
  labels:
    app: openclaw-ui
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openclaw-ui
  template:
    metadata:
      labels:
        app: openclaw-ui
    spec:
      containers:
      - name: app
        image: openclaw/ui:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: openclaw-ui-service
spec:
  selector:
    app: openclaw-ui
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: openclaw-ui-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt"
spec:
  tls:
  - hosts:
    - ui.openclaw.ai
    secretName: openclaw-ui-tls
  rules:
  - host: ui.openclaw.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: openclaw-ui-service
            port:
              number: 80
```

---

## 第八部分：监控与日志

### 8.1 指标收集

```typescript
// metrics/collector.ts
import { Counter, Histogram, Gauge, register } from 'prom-client';

// 请求计数器
export const httpRequestsTotal = new Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

// 请求延迟
export const httpRequestDuration = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route'],
  buckets: [0.1, 0.5, 1, 2, 5, 10]
});

// 活跃会话数
export const activeSessions = new Gauge({
  name: 'active_sessions',
  help: 'Number of active sessions'
});

// LLM 请求指标
export const llmRequestsTotal = new Counter({
  name: 'llm_requests_total',
  help: 'Total number of LLM requests',
  labelNames: ['model', 'status']
});

export const llmTokensUsed = new Counter({
  name: 'llm_tokens_used_total',
  help: 'Total number of tokens used',
  labelNames: ['model']
});

export const llmRequestDuration = new Histogram({
  name: 'llm_request_duration_seconds',
  help: 'LLM request duration',
  labelNames: ['model'],
  buckets: [1, 5, 10, 30, 60, 120]
});

// 暴露指标端点
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});
```

### 8.2 日志系统

```typescript
// logging/logger.ts
import winston from 'winston';

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { 
    service: 'openclaw-ui',
    version: process.env.APP_VERSION 
  },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error' 
    }),
    new winston.transports.File({ 
      filename: 'logs/combined.log' 
    })
  ]
});

// 请求日志中间件
export function requestLogger() {
  return async (req: FastifyRequest, reply: FastifyReply) => {
    const startTime = Date.now();
    
    reply.raw.on('finish', () => {
      const duration = Date.now() - startTime;
      
      logger.info('HTTP Request', {
        method: req.method,
        url: req.url,
        statusCode: reply.statusCode,
        duration,
        userId: req.user?.id,
        ip: req.ip,
        userAgent: req.headers['user-agent'],
        requestId: req.id
      });
    });
  };
}

// 性能日志
export function performanceLogger(label: string) {
  const start = Date.now();
  
  return {
    end: (metadata?: Record<string, any>) => {
      logger.info('Performance', {
        label,
        duration: Date.now() - start,
        ...metadata
      });
    }
  };
}
```

---

## 第九部分：测试策略

### 9.1 测试架构

```typescript
// tests/unit/sessionService.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SessionService } from '../../services/SessionService';

describe('SessionService', () => {
  let service: SessionService;
  let mockRepo: any;
  let mockAgentService: any;
  let mockLLMRouter: any;
  
  beforeEach(() => {
    mockRepo = {
      create: vi.fn(),
      get: vi.fn(),
      update: vi.fn()
    };
    
    mockAgentService = {
      get: vi.fn()
    };
    
    mockLLMRouter = {
      stream: vi.fn()
    };
    
    service = new SessionService(
      mockRepo,
      mockAgentService,
      mockLLMRouter,
      {} as any,
      {} as any
    );
  });
  
  describe('create', () => {
    it('should create a session with valid agent', async () => {
      const agent = { id: 'agent-1', config: { model: 'gpt-4' } };
      mockAgentService.get.mockResolvedValue(agent);
      mockRepo.create.mockResolvedValue({ id: 'session-1', ...agent });
      
      const result = await service.create({ agentId: 'agent-1' });
      
      expect(result.id).toBe('session-1');
      expect(mockRepo.create).toHaveBeenCalled();
    });
    
    it('should throw error for non-existent agent', async () => {
      mockAgentService.get.mockResolvedValue(null);
      
      await expect(service.create({ agentId: 'invalid' }))
        .rejects
        .toThrow('Agent invalid not found');
    });
  });
  
  describe('sendMessage', () => {
    it('should stream message response', async () => {
      const session = { id: 'session-1', agentId: 'agent-1' };
      mockRepo.get.mockResolvedValue(session);
      
      const chunks = [
        { content: 'Hello', tokens: 1 },
        { content: ' world', tokens: 1 }
      ];
      mockLLMRouter.stream.mockReturnValue(async function* () {
        for (const chunk of chunks) yield chunk;
      }());
      
      const stream = await service.sendMessage('session-1', {
        content: 'Hi'
      });
      
      const results = [];
      for await (const chunk of stream) {
        results.push(chunk);
      }
      
      expect(results).toHaveLength(2);
      expect(results[0].content).toBe('Hello');
    });
  });
});

// tests/integration/api.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createApp } from '../../app';

describe('API Integration', () => {
  let app: FastifyInstance;
  let authToken: string;
  
  beforeAll(async () => {
    app = await createApp({
      database: ':memory:', // 内存数据库
      redis: 'mock'
    });
    
    // 创建测试用户并获取 Token
    const response = await app.inject({
      method: 'POST',
      url: '/api/auth/register',
      payload: {
        username: 'test',
        email: 'test@example.com',
        password: 'password123'
      }
    });
    
    authToken = JSON.parse(response.payload).token;
  });
  
  afterAll(async () => {
    await app.close();
  });
  
  describe('Sessions API', () => {
    it('should create and retrieve a session', async () => {
      // 创建 Agent
      const agentRes = await app.inject({
        method: 'POST',
        url: '/api/agents',
        headers: { Authorization: `Bearer ${authToken}` },
        payload: {
          name: 'Test Agent',
          model: 'gpt-4o',
          systemPrompt: 'You are a test agent'
        }
      });
      
      const agent = JSON.parse(agentRes.payload);
      
      // 创建会话
      const sessionRes = await app.inject({
        method: 'POST',
        url: '/api/sessions',
        headers: { Authorization: `Bearer ${authToken}` },
        payload: { agentId: agent.id }
      });
      
      expect(sessionRes.statusCode).toBe(201);
      const session = JSON.parse(sessionRes.payload);
      expect(session.agentId).toBe(agent.id);
      
      // 获取会话
      const getRes = await app.inject({
        method: 'GET',
        url: `/api/sessions/${session.id}`,
        headers: { Authorization: `Bearer ${authToken}` }
      });
      
      expect(getRes.statusCode).toBe(200);
      expect(JSON.parse(getRes.payload).id).toBe(session.id);
    });
  });
});

// tests/e2e/chatFlow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('user can send message and receive response', async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // 等待跳转到首页
    await page.waitForURL('/');
    
    // 创建新会话
    await page.click('[data-testid="new-session"]');
    await page.selectOption('[name="agent"]', 'test-agent');
    await page.click('[data-testid="create-session"]');
    
    // 发送消息
    await page.fill('[data-testid="message-input"]', 'Hello, AI!');
    await page.click('[data-testid="send-message"]');
    
    // 验证消息出现
    await expect(page.locator('.message-bubble--user')).toContainText('Hello, AI!');
    
    // 等待 AI 响应
    await expect(page.locator('.message-bubble--assistant')).toBeVisible({
      timeout: 30000
    });
  });
});
```

---

## 第十部分：扩展设计

### 10.1 插件系统

```typescript
// plugins/PluginManager.ts
export class PluginManager {
  private plugins: Map<string, Plugin> = new Map();
  private hooks: Map<string, Hook[]> = new Map();
  
  async load(pluginPath: string): Promise<Plugin> {
    // 加载插件
    const manifest = await this.loadManifest(pluginPath);
    
    // 验证
    this.validateManifest(manifest);
    
    // 实例化
    const plugin = await this.instantiate(pluginPath, manifest);
    
    // 注册钩子
    this.registerHooks(plugin);
    
    this.plugins.set(manifest.id, plugin);
    
    return plugin;
  }
  
  async executeHook(hookName: string, context: HookContext): Promise<any> {
    const hooks = this.hooks.get(hookName) || [];
    
    let result = context;
    for (const hook of hooks) {
      result = await hook.handler(result);
    }
    
    return result;
  }
  
  private registerHooks(plugin: Plugin): void {
    for (const [hookName, handler] of Object.entries(plugin.hooks)) {
      if (!this.hooks.has(hookName)) {
        this.hooks.set(hookName, []);
      }
      
      this.hooks.get(hookName)!.push({
        plugin: plugin.id,
        handler,
        priority: plugin.manifest.hooks[hookName]?.priority || 0
      });
      
      // 按优先级排序
      this.hooks.get(hookName)!.sort((a, b) => b.priority - a.priority);
    }
  }
}

// 插件接口
export interface Plugin {
  id: string;
  manifest: PluginManifest;
  hooks: Record<string, HookHandler>;
  activate(): Promise<void>;
  deactivate(): Promise<void>;
}

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  hooks: Record<string, {
    priority: number;
    description: string;
  }>;
  permissions: string[];
  dependencies: string[];
}
```

### 10.2 主题系统

```typescript
// themes/ThemeManager.ts
export class ThemeManager {
  private themes: Map<string, Theme> = new Map();
  private activeTheme: string = 'default';
  
  register(theme: Theme): void {
    this.themes.set(theme.id, theme);
  }
  
  activate(themeId: string): void {
    if (!this.themes.has(themeId)) {
      throw new Error(`Theme ${themeId} not found`);
    }
    
    this.activeTheme = themeId;
    this.applyTheme(this.themes.get(themeId)!);
  }
  
  private applyTheme(theme: Theme): void {
    const root = document.documentElement;
    
    // 应用 CSS 变量
    for (const [key, value] of Object.entries(theme.colors)) {
      root.style.setProperty(`--color-${key}`, value);
    }
    
    // 应用字体
    root.style.setProperty('--font-body', theme.fonts.body);
    root.style.setProperty('--font-mono', theme.fonts.mono);
    
    // 应用间距
    for (const [key, value] of Object.entries(theme.spacing)) {
      root.style.setProperty(`--spacing-${key}`, value);
    }
  }
}

export interface Theme {
  id: string;
  name: string;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textMuted: string;
    border: string;
    success: string;
    warning: string;
    error: string;
    info: string;
  };
  fonts: {
    body: string;
    mono: string;
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
}
```

---

## 总结

这份蓝图详细描述了 OpenClaw Control UI 的完整实现路径：

### 核心特性
1. **多端适配**：Web + Desktop + Mobile 统一体验
2. **实时通信**：WebSocket + SSE 流式输出
3. **状态管理**：Zustand + TanStack Query 高效同步
4. **插件系统**：可扩展的钩子机制
5. **主题系统**：动态切换外观

### 技术亮点
1. **类型安全**：全 TypeScript 覆盖
2. **性能优化**：虚拟列表、增量加载、请求去重
3. **安全设计**：JWT 认证、权限控制、输入验证
4. **监控完善**：Prometheus 指标、结构化日志
5. **测试覆盖**：单元 + 集成 + E2E 三层测试

### 部署方案
1. **Docker**：单机快速部署
2. **Kubernetes**：生产级集群部署
3. **监控**：Prometheus + Grafana
4. **日志**：ELK Stack 或 Loki

### 开发阶段
1. **MVP**（2周）：基础会话和消息功能
2. **核心**（4周）：Agent 管理和插件系统
3. **完善**（4周）：高级功能和性能优化
4. **发布**（2周）：测试、文档、部署

这是一个企业级的控制界面，不仅功能完善，而且架构清晰、易于扩展。

---

*文档版本: v1.0*
*更新日期: 2026-04-28*
*作者: 小R (AI Assistant)*
