# Contributing to AI-Novels

感谢您对 AI-Novels 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 报告问题
- 提交功能建议
- 改进文档
- 提交代码修复
- 添加新功能

## 开发环境设置

1. Fork 并克隆仓库
```bash
git clone https://github.com/Ryan-0625/AI-Novels.git
cd AI-Novels
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境
```bash
cp config/.env.example config/.env
# 编辑 config/.env 填入你的配置
```

## 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 格式（不影响代码运行的变动）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试
- `chore`: 构建过程或辅助工具的变动

### 示例

```
feat(agent): add quality checker agent

Implement quality checker agent for content validation.
Support multiple quality metrics including coherence and style.

Closes #123
```

## 代码规范

- 遵循 PEP 8 规范
- 使用类型注解
- 添加必要的文档字符串
- 保持代码简洁清晰

## Pull Request 流程

1. 确保代码通过所有测试
2. 更新相关文档
3. 提交 PR 前 rebase 到最新 main 分支
4. 填写清晰的 PR 描述

## 问题报告

提交 Issue 时请包含：

- 问题描述
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python 版本、操作系统等）

## 联系方式

如有疑问，欢迎通过 Issue 或邮件联系我们。

再次感谢您的贡献！
