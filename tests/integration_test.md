# AI-Novels 前后端联调测试文档

## 测试概述

本文档记录 AI-Novels 项目前后端集成测试的用例和结果。

## 测试环境

- **后端 API**: FastAPI (http://localhost:8000)
- **前端应用**: Vue3 (http://localhost:5173)
- **数据库**: MySQL 8.0, MongoDB 7.0, Neo4j 5.x, ChromaDB

## API 测试

### 1. 任务创建 API

#### Endpoint: `POST /api/tasks`

**请求体**:
```json
{
  "user_id": "test_user_001",
  "task_type": "generate_novel",
  "task_params": {
    "genre": "fantasy",
    "length": "long",
    "theme": "magic academy",
    "chapter_count": 10
  }
}
```

**预期响应**:
```json
{
  "code": 200,
  "data": {
    "task_id": "task_20260313_001",
    "status": "pending",
    "created_at": "2026-03-13T10:00:00Z"
  },
  "message": "Task created successfully"
}
```

**测试结果**: ⏳ 待测试

### 2. 任务状态查询 API

#### Endpoint: `GET /api/tasks/{task_id}/status`

**预期响应**:
```json
{
  "code": 200,
  "data": {
    "task_id": "task_20260313_001",
    "status": "executing",
    "progress": 75,
    "current_stage": "content_generation",
    "estimated_completion": "2026-03-13T10:30:00Z"
  },
  "message": "Status retrieved successfully"
}
```

**测试结果**: ⏳ 待测试

### 3. 任务健康检查 API

#### Endpoint: `GET /tasks/{task_id}/health`

**预期响应**:
```json
{
  "code": 200,
  "data": {
    "task_id": "task_20260313_001",
    "health_status": "healthy",
    "components": {
      "database": "healthy",
      "llm": "healthy",
      "mq": "healthy"
    }
  },
  "message": "Health check passed"
}
```

**测试结果**: ⏳ 待测试

### 4. 小说预览 API

#### Endpoint: `GET /api/tasks/{task_id}/content`

**预期响应**:
```json
{
  "code": 200,
  "data": {
    "task_id": "task_20260313_001",
    "title": "Magic Academy Chronicles",
    "chapters": [
      {
        "chapter_id": "ch_001",
        "title": "The Selection Day",
        "content": "# The Selection Day...\n"
      }
    ],
    "word_count": 15000
  },
  "message": "Content retrieved successfully"
}
```

**测试结果**: ⏳ 待测试

### 5. 配置查询 API

#### Endpoint: `GET /api/config`

**预期响应**:
```json
{
  "code": 200,
  "data": {
    "llm_provider": "ollama",
    "llm_model": "qwen2.5-14b",
    "default_temperate": 0.7,
    "max_tokens": 8192
  },
  "message": "Configuration retrieved successfully"
}
```

**测试结果**: ⏳ 待测试

## 异常处理测试

### 1. 无效的请求参数

**请求**:
```json
{
  "user_id": "test_user",
  "task_type": "invalid_type"
}
```

**预期响应**:
```json
{
  "code": 400,
  "error": "Invalid task type",
  "message": "Supported types: generate_novel, generate_chapter"
}
```

**测试结果**: ⏳ 待测试

### 2. 任务不存在

**请求**: `GET /api/tasks/non_existent_task`

**预期响应**:
```json
{
  "code": 404,
  "error": "Task not found",
  "message": "The requested task does not exist"
}
```

**测试结果**: ⏳ 待测试

### 3. 数据库连接失败

**预期响应**:
```json
{
  "code": 503,
  "error": "Service unavailable",
  "message": "Database connection failed"
}
```

**测试结果**: ⏳ 待测试

## 前端测试

### 1. 任务创建页面

**测试场景**:
- [ ] 用户填写任务配置
- [ ] 点击"提交"按钮
- [ ] 提交成功后显示任务ID
- [ ] 输入验证（空字段检查）

**测试结果**: ⏳ 待测试

### 2. 任务监控页面

**测试场景**:
- [ ] 显示任务进度条
- [ ] 实时更新状态
- [ ] 显示日志信息
- [ ] 支持暂停/恢复操作

**测试结果**: ⏳ 待测试

### 3. 小说预览页面

**测试场景**:
- [ ] 章节列表加载
- [ ] 章节内容显示
- [ ] 阅读体验（字体、行高、颜色主题）
- [ ] 分页导航

**测试结果**: ⏳ 待测试

## 性能测试

### 1. 并发任务创建

**场景**: 同时创建10个任务

**预期**:
- 所有任务在1秒内返回创建响应
- 无数据竞争问题

**测试结果**: ⏳ 待测试

### 2. 大容量内容生成

**场景**: 生成50章，每章3000词的小说

**预期**:
- 总生成时间 < 5分钟
- 中间状态可查询

**测试结果**: ⏳ 待测试

## 测试总结

| 测试类型 | 测试用例数 | 通过 | 失败 | 跳过 |
|---------|-----------|------|------|------|
| API测试 | 5 | 0 | 0 | 5 |
| 异常处理 | 3 | 0 | 0 | 3 |
| 前端测试 | 3 | 0 | 0 | 3 |
| 性能测试 | 2 | 0 | 0 | 2 |
| **总计** | **13** | **0** | **0** | **13** |

**备注**: 所有测试用例已定义，等待实际运行环境部署完成后再执行。

## 下一步

1. 部署完整的测试环境
2. 运行自动化测试脚本
3. 修复发现的问题
4. 更新测试报告
