-- AI-Novels MySQL Database Initialization
--==========================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ai_novels CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_novels;

-- 小说生成任务表
--==========================================================
CREATE TABLE IF NOT EXISTS novel_tasks (
    task_id VARCHAR(64) PRIMARY KEY COMMENT '任务唯一ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    task_type VARCHAR(32) NOT NULL COMMENT '任务类型：generate_novel, generate_chapter, etc.',
    task_status VARCHAR(16) DEFAULT 'pending' COMMENT '任务状态：pending, initializing, executing, completed, failed, cancelled',
    task_config JSON NOT NULL COMMENT '任务配置JSON',
    output_path VARCHAR(512) DEFAULT NULL COMMENT '输出路径',
    progress FLOAT DEFAULT 0.0 COMMENT '进度百分比（0-100）',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    current_stage VARCHAR(64) DEFAULT NULL COMMENT '当前执行阶段',
    total_stages INT DEFAULT 0 COMMENT '总阶段数',
    current_stage_idx INT DEFAULT 0 COMMENT '当前阶段索引',
    start_time DATETIME DEFAULT NULL COMMENT '开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '结束时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (task_status),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='小说生成任务表';

-- 生成日志表
--==========================================================
CREATE TABLE IF NOT EXISTS generation_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    task_id VARCHAR(64) NOT NULL COMMENT '关联的任务ID',
    agent_type VARCHAR(64) DEFAULT NULL COMMENT '智能体类型',
    action VARCHAR(128) DEFAULT NULL COMMENT '执行的动作',
    input_data LONGTEXT DEFAULT NULL COMMENT '输入数据（JSON格式）',
    output_data LONGTEXT DEFAULT NULL COMMENT '输出数据（JSON格式）',
    duration_ms INT DEFAULT NULL COMMENT '执行耗时（毫秒）',
    status VARCHAR(16) DEFAULT 'success' COMMENT '执行状态：success, failed, skipped',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at),
    INDEX idx_agent_type (agent_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生成日志表';

-- 阶段任务跟踪表（用于断点续传）
--==========================================================
CREATE TABLE IF NOT EXISTS stage_tasks (
    stage_id VARCHAR(64) PRIMARY KEY COMMENT '阶段任务ID',
    task_id VARCHAR(64) NOT NULL COMMENT '关联的任务ID',
    stage_name VARCHAR(64) NOT NULL COMMENT '阶段名称',
    stage_status VARCHAR(16) DEFAULT 'pending' COMMENT '阶段状态',
    input_data JSON DEFAULT NULL COMMENT '阶段输入',
    output_data JSON DEFAULT NULL COMMENT '阶段输出',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    last_failed_error TEXT DEFAULT NULL COMMENT '最后失败错误',
    started_at DATETIME DEFAULT NULL COMMENT '开始时间',
    completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_stage_status (stage_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='阶段任务跟踪表';

-- 任务错误历史表
--==========================================================
CREATE TABLE IF NOT EXISTS task_error_history (
    error_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '错误ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    error_stage VARCHAR(64) NOT NULL COMMENT '错误阶段',
    error_type VARCHAR(64) NOT NULL COMMENT '错误类型',
    error_message TEXT NOT NULL COMMENT '错误信息',
    error_stack TEXT DEFAULT NULL COMMENT '错误堆栈',
    recovered BOOLEAN DEFAULT FALSE COMMENT '是否已恢复',
    recovery_time DATETIME DEFAULT NULL COMMENT '恢复时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_error_stage (error_stage),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务错误历史表';

-- 系统配置表
--==========================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(64) PRIMARY KEY COMMENT '配置键',
    config_value JSON NOT NULL COMMENT '配置值',
    config_type VARCHAR(32) NOT NULL COMMENT '配置类型',
    description VARCHAR(255) DEFAULT NULL COMMENT '配置描述',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 插入默认系统配置
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
    ('llm_settings', '{"default_provider": "ollama", "default_temperature": 0.7, "default_max_tokens": 8192}', 'llm', 'LLM默认设置'),
    ('agent_models', '{"coordinator": "qwen2.5-14b", "content_generator": "qwen2.5-7b", "quality_checker": "qwen2.5-7b"}', 'agent', '智能体默认模型'),
    ('generation_rules', '{"default_word_count": 3000, "max_retries": 3, "parallel_chapters": 1}', 'generation', '生成规则');

-- 查看创建结果
SELECT 'MySQL数据库初始化完成' AS status;
SELECT '表创建列表:' AS info;
SHOW TABLES;
