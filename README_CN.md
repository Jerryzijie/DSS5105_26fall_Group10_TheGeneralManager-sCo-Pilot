# SweaterCo 总经理 Co-Pilot

SweaterCo 是 DSS5105 Track 1 项目，面向小型针织服装工厂的总经理。项目
由能够调用业务工具的 LangGraph Agent、FastAPI 后端、React 管理端和
PostgreSQL 持久化层组成，不是通用聊天机器人。

数据集表示的工厂业务日期是 **2026-04-01**。业务规则必须使用该日期或
调用方明确传入的 `as_of` 日期，不能悄悄改用计算机系统时间。

[English documentation](README.md)

## 当前能力

- 支持 `ADMIN` 和 `EMPLOYEE` 账号认证。
- 工厂数据、管理元数据、用户、Copilot 操作和聊天记录均使用 PostgreSQL。
- 提供检索、判断、追踪、发现、简报和操作类工具。
- 按用户保存会话列表和每轮聊天记录。
- 页面刷新、重新打开浏览器或重启后端后可以恢复历史对话。
- 使用 PostgreSQL LangGraph checkpoint 恢复多轮上下文。
- 模型 thread key 同时包含用户 ID 和会话 UUID，用户与会话之间不会共享记忆。
- 有副作用的操作必须经过 Confirm 或 Dismiss。
- Confirm/Dismiss 的决定会写入聊天轮次，刷新后不会再次出现同一组待处理按钮。
- **Why?** 区域可以展示来源行、工具和计算过程。

## 总体结构

```text
React 管理端
    |
    | Bearer Token + conversation UUID
    v
FastAPI API
    |-- 登录认证与会话所有权检查
    |-- 历史会话 API
    |-- 可检查的路由与可回答性判断
    |-- LangGraph Agent 与业务工具
    `-- 明确的操作确认 API
             |
             v
PostgreSQL: factory_copilot_db
    |-- app          工厂业务数据
    |-- admin_meta   文件导入与数据源元数据
    |-- auth         网站用户
    `-- copilot      操作记录、历史对话与模型 checkpoint
```

日期、总数、风险标记、可行性和简报事实由确定性的 Python 代码计算。LLM
负责选择受支持的工具并解释结果，不得编造数据库中不存在的字段，也不得把
隐藏的业务计算塞进 Prompt。

## 持久化分工

| 数据 | PostgreSQL 位置 | 用途 |
|---|---|---|
| 订单、生产、车间、状态快照 | `app.*` | Agent 查询的工厂事实 |
| 上传历史和数据源 | `admin_meta.*` | 数据管理状态 |
| 账号与账号生命周期 | `auth.users` | 登录、角色、审批和停用 |
| 备注、提醒、监控和审计事件 | `copilot.*` | 已确认的业务操作 |
| 会话列表和可见聊天轮次 | `copilot.conversations`、`copilot.chat_turns` | 前端历史记录 |
| LangGraph 状态 | `copilot.checkpoint_*` | 追问所需的 Human、AI 和 Tool 上下文 |

可见聊天历史与 LangGraph checkpoint 是两套用途不同的持久化：前者负责
重建页面，后者负责恢复 Agent 内部上下文。两者都能跨越后端重启保留。

## 历史会话

以下接口都要求登录：

| 接口 | 用途 |
|---|---|
| `POST /api/conversations` | 为当前用户创建新会话 |
| `GET /api/conversations?limit=50` | 只列出当前用户的会话 |
| `GET /api/conversations/{id}` | 读取本人会话及分页历史窗口 |
| `POST /api/chat` | 在本人会话中调用 Agent，并保存成功的聊天轮次 |

后端不会接受客户端自行声明的用户 ID，而是从访问令牌得到当前用户，验证会话
所有权，并生成：

```text
user:{authenticated_user_id}:conversation:{conversation_uuid}
```

第一条成功问题会成为会话标题。前端使用按用户区分的浏览器键保存最后打开的
会话 ID；用户登录后会恢复该会话，没有历史时则创建一个空会话。

当前范围不包含会话重命名、删除、分享，也不支持多个会话同时在后台请求。
聊天请求进行时会暂时禁止切换会话，避免旧请求的结果显示到新会话中。

## 操作确认

所有有副作用的工具遵循：

```text
提出操作 -> 用户明确 Confirm 或 Dismiss -> 保存决定
```

`POST /api/actions/confirm` 会先验证该操作属于当前用户拥有的聊天轮次，再执行
白名单内的业务操作，并把决定写入该轮 `response_json`。
`POST /api/actions/decline` 会保存拒绝决定，但不会执行该业务操作。刷新页面时，
前端会恢复已解决状态，不会再次要求用户处理同一个操作。

当前白名单包括 `create_watch`、`cancel_watch`、`send_email`、
`add_order_note` 和 `create_reminder`。邮件仍为模拟操作：系统只保存审计结果，
不会通过 SMTP 向外发送邮件。

## 工具

| 类型 | 工具 | 用途 |
|---|---|---|
| Retrieval | `get_order_status` | 查询单个订单；描述对应多个订单时要求提供 ID |
| Retrieval | `get_orders_at_risk` | 查询逾期、停滞和交期紧张的订单 |
| Judgement | `check_feasibility` | 估算新订单是否符合可用产能 |
| Tracing | `trace_order` | 返回来源字段、计算字段和风险依据 |
| Discovery | `find_orders` | 应用经理给出的筛选条件 |
| Discovery | `discover_factory_issues` | 按明确规则排序订单和生产问题 |
| Briefing | `get_morning_briefing` | 返回结构化晨间运营事实 |
| Action | `draft_chase_email` | 生成本地草稿，不发送邮件 |
| Action | `send_email` | 提出并模拟执行已确认的邮件操作 |
| Action | `add_order_note` | 确认后保存订单备注 |
| Action | `create_reminder` | 确认后保存日历提醒记录 |
| Action | `create_watch`、`list_watches`、`cancel_watch` | 管理本地评估的持续监控 |
| Audit | `get_recent_actions` | 读取最近 Copilot 操作记录 |

`production_log` 的粒度是整个工厂的 `date x stage`，不是订单级事件日志。

## Standing Watches

当前实现的监控条件是 `ORDER_INACTIVE_BY_DATE`。系统在调用
`GET /api/watches?as_of=YYYY-MM-DD` 时评估监控规则；它不是后台定时任务，
也不是实时推送系统。

- 监控触发后会生成 `watch_events` 和审计记录。
- 同一个监控不会重复触发。
- 取消操作会保留记录并设置 `status=CANCELLED`，不会删除历史。
- 当前使用 `LocalWatchNotifier`，没有邮件或 Push Notification。
- Reminder 是保存的日历备注，不会像 Watch 一样自动评估条件。

## 项目结构

```text
backend/               FastAPI、LangGraph、工具和运行时服务
frontend/              React、Vite 和 Tailwind 管理端
data/                  来源数据、示例和语义定义
docs/                  架构和工具契约
evaluation/            开发问题集与评测材料
postgresql_database/   数据库生命周期、迁移、种子数据和数据库测试
SQL_related_app/       独立的数据管理中台
tests/                 后端与 API 测试
```

`SQL_related_app` 仍是独立的数据管理组件。它可以更新共享工厂数据，但不负责
Manager 历史对话。

## 运行环境

- 建议使用 Python 3.12 创建项目虚拟环境。
- Node.js 18 或更高版本。
- 本地 PostgreSQL 服务和 `psql`。
- 只有运行 LLM Chat 时才需要 Gemini 或 OpenAI-compatible API Key。

不调用 LLM 的测试不需要 LLM Key；PostgreSQL 集成测试需要已经配置好的本地
测试数据库。

## 本地安装

### 1. 创建 Python 环境

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env
```

在本地 `.env` 中填写数据库密码、至少 32 个字符的 `AUTH_SECRET_KEY`，以及
所选 LLM Provider 的 Key。不要提交 `.env`。

### 2. 准备 PostgreSQL

角色、数据库、迁移、种子导入、验证和权限测试的完整命令参见
[postgresql_database/README.md](postgresql_database/README.md)。核心结构步骤是：

```powershell
.\.venv\Scripts\python.exe -m alembic -c postgresql_database\alembic.ini upgrade head
.\.venv\Scripts\python.exe postgresql_database\bootstrap\setup_checkpoints.py
```

Alembic 和 checkpoint 初始化是明确的数据库管理步骤。FastAPI 启动时不会自动
建表或执行数据库迁移。

### 3. 启动后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

健康检查：[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 4. 启动前端

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

访问 [http://localhost:5173](http://localhost:5173)，Vite 会把 `/api` 代理到
后端 8000 端口。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest postgresql_database\tests -q
npm --prefix frontend run build
git diff --check
```

数据校验与数据库权限测试命令参见数据库 README。

## 当前限制

- Morning Briefing 和 Standing Watches 没有后台调度器。
- 邮件、日历和 Push 集成都只是本地模拟。
- `assess_stage_performance` 尚未成为独立工具；Discovery 和 Briefing 只使用
  已记录的产量基线启发式规则。
- `evaluation/questions.json` 是开发阶段/few-shot 表述模板库，不是独立
  Held-out 准确率测试集。
- 当前一轮 Assistant 消息只按一个决定处理整个 proposed-action 列表，尚不支持
  同一轮多个操作分别 Confirm/Dismiss。

## 协作规则

1. 不得编造存储数据和 `data/semantic_layer.yaml` 中不存在的字段或业务事实。
2. 数字计算与业务规则必须写在确定性的 Python 服务中，不能隐藏在 Prompt 里。
3. 任何有副作用的操作都必须先获得用户明确确认。
4. 不得声称系统已经发送外部邮件或通知。
5. 数据库结构变更必须通过经过审核的 Alembic migration；正常启动应用时不得建表。

修改系统行为前请阅读 [docs/architecture.md](docs/architecture.md) 和
[docs/tool_spec.md](docs/tool_spec.md)。
