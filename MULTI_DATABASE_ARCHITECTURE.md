# AI-Novels 多数据库架构设计 - 小说生成专用

## 核心思想：每种数据库负责最擅长的领域

```
┌─────────────────────────────────────────────────────────────────┐
│                    小说生成数据架构                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   MySQL      │  │   MongoDB    │  │   Neo4j      │         │
│  │   (关系)      │  │   (文档)      │  │   (图)        │         │
│  │              │  │              │  │              │         │
│  │ 用户/订单    │  │ 小说内容     │  │ 角色关系     │         │
│  │ 配置/权限    │  │ 章节/版本    │  │ 情节网络     │         │
│  │ 事务处理     │  │ 草稿/历史    │  │ 因果推理     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                   ┌────────┴────────┐                            │
│                   │   ChromaDB      │                            │
│                   │   (向量)         │                            │
│                   │                 │                            │
│                   │ 语义检索        │                            │
│                   │ 风格匹配        │                            │
│                   │ 相似度分析      │                            │
│                   └─────────────────┘                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Redis      │  │   MinIO      │  │   Qdrant     │         │
│  │   (缓存)      │  │   (对象)      │  │   (向量增强)  │         │
│  │              │  │              │  │              │         │
│  │ 会话状态     │  │ 小说文件     │  │ 大规模向量   │         │
│  │ 实时计数     │  │ 图片/音频    │  │ 高性能检索   │         │
│  │ 分布式锁     │  │ 备份归档     │  │ 混合搜索     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 第一部分：MySQL - 事务与关系核心

### 1.1 核心表设计

```sql
-- 用户系统
CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    status TINYINT DEFAULT 1 COMMENT '0-禁用 1-正常 2-VIP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='用户表';

-- 小说项目表（核心）
CREATE TABLE novels (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255),
    genre VARCHAR(50) COMMENT '玄幻/仙侠/都市/科幻/历史/悬疑/言情/其他',
    sub_genre VARCHAR(50) COMMENT '子类型：东方玄幻/西方奇幻/末日废土等',
    status TINYINT DEFAULT 0 COMMENT '0-构思 1-大纲 2-写作中 3-已完成 4-已发布',
    word_count INT UNSIGNED DEFAULT 0,
    chapter_count INT UNSIGNED DEFAULT 0,
    target_word_count INT UNSIGNED DEFAULT 100000,
    target_chapter_count INT UNSIGNED DEFAULT 100,
    
    -- 生成配置
    generation_config JSON COMMENT '生成参数：温度、风格、模型等',
    
    -- 内容摘要
    summary TEXT COMMENT '故事梗概',
    premise TEXT COMMENT '核心设定',
    themes JSON COMMENT '主题标签',
    
    -- 统计
    generation_count INT UNSIGNED DEFAULT 0 COMMENT '生成次数',
    revision_count INT UNSIGNED DEFAULT 0 COMMENT '修改次数',
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_genre (genre, sub_genre),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB COMMENT='小说项目表';

-- 章节表
CREATE TABLE chapters (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    novel_id BIGINT UNSIGNED NOT NULL,
    chapter_number INT UNSIGNED NOT NULL COMMENT '章节序号',
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255),
    
    -- 内容状态
    status TINYINT DEFAULT 0 COMMENT '0-构思 1-生成中 2-已完成 3-已审核 4-已发布',
    generation_status TINYINT DEFAULT 0 COMMENT '0-未开始 1-排队中 2-生成中 3-已完成 4-失败',
    
    -- 内容统计
    word_count INT UNSIGNED DEFAULT 0,
    paragraph_count INT UNSIGNED DEFAULT 0,
    scene_count INT UNSIGNED DEFAULT 0,
    
    -- 情节信息
    plot_point_type VARCHAR(50) COMMENT '起/承/转/合/高潮/伏笔',
    tension_score TINYINT UNSIGNED COMMENT '张力评分 0-100',
    emotional_tone VARCHAR(50) COMMENT '情感基调',
    
    -- 关联
    previous_chapter_id BIGINT UNSIGNED NULL,
    next_chapter_id BIGINT UNSIGNED NULL,
    
    -- 版本控制
    current_version INT UNSIGNED DEFAULT 1,
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    generated_at TIMESTAMP NULL,
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    UNIQUE KEY uk_novel_chapter (novel_id, chapter_number),
    INDEX idx_status (status),
    INDEX idx_generation (generation_status)
) ENGINE=InnoDB COMMENT='章节表';

-- 版本表（支持章节多版本）
CREATE TABLE chapter_versions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    chapter_id BIGINT UNSIGNED NOT NULL,
    version_number INT UNSIGNED NOT NULL,
    content_id VARCHAR(64) NOT NULL COMMENT 'MongoDB文档ID',
    word_count INT UNSIGNED DEFAULT 0,
    
    -- 生成信息
    generation_params JSON COMMENT '生成参数快照',
    model_used VARCHAR(100) COMMENT '使用的模型',
    generation_time INT UNSIGNED COMMENT '生成耗时(秒)',
    
    -- 质量评分
    quality_score DECIMAL(3,2) COMMENT '质量评分 0.00-1.00',
    coherence_score DECIMAL(3,2),
    creativity_score DECIMAL(3,2),
    style_score DECIMAL(3,2),
    
    -- 用户反馈
    user_rating TINYINT UNSIGNED COMMENT '用户评分 1-5',
    user_comment TEXT,
    
    -- 状态
    is_current BOOLEAN DEFAULT FALSE,
    status TINYINT DEFAULT 1 COMMENT '0-废弃 1-可用 2-推荐',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    UNIQUE KEY uk_chapter_version (chapter_id, version_number),
    INDEX idx_current (chapter_id, is_current)
) ENGINE=InnoDB COMMENT='章节版本表';

-- 角色表
CREATE TABLE characters (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    novel_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    alias JSON COMMENT '别名/称号',
    
    -- 基本信息
    gender TINYINT COMMENT '0-女 1-男 2-其他',
    age VARCHAR(20) COMMENT '年龄描述',
    appearance TEXT COMMENT '外貌描述',
    
    -- 角色定位
    role_type VARCHAR(50) COMMENT ' protagonist/antagonist/supporting/mentor',
    importance TINYINT UNSIGNED DEFAULT 3 COMMENT '重要性 1-5',
    
    -- 性格（MySQL存储结构化数据）
    personality_traits JSON COMMENT '性格特征 [{trait, intensity}]',
    personality_mbti VARCHAR(4),
    personality_big5 JSON COMMENT '大五人格 {O,C,E,A,N}',
    
    -- 背景
    background_story TEXT,
    motivation TEXT COMMENT '核心动机',
    goal TEXT COMMENT '目标',
    conflict TEXT COMMENT '内心冲突',
    
    -- 状态
    status VARCHAR(20) DEFAULT 'alive' COMMENT 'alive/dead/missing/transformed',
    
    -- 统计
    appearance_count INT UNSIGNED DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    INDEX idx_novel (novel_id),
    INDEX idx_importance (novel_id, importance),
    INDEX idx_role (novel_id, role_type)
) ENGINE=InnoDB COMMENT='角色表';

-- 世界观元素表
CREATE TABLE world_elements (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    novel_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    element_type VARCHAR(50) COMMENT 'location/organization/item/system/rule/event',
    category VARCHAR(50) COMMENT '分类',
    
    -- 描述
    description TEXT,
    significance TEXT COMMENT '重要性/意义',
    
    -- 属性
    attributes JSON COMMENT '动态属性',
    
    -- 关联
    parent_id BIGINT UNSIGNED NULL,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES world_elements(id),
    INDEX idx_novel_type (novel_id, element_type)
) ENGINE=InnoDB COMMENT='世界观元素表';

-- 生成任务表（队列管理）
CREATE TABLE generation_tasks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    novel_id BIGINT UNSIGNED NOT NULL,
    chapter_id BIGINT UNSIGNED,
    task_type VARCHAR(50) NOT NULL COMMENT 'outline/chapter/character/world/revision',
    
    -- 任务状态
    status TINYINT DEFAULT 0 COMMENT '0-排队 1-运行中 2-完成 3-失败 4-取消',
    priority TINYINT DEFAULT 3 COMMENT '1-最高 5-最低',
    
    -- 输入输出
    input_params JSON NOT NULL,
    output_result JSON,
    error_message TEXT,
    
    -- 资源使用
    tokens_used INT UNSIGNED,
    cost DECIMAL(10,4),
    generation_time INT UNSIGNED,
    
    -- 执行信息
    worker_id VARCHAR(100),
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL,
    INDEX idx_status_priority (status, priority),
    INDEX idx_novel (novel_id, status)
) ENGINE=InnoDB COMMENT='生成任务表';

-- 用户偏好表
CREATE TABLE user_preferences (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    
    -- 生成偏好
    default_genre VARCHAR(50),
    default_style VARCHAR(50),
    default_model VARCHAR(100),
    temperature_preference DECIMAL(3,2) DEFAULT 0.7,
    
    -- 界面偏好
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'zh-CN',
    
    -- 高级设置
    auto_save_interval INT DEFAULT 60,
    max_concurrent_generations TINYINT DEFAULT 3,
    
    -- 订阅
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires_at TIMESTAMP NULL,
    
    -- 限额
    monthly_word_quota INT DEFAULT 100000,
    monthly_word_used INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='用户偏好表';

-- 审计日志表（分区表）
CREATE TABLE audit_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT,
    user_id BIGINT UNSIGNED,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id BIGINT UNSIGNED,
    details JSON,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id, created_at)
) ENGINE=InnoDB 
PARTITION BY RANGE (UNIX_TIMESTAMP(created_at)) (
    PARTITION p202401 VALUES LESS THAN (UNIX_TIMESTAMP('2024-02-01')),
    PARTITION p202402 VALUES LESS THAN (UNIX_TIMESTAMP('2024-03-01')),
    PARTITION p202403 VALUES LESS THAN (UNIX_TIMESTAMP('2024-04-01')),
    PARTITION pfuture VALUES LESS THAN MAXVALUE
) COMMENT='审计日志分区表';
```

### 1.2 事务场景示例

```sql
-- 场景1：创建小说并初始化配置（事务）
START TRANSACTION;

-- 插入小说
INSERT INTO novels (user_id, title, genre, generation_config) 
VALUES (1, '仙剑奇侠传', '仙侠', '{"temperature": 0.8, "style": "古典仙侠"}');

SET @novel_id = LAST_INSERT_ID();

-- 创建默认角色
INSERT INTO characters (novel_id, name, role_type, importance) VALUES
(@novel_id, '李逍遥', 'protagonist', 5),
(@novel_id, '赵灵儿', 'protagonist', 5),
(@novel_id, '林月如', 'supporting', 4);

-- 创建章节框架
INSERT INTO chapters (novel_id, chapter_number, title, plot_point_type) VALUES
(@novel_id, 1, '仙灵岛奇遇', '起'),
(@novel_id, 2, '山神庙拜师', '承'),
(@novel_id, 3, '锁妖塔危机', '转');

-- 初始化用户计数
UPDATE user_preferences 
SET monthly_word_used = monthly_word_used + 0 
WHERE user_id = 1;

COMMIT;

-- 场景2：版本切换（原子操作）
START TRANSACTION;

-- 获取当前版本
SELECT current_version INTO @old_version 
FROM chapters WHERE id = 123;

-- 更新章节指向新版本
UPDATE chapters 
SET current_version = 5, 
    word_count = (SELECT word_count FROM chapter_versions WHERE chapter_id = 123 AND version_number = 5),
    updated_at = NOW()
WHERE id = 123;

-- 标记新版本为当前
UPDATE chapter_versions 
SET is_current = TRUE, status = 2
WHERE chapter_id = 123 AND version_number = 5;

-- 标记旧版本为非当前
UPDATE chapter_versions 
SET is_current = FALSE
WHERE chapter_id = 123 AND version_number = @old_version;

COMMIT;
```

---

## 第二部分：MongoDB - 内容存储与版本

### 2.1 文档结构设计

```javascript
// 小说内容集合 (novel_contents)
{
  _id: ObjectId("..."),
  novel_id: 12345,
  chapter_id: 67890,
  version: 3,
  
  // 内容结构
  content: {
    // 富文本结构（支持多种元素）
    blocks: [
      {
        type: "paragraph",
        style: "narrative",  // narrative/dialogue/description/action/inner_thought
        text: "李逍遥站在仙灵岛的桃花树下，微风拂过，花瓣如雨般飘落...",
        // 元数据
        metadata: {
          word_count: 45,
          sentiment: "peaceful",
          imagery: ["visual", "tactile"],
          pov_character: "李逍遥",
          location: "仙灵岛"
        }
      },
      {
        type: "dialogue",
        speaker: "赵灵儿",
        text: "逍遥哥哥，你终于来了...",
        emotion: "joyful",
        tone: "gentle",
        metadata: {
          word_count: 12,
          speech_act: "greeting",
          subtext: "期待已久"
        }
      },
      {
        type: "action",
        text: "李逍遥快步上前，握住了灵儿的手。",
        characters: ["李逍遥"],
        metadata: {
          word_count: 15,
          pace: "fast",
          intensity: "high"
        }
      },
      {
        type: "scene_break",
        marker: "***",
        transition_type: "time_jump",
        duration: "三天后"
      }
    ],
    
    // 统计
    stats: {
      total_word_count: 3500,
      paragraph_count: 42,
      dialogue_count: 15,
      action_count: 20,
      description_count: 7,
      
      // 角色出场统计
      character_appearances: {
        "李逍遥": { count: 25, first_paragraph: 1, last_paragraph: 40 },
        "赵灵儿": { count: 18, first_paragraph: 3, last_paragraph: 38 }
      },
      
      // 情感分布
      sentiment_distribution: {
        "joyful": 0.3,
        "tense": 0.4,
        "peaceful": 0.2,
        "sad": 0.1
      }
    }
  },
  
  // 生成信息
  generation: {
    model: "gpt-4o",
    temperature: 0.8,
    max_tokens: 4000,
    prompt_template: "classical_xianxia_chapter",
    
    // 输入上下文（用于追溯）
    input_context: {
      previous_chapter_summary: "上一章结尾...",
      character_states: {
        "李逍遥": { location: "仙灵岛", mood: "excited" },
        "赵灵儿": { location: "仙灵岛", mood: "nervous" }
      },
      plot_requirements: ["初次相遇", "揭示身世"],
      tone_requirements: ["浪漫", "神秘"]
    },
    
    // 生成过程记录
    generation_log: [
      { step: "outline", timestamp: ISODate("..."), output: "大纲内容..." },
      { step: "draft", timestamp: ISODate("..."), output: "初稿内容..." },
      { step: "refine", timestamp: ISODate("..."), output: "精修内容..." }
    ],
    
    // 质量评估
    quality_metrics: {
      coherence: 0.92,
      creativity: 0.85,
      style_consistency: 0.90,
      grammar: 0.98
    }
  },
  
  // 编辑历史
  edit_history: [
    {
      timestamp: ISODate("..."),
      editor: "user_123",
      action: "modify",
      position: { block_index: 5, offset: 120 },
      original: "原文...",
      modified: "修改后...",
      reason: "优化对话流畅度"
    }
  ],
  
  // 用户反馈
  feedback: {
    rating: 5,
    tags: ["感人", "画面感强"],
    comment: "这段描写太美了！"
  },
  
  created_at: ISODate("2024-01-15T10:30:00Z"),
  updated_at: ISODate("2024-01-15T11:45:00Z")
}

// 角色详细档案集合 (character_profiles)
{
  _id: ObjectId("..."),
  character_id: 1001,  // MySQL角色ID
  novel_id: 12345,
  
  // 深度档案
  profile: {
    // 心理学模型
    psychology: {
      // MBTI
      mbti: {
        type: "ENFP",
        functions: {
          dominant: "Ne",
          auxiliary: "Fi",
          tertiary: "Te",
          inferior: "Si"
        }
      },
      
      // 大五人格
      big5: {
        openness: 0.85,
        conscientiousness: 0.60,
        extraversion: 0.75,
        agreeableness: 0.70,
        neuroticism: 0.45
      },
      
      // 九型人格
      enneagram: {
        type: 7,
        wing: 6,
        triad: "head"
      },
      
      // 核心驱动力
      core_drives: [
        { drive: "追求自由", strength: 0.9 },
        { drive: "保护所爱", strength: 0.8 },
        { drive: "探索未知", strength: 0.85 }
      ],
      
      // 恐惧与渴望
      fears: ["被束缚", "失去重要之人", "平庸度过一生"],
      desires: ["成为大侠", "找到真爱", "解开身世之谜"],
      
      // 内在冲突
      internal_conflicts: [
        {
          conflict: "责任 vs 自由",
          description: "渴望逍遥自在，却被命运推向责任",
          manifestation: "经常逃避，最终不得不面对"
        }
      ]
    },
    
    // 关系网络（引用Neo4j节点）
    relationships: [
      {
        character_id: 1002,
        relationship_type: "romantic",
        dynamics: "soulmates",
        development_arc: [
          { stage: "初遇", chapter: 1, description: "仙灵岛邂逅" },
          { stage: "相知", chapter: 5, description: "共同冒险" },
          { stage: "分离", chapter: 15, description: "锁妖塔之别" }
        ],
        tension_level: 0.9,
        emotional_bond: 0.95
      }
    ],
    
    // 成长弧线
    character_arc: {
      arc_type: "hero_journey",
      stages: [
        {
          stage: "ordinary_world",
          chapter_range: [1, 3],
          description: "余杭镇的小混混",
          psychological_state: "unaware"
        },
        {
          stage: "call_to_adventure",
          chapter_range: [4, 6],
          description: "仙灵岛求药",
          psychological_state: "reluctant"
        },
        {
          stage: "transformation",
          chapter_range: [10, 20],
          description: "经历磨难，逐渐成熟",
          psychological_state: "committed"
        }
      ]
    },
    
    // 语言风格
    voice: {
      speaking_style: "口语化，带痞气，关键时刻认真",
      vocabulary_level: "中等，偶尔冒出诗词",
      sentence_patterns: ["短句为主", "反问句多", "感叹词丰富"],
      signature_phrases: ["我李逍遥...", "小爷我..."],
      
      // 内心独白风格
      inner_voice: {
        style: "直白，偶尔诗意",
        concerns: ["身份", "责任", "感情"],
        growth_markers: [
          { chapter: 1, marker: "只想当大侠" },
          { chapter: 10, marker: "开始思考责任" },
          { chapter: 20, marker: "真正理解大侠含义" }
        ]
      }
    }
  },
  
  // 出场记录
  appearances: [
    {
      chapter_id: 1,
      scenes: ["开场", "仙灵岛"],
      significance: "introduction",
      key_moments: ["首次出场", "获得仙剑"]
    }
  ],
  
  // 记忆（用于生成一致性）
  memories: [
    {
      type: "episodic",
      content: "在仙灵岛第一次见灵儿",
      emotional_valence: 0.9,
      importance: 1.0,
      chapter: 1
    },
    {
      type: "semantic",
      content: "自己是蜀山派传人",
      emotional_valence: 0.5,
      importance: 0.9,
      chapter: 5
    }
  ],
  
  created_at: ISODate("2024-01-10T08:00:00Z"),
  updated_at: ISODate("2024-01-15T14:30:00Z")
}

// 生成提示模板集合 (prompt_templates)
{
  _id: ObjectId("..."),
  template_id: "classical_xianxia_chapter",
  name: "古典仙侠章节生成",
  category: "chapter",
  genre: "仙侠",
  
  // 模板版本
  version: "2.1",
  
  // 提示结构
  structure: {
    system_prompt: `你是一位精通古典仙侠小说的资深作家...
创作要求：
1. 语言风格：古典雅致，意境深远
2. 描写重点：环境氛围、人物心理、动作细节
3. 对话特点：符合身份，推动情节
4. 节奏控制：张弛有度，高潮迭起`,
    
    user_prompt_template: `请创作《{novel_title}》第{chapter_number}章：{chapter_title}

【前文摘要】
{previous_summary}

【本章要求】
情节目标：{plot_goal}
情感基调：{emotional_tone}
出场角色：{characters}
关键场景：{key_scenes}

【角色状态】
{character_states}

【世界观约束】
{world_rules}

【输出格式】
{output_format}`,
    
    // 变量定义
    variables: [
      { name: "novel_title", type: "string", required: true },
      { name: "chapter_number", type: "number", required: true },
      { name: "previous_summary", type: "text", required: true },
      { name: "plot_goal", type: "text", required: true },
      { name: "emotional_tone", type: "string", required: false, default: "根据情节自动判断" },
      { name: "characters", type: "array", required: true },
      { name: "character_states", type: "object", required: true },
      { name: "world_rules", type: "array", required: false },
      { name: "output_format", type: "string", required: false, default: "标准章节格式" }
    ]
  },
  
  // 示例
  examples: [
    {
      input: { /* 示例输入 */ },
      output: "示例输出...",
      explanation: "为什么这样写"
    }
  ],
  
  // 性能统计
  performance: {
    usage_count: 1250,
    avg_quality_score: 0.88,
    avg_generation_time: 45,
    user_satisfaction: 4.5
  },
  
  created_at: ISODate("2024-01-01T00:00:00Z"),
  updated_at: ISODate("2024-01-20T10:00:00Z")
}

// 生成历史集合 (generation_history)
{
  _id: ObjectId("..."),
  task_id: 99999,  // MySQL任务ID
  
  // 完整输入输出记录
  input: {
    prompt: "完整的提示内容...",
    context_window: [/* 上下文片段 */],
    parameters: {
      model: "gpt-4o",
      temperature: 0.8,
      max_tokens: 4000
    }
  },
  
  output: {
    raw_text: "原始生成文本...",
    parsed_structure: { /* 解析后的结构 */ },
    token_usage: {
      prompt_tokens: 1500,
      completion_tokens: 2000,
      total_tokens: 3500
    }
  },
  
  // 处理过程
  processing: {
    stages: [
      {
        name: "context_building",
        duration_ms: 120,
        details: { fragments_retrieved: 15, total_tokens: 3000 }
      },
      {
        name: "llm_generation",
        duration_ms: 8500,
        details: { model: "gpt-4o", streaming: true }
      },
      {
        name: "post_processing",
        duration_ms: 300,
        details: { parsing: true, validation: true }
      }
    ],
    total_duration_ms: 8920
  },
  
  // 质量评估
  evaluation: {
    automatic: {
      coherence: 0.92,
      grammar: 0.98,
      style_match: 0.85,
      length_accuracy: 0.95
    },
    human: {
      rating: 5,
      feedback: "非常满意"
    }
  },
  
  created_at: ISODate("2024-01-15T10:30:00Z")
}
```

### 2.2 MongoDB 索引策略

```javascript
// 小说内容集合索引
db.novel_contents.createIndex({ novel_id: 1, chapter_id: 1, version: 1 }, { unique: true });
db.novel_contents.createIndex({ "content.blocks.type": 1 });
db.novel_contents.createIndex({ "content.stats.total_word_count": 1 });
db.novel_contents.createIndex({ "generation.quality_metrics.coherence": 1 });
db.novel_contents.createIndex({ created_at: -1 });

// 角色档案集合索引
db.character_profiles.createIndex({ character_id: 1 }, { unique: true });
db.character_profiles.createIndex({ novel_id: 1 });
db.character_profiles.createIndex({ "profile.psychology.mbti.type": 1 });
db.character_profiles.createIndex({ "profile.relationships.character_id": 1 });

// 文本搜索索引
db.novel_contents.createIndex(
  { "content.blocks.text": "text" },
  { 
    weights: {
      "content.blocks.text": 10
    },
    default_language: "chinese"
  }
);
```

---

## 第三部分：Neo4j - 关系与推理引擎

### 3.1 图数据模型

```cypher
// 创建约束
CREATE CONSTRAINT character_id IF NOT EXISTS
FOR (c:Character) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT scene_id IF NOT EXISTS
FOR (s:Scene) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT plot_point_id IF NOT EXISTS
FOR (p:PlotPoint) REQUIRE p.id IS UNIQUE;

// 创建索引
CREATE INDEX character_name_idx FOR (c:Character) ON (c.name);
CREATE INDEX scene_chapter_idx FOR (s:Scene) ON (s.chapter_id);
CREATE INDEX relationship_type_idx FOR ()-[r:RELATES_TO]-() ON (r.type);

// ==================== 节点类型 ====================

// 角色节点
(:Character {
  id: "char_1001",
  name: "李逍遥",
  importance: 5,
  role_type: "protagonist",
  status: "alive",
  // 动态属性（随剧情变化）
  current_location: "锁妖塔",
  current_mood: "determined",
  power_level: 85,
  // 向量嵌入（用于相似度查询）
  embedding: [0.12, -0.34, 0.56, ...]
})

// 场景节点
(:Scene {
  id: "scene_5001",
  chapter_id: 1,
  scene_number: 3,
  location: "仙灵岛桃花林",
  time: "清晨",
  atmosphere: "romantic",
  tension_level: 0.3,
  embedding: [0.23, 0.45, -0.12, ...]
})

// 情节点
(:PlotPoint {
  id: "plot_2001",
  type: "inciting_incident",
  description: "李逍遥闯入仙灵岛",
  importance: 0.9,
  chapter: 1,
  embedding: [0.34, -0.22, 0.67, ...]
})

// 物品节点
(:Item {
  id: "item_3001",
  name: "七星剑",
  type: "weapon",
  significance: "high",
  current_holder: "char_1001",
  origin: "蜀山派"
})

// 组织节点
(:Organization {
  id: "org_4001",
  name: "蜀山派",
  type: "sect",
  alignment: "righteous",
  influence: 0.9
})

// 主题节点
(:Theme {
  id: "theme_6001",
  name: "宿命与自由",
  type: "central",
  expression: "李逍遥被命运推动，最终接受使命"
})

// ==================== 关系类型 ====================

// 角色关系
(:Character)-[:RELATES_TO {
  type: "romantic",
  dynamics: "star_crossed_lovers",
  intensity: 0.95,
  start_chapter: 1,
  development: [
    {chapter: 1, stage: "初遇", tension: 0.3},
    {chapter: 5, stage: "相知", tension: 0.6},
    {chapter: 15, stage: "分离", tension: 0.9}
  ],
  is_active: true
}]-(:Character)

// 角色出场
(:Character)-[:APPEARS_IN {
  role: "protagonist",
  significance: "central",
  entrance_type: "active",
  exit_type: null,
  scenes: ["scene_5001", "scene_5002"]
}]-(:Scene)

// 情节推进
(:PlotPoint)-[:LEADS_TO {
  causality: "direct",
  strength: 0.9,
  time_gap: "immediate"
}]-(:PlotPoint)

// 场景包含
(:Scene)-[:CONTAINS {
  content_type: "dialogue"
}]-(:PlotPoint)

// 物品归属
(:Character)-[:POSSESSES {
  acquired_at: "scene_5005",
  significance: "plot_critical"
}]-(:Item)

// 组织成员
(:Character)-[:BELONGS_TO {
  role: "disciple",
  rank: "senior",
  joined_at: "chapter_5"
}]-(:Organization)

// 主题表达
(:Scene)-[:EXPRESSES {
  strength: 0.8,
  manifestation: "李逍遥面对选择"
}]-(:Theme)

// 情感影响
(:Scene)-[:EMOTIONAL_IMPACT {
  target_character: "char_1001",
  emotion: "joy",
  intensity: 0.9,
  duration: "lasting"
}]-(:Character)
```

### 3.2 核心查询模式

```cypher
// 查询1：获取角色的完整关系网络
MATCH (c:Character {id: "char_1001"})-[r:RELATES_TO]-(other:Character)
RETURN c, r, other
ORDER BY r.intensity DESC;

// 查询2：追踪情节因果链
MATCH path = (start:PlotPoint {id: "plot_2001"})-[:LEADS_TO*1..5]->(end:PlotPoint)
RETURN path,
       reduce(strength = 1.0, r in relationships(path) | strength * r.strength) AS total_strength
ORDER BY total_strength DESC
LIMIT 5;

// 查询3：查找情感高潮路径
MATCH path = (scene1:Scene)-[:LEADS_TO*2..4]->(scene2:Scene)
WHERE scene1.tension_level < 0.3 AND scene2.tension_level > 0.8
RETURN path,
       [s in nodes(path) | s.tension_level] AS tension_arc
ORDER BY length(path) ASC;

// 查询4：角色成长轨迹
MATCH (c:Character {id: "char_1001"})-[a:APPEARS_IN]->(s:Scene)
WITH c, s, a
ORDER BY s.scene_number
RETURN c.name,
       collect({
         scene: s.id,
         chapter: s.chapter_id,
         significance: a.significance,
         tension: s.tension_level
       }) AS character_arc;

// 查询5：发现潜在情节漏洞
// 查找没有前因或后果的情节点
MATCH (p:PlotPoint)
WHERE NOT (p)-[:LEADS_TO]->() AND NOT ()-[:LEADS_TO]->(p)
RETURN p.id, p.description, p.chapter
ORDER BY p.chapter;

// 查询6：主题一致性检查
MATCH (t:Theme {id: "theme_6001"})
MATCH (s:Scene)-[e:EXPRESSES]->(t)
WITH t, collect({scene: s.id, strength: e.strength}) AS expressions
RETURN t.name,
       avg(e.strength) AS avg_strength,
       expressions
ORDER BY avg_strength DESC;

// 查询7：相似角色发现（基于向量）
MATCH (c1:Character {id: "char_1001"})
MATCH (c2:Character)
WHERE c1.id <> c2.id
WITH c1, c2,
     gds.similarity.cosine(c1.embedding, c2.embedding) AS similarity
WHERE similarity > 0.8
RETURN c2.name, similarity
ORDER BY similarity DESC
LIMIT 5;

// 查询8：预测角色冲突
// 查找关系紧张且目标冲突的角色对
MATCH (c1:Character)-[r1:RELATES_TO {type: "romantic"}]->(c2:Character),
      (c1)-[r2:RELATES_TO {type: "rivalry"}]->(c3:Character),
      (c2)-[r3:RELATES_TO]->(c3)
WHERE r1.intensity > 0.7 AND r2.intensity > 0.6
RETURN c1.name, c2.name, c3.name,
       r1.intensity AS romantic_tension,
       r2.intensity AS rivalry_tension,
       "潜在三角冲突" AS prediction;

// 查询9：场景连贯性分析
MATCH (s1:Scene)-[:NEXT_SCENE]->(s2:Scene)
WHERE s1.chapter_id = s2.chapter_id
WITH s1, s2,
     gds.similarity.cosine(s1.embedding, s2.embedding) AS continuity
WHERE continuity < 0.5
RETURN s1.id, s2.id, continuity,
       "场景连贯性较低，建议检查过渡" AS warning;
```

### 3.3 图算法应用

```cypher
// 使用 GDS 库进行图分析

// 1. 社区检测 - 发现角色阵营
CALL gds.louvain.stream('character-network')
YIELD nodeId, communityId
MATCH (c:Character) WHERE id(c) = nodeId
RETURN communityId,
       collect(c.name) AS characters,
       count(*) AS count
ORDER BY count DESC;

// 2. 中心性分析 - 关键角色识别
CALL gds.betweenness.stream('character-network')
YIELD nodeId, score
MATCH (c:Character) WHERE id(c) = nodeId
RETURN c.name, score
ORDER BY score DESC
LIMIT 10;

// 3. 最短路径 - 角色关系距离
MATCH (c1:Character {name: "李逍遥"}), (c2:Character {name: "拜月教主"})
CALL gds.shortestPath.dijkstra.stream('character-network', {
  sourceNode: id(c1),
  targetNode: id(c2),
  relationshipWeightProperty: 'intensity'
})
YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
RETURN [nodeId IN nodeIds | gds.util.asNode(nodeId).name] AS path_names,
       totalCost;

// 4. 相似度传播 - 发现相似场景
CALL gds.nodeSimilarity.stream('scene-network', {
  topK: 5,
  similarityCutoff: 0.7
})
YIELD node1, node2, similarity
RETURN gds.util.asNode(node1).id AS scene1,
       gds.util.asNode(node2).id AS scene2,
       similarity
ORDER BY similarity DESC;
```

---

## 第四部分：ChromaDB - 语义检索引擎

### 4.1 集合设计

```python
import chromadb
from chromadb.config import Settings

class NovelVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # 初始化集合
        self.collections = {
            # 章节内容语义检索
            "chapter_segments": self.client.get_or_create_collection(
                name="chapter_segments",
                metadata={"hnsw:space": "cosine", "description": "章节片段语义检索"}
            ),
            
            # 角色描述检索
            "character_descriptions": self.client.get_or_create_collection(
                name="character_descriptions",
                metadata={"hnsw:space": "cosine", "description": "角色描述语义匹配"}
            ),
            
            # 场景氛围检索
            "scene_atmospheres": self.client.get_or_create_collection(
                name="scene_atmospheres",
                metadata={"hnsw:space": "cosine", "description": "场景氛围相似度"}
            ),
            
            # 对话风格检索
            "dialogue_styles": self.client.get_or_create_collection(
                name="dialogue_styles",
                metadata={"hnsw:space": "cosine", "description": "对话风格匹配"}
            ),
            
            # 写作风格模板
            "style_templates": self.client.get_or_create_collection(
                name="style_templates",
                metadata={"hnsw:space": "cosine", "description": "写作风格模板"}
            ),
            
            # 情节模式
            "plot_patterns": self.client.get_or_create_collection(
                name="plot_patterns",
                metadata={"hnsw:space": "cosine", "description": "情节模式检索"}
            )
        }
    
    # ==================== 章节片段操作 ====================
    
    def add_chapter_segment(self, 
                          segment_id: str,
                          text: str,
                          novel_id: int,
                          chapter_id: int,
                          segment_type: str,  # narrative/dialogue/description/action
                          characters: List[str],
                          location: str,
                          embedding: List[float]):
        """添加章节片段"""
        self.collections["chapter_segments"].add(
            ids=[segment_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "novel_id": novel_id,
                "chapter_id": chapter_id,
                "segment_type": segment_type,
                "characters": json.dumps(characters),
                "location": location,
                "timestamp": datetime.now().isoformat()
            }]
        )
    
    def search_similar_segments(self,
                              query_text: str,
                              query_embedding: List[float],
                              novel_id: Optional[int] = None,
                              segment_type: Optional[str] = None,
                              limit: int = 10) -> List[Dict]:
        """搜索相似片段"""
        where_filter = {}
        if novel_id:
            where_filter["novel_id"] = novel_id
        if segment_type:
            where_filter["segment_type"] = segment_type
        
        results = self.collections["chapter_segments"].query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )
        
        return self._format_results(results)
    
    def find_character_voice(self,
                           character_name: str,
                           query_embedding: List[float],
                           limit: int = 5) -> List[Dict]:
        """查找角色的语言风格样本"""
        results = self.collections["chapter_segments"].query(
            query_embeddings=[query_embedding],
            n_results=limit * 2,  # 多取一些用于过滤
            where={
                "$and": [
                    {"segment_type": "dialogue"},
                    {"characters": {"$contains": character_name}}
                ]
            }
        )
        
        # 过滤并格式化
        segments = self._format_results(results)
        return segments[:limit]
    
    # ==================== 风格模板操作 ====================
    
    def add_style_template(self,
                         template_id: str,
                         name: str,
                         description: str,
                         sample_texts: List[str],
                         embeddings: List[List[float]],
                         metadata: Dict):
        """添加风格模板"""
        self.collections["style_templates"].add(
            ids=[f"{template_id}_{i}" for i in range(len(sample_texts))],
            embeddings=embeddings,
            documents=sample_texts,
            metadatas=[{
                "template_id": template_id,
                "name": name,
                "description": description,
                **metadata
            }] * len(sample_texts)
        )
    
    def match_style(self,
                   query_embedding: List[float],
                   genre: Optional[str] = None,
                   limit: int = 3) -> List[Dict]:
        """匹配写作风格"""
        where_filter = {}
        if genre:
            where_filter["genre"] = genre
        
        results = self.collections["style_templates"].query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter if where_filter else None
        )
        
        return self._format_results(results)
    
    # ==================== 情节模式操作 ====================
    
    def add_plot_pattern(self,
                       pattern_id: str,
                       name: str,
                       description: str,
                       embedding: List[float],
                       pattern_type: str,  # twist/climax/turning_point/foreshadowing
                       emotional_impact: str,
                       examples: List[str]):
        """添加情节模式"""
        self.collections["plot_patterns"].add(
            ids=[pattern_id],
            embeddings=[embedding],
            documents=[description],
            metadatas=[{
                "name": name,
                "pattern_type": pattern_type,
                "emotional_impact": emotional_impact,
                "examples": json.dumps(examples)
            }]
        )
    
    def find_plot_inspiration(self,
                             current_context: str,
                             context_embedding: List[float],
                             desired_emotion: str,
                             limit: int = 5) -> List[Dict]:
        """寻找情节灵感"""
        results = self.collections["plot_patterns"].query(
            query_embeddings=[context_embedding],
            n_results=limit,
            where={"emotional_impact": desired_emotion}
        )
        
        return self._format_results(results)
    
    def _format_results(self, results) -> List[Dict]:
        """格式化查询结果"""
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i] if results.get("documents") else None,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else None,
                "distance": results["distances"][0][i] if results.get("distances") else None,
                "score": 1 - results["distances"][0][i] if results.get("distances") else None
            })
        return formatted
```

### 4.2 语义检索应用

```python
class SemanticNovelHelper:
    def __init__(self, vector_store: NovelVectorStore, embedder):
        self.vector_store = vector_store
        self.embedder = embedder
    
    async def find_similar_scenes(self, 
                                  description: str,
                                  novel_id: Optional[int] = None,
                                  limit: int = 5) -> List[Dict]:
        """查找相似场景（用于参考和灵感）"""
        embedding = await self.embedder.embed(description)
        
        return self.vector_store.search_similar_segments(
            query_text=description,
            query_embedding=embedding,
            novel_id=novel_id,
            segment_type="description",
            limit=limit
        )
    
    async def maintain_character_consistency(self,
                                            character_name: str,
                                            new_dialogue: str,
                                            threshold: float = 0.7) -> Dict:
        """检查角色对话一致性"""
        # 获取角色历史对话风格
        dialogue_embedding = await self.embedder.embed(new_dialogue)
        
        historical_voices = self.vector_store.find_character_voice(
            character_name=character_name,
            query_embedding=dialogue_embedding,
            limit=10
        )
        
        if not historical_voices:
            return {"consistent": True, "reason": "无历史对话"}
        
        # 计算平均相似度
        similarities = [voice["score"] for voice in historical_voices]
        avg_similarity = sum(similarities) / len(similarities)
        
        # 检查是否偏离
        if avg_similarity < threshold:
            # 找出最相似的历史对话作为参考
            best_match = max(historical_voices, key=lambda x: x["score"])
            
            return {
                "consistent": False,
                "similarity": avg_similarity,
                "threshold": threshold,
                "suggestion": f"对话风格与角色历史不符",
                "reference": best_match["text"],
                "issues": self._analyze_style_divergence(
                    new_dialogue, 
                    [v["text"] for v in historical_voices[:3]]
                )
            }
        
        return {
            "consistent": True,
            "similarity": avg_similarity,
            "references": [v["text"] for v in historical_voices[:3]]
        }
    
    async def suggest_style_for_scene(self,
                                     scene_description: str,
                                     genre: str,
                                     emotional_tone: str) -> List[Dict]:
        """为场景建议写作风格"""
        scene_embedding = await self.embedder.embed(
            f"{scene_description} {emotional_tone}"
        )
        
        # 查找相似场景的风格
        similar_scenes = self.vector_store.search_similar_segments(
            query_text=scene_description,
            query_embedding=scene_embedding,
            segment_type="description",
            limit=5
        )
        
        # 匹配风格模板
        style_matches = self.vector_store.match_style(
            query_embedding=scene_embedding,
            genre=genre,
            limit=3
        )
        
        return {
            "similar_scenes": similar_scenes,
            "recommended_styles": style_matches,
            "synthesis": self._synthesize_style_recommendation(
                similar_scenes, style_matches
            )
        }
    
    async def find_plot_twist_inspiration(self,
                                          current_plot: str,
                                          desired_effect: str) -> List[Dict]:
        """寻找情节转折灵感"""
        plot_embedding = await self.embedder.embed(current_plot)
        
        inspirations = self.vector_store.find_plot_inspiration(
            current_context=current_plot,
            context_embedding=plot_embedding,
            desired_emotion=desired_effect,
            limit=5
        )
        
        return inspirations
    
    def _analyze_style_divergence(self, new_text: str, references: List[str]) -> List[str]:
        """分析风格差异"""
        issues = []
        
        # 简单启发式分析
        new_words = set(new_text.split())
        ref_words = set(" ".join(references).split())
        
        # 检查词汇重叠
        overlap = len(new_words & ref_words) / len(new_words | ref_words)
        if overlap < 0.3:
            issues.append("词汇选择差异过大")
        
        # 检查句式长度
        new_avg_len = sum(len(s) for s in new_text.split("。")) / len(new_text.split("。"))
        ref_avg_len = sum(len(s) for s in " ".join(references).split("。")) / len(" ".join(references).split("。"))
        
        if abs(new_avg_len - ref_avg_len) > 20:
            issues.append("句式长度差异明显")
        
        return issues
    
    def _synthesize_style_recommendation(self, 
                                        scenes: List[Dict], 
                                        styles: List[Dict]) -> str:
        """综合风格建议"""
        # 基于相似场景和风格模板生成建议
        recommendations = []
        
        if scenes:
            recommendations.append(
                f"参考场景风格：{scenes[0]['metadata'].get('location', '未知场景')}"
            )
        
        if styles:
            recommendations.append(
                f"推荐风格模板：{styles[0]['metadata'].get('name', '未知风格')}"
            )
        
        return "；".join(recommendations)
```

---

## 第五部分：Redis - 实时状态与缓存

### 5.1 数据结构设计

```redis
# ==================== 会话状态 ====================

# 小说生成会话
HSET novel_session:12345 \
    novel_id 12345 \
    user_id 1 \
    status "generating" \
    current_chapter 5 \
    total_chapters 100 \
    progress "45%" \
    started_at "2024-01-15T10:00:00Z" \
    estimated_completion "2024-01-15T11:30:00Z"

# 设置过期时间（2小时）
EXPIRE novel_session:12345 7200

# 生成进度流（有序集合）
ZADD novel_progress:12345 \
    10 "chapter_1_complete" \
    20 "chapter_2_complete" \
    30 "chapter_3_complete"

# ==================== 实时计数器 ====================

# 小说生成计数（按天）
HINCRBY novel_stats:20240115 generate_count 1
HINCRBY novel_stats:20240115 word_count 3500
HINCRBY novel_stats:20240115 token_count 15000

# 用户实时限额
HGET user_quota:1 monthly_word_used
HINCRBY user_quota:1 monthly_word_used 3500

# 检查是否超限
HLEN user_quota:1

# ==================== 分布式锁 ====================

# 章节生成锁（防止并发生成同一章节）
SET chapter_lock:12345:5 "worker_001" NX EX 300

# 检查锁
GET chapter_lock:12345:5

# 释放锁
DEL chapter_lock:12345:5

# ==================== 缓存热点数据 ====================

# 小说基础信息缓存
HSET novel_cache:12345 \
    title "仙剑奇侠传" \
    genre "仙侠" \
    status "writing" \
    word_count 45000 \
    chapter_count 15

# 角色基础信息缓存
HSET character_cache:1001 \
    name "李逍遥" \
    role_type "protagonist" \
    importance 5 \
    status "alive"

# 设置缓存过期
EXPIRE novel_cache:12345 3600
EXPIRE character_cache:1001 3600

# ==================== 排行榜/统计 ====================

# 热门小说排行（有序集合）
ZADD novel_ranking:weekly \
    15000 "novel:12345" \
    12000 "novel:12346" \
    8000 "novel:12347"

# 获取前10
ZREVRANGE novel_ranking:weekly 0 9 WITHSCORES

# 用户创作排行
ZADD author_ranking:monthly \
    50000 "user:1" \
    35000 "user:2"

# ==================== 消息队列 ====================

# 生成任务队列
LPUSH novel_generation_queue '{"task_id": 999, "novel_id": 12345, "chapter_id": 6, "priority": 3}'

# 消费者取任务
BRPOP novel_generation_queue 5

# 优先级队列（多个列表）
LPUSH novel_queue:priority:1 '{"task_id": 1000, ...}'  # 高优先级
LPUSH novel_queue:priority:3 '{"task_id": 1001, ...}'  # 普通优先级

# ==================== 发布订阅 ====================

# 订阅小说更新
SUBSCRIBE novel_updates:12345

# 发布更新
PUBLISH novel_updates:12345 '{"event": "chapter_completed", "chapter_id": 5}'

# 订阅用户通知
SUBSCRIBE user_notifications:1

# ==================== 布隆过滤器 ====================

# 检查是否已生成过相似内容
BF.ADD novel_content_filter:12345 "segment_hash_abc123"
BF.EXISTS novel_content_filter:12345 "segment_hash_abc123"

# ==================== 限流器 ====================

# 滑动窗口限流
# 用户每分钟最多10次生成请求
CL.THROTTLE user_rate_limit:1 10 60 1

# ==================== 地理位置（如果小说涉及地图） ====================

# 添加地点
GEOADD novel_world_map:12345 116.4074 39.9042 "长安" 121.4737 31.2304 "苏州"

# 查找附近的地点
GEORADIUS novel_world_map:12345 116.4 39.9 100 km WITHDIST
```

### 5.2 缓存策略

```python
import redis
import json
from functools import wraps
from typing import Optional, Any

class NovelCacheManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # 缓存策略配置
        self.ttl_config = {
            "novel_basic": 3600,        # 小说基础信息 1小时
            "chapter_content": 1800,    # 章节内容 30分钟
            "character_profile": 3600, # 角色档案 1小时
            "generation_status": 300,   # 生成状态 5分钟
            "user_quota": 60,          # 用户限额 1分钟
            "search_results": 600,     # 搜索结果 10分钟
            "style_templates": 7200,   # 风格模板 2小时
        }
    
    # ==================== 基础缓存操作 ====================
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if ttl is None:
            ttl = self.ttl_config.get("default", 3600)
        
        return self.redis.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        return self.redis.delete(key) > 0
    
    def invalidate_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0
    
    # ==================== 小说数据缓存 ====================
    
    def cache_novel_basic(self, novel_id: int, data: Dict) -> bool:
        """缓存小说基础信息"""
        key = f"novel_cache:{novel_id}"
        return self.set(key, data, self.ttl_config["novel_basic"])
    
    def get_novel_basic(self, novel_id: int) -> Optional[Dict]:
        """获取小说基础信息"""
        return self.get(f"novel_cache:{novel_id}")
    
    def invalidate_novel(self, novel_id: int) -> None:
        """失效小说相关缓存"""
        patterns = [
            f"novel_cache:{novel_id}",
            f"novel_chapters:{novel_id}:*",
            f"novel_characters:{novel_id}:*",
        ]
        for pattern in patterns:
            self.invalidate_pattern(pattern)
    
    # ==================== 章节缓存 ====================
    
    def cache_chapter_content(self, chapter_id: int, version: int, content: Dict) -> bool:
        """缓存章节内容"""
        key = f"chapter_cache:{chapter_id}:{version}"
        return self.set(key, content, self.ttl_config["chapter_content"])
    
    def get_chapter_content(self, chapter_id: int, version: int) -> Optional[Dict]:
        """获取章节内容"""
        return self.get(f"chapter_cache:{chapter_id}:{version}")
    
    # ==================== 生成状态缓存 ====================
    
    def cache_generation_status(self, task_id: int, status: Dict) -> bool:
        """缓存生成状态"""
        key = f"generation_status:{task_id}"
        return self.set(key, status, self.ttl_config["generation_status"])
    
    def get_generation_status(self, task_id: int) -> Optional[Dict]:
        """获取生成状态"""
        return self.get(f"generation_status:{task_id}")
    
    def update_generation_progress(self, task_id: int, progress: int, message: str) -> bool:
        """更新生成进度"""
        key = f"generation_progress:{task_id}"
        data = {
            "progress": progress,
            "message": message,
            "updated_at": datetime.now().isoformat()
        }
        return self.set(key, data, self.ttl_config["generation_status"])
    
    # ==================== 用户限额缓存 ====================
    
    def get_user_quota(self, user_id: int) -> Optional[Dict]:
        """获取用户限额"""
        return self.get(f"user_quota:{user_id}")
    
    def update_user_quota(self, user_id: int, quota_type: str, used: int) -> bool:
        """更新用户限额"""
        key = f"user_quota:{user_id}"
        
        # 使用哈希存储
        self.redis.hset(key, f"{quota_type}_used", used)
        self.redis.expire(key, self.ttl_config["user_quota"])
        
        return True
    
    def check_rate_limit(self, user_id: int, action: str, 
                        max_requests: int, window_seconds: int) -> bool:
        """检查速率限制"""
        key = f"rate_limit:{user_id}:{action}"
        
        current = self.redis.get(key)
        if current is None:
            self.redis.setex(key, window_seconds, 1)
            return True
        
        count = int(current)
        if count >= max_requests:
            return False
        
        self.redis.incr(key)
        return True

# 装饰器：自动缓存
def cached(cache_manager: NovelCacheManager, 
          key_prefix: str, 
          ttl: Optional[int] = None,
          invalidate_on: Optional[List[str]] = None):
    """自动缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # 尝试获取缓存
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
```

---

## 第六部分：数据流与业务逻辑

### 6.1 小说生成完整数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户请求   │────▶│   API层     │────▶│  业务逻辑层  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │   MySQL     │            │   MongoDB   │            │   Neo4j     │
            │  事务控制    │            │  内容存储    │            │  关系推理    │
            │             │            │             │            │             │
            │ • 创建任务   │            │ • 读取模板   │            │ • 查询角色   │
            │ • 检查限额   │            │ • 加载配置   │            │ • 情节网络   │
            │ • 状态更新   │            │ • 存储结果   │            │ • 一致性检查 │
            └─────────────┘            └─────────────┘            └─────────────┘
                    │                          │                          │
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │   Redis     │            │  ChromaDB   │            │   LLM API   │
            │  缓存/锁    │            │  语义检索    │            │  生成引擎    │
            │             │            │             │            │             │
            │ • 获取锁    │            │ • 风格匹配   │            │ • 生成内容   │
            │ • 检查状态   │            │ • 相似场景   │            │ • 返回结果   │
            │ • 更新进度   │            │ • 角色声音   │            │             │
            └─────────────┘            └─────────────┘            └─────────────┘
```

### 6.2 核心业务流程代码

```python
class NovelGenerationService:
    def __init__(self,
                 mysql_pool,
                 mongo_db,
                 neo4j_driver,
                 chroma_store,
                 redis_client,
                 llm_client):
        self.mysql = mysql_pool
        self.mongo = mongo_db
        self.neo4j = neo4j_driver
        self.chroma = chroma_store
        self.redis = redis_client
        self.llm = llm_client
        self.cache = NovelCacheManager(redis_client)
    
    async def generate_chapter(self, novel_id: int, chapter_number: int) -> Dict:
        """生成章节完整流程"""
        
        # 1. 获取分布式锁
        lock_key = f"chapter_lock:{novel_id}:{chapter_number}"
        lock = self.redis.set(lock_key, "1", nx=True, ex=300)
        if not lock:
            raise ChapterGenerationError("章节正在生成中，请稍后")
        
        try:
            # 2. 从MySQL获取基础信息（事务）
            async with self.mysql.acquire() as conn:
                async with conn.cursor() as cur:
                    # 检查小说状态
                    await cur.execute(
                        "SELECT status, generation_config FROM novels WHERE id = %s",
                        (novel_id,)
                    )
                    novel = await cur.fetchone()
                    
                    if not novel or novel[0] not in ['writing', 'active']:
                        raise NovelStatusError("小说状态不允许生成")
                    
                    # 检查用户限额
                    await cur.execute(
                        """SELECT monthly_word_used, monthly_word_quota 
                           FROM user_preferences WHERE user_id = 
                           (SELECT user_id FROM novels WHERE id = %s)""",
                        (novel_id,)
                    )
                    quota = await cur.fetchone()
                    
                    if quota[0] >= quota[1]:
                        raise QuotaExceededError("月度字数限额已用完")
                    
                    # 创建生成任务
                    await cur.execute(
                        """INSERT INTO generation_tasks 
                           (novel_id, chapter_id, task_type, status, priority, input_params)
                           VALUES (%s, %s, 'chapter', 1, 3, %s)""",
                        (novel_id, chapter_number, json.dumps({"chapter_number": chapter_number}))
                    )
                    task_id = cur.lastrowid
                    
                    await conn.commit()
            
            # 3. 从MongoDB获取生成配置和模板
            config = await self.mongo.prompt_templates.find_one({
                "template_id": novel[1].get("prompt_template", "default")
            })
            
            # 4. 从Neo4j获取角色关系和世界状态
            with self.neo4j.session() as session:
                # 获取活跃角色
                characters_result = session.run("""
                    MATCH (c:Character)-[:APPEARS_IN]->(s:Scene)
                    WHERE c.novel_id = $novel_id
                    RETURN c.id, c.name, c.current_location, c.current_mood,
                           c.power_level, c.status
                    ORDER BY c.importance DESC
                """, novel_id=novel_id)
                
                characters = [dict(record) for record in characters_result]
                
                # 获取角色关系
                for char in characters:
                    relations_result = session.run("""
                        MATCH (c:Character {id: $char_id})-[r:RELATES_TO]-(other:Character)
                        RETURN other.name, r.type, r.intensity, r.dynamics
                    """, char_id=char["c.id"])
                    
                    char["relations"] = [dict(r) for r in relations_result]
                
                # 获取前序情节
                plot_result = session.run("""
                    MATCH (p:PlotPoint)
                    WHERE p.novel_id = $novel_id AND p.chapter < $chapter
                    RETURN p ORDER BY p.chapter DESC LIMIT 5
                """, novel_id=novel_id, chapter=chapter_number)
                
                previous_plot = [dict(r["p"]) for r in plot_result]
            
            # 5. 从ChromaDB检索相似场景和风格
            chapter_description = f"第{chapter_number}章，{novel[1].get('genre', 'general')}风格"
            embedding = await self.llm.embed(chapter_description)
            
            similar_scenes = self.chroma.search_similar_segments(
                query_text=chapter_description,
                query_embedding=embedding,
                novel_id=novel_id,
                limit=3
            )
            
            style_match = self.chroma.match_style(
                query_embedding=embedding,
                genre=novel[1].get("genre"),
                limit=1
            )
            
            # 6. 构建生成提示
            prompt = self._build_chapter_prompt(
                config=config,
                characters=characters,
                previous_plot=previous_plot,
                similar_scenes=similar_scenes,
                style_match=style_match[0] if style_match else None,
                chapter_number=chapter_number
            )
            
            # 7. 调用LLM生成
            generation_result = await self.llm.generate(
                prompt=prompt,
                model=novel[1].get("model", "gpt-4o"),
                temperature=novel[1].get("temperature", 0.8),
                max_tokens=4000,
                streaming=True
            )
            
            # 8. 解析和验证生成结果
            parsed_content = self._parse_generated_content(generation_result["text"])
            
            # 9. 一致性检查（Neo4j + ChromaDB）
            consistency_issues = await self._check_consistency(
                novel_id=novel_id,
                chapter_content=parsed_content,
                characters=characters
            )
            
            if consistency_issues:
                # 修复或标记
                parsed_content["consistency_notes"] = consistency_issues
            
            # 10. 存储到MongoDB
            content_id = await self.mongo.novel_contents.insert_one({
                "novel_id": novel_id,
                "chapter_id": chapter_number,
                "version": 1,
                "content": parsed_content,
                "generation": {
                    "model": generation_result["model"],
                    "tokens": generation_result["usage"],
                    "prompt": prompt,
                    "generation_time": generation_result["duration"]
                },
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }).inserted_id
            
            # 11. 更新Neo4j图（新情节、角色状态变化）
            with self.neo4j.session() as session:
                # 提取新情节点
                for plot_point in parsed_content.get("plot_points", []):
                    session.run("""
                        CREATE (p:PlotPoint {
                            id: $plot_id,
                            novel_id: $novel_id,
                            chapter: $chapter,
                            type: $type,
                            description: $description,
                            importance: $importance
                        })
                    """, 
                    plot_id=f"plot_{novel_id}_{chapter_number}_{plot_point['index']}",
                    novel_id=novel_id,
                    chapter=chapter_number,
                    type=plot_point["type"],
                    description=plot_point["description"],
                    importance=plot_point.get("importance", 0.5)
                    )
                
                # 更新角色状态
                for char_update in parsed_content.get("character_updates", []):
                    session.run("""
                        MATCH (c:Character {id: $char_id})
                        SET c.current_location = $location,
                            c.current_mood = $mood,
                            c.power_level = $power
                    """,
                    char_id=char_update["character_id"],
                    location=char_update.get("location"),
                    mood=char_update.get("mood"),
                    power=char_update.get("power_level")
                    )
            
            # 12. 添加到ChromaDB向量索引
            for segment in parsed_content.get("segments", []):
                segment_embedding = await self.llm.embed(segment["text"])
                self.chroma.add_chapter_segment(
                    segment_id=f"seg_{content_id}_{segment['index']}",
                    text=segment["text"],
                    novel_id=novel_id,
                    chapter_id=chapter_number,
                    segment_type=segment["type"],
                    characters=segment.get("characters", []),
                    location=segment.get("location", ""),
                    embedding=segment_embedding
                )
            
            # 13. 更新MySQL状态（事务）
            async with self.mysql.acquire() as conn:
                async with conn.cursor() as cur:
                    # 更新章节状态
                    await cur.execute(
                        """UPDATE chapters 
                           SET status = 2, 
                               word_count = %s,
                               generated_at = NOW(),
                               current_version = 1
                           WHERE novel_id = %s AND chapter_number = %s""",
                        (parsed_content["stats"]["total_word_count"], novel_id, chapter_number)
                    )
                    
                    # 创建版本记录
                    await cur.execute(
                        """INSERT INTO chapter_versions 
                           (chapter_id, version_number, content_id, word_count, 
                            model_used, generation_time, is_current, status)
                           VALUES (
                               (SELECT id FROM chapters WHERE novel_id = %s AND chapter_number = %s),
                               1, %s, %s, %s, %s, TRUE, 1
                           )""",
                        (novel_id, chapter_number, str(content_id),
                         parsed_content["stats"]["total_word_count"],
                         generation_result["model"],
                         generation_result["duration"])
                    )
                    
                    # 更新小说统计
                    await cur.execute(
                        """UPDATE novels 
                           SET word_count = word_count + %s,
                               chapter_count = (SELECT COUNT(*) FROM chapters 
                                              WHERE novel_id = %s AND status = 2),
                               generation_count = generation_count + 1,
                               updated_at = NOW()
                           WHERE id = %s""",
                        (parsed_content["stats"]["total_word_count"], novel_id, novel_id)
                    )
                    
                    # 更新用户限额
                    await cur.execute(
                        """UPDATE user_preferences 
                           SET monthly_word_used = monthly_word_used + %s
                           WHERE user_id = (SELECT user_id FROM novels WHERE id = %s)""",
                        (parsed_content["stats"]["total_word_count"], novel_id)
                    )
                    
                    # 完成任务
                    await cur.execute(
                        """UPDATE generation_tasks 
                           SET status = 2, 
                               output_result = %s,
                               tokens_used = %s,
                               generation_time = %s,
                               completed_at = NOW()
                           WHERE id = %s""",
                        (json.dumps({"content_id": str(content_id)}),
                         generation_result["usage"]["total_tokens"],
                         generation_result["duration"],
                         task_id)
                    )
                    
                    await conn.commit()
            
            # 14. 更新Redis缓存
            self.cache.invalidate_novel(novel_id)
            self.cache.cache_generation_status(task_id, {
                "status": "completed",
                "chapter": chapter_number,
                "word_count": parsed_content["stats"]["total_word_count"]
            })
            
            # 15. 发布完成通知
            self.redis.publish(f"novel_updates:{novel_id}", json.dumps({
                "event": "chapter_completed",
                "chapter_number": chapter_number,
                "word_count": parsed_content["stats"]["total_word_count"]
            }))
            
            return {
                "success": True,
                "chapter_number": chapter_number,
                "word_count": parsed_content["stats"]["total_word_count"],
                "content_id": str(content_id),
                "generation_time": generation_result["duration"],
                "consistency_issues": consistency_issues
            }
            
        except Exception as e:
            # 错误处理
            async with self.mysql.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """UPDATE generation_tasks 
                           SET status = 3, 
                               error_message = %s,
                               completed_at = NOW()
                           WHERE id = %s""",
                        (str(e), task_id)
                    )
                    await conn.commit()
            
            raise ChapterGenerationError(f"生成失败: {str(e)}")
            
        finally:
            # 释放锁
            self.redis.delete(lock_key)
    
    async def _check_consistency(self, novel_id: int, 
                                chapter_content: Dict,
                                characters: List[Dict]) -> List[Dict]:
        """检查生成内容的一致性"""
        issues = []
        
        # 1. 角色一致性（ChromaDB）
        for segment in chapter_content.get("segments", []):
            if segment["type"] == "dialogue" and segment.get("speaker"):
                speaker = segment["speaker"]
                speaker_char = next((c for c in characters if c["c.name"] == speaker), None)
                
                if speaker_char:
                    # 检查对话风格一致性
                    consistency = await self.chroma.maintain_character_consistency(
                        character_name=speaker,
                        new_dialogue=segment["text"],
                        threshold=0.6
                    )
                    
                    if not consistency["consistent"]:
                        issues.append({
                            "type": "character_voice",
                            "character": speaker,
                            "message": f"角色'{speaker}'的对话风格可能不一致",
                            "similarity": consistency["similarity"],
                            "reference": consistency.get("reference", "")
                        })
        
        # 2. 情节连贯性（Neo4j）
        with self.neo4j.session() as session:
            # 检查新情节点是否与前文连贯
            for plot_point in chapter_content.get("plot_points", []):
                result = session.run("""
                    MATCH (prev:PlotPoint {novel_id: $novel_id})
                    WHERE prev.chapter < $chapter
                    WITH prev ORDER BY prev.chapter DESC LIMIT 1
                    MATCH (new:PlotPoint {description: $description})
                    WITH prev, new,
                         gds.similarity.cosine(prev.embedding, new.embedding) AS similarity
                    WHERE similarity < 0.3
                    RETURN prev.description AS previous, similarity
                """, 
                novel_id=novel_id,
                chapter=chapter_content.get("chapter_number", 0),
                description=plot_point["description"]
                )
                
                record = result.single()
                if record and record["similarity"] < 0.2:
                    issues.append({
                        "type": "plot_coherence",
                        "message": f"情节点'{plot_point['description']}'与上文连贯性较低",
                        "similarity": record["similarity"]
                    })
        
        # 3. 世界观一致性（简单检查）
        world_rules = chapter_content.get("world_rules", [])
        for segment in chapter_content.get("segments", []):
            # 检查是否违反已建立的世界规则
            # 这里可以扩展为更复杂的规则引擎
            pass
        
        return issues
    
    def _build_chapter_prompt(self, config: Dict, characters: List[Dict],
                            previous_plot: List[Dict], similar_scenes: List[Dict],
                            style_match: Optional[Dict], chapter_number: int) -> str:
        """构建章节生成提示"""
        
        # 角色状态描述
        character_states = "\n".join([
            f"- {char['c.name']}: 位于{char['c.current_location']}, "
            f"心情{char['c.current_mood']}, 实力等级{char['c.power_level']}"
            for char in characters[:5]  # 主要角色
        ])
        
        # 前序情节摘要
        plot_summary = "\n".join([
            f"- 第{plot['chapter']}章: {plot['description']}"
            for plot in previous_plot[:3]
        ])
        
        # 相似场景参考
        scene_references = ""
        if similar_scenes:
            scene_references = "\n参考场景:\n" + "\n".join([
                f"- {scene['text'][:100]}..."
                for scene in similar_scenes[:2]
            ])
        
        # 风格指导
        style_guide = ""
        if style_match:
            style_guide = f"\n风格指导: {style_match['metadata'].get('name', 'default')}"
        
        prompt = f"""请创作第{chapter_number}章。

【角色状态】
{character_states}

【前序情节】
{plot_summary}

【创作要求】
{config.get('structure', {}).get('system_prompt', '请创作精彩的章节内容。')}

{scene_references}
{style_guide}

请确保：
1. 角色行为符合其性格和当前状态
2. 情节与前文连贯
3. 情感基调一致
4. 对话符合角色语言风格
"""
        
        return prompt
    
    def _parse_generated_content(self, text: str) -> Dict:
        """解析生成的内容"""
        # 这里需要实现具体的解析逻辑
        # 将LLM输出解析为结构化数据
        
        # 简化示例
        paragraphs = text.split("\n\n")
        segments = []
        
        for i, para in enumerate(paragraphs):
            if para.strip():
                # 简单分类
                if para.startswith("「") or para.startswith('"'):
                    seg_type = "dialogue"
                elif "。" in para and len(para) > 100:
                    seg_type = "narrative"
                else:
                    seg_type = "description"
                
                segments.append({
                    "index": i,
                    "type": seg_type,
                    "text": para,
                    "word_count": len(para)
                })
        
        return {
            "segments": segments,
            "stats": {
                "total_word_count": sum(s["word_count"] for s in segments),
                "paragraph_count": len(segments),
                "dialogue_count": sum(1 for s in segments if s["type"] == "dialogue"),
                "narrative_count": sum(1 for s in segments if s["type"] == "narrative")
            },
            "plot_points": [],  # 需要进一步提取
            "character_updates": []  # 需要进一步提取
        }
```

---

## 第七部分：性能优化策略

### 7.1 读写分离与分片

```yaml
# MySQL 主从配置
mysql:
  master:
    host: mysql-master
    port: 3306
    role: write
  slaves:
    - host: mysql-slave-1
      port: 3306
      role: read
      weight: 1
    - host: mysql-slave-2
      port: 3306
      role: read
      weight: 1

# MongoDB 分片集群
mongodb:
  shards:
    - rs0/shard0-rs0:27017,shard0-rs1:27017
    - rs1/shard1-rs0:27017,shard1-rs1:27017
  config_servers:
    - config0:27019
    - config1:27019
  mongos:
    - mongos0:27017
    - mongos1:27017

# Neo4j 集群
neo4j:
  core_servers:
    - neo4j-core-1:7687
    - neo4j-core-2:7687
    - neo4j-core-3:7687
  read_replicas:
    - neo4j-read-1:7687
    - neo4j-read-2:7687
```

### 7.2 缓存预热与冷启动

```python
class CacheWarmer:
    def __init__(self, cache_manager: NovelCacheManager, 
                 mysql_pool, mongo_db, neo4j_driver):
        self.cache = cache_manager
        self.mysql = mysql_pool
        self.mongo = mongo_db
        self.neo4j = neo4j_driver
    
    async def warm_novel_cache(self, novel_id: int) -> None:
        """预热小说相关缓存"""
        
        # 1. 缓存基础信息
        async with self.mysql.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM novels WHERE id = %s",
                    (novel_id,)
                )
                novel = await cur.fetchone()
                
                if novel:
                    self.cache.cache_novel_basic(novel_id, dict(novel))
        
        # 2. 缓存角色信息
        async with self.mysql.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM characters WHERE novel_id = %s",
                    (novel_id,)
                )
                characters = await cur.fetchall()
                
                for char in characters:
                    self.cache.set(
                        f"character_cache:{char['id']}",
                        dict(char),
                        3600
                    )
        
        # 3. 缓存最近章节
        async with self.mysql.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT * FROM chapters 
                       WHERE novel_id = %s AND status = 2
                       ORDER BY chapter_number DESC LIMIT 5""",
                    (novel_id,)
                )
                chapters = await cur.fetchall()
                
                for ch in chapters:
                    # 从MongoDB获取内容
                    content = await self.mongo.novel_contents.find_one({
                        "novel_id": novel_id,
                        "chapter_id": ch["chapter_number"],
                        "version": ch["current_version"]
                    })
                    
                    if content:
                        self.cache.cache_chapter_content(
                            ch["id"], 
                            ch["current_version"],
                            content
                        )
    
    async def warm_vector_cache(self, novel_id: int) -> None:
        """预热向量索引"""
        
        # 获取所有章节片段
        contents = await self.mongo.novel_contents.find({
            "novel_id": novel_id
        }).to_list(None)
        
        for content in contents:
            for segment in content.get("content", {}).get("segments", []):
                # 检查是否已在ChromaDB中
                existing = self.chroma.collections["chapter_segments"].get(
                    ids=[f"seg_{content['_id']}_{segment['index']}"]
                )
                
                if not existing or not existing["ids"]:
                    # 生成嵌入并添加
                    embedding = await self.llm.embed(segment["text"])
                    self.chroma.add_chapter_segment(
                        segment_id=f"seg_{content['_id']}_{segment['index']}",
                        text=segment["text"],
                        novel_id=novel_id,
                        chapter_id=content["chapter_id"],
                        segment_type=segment["type"],
                        characters=segment.get("characters", []),
                        location=segment.get("location", ""),
                        embedding=embedding
                    )
```

### 7.3 批量操作优化

```python
class BatchProcessor:
    def __init__(self, mysql_pool, mongo_db, chroma_store):
        self.mysql = mysql_pool
        self.mongo = mongo_db
        self.chroma = chroma_store
    
    async def batch_update_chapter_status(self, 
                                         updates: List[Tuple[int, int, str]]) -> None:
        """批量更新章节状态"""
        
        # MySQL 批量更新
        async with self.mysql.acquire() as conn:
            async with conn.cursor() as cur:
                # 使用 executemany 进行批量更新
                await cur.executemany(
                    "UPDATE chapters SET status = %s WHERE novel_id = %s AND chapter_number = %s",
                    [(status, novel_id, chapter_num) for novel_id, chapter_num, status in updates]
                )
                await conn.commit()
    
    async def batch_insert_vectors(self, 
                                  segments: List[Dict],
                                  embeddings: List[List[float]]) -> None:
        """批量插入向量"""
        
        # ChromaDB 批量添加
        self.chroma.collections["chapter_segments"].add(
            ids=[seg["id"] for seg in segments],
            embeddings=embeddings,
            documents=[seg["text"] for seg in segments],
            metadatas=[seg["metadata"] for seg in segments]
        )
    
    async def batch_migrate_data(self, 
                               source_novel_id: int,
                               target_novel_id: int) -> None:
        """批量迁移数据（复制小说）"""
        
        # 1. MySQL 数据复制
        async with self.mysql.acquire() as conn:
            async with conn.cursor() as cur:
                # 复制小说记录
                await cur.execute(
                    """INSERT INTO novels 
                       (user_id, title, genre, generation_config, status)
                       SELECT user_id, CONCAT(title, ' (副本)'), genre, 
                              generation_config, 'draft'
                       FROM novels WHERE id = %s""",
                    (source_novel_id,)
                )
                new_novel_id = cur.lastrowid
                
                # 复制角色
                await cur.execute(
                    """INSERT INTO characters 
                       (novel_id, name, role_type, importance, personality_traits,
                        background_story, motivation, goal)
                       SELECT %s, name, role_type, importance, personality_traits,
                              background_story, motivation, goal
                       FROM characters WHERE novel_id = %s""",
                    (new_novel_id, source_novel_id)
                )
                
                # 复制章节框架
                await cur.execute(
                    """INSERT INTO chapters 
                       (novel_id, chapter_number, title, plot_point_type)
                       SELECT %s, chapter_number, title, plot_point_type
                       FROM chapters WHERE novel_id = %s""",
                    (new_novel_id, source_novel_id)
                )
                
                await conn.commit()
        
        # 2. MongoDB 数据复制
        async for content in self.mongo.novel_contents.find({"novel_id": source_novel_id}):
            content["novel_id"] = new_novel_id
            content["version"] = 1
            del content["_id"]
            await self.mongo.novel_contents.insert_one(content)
        
        # 3. Neo4j 数据复制
        with self.neo4j.session() as session:
            session.run("""
                MATCH (n {novel_id: $source_id})
                WITH collect(n) AS nodes
                UNWIND nodes AS node
                CREATE (new_node) SET new_node = properties(node)
                SET new_node.novel_id = $target_id,
                    new_node.id = node.id + '_copy'
            """, source_id=source_novel_id, target_id=new_novel_id)
        
        return new_novel_id
```

---

## 总结

这套多数据库架构专为小说生成优化：

### 数据库分工
| 数据库 | 核心职责 | 数据类型 |
|--------|---------|---------|
| **MySQL** | 事务、关系、配置 | 用户、订单、角色基础、章节状态 |
| **MongoDB** | 内容、文档、版本 | 章节内容、角色档案、生成模板 |
| **Neo4j** | 关系、推理、网络 | 角色关系、情节因果、场景连接 |
| **ChromaDB** | 语义、相似度、风格 | 文本向量、风格模板、情节模式 |
| **Redis** | 缓存、状态、队列 | 会话、进度、限额、分布式锁 |

### 核心优势
1. **事务安全**：MySQL 保证核心数据一致性
2. **灵活内容**：MongoDB 存储富文本和复杂结构
3. **智能推理**：Neo4j 支持情节因果和角色关系分析
4. **语义理解**：ChromaDB 实现风格匹配和一致性检查
5. **高性能**：Redis 缓存和队列保证响应速度

### 业务增强
1. **角色一致性**：通过向量检索确保角色声音统一
2. **情节连贯**：图数据库追踪因果链，发现漏洞
3. **风格匹配**：语义检索找到最合适的写作风格
4. **版本管理**：多数据库协同支持章节多版本
5. **实时反馈**：Redis 流式更新生成进度

这套架构让小说生成不仅更快，更智能、更连贯、更有文学性。

---

*文档版本: v1.0*
*更新日期: 2026-04-28*
*作者: 小R (AI Assistant)*
