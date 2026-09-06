# Graphics Engine Radar — 部署说明书

> 适用版本:v0.1(MVP)。**推荐:§1 内嵌数据库模式**(Windows/macOS/Linux 三平台命令完全一致,无需 Docker/WSL/手动装库)。
> 其他路径:§2 macOS/Linux 原生(本机当前运行方式)、§3 Docker Compose、§3.5 Windows 专项说明。

---

## 0. 快速速查(已部署机器)

```bash
cd ~/Documents/AIWork/GraphicsEngineRadar
uv run python scripts/service.py start   # 启动 API + Web(幂等;status 查看 / stop 停止 / restart 重启)
uv run python scripts/pipeline.py        # 采集 → 管线 → 趋势 → 日报(幂等,跨平台)
open http://localhost:8301               # 查看界面
```

新机器最简部署(全平台统一,无需 Docker/WSL/装库,见 §1a):

```bash
uv sync --all-packages && uv run python scripts/embedded_db.py start   && uv run radar-collector sync-config && uv run python scripts/pipeline.py
```

界面入口:

| 页面 | 地址 |
|---|---|
| 首页(今日精选 / 正在加速 / 重大演进) | http://localhost:8301 |
| 全部动态 | http://localhost:8301/events |
| 趋势 | http://localhost:8301/trends |
| 主题(示例 WebGPU) | http://localhost:8301/topics/webgpu |
| 对象(示例 wgpu) | http://localhost:8301/objects/wgpu |
| 日报 / 周报 / 月报 | http://localhost:8301/digest?kind=daily|weekly|monthly |
| API 根 | http://localhost:8300(交互文档 /docs) |

日志:`data/logs/{api,web}.log`(service.py 托管时)或 `/tmp/radar-api.log`、`/tmp/radar-web.log`;数据库日志 `~/gr-pg/pg.log`(§2 原生库)。

---

## 1. 前置条件

| 组件 | 用途 | 检查命令 |
|---|---|---|
| uv ≥ 0.5 | Python 环境与 workspace 依赖 | `uv --version` |
| Node.js ≥ 20 + npm | Web 前端 | `node --version` |
| PostgreSQL 17 + pgvector 0.8 | 数据库 | 见 §2.1(或直接用 §1a 内嵌模式;Windows 见 §3.5) |
| gh CLI(可选但推荐) | 提供 GitHub Token,避免 60 次/时限流 | `gh auth status` |
| Docker(可选,路径 B/Windows 方案1) | 服务器与 Windows 部署 | `docker --version` |

> ⚠️ 本机未安装 Docker 不影响任何功能——路径 A 完全不依赖 Docker。
> 如需路径 B,先安装: `brew install --cask docker`(Docker Desktop)或 `brew install orbstack`(OrbStack,更轻量),安装后启动一次并确认 `docker --version` 可用。

---

## 1a. 推荐方案:内嵌数据库模式(全平台统一,最简单)

原理:用 pip 包 `pgserver`(内置 PostgreSQL 17 + pgvector 二进制,含 Windows/macOS x86/macOS ARM/Linux wheel)。
数据库就是项目目录下一个普通文件夹,不需要安装 PostgreSQL、不需要 Docker/WSL、不需要编译。

**前置:只有 uv 和 Node.js 两个**(Windows 用官方安装包或 `winget install astral-sh.uv`、`winget install openjs.nodejs`)。

```bash
uv sync --all-packages                        # 依赖(含内嵌数据库)
uv run python scripts/embedded_db.py start    # 启动内嵌库 + 建库 + 建表 + 写 .env(幂等)
uv run radar-collector sync-config            # 装载监控配置
uv run python scripts/pipeline.py             # 采集 → 管线 → 趋势 → 日报

# 起服务(两个终端)
uv run uvicorn radar_api.app:app --port 8300          # API
cd apps/web && npm install && npm run dev             # Web → http://localhost:8301
```

数据目录:`<项目>/data/pgdata`(可用环境变量 `GRADAR_DATA_DIR` 改)。数据库管理命令:

```bash
uv run python scripts/embedded_db.py status   # running / stopped
uv run python scripts/embedded_db.py uri      # 打印 SQLAlchemy 连接串
uv run python scripts/embedded_db.py stop     # 停止(幂等)
```

说明:
- `start` 是幂等的:已启动则只校验并补齐(建库/扩展/迁移),可放心重复执行。
- 数据仍 100% 是 PostgreSQL + pgvector,与 Docker/原生方式完全等价,`.env` 的
  `DATABASE_URL` 由脚本自动写入(会覆盖已有值,注意备份)。
- 生产/多用户部署仍建议用 §2/§3 的独立数据库形态;内嵌模式面向个人与开发机。

### 1b. 服务的启动 / 终止 / 状态(跨平台)

API 与 Web 由统一的服务脚本管理(PID 文件在 `data/services/`,日志在 `data/logs/`):

```bash
uv run python scripts/service.py start      # 后台启动 API(:8300)+ Web(:8301)
uv run python scripts/service.py status     # 查看运行状态(含数据库提示)
uv run python scripts/service.py restart
uv run python scripts/service.py stop       # 停止(含子进程,Windows/macOS/Linux 通用)
```

完整的一次「开机 → 出数据 → 关机」循环:

```bash
uv run python scripts/embedded_db.py start   # 1. 数据库
uv run radar-collector sync-config           # 2. 监控配置(仅首次/配置变更后)
uv run python scripts/service.py start       # 3. API + Web
uv run python scripts/pipeline.py            # 4. 采集与情报生产(日常重复)
uv run python scripts/service.py stop        # 5. 停服务
uv run python scripts/embedded_db.py stop    # 6. 停数据库
```

前台运行(想看实时日志时):两个终端分别执行
`uv run uvicorn radar_api.app:app --port 8300` 和 `cd apps/web && npm run dev`,`Ctrl+C` 即停止。

## 2. 路径 A:macOS/Linux 原生部署(独立数据库)

### 2.1 PostgreSQL 17 + pgvector(一次性;若用 §1a 内嵌模式可跳过本节)

macOS 上 brew 对 postgresql@17 依赖的 openssl@3 新版本没有 x86_64 bottle,会退化为源码编译且极慢,因此采用 **EDB 官方二进制包**:

```bash
mkdir -p ~/gr-pg && cd ~/gr-pg
# 下载(约 360MB,EDB CDN 较快)
curl -O https://get.enterprisedb.com/postgresql/postgresql-17.6-1-osx-binaries.zip
unzip -q postgresql-17.6-1-osx-binaries.zip    # 得到 pgsql/

# 初始化并启动(端口 5432,用户 radar,trust 本地认证)
~/gr-pg/pgsql/bin/initdb -D ~/gr-pg/data -U radar --auth=trust -E UTF8
~/gr-pg/pgsql/bin/pg_ctl -D ~/gr-pg/data -o "-p 5432" -l ~/gr-pg/pg.log start
~/gr-pg/pgsql/bin/psql -U radar -d postgres -c "CREATE DATABASE radar;"
~/gr-pg/pgsql/bin/psql -U radar -d postgres -c "ALTER USER radar PASSWORD 'radar';"
```

编译 pgvector 扩展(需要 Xcode Command Line Tools 的 clang;注意 EDB 的 pg_config 自带
universal-arch/坏 sysroot 标志,必须按下面参数覆盖):

```bash
git clone --depth 1 https://github.com/pgvector/pgvector.git ~/gr-pg/pgvector
cd ~/gr-pg/pgvector
make -j4 OPTFLAGS="" COPT="-O2" \
     CPPFLAGS="-I$HOME/gr-pg/pgsql/include" LDFLAGS="" \
     PG_CONFIG="$HOME/gr-pg/pgsql/bin/pg_config"
make install OPTFLAGS="" COPT="-O2" \
     CPPFLAGS="-I$HOME/gr-pg/pgsql/include" LDFLAGS="" \
     PG_CONFIG="$HOME/gr-pg/pgsql/bin/pg_config"
~/gr-pg/pgsql/bin/psql -U radar -d radar -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

验证:`SELECT extversion FROM pg_extension WHERE extname='vector';` 应返回 0.8.x。

> Linux 服务器无需这些 workaround,`apt install postgresql-17 postgresql-17-pgvector` 即可。

### 2.2 后端

```bash
cd ~/Documents/AIWork/GraphicsEngineRadar
uv sync --all-packages                     # Python 3.12 venv + workspace 全部包
cp .env.example .env                       # 按需修改(默认连 localhost:5432 即本机默认)
uv run alembic upgrade head                # 建表(11 张表)
uv run python tools/gen_configs.py         # (可选)重新生成监控 YAML
uv run radar-collector sync-config         # 装载 125 对象 / 28 主题 / 116 来源
```

`.env` 关键项:

```bash
DATABASE_URL=postgresql+psycopg://radar:radar@localhost:5432/radar
GITHUB_TOKEN=            # 建议填 gh auth token 的输出;留空则受 60 次/时限流
LLM_API_KEY=             # 留空 = 启发式分析器;填 OpenAI 兼容 key 即切换真实 LLM
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### 2.3 前端

```bash
cd apps/web
npm install
npm run dev        # 开发模式,端口 8301
# 生产模式: npm run build && npm run start
```

### 2.4 启动与数据生产

```bash
uv run python scripts/service.py start   # API + Web(幂等)
uv run python scripts/pipeline.py        # 采集 → 管线 → 趋势 → 三种日报
```

服务的启动/终止/状态统一用 §1b 的 `scripts/service.py`;
数据库启停用 `~/gr-pg/pgsql/bin/pg_ctl -D ~/gr-pg/data start|stop`。
首次部署执行顺序必须是:§2.1 → §2.2 → `service.py start` → `pipeline.py`。

---

## 3. 路径 B:Docker Compose(服务器)

先安装 Docker(见 §1 提示),然后:

```bash
docker compose up -d --build           # postgres(pgvector 镜像) + api + web
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python -m radar_collector.cli sync-config
docker compose exec -e GITHUB_TOKEN="$GITHUB_TOKEN" api \
  uv run python -m radar_collector.cli run-all
# 管线与日报(容器内执行):
docker compose exec api uv run python -m radar_intelligence.cli process
docker compose exec api uv run python -m radar_intelligence.cli trends
docker compose exec api uv run python -m radar_intelligence.cli digest --kind daily
```

端口:Web `8301`、API `8300`、Postgres `5433`(宿主机映射)。
容器内 `.env` 通过 compose environment 注入,支持 `GITHUB_TOKEN`、`LLM_API_KEY` 等。

服务生命周期(Docker 路径):

```bash
docker compose ps                     # 状态
docker compose logs -f api web        # 实时日志
docker compose restart api web        # 重启服务
docker compose stop                   # 终止(保留容器与数据卷)
docker compose start                  # 再启动
docker compose down                   # 终止并删除容器(数据卷 pgdata 保留)
docker compose down -v                # ⚠️ 连数据卷一起删除(危险)
```

---

## 3.5 Windows 平台部署

Windows 上共四条路:最简单的是 §1a 内嵌数据库模式(与 macOS/Linux 命令完全一致,无 Docker/WSL/编译);若想要容器化再用下列方案。推荐顺序:**§1a > 方案 1(Docker)> 方案 2(WSL2)> 方案 3(原生)**。
所有方案中,数据生产都只需一条命令(跨平台脚本,无需 bash):

```powershell
uv run python scripts/pipeline.py     # 采集 → 管线 → 趋势 → 三种日报(幂等)
```

### 方案 1:Docker Desktop(最简单,推荐)

前置:安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
(需 WSL2 后端,安装器会自动启用),然后:

```powershell
cd C:\path\to\GraphicsEngineRadar
docker compose up -d --build          # 一次起齐 postgres(pgvector) + api + web
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python -m radar_collector.cli sync-config
docker compose exec -e GITHUB_TOKEN="$env:GITHUB_TOKEN" api uv run python -m radar_collector.cli run-all
docker compose exec api uv run python -m radar_intelligence.cli process
docker compose exec api uv run python -m radar_intelligence.cli trends
docker compose exec api uv run python -m radar_intelligence.cli digest --kind daily
```

浏览器打开 `http://localhost:8301`。数据库、端口全部由 compose 托管,Windows 上不需要装
PostgreSQL/Python/Node,唯一前置就是 Docker 本身。

### 方案 2:WSL2(Ubuntu)——不想装 Docker 时的推荐路径

管理员 PowerShell 执行 `wsl --install -d Ubuntu`(装完重启一次),之后在 WSL 里完全按 Linux
路径走,比纯 Windows 原生简单得多(apt 直接装 postgresql + pgvector,免去 MSVC 编译):

```bash
sudo apt update && sudo apt install -y postgresql-16 postgresql-16-pgvector git curl
sudo -u postgres psql -c "CREATE USER radar PASSWORD 'radar'; CREATE DATABASE radar OWNER radar;"
# 安装 uv 与 Node(WSL 内)
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
# 项目放入 WSL 文件系统(如 ~/GraphicsEngineRadar)后:
uv sync --all-packages
uv run alembic upgrade head
uv run radar-collector sync-config
# 终端1: uv run uvicorn radar_api.app:app --port 8300
# 终端2: cd apps/web && npm install && npm run dev
# 终端3: uv run python scripts/pipeline.py
```

Windows 浏览器直接访问 `http://localhost:8301`(WSL2 端口自动转发)。
`.env` 数据库连接串用 `postgresql+psycopg://radar:radar@localhost:5432/radar`。

### 方案 3:纯 Windows 原生(可行,步骤最多)

```powershell
# 1) PostgreSQL 17:EDB 图形安装器(https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
#    安装时记住密码;用 pgAdmin/psql 创建用户 radar 与数据库 radar
# 2) pgvector:安装 "Visual Studio 2022 Build Tools"(勾选 C++ 工作负载)后,在
#    "x64 Native Tools Command Prompt" 中:
git clone --depth 1 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win PG_CONFIG="C:\Program Files\PostgreSQL\17\bin\pg_config"
nmake /F Makefile.win install PG_CONFIG="C:\Program Files\PostgreSQL\17\bin\pg_config"
# 3) psql 中执行: CREATE EXTENSION vector;
# 4) Python 3.12 与 Node 22 官方安装器;项目目录内:
uv sync --all-packages
uv run alembic upgrade head
uv run radar-collector sync-config
# 终端1: uv run uvicorn radar_api.app:app --port 8300
# 终端2: cd apps\web ; npm install ; npm run dev
# 终端3: uv run python scripts\pipeline.py
```

`.env` 示例(Windows 同样适用):

```bash
DATABASE_URL=postgresql+psycopg://radar:radar@localhost:5432/radar
GITHUB_TOKEN=<gh auth token 的输出>
LLM_API_KEY=
```

Windows 注意事项:
- 一切命令在 **PowerShell** 中执行;`scripts/*.sh` 是 macOS/Linux 用的,Windows 用
  `scripts/pipeline.py`(跨平台)+ 两条终端命令分别起 API 与 Web。
- 防火墙首次会询问放行 python/node,选择"专用网络"允许即可。
- `gh auth login` 一次后 `gh auth token` 可取 token;没有 gh 就手动填 GITHUB_TOKEN。

---

## 4. 大模型(LLM)接入说明

管线 6 个阶段(候选检测 / 事件归并 / 技术分析 / 主题映射 / 影响评估 / 日报)都有独立 Prompt。
**不配置任何 LLM 时以确定性启发式分析器运行**(零成本、可用);配置后自动切换为真实 LLM,
所有判断落 `ai_executions` 表(model / prompt_version / input_hash / output / 失败信息)。

### 4.1 三种接入方式

| 方式 | LLM_PROVIDER | 前置 | 费用 |
|---|---|---|---|
| Claude Code CLI(推荐) | `claude-cli` | 已安装并登录 `claude` 命令 | Claude 订阅内 |
| Codex CLI | `codex-cli` | 已安装并登录 `codex` 命令 | ChatGPT 账号内 |
| OpenAI 兼容 HTTP | `openai`(默认) | `LLM_API_KEY` | 按 API 计费 |

方式 1/2 **直接支持调用 Claude 与 Codex 执行**,复用你本机 CLI 的登录态,无需 API Key。
系统调用方式:`claude -p "<prompt>"` 与 `codex exec --skip-git-repo-check "<prompt>"`,
输出经 JSON 提取 + Pydantic 严格校验后进入下一阶段,失败自动回落启发式并记录错误。

### 4.2 配置示例(写入 `.env` 后重启 API/管线进程生效)

```bash
# Claude CLI(订阅内使用)
LLM_PROVIDER=claude-cli
LLM_MODEL=                          # 留空=CLI 默认;如 claude-sonnet-4-5

# Codex CLI
LLM_PROVIDER=codex-cli
LLM_MODEL=gpt-5.1-codex             # 留空=CLI 默认模型

# OpenAI 官方
LLM_PROVIDER=openai
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Anthropic 官方(OpenAI 兼容端点,注意 key 前缀 sk-ant-)
LLM_API_BASE=https://api.anthropic.com/v1
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-5

# OpenRouter(可路由到 Claude / GPT / Gemini 全系)
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
LLM_MODEL=anthropic/claude-sonnet-4.5

# DeepSeek / 通义 / 智谱 / Kimi(同为 OpenAI 兼容,只换 BASE/MODEL)
# DeepSeek:  https://api.deepseek.com/v1          deepseek-chat
# 通义:      https://dashscope.aliyuncs.com/compatible-mode/v1   qwen-plus
# 智谱/Z.ai: https://open.bigmodel.cn/api/paas/v4  glm-4.6
# Kimi:      https://api.moonshot.cn/v1            kimi-k2

# 本地模型(Ollama / LM Studio,无需 Key)
LLM_API_BASE=http://localhost:11434/v1
LLM_API_KEY=local
LLM_MODEL=qwen2.5:14b
```

### 4.3 阶段级开关与成本控制(重要)

一次全量运行约有 **2000 次候选检测 + 900×2 次分析/影响评估** 调用。候选检测规则已很强,
建议把 LLM 留给高价值阶段:

```bash
LLM_STAGES=technical_analysis,impact_evaluation,digest   # 仅这些阶段走 LLM
LLM_CLI_TIMEOUT=240                                      # CLI 单次超时(秒)
```

验证当前生效配置:`grep LLM .env`;验证真实调用与模型:
`psql ... -c "SELECT pipeline_stage, model, success FROM ai_executions ORDER BY created_at DESC LIMIT 10;"`。

### 4.4 说明与限制

- Embedding:事件相似度检索默认用本地特征哈希嵌入(256 维,零依赖),不消耗 API;
  向量存于 pgvector。真实 embedding API 的接入点已预留(`radar_intelligence/embeddings.py`)。
- `response_format=json_object` 由 OpenAI 兼容层使用;CLI 与不支持该参数的服务端由
  JSON 提取器兜底(容忍 ```json 围栏、前后缀文本、codex 的尾部日志)。
- CLI 方式在 Windows 上同样可用(前提 claude/codex CLI 可执行);每次调用是独立进程,
  批量跑大阶段时比 HTTP 慢,建议配合 `LLM_STAGES` 使用。

---

## 5. 命令速查(CLI)

| 命令 | 作用 |
|---|---|
| `uv run radar-collector sync-config` | config/{objects,topics,sources} → 数据库(幂等) |
| `uv run radar-collector run-all` | 立即采集全部启用源 |
| `uv run radar-collector run --loop --interval 3600` | 常驻:每小时按各源 poll_interval 轮询到期源 |
| `uv run radar-intelligence process` | 规则过滤 → 候选 → 事件管线(只处理 new 状态 RawItem) |
| `uv run radar-intelligence trends` | 重算 30d/90d 趋势快照 |
| `uv run radar-intelligence digest --kind daily` | 生成日报(weekly/monthly 同理) |
| `uv run radar-intelligence metrics` | 输出 MVP 验收指标 |
| `uv run pytest -q` | 21 个单元测试 |

## 6. 日常运行建议

- **手动节奏**:每天跑一次 `uv run python scripts/pipeline.py`(约 10 分钟,增量处理,macOS/Linux/Windows 通用)。
- **自动节奏**:`uv run radar-collector run --loop --interval 3600` 常驻采集;
  或用 launchd/cron/任务计划程序每小时执行 `scripts/pipeline.py`。全部幂等,重复执行无副作用。
- **数据重置**(重新从头构建数据集):

```bash
~/gr-pg/pgsql/bin/psql -U radar -d radar -c \
  "TRUNCATE objects, topics, event_topics, event_sources, events, raw_items, \
   sources, ai_executions, trend_snapshots, digests CASCADE;"
uv run radar-collector sync-config && uv run python scripts/pipeline.py
```

## 7. 人工干预 / 反馈闭环(Admin API,无鉴权,仅限内网)

```bash
curl -X POST localhost:8300/admin/events/<slug>/promote        # 提升精选
curl -X POST localhost:8300/admin/events/<slug>/reject         # 否决
curl -X POST localhost:8300/admin/events/<a>/merge-into/<b>    # 合并事件
curl -X PATCH localhost:8300/admin/events/<slug> \
  -H 'content-type: application/json' -d '{"impact_level":"High"}'   # 覆盖 Impact
curl -X POST localhost:8300/admin/events/<slug>/topics/<topic>       # 补主题
```

所有人工操作都会改变事件状态并在下次聚合中生效;这些反馈是后续调优过滤/评级规则的数据集。

## 8. 故障排查

| 现象 | 处置 |
|---|---|
| `docker: command not found` | 正常,路径 A 不需要 Docker;需要时 `brew install --cask docker` |
| API 500 / 枚举报错 | API 进程代码过期:`pkill -f uvicorn radar_api` 后重启,跑 `alembic upgrade head` |
| Web 打不开 | `uv run python scripts/service.py status`;看 `data/logs/web.log` |
| 端口被占/服务起不来 | `uv run python scripts/service.py stop` 后 `start`;或 `lsof -i :8300 -i :8301` 查占用 |
| GitHub 403 rate limit | `export GITHUB_TOKEN=$(gh auth token)` 后重新采集 |
| 某源一直失败 | `SELECT o.slug, s.type, left(s.last_error,90) FROM sources s JOIN objects o ON o.id=s.object_id WHERE s.last_error IS NOT NULL;`(源失败不影响其他源) |
| 连接 5433 被拒 | `.env` 的 DATABASE_URL 端口要与实际 postgres 一致(本机原生=5432,Docker=5433) |
| 事件为 0 | 确认执行过 `scripts/pipeline.py`;`SELECT filter_status, count(*) FROM raw_items GROUP BY 1;` 查看分布 |
| 精选太少/太多 | 精选是规则动态阈值(`radar-intelligence select` 可预览);调整后重跑 `digest` |
| LLM 未生效 | `ai_executions` 表看 model 字段:heuristic-rules=未接入;再查 CLI 是否登录(`claude -p hi`)/Key 是否正确 |
| LLM 阶段很慢 | 用 `LLM_STAGES` 限制阶段;CLI 每次调用是独立进程,属正常 |
