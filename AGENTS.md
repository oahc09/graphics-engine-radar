# AGENTS.md — AI Agent 快速上手指南

> 本文件面向 AI agent(和人)。目标:读完即可开发、部署、运维本项目,不必通读全部代码。
> 产品事实源是 `docs/` 下两份 Spec v0.1;本文只讲"怎么跑、在哪改、什么不能动"。

## 一句话理解本项目

**Graphics Technology Intelligence 系统,不是新闻聚合器。** 持续采集图形引擎领域的
GitHub Release / Merged PR / 官方 Blog / Release Notes / Spec Registry,过滤噪声后把
多条证据归并为一个 **Event**(核心产品数据),再做工程向技术分析(why it matters)、
主题映射、影响分级、趋势快照,通过 API 与 Next.js 站点输出。

铁律:`RawItem != Event` — 文章/Release/PR 只是证据,Event 才是产品。

## 技术栈与端口

| 层 | 技术 | 默认端口 |
|---|---|---|
| 后端 API | FastAPI + SQLAlchemy 2 + Alembic | 8300 |
| 数据库 | PostgreSQL 17 + pgvector(向量 256 维) | 5432(内嵌) |
| 前端 | Next.js 15(App Router)+ TS | 8301 |
| 采集/管线 | Python 3.12(uv workspace,6 个子包) | - |

## 项目结构

```text
apps/
  api/radar_api/        FastAPI:app.py(公开端点) admin.py(人工干预)
  web/                  Next.js:app/(页面) lib/api.ts(唯一 API 客户端)
services/
  collector/radar_collector/    采集:runner.py(幂等入库+cursor) cli.py
  intelligence/radar_intelligence/
    pipeline.py        管线编排(一 RawItem 的完整旅程)
    rule_filter.py     噪声规则(ignored 不删数据)
    candidate.py       候选检测(规则评分+相关性门控)
    retrieval.py       pgvector 90 天相似事件检索
    cluster.py         事件归并(规则+相似度+LLM 模糊带终审)
    analysis.py        技术分析/主题/成熟度/影响(启发式实现+LLM 阶段)
    trend.py           趋势快照(30d/90d,可解释规则)
    digest.py          日报/周报/月报 + 精选规则
    llm.py             三后端 LLM(openai/claude-cli/codex-cli)+ 全量追踪
    embeddings.py      特征哈希嵌入(零 API 依赖)
packages/
  domain/               SQLAlchemy 模型、枚举、Settings、config 装载
  adapters/             采集适配器:github.py http_sources.py normalize.py
  prompts/              6 个阶段的版本化 Prompt(禁止合并!)
config/
  objects/  125 个监控对象 YAML(engine/api/gpu/tool/dcc/standard 全覆盖)
  topics/   28 个主题 YAML             ← 由 tools/gen_configs.py 生成,可手改再重生成
migrations/versions/    Alembic 迁移
scripts/
  embedded_db.py        内嵌数据库(pgserver,免装 PostgreSQL)
  service.py            API+Web 启停(start|stop|status|restart,跨平台)
  pipeline.py           采集→管线→趋势→日报(一键,幂等)
tools/
  gen_configs.py        生成 config/ YAML(对象/主题定义在这里)
  validate_sample.py    生成 docs/VALIDATION.md 抽样验证
tests/                  28 个单元测试
docs/                   两份 Spec + DEPLOYMENT.md + VALIDATION.md
```

## 一键部署(全平台,无需 Docker/WSL)

前置:仅 `uv` 和 Node.js ≥ 20(Windows 官方安装包/winget 即可)。

```bash
uv sync --all-packages                        # 1. 依赖(含内嵌 PostgreSQL+pgvector)
uv run python scripts/embedded_db.py start    # 2. 起库+建表+写 .env(幂等)
uv run radar-collector sync-config            # 3. 装载监控配置
uv run python scripts/service.py start        # 4. API(:8300)+ Web(:8301)
uv run python scripts/pipeline.py             # 5. 采集→管线→趋势→日报(约10分钟)
open http://localhost:8301                    # 6. 界面
```

服务与数据库生命周期:

```bash
uv run python scripts/service.py start|stop|status|restart    # API+Web
uv run python scripts/embedded_db.py start|stop|status|uri    # 数据库
```

全部命令幂等,重复执行安全。数据重置(危险):

```bash
uv run python scripts/embedded_db.py stop
rm -rf data/pgdata && uv run python scripts/embedded_db.py start
uv run radar-collector sync-config && uv run python scripts/pipeline.py
```

## 配置(唯一入口:根目录 `.env`)

复制 `.env.example` 为 `.env`,所有可配置项都在这一个文件:
数据库连接(内嵌模式自动写入 `DATABASE_URL`)、`API_PORT`/`WEB_PORT`、
`GITHUB_TOKEN`(不填限流 60 次/时)、LLM 接入(见下)、LLM 阶段门控。
前端端口/代理也由同一 `.env` 驱动(next.config.mjs 内置无依赖 loader)。

**LLM 三选一**:①`LLM_PROVIDER=claude-cli`(用本机已登录 claude,零成本)
②`LLM_PROVIDER=codex-cli` ③`LLM_PROVIDER=openai` + `LLM_API_BASE`/`LLM_API_KEY`/
`LLM_MODEL`(兼容 DeepSeek/Qwen/GLM/OpenRouter/Ollama,示例见 `.env.example`)。
不配置则用启发式分析器(零成本可用)。成本控制:`LLM_STAGES=technical_analysis,impact_evaluation,digest`。
所有 AI 判断落 `ai_executions` 表(model/prompt_version/input_hash/output/失败)。

监控范围不是代码:加对象/来源 = 在 `tools/gen_configs.py` 补定义(或直接写
`config/objects/*.yaml`)→ `uv run python tools/gen_configs.py && uv run radar-collector sync-config`。

## 常用运维命令

```bash
uv run pytest -q                                  # 28 个测试
uv run radar-collector run-all                    # 立即采集全部源
uv run radar-intelligence process                 # 只处理新增 RawItem
uv run radar-intelligence trends|metrics|select   # 趋势/验收指标/精选预览
uv run radar-intelligence digest --kind daily     # 日报(weekly/monthly)
uv run python tools/validate_sample.py            # 重新生成 docs/VALIDATION.md
uv run uvicorn radar_api.app:app --port 8300      # API(交互文档 /docs)
```

API 速查:`GET /events /events/{slug} /selected /objects /objects/{slug}
/topics /topics/{slug} /trends /digests/{kind} /metrics /health`;
Admin(无鉴权,仅内网):`POST /admin/events/{slug}/promote|reject`,
`POST /admin/events/{a}/merge-into/{b}`,`PATCH /admin/events/{slug}`,
`POST|DELETE /admin/events/{slug}/topics/{topic}`。

## 数据流(改代码前先看这个)

```text
116 Sources → collect(runner.py 幂等入库) → RawItem(new)
  → rule_filter(ignored 不删!) → candidate.py(相关性门控)
  → retrieval.py(pgvector 相似事件) → cluster.py(归并=1 Event:N 证据)
  → analysis.py(what/why/maturity) → topics → impact(5维0..5→Critical/High/Notable)
  → Event(verified) → trend.py → digest.py → API → Web
```

RawItem 去重键:source_id+external_id → canonical_url → content_hash(在
`adapters/normalize.py` + `collector/runner.py`)。

## 不变量(修改代码前必读)

1. **不许把 AI 管线合并成一个大 Prompt**:每阶段独立 Prompt + 版本号(`packages/prompts`)。
2. **Rule Filter 不删除 RawItem**:只标 `filter_status=ignored` + reason。
3. **不许删减监控对象**:125 个对象是 Spec 明确范围,只能增不能减。
4. **不用浏览量/热度做 Impact 与 Trend**;精选数量动态(宁少勿水),不固定条数。
5. **GitHub 不扫全部 commit**:只抓 Release / Merged PR(关键词)/ 重要 Issue。
6. Impact 外显只有 Critical/High/Notable(内部 5 维 0..5);Event 层语义去重必须先检索后创建。
7. 所有 AI 调用必须写 `ai_executions`(含失败);schema 校验失败不得进入下一阶段。
8. 数据契约:改 `packages/domain/radar_domain/models.py` 必须同步 Alembic 迁移
   (`uv run alembic revision --autogenerate -m "..."`,注意检查 pgvector 列导入)。

## 常见坑

- 改了 `.env` 要重启服务(`service.py restart`);`NEXT_PUBLIC_*` 与端口烘焙在 Web 启动时。
- `uv run radar-collector` 若报 "Failed to spawn":`uv sync --all-packages` 重建入口。
- Alembic autogenerate 会把 Vector 写成 `pgvector.sqlalchemy.vector.VECTOR`,
  需手改为 `Vector`(from pgvector.sqlalchemy import)。
- API 返回 500 且日志有枚举 LookupError:API 进程代码过期,restart。
- Windows:一切用 `scripts/pipeline.py`(bash 脚本不存在);防火墙放行 python/node。
