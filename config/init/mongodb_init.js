// AI-Novels MongoDB Initialization Script
//==========================================================

use ai_novels;

// 1. world_bible 集合 - 世界观、魔法系统、地理、势力
//==========================================================
db.world_bible.createIndex({ world_id: 1 }, { unique: true });
db.world_bible.createIndex({ category: 1 });
db.world_bible.createIndex({ tags: 1 });
db.world_bible.createIndex({ updated_at: -1 });

// 创建集合的示例文档（用于验证）
db.world_bible.insertOne({
    world_id: "wb_001",
    name: "测试世界观",
    category: "magic",
    public_description: "世界表象描述",
    secret_truth: "隐藏真相",
    unspoken_tension: "潜在冲突",
    tags: ["测试", "示例"],
    created_at: new Date(),
    updated_at: new Date()
});
db.world_bible.deleteMany({ world_id: "wb_001" });

// 2. characters 集合 - 角色档案
//==========================================================
db.characters.createIndex({ char_id: 1 }, { unique: true });
db.characters.createIndex({ name: 1 });
db.characters.createIndex({ archetype: 1 });
db.characters.createIndex({ core_drive: 1 });
db.characters.createIndex({ updated_at: -1 });

db.characters.insertOne({
    char_id: "char_001",
    name: "测试角色",
    aliases: [],
    age_visual: 25,
    age_real: 25,
    gender: "male",
    archetype: "hero",
    core_drive: "核心驱动力",
    core_wound: "核心创伤",
    voice_style: "说话风格",
    base_profile: {
        name: "测试角色",
        aliases: [],
        age_visual: 25,
        age_real: 25,
        gender: "male"
    },
    narrative_core: {
        archetype: "hero",
        core_drive: "核心驱动力",
        core_wound: "核心创伤",
        voice_style: "说话风格"
    },
    dynamic_attributes: {
        current_state: "初始状态",
        emotional_memories: []
    },
    created_at: new Date()
});
db.characters.deleteMany({ char_id: "char_001" });

// 3. outlines 集合 - 大纲结构
//==========================================================
db.outlines.createIndex({ outline_id: 1 }, { unique: true });
db.outlines.createIndex({ "nodes.0.node_id": 1 });
db.outlines.createIndex({ created_at: -1 });

db.outlines.insertOne({
    outline_id: "ol_001",
    project_name: "测试小说",
    nodes: [
        {
            node_id: "node_001",
            node_type: "vol",
            title: "第一卷",
            arc_goals: ["目标1", "目标2"],
            emotional_trajectory: ["平静", "紧张"],
            pacing: 5
        }
    ],
    created_at: new Date()
});
db.outlines.deleteMany({ outline_id: "ol_001" });

// 4. manuscripts 集合 - 章节手稿
//==========================================================
db.manuscripts.createIndex({ manuscript_id: 1 }, { unique: true });
db.manuscripts.createIndex({ outline_id: 1 });
db.manuscripts.createIndex({ chapter_id: 1 });
db.manuscripts.createIndex({ created_at: -1 });
db.manuscripts.createIndex({ "content.word_count": -1 });

db.manuscripts.insertOne({
    manuscript_id: "ms_001",
    outline_id: "ol_001",
    chapter_id: "ch_001",
    content: {
        markdown_text: "# 章节标题\n\n内容",
        word_count: 3000,
        language: "Chinese"
    },
    metadata: {
        pacing: 5,
        hooks: [],
        conflicts: [],
        characters: []
    },
    feedback: [],
    created_at: new Date()
});
db.manuscripts.deleteMany({ manuscript_id: "ms_001" });

// 5. narrative_hooks 集合 - 叙事钩子
//==========================================================
db.narrative_hooks.createIndex({ hook_id: 1 }, { unique: true });
db.narrative_hooks.createIndex({ hook_type: 1 });
db.narrative_hooks.createIndex({ status: 1 });
db.narrative_hooks.createIndex({ intensity: -1 });
db.narrative_hooks.createIndex({ created_at: -1 });

db.narrative_hooks.insertOne({
    hook_id: "hook_001",
    hook_type: "mystery",
    hook_text: "钩子文本",
    intensity: 7,
    status: "open",
    created_chapter: "ch_001",
    resolved_chapter: null,
    related_entities: {
        characters: [],
        locations: [],
        objects: []
    },
    created_at: new Date()
});
db.narrative_hooks.deleteMany({ hook_id: "hook_001" });

// 6. conflicts 集合 - 冲突记录
//==========================================================
db.conflicts.createIndex({ conflict_id: 1 }, { unique: true });
db.conflicts.createIndex({ status: 1 });
db.conflicts.createIndex({ conflict_type: 1 });
db.conflicts.createIndex({ intensity: -1 });
db.conflicts.createIndex({ created_at: -1 });

db.conflicts.insertOne({
    conflict_id: "conf_001",
    conflict_type: "character",
    conflict_text: "冲突描述",
    intensity: 6,
    status: "active",
    involved_characters: ["char_001", "char_002"],
    resolution: null,
    escalation_level: 1,
    created_at: new Date(),
    updated_at: new Date()
});
db.conflicts.deleteMany({ conflict_id: "conf_001" });

// 7. character_memories 集合 - 角色记忆（向量存储ID）
//==========================================================
db.character_memories.createIndex({ char_id: 1 });
db.character_memories.createIndex({ memory_id: 1 }, { unique: true });
db.character_memories.createIndex({ created_at: -1 });

// 8. generation_queue 集合 - 生成队列
//==========================================================
db.generation_queue.createIndex({ queue_id: 1 }, { unique: true });
db.generation_queue.createIndex({ status: 1 });
db.generation_queue.createIndex({ priority: -1 });
db.generation_queue.createIndex({ created_at: -1 });

// 9. task_status 集合 - 任务状态快照
//==========================================================
db.task_status.createIndex({ task_id: 1 }, { unique: true });
db.task_status.createIndex({ updated_at: -1 });

// 性能优化：启用マージ（MongoDB 6.0+）
db.adminCommand({ setParameter: 1, internalQueryExecMaxBlockingSortBytes: 33554432 });

// 输出创建结果
print("MongoDB collections created successfully:");
db.getCollectionNames().forEach(col => print("  - " + col));
