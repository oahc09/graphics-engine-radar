# Graphics Engine Radar

> 图形引擎每天都在变化。我们持续监控引擎、Graphics API、GPU、渲染技术和工具链。AI 帮你过滤噪声,只留下真正值得关注的变化。
>
> Don't rank news. Detect meaningful changes in graphics technology.

Graphics Engine Radar 是一个**图形技术情报系统**,不是新闻聚合器。核心原则:

```text
RawItem != Event
Article / Release / PR / Blog 只是证据,Event 才是产品核心数据
```

完整链路(全部真实运行):

```text
真实 Source → Collect → Normalize → Rule Filter → Candidate Detection
→ Event Retrieval → Event Clustering → Source Verification
→ Technical Analysis → Topic Mapping → Maturity Analysis
→ Impact Evaluation → Trend Update → API → Web
```

## 架构

```text
apps/
  api/        FastAPI (events / selected / objects / topics / trends / digests / metrics)
  web/        Next.js + TypeScript (精选 / 全部动态 / 趋势 / 主题 / 对象 / 日报)
services/
  collector/  采集调度: adapter 分发、幂等入库、cursor 管理、失败隔离
  intelligence/ 分阶段 AI 管线: rule filter → candidate → retrieval → cluster
              → technical analysis → topic → impact → trend → digest
packages/
  domain/     SQLAlchemy 模型 + 枚举 + 配置装载器
  adapters/   GitHub / RSS / ReleaseNotes / HTML / SpecRegistry 适配器
  prompts/    分阶段版本化 Prompt(禁止大总结 Prompt)
config/
  objects/    监控对象(125 个,配置驱动,不硬编码)
  topics/     主题树(28 个)
migrations/   Alembic
```

技术栈:FastAPI + SQLAlchemy + Alembic + PostgreSQL + pgvector + Next.js。
不使用 Kafka / Neo4j / Elasticsearch / 微服务(spec §29)。

## 快速开始

**全平台最简部署(Windows/macOS/Linux,无需 Docker/WSL/装库):**

```bash
uv sync --all-packages                        # 依赖(含内嵌 PostgreSQL+pgvector)
uv run python scripts/embedded_db.py start    # 启动内嵌库+建表+写 .env(幂等)
uv run radar-collector sync-config            # 装载 125 对象/116 来源
uv run python scripts/pipeline.py             # 采集→管线→趋势→日报
uv run uvicorn radar_api.app:app --port 8300  # API(:8300/docs)
cd apps/web && npm install && npm run dev     # Web → http://localhost:8301
```

完整部署说明(含服务启停、macOS/Linux 原生独立数据库、Docker、Windows 路径)见 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**。
已部署机器的一键操作:

```bash
uv run python scripts/service.py start   # 启动/停止/重启 API + Web(start|stop|status|restart)
uv run python scripts/pipeline.py        # 采集 → 管线 → 趋势 → 日报(幂等)
```

### 1. 数据库

方式 A — Docker(推荐):

```bash
docker compose up -d postgres redis
```

方式 B — 本地 brew:

```bash
brew install postgresql@17 pgvector redis
brew services start postgresql@17
createuser radar && createdb radar -O radar
psql radar -c 'CREATE EXTENSION IF NOT EXISTS vector; ALTER USER radar PASSWORD '"'"'radar'"'"';'
```

`.env`(参考 `.env.example`)中配置 `DATABASE_URL`。

### 2. 后端

```bash
uv sync --all-packages
uv run alembic upgrade head                      # 建表
uv run radar-collector sync-config               # 装载监控配置(125 对象/28 主题)
export GITHUB_TOKEN=$(gh auth token)             # 提高GitHub限额(可选但推荐)
uv run radar-collector run-all                   # 采集真实来源
uv run radar-intelligence process                # 规则过滤→候选→事件→分析→影响
uv run radar-intelligence trends                 # 趋势快照
uv run radar-intelligence digest --kind daily    # 日报
uv run uvicorn radar_api.app:app --port 8300     # API
```

### 3. 前端

```bash
cd apps/web && npm install && npm run dev        # http://localhost:8301
```

## AI Pipeline 说明

- 每个阶段(candidate / clustering / technical analysis / topic / impact / digest)有独立
  版本化 Prompt(`packages/prompts`),不允许合并成一个大总结 Prompt。
- 所有 AI 判断写入 `ai_executions` 表:model、prompt_version、input_hash、input/output、
  失败信息,保证"为什么被过滤/合并/评 High"可追溯(spec §36)。
- LLM 接入三选一(详见 `docs/DEPLOYMENT.md` §4):**Claude CLI**(`LLM_PROVIDER=claude-cli`,
  直接用本机已登录的 Claude,无需 Key)、**Codex CLI**(`LLM_PROVIDER=codex-cli`)、
  或任意 **OpenAI 兼容 API**(OpenAI/DeepSeek/通义/GLM/OpenRouter/本地 Ollama,
  配 `LLM_API_BASE`+`LLM_API_KEY`+`LLM_MODEL`)。
- 未接入 LLM 时,管线以确定性启发式分析器运行并如实记录(model=heuristic-rules)。
- `LLM_STAGES=technical_analysis,impact_evaluation,digest` 可限制仅高价值阶段调用 LLM。

## 关键设计约束(来自 Spec v0.1)

- GitHub 不扫全部 commit:只抓 Releases、Merged PR(关键词/标签过滤)、重要 Issue。
- Rule Filter 不删除 RawItem:统一标 `ignored` + reason,可重放。
- 去重键:source_id+external_id → canonical_url → content_hash;Event 层再做
  90 天窗口 pgvector 语义检索 + 规则 + LLM 归并。
- 一手源优先:official release notes / GitHub release / spec registry 担任 primary。
- Impact 不显示伪精确分数:内部 5 维 0..5,外显 Critical / High / Notable。
- 精选数量动态,宁少勿水;不用浏览量做 Trend。

## 测试

```bash
uv run pytest -q
```

覆盖:canonical URL / RawItem 去重键 / 噪声规则 / 启发式分析 / 成熟度迁移 / Impact 映射 / 嵌入相似度。
