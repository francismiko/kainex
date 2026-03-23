# Contributing to Kainex

Thank you for your interest in contributing to Kainex! This guide will help you get started.

感谢你有兴趣为 Kainex 做贡献！本指南将帮助你快速上手。

## Table of Contents / 目录

- [Development Environment / 开发环境](#development-environment--开发环境)
- [Code Style / 代码规范](#code-style--代码规范)
- [Branch Naming / 分支命名](#branch-naming--分支命名)
- [Commit Convention / 提交规范](#commit-convention--提交规范)
- [Pull Request Process / PR 流程](#pull-request-process--pr-流程)
- [Strategy Development / 策略开发](#strategy-development--策略开发)
- [Testing / 测试](#testing--测试)

---

## Development Environment / 开发环境

### Prerequisites / 前置依赖

| Tool | Version | Purpose |
|------|---------|---------|
| [Node.js](https://nodejs.org/) | 22+ | Frontend runtime |
| [pnpm](https://pnpm.io/) | 9+ | Node package manager |
| [Python](https://www.python.org/) | 3.12+ | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| [just](https://github.com/casey/just) | latest | Command runner |
| [Docker](https://www.docker.com/) | latest | Optional, for TimescaleDB/Redis |

### Setup / 搭建步骤

```bash
# 1. Fork and clone the repository / Fork 并克隆仓库
git clone https://github.com/<your-username>/kainex.git
cd kainex

# 2. Install all dependencies / 安装所有依赖
just setup
# This runs: pnpm install + uv sync for collector & engine

# 3. Start all services in dev mode / 启动开发服务
just dev

# Or start individual services / 或单独启动某个服务
just web          # Frontend at http://localhost:5173
just engine       # Engine API at http://localhost:8001
just collector    # Data collector
```

### Useful Commands / 常用命令

```bash
just              # List all available commands / 列出所有命令
just py-test      # Run Python tests / 运行 Python 测试
just lint         # Lint frontend / 前端 lint
just typecheck    # Type check frontend / 前端类型检查
just build        # Build frontend / 构建前端
just seed         # Seed sample data / 导入样本数据
```

---

## Code Style / 代码规范

### Python

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

我们使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化。

```bash
# In a service directory / 在服务目录下
cd services/engine  # or services/collector
uv run ruff check .
uv run ruff format .
```

Key rules:
- Line length: 88 characters
- Follow PEP 8 conventions
- Use type hints for function signatures
- Docstrings for public functions and classes

### TypeScript

We use [ESLint](https://eslint.org/) with `typescript-eslint` and React-specific plugins.

我们使用 [ESLint](https://eslint.org/) 配合 `typescript-eslint` 和 React 插件。

```bash
just lint         # Run ESLint
just typecheck    # Run TypeScript type checking
```

Key rules:
- Strict TypeScript (no `any` unless unavoidable)
- React Hooks rules enforced
- Consistent import ordering

---

## Branch Naming / 分支命名

Use the following prefixes for branch names:

请使用以下前缀命名分支：

| Prefix | Purpose / 用途 | Example |
|--------|----------------|---------|
| `feat/` | New feature / 新功能 | `feat/portfolio-rebalancing` |
| `fix/` | Bug fix / 修复 | `fix/backtest-date-range` |
| `docs/` | Documentation / 文档 | `docs/api-reference` |
| `refactor/` | Code refactoring / 重构 | `refactor/strategy-registry` |
| `test/` | Tests / 测试 | `test/paper-trading-edge-cases` |
| `chore/` | Tooling, CI, deps / 工具链 | `chore/upgrade-fastapi` |

---

## Commit Convention / 提交规范

We follow [Conventional Commits](https://www.conventionalcommits.org/).

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### Format / 格式

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types / 类型

| Type | Description |
|------|-------------|
| `feat` | A new feature / 新功能 |
| `fix` | A bug fix / 修复 |
| `docs` | Documentation only / 仅文档 |
| `style` | Formatting, no code change / 格式调整 |
| `refactor` | Code change that neither fixes a bug nor adds a feature / 重构 |
| `test` | Adding or updating tests / 测试 |
| `chore` | Build process, CI, dependencies / 构建、CI、依赖 |
| `perf` | Performance improvement / 性能优化 |

### Scopes / 作用域

Common scopes: `engine`, `collector`, `web`, `shared`, `ci`, `docker`

### Examples / 示例

```
feat(engine): add grid trading strategy
fix(collector): handle baostock weekend disconnect
docs(web): update chart component API reference
test(engine): add backtest edge case for T+1 rule
chore(ci): add ruff linting step
```

---

## Pull Request Process / PR 流程

1. **Create a branch** from `main` using the naming convention above.

   从 `main` 创建分支，遵循上述命名规范。

2. **Make your changes.** Keep PRs focused -- one feature or fix per PR.

   进行修改。保持 PR 聚焦——每个 PR 只做一件事。

3. **Add tests** for any new functionality (see [Testing](#testing--测试)).

   为新功能添加测试（见[测试](#testing--测试)）。

4. **Run checks locally** before pushing:

   推送前在本地运行检查：

   ```bash
   just py-test      # Python tests
   just lint         # Frontend lint
   just typecheck    # Frontend type check
   just build        # Frontend build
   ```

5. **Push and open a PR** against `main`. Fill in the PR template.

   推送并向 `main` 发起 PR，填写 PR 模板。

6. **CI must pass.** The GitHub Actions workflow runs Python tests (collector + engine) and frontend checks (lint + typecheck + build).

   CI 必须通过。GitHub Actions 会运行 Python 测试和前端检查。

7. **Code review.** At least one maintainer will review your PR. Address feedback promptly.

   代码评审。至少一位维护者会审查你的 PR，请及时回复反馈。

---

## Strategy Development / 策略开发

For a quick guide on writing custom strategies, see the **Strategy Development** section in the [README](README.md#strategy-development).

策略开发的快速指南请参见 [README](README.md#strategy-development) 中的 **Strategy Development** 部分。

Key points:
- Subclass `AbstractStrategy` (or `KainexStrategy` for NautilusTrader integration)
- Place your strategy in `services/engine/src/engine/strategies/examples/`
- Register it in `engine/strategies/__init__.py`
- Include both unit tests and a backtest integration test

要点：
- 继承 `AbstractStrategy`（或 `KainexStrategy` 用于 NautilusTrader 集成）
- 将策略放在 `services/engine/src/engine/strategies/examples/`
- 在 `engine/strategies/__init__.py` 中注册
- 包含单元测试和回测集成测试

---

## Testing / 测试

**All new features and bug fixes must include tests.** / **所有新功能和 Bug 修复都必须包含测试。**

### Python Tests

```bash
# Run all Python tests / 运行所有 Python 测试
just py-test

# Run tests for a specific service / 运行指定服务的测试
cd services/engine && uv run pytest
cd services/collector && uv run pytest

# Run a specific test file / 运行指定测试文件
cd services/engine && uv run pytest tests/test_engine.py

# Run with verbose output / 详细输出
cd services/engine && uv run pytest -v
```

Test files are located in:
- `services/collector/tests/` -- Data source, model, and storage tests
- `services/engine/tests/` -- Engine, API, and integration tests

### Frontend Tests

```bash
just lint         # ESLint checks
just typecheck    # TypeScript type checks
just build        # Build verification (catches import errors, etc.)
```

### What to Test / 测试内容

| Area | What to test |
|------|-------------|
| Strategies | Signal generation, edge cases, parameter validation |
| Engine | Backtest execution, PnL calculation, risk limit enforcement |
| Collector | Data source parsing, storage writes, error handling |
| API | Endpoint responses, validation errors, WebSocket messages |
| Frontend | Type correctness (via typecheck), lint compliance |

---

## Questions? / 有问题？

Feel free to open an [issue](https://github.com/francismiko/kainex/issues) or start a [discussion](https://github.com/francismiko/kainex/discussions).

欢迎提 [Issue](https://github.com/francismiko/kainex/issues) 或发起 [讨论](https://github.com/francismiko/kainex/discussions)。
