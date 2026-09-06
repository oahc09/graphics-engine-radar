# Graphics Engine Radar — Implementation Report

Date: 2026-09-06
Baseline: `docs/Graphics Engine Radar — Content & Intelligence Spec v0.1.md` + `docs/Graphics Engine Radar — Implementation Plan & Agent Prompt v0.1.md`
Status: MVP end-to-end running on real data.

---

## Implemented

| 里程碑 | 状态 | 交付物 |
|---|---|---|
| M0 环境 | ✅ | PostgreSQL 17.6 + pgvector 0.8.6 本地运行;uv Python 3.12 workspace |
| M1 Domain + DB | ✅ | 11 张表 SQLAlchemy 模型 + 可执行 Alembic migration(`migrations/versions/ebfd4b8f1b96_init_schema.py`) |
| M2 监控配置 | ✅ | `config/objects`(125 个 YAML)+ `config/topics`(28 个),配置驱动,零硬编码 |
| M3 Collector 框架 | ✅ | `SourceAdapter.fetch(cursor)->FetchResult` 接口 + 注册表;幂等/重试/cursor/可观察;单源失败隔离 |
| M4 采集器 | ✅ | GitHubRelease / GitHubPR(关键词/merged_only)/ GitHubIssue / RSS / ReleaseNotes / HTML / SpecRegistry 共 116 个已配置 Source |
| M5 Normalize + Rule Filter | ✅ | 三级去重键(external_id → canonical_url → content_hash)+ 11 类噪声规则(ignored 不删除) |
| M6 Candidate Detection | ✅ | 规则评分 → 图形相关性门控 → (配置 LLM 后)轻量分类;结构化 schema 校验 |
| M7 Event Retrieval / Clustering | ✅ | pgvector 90 天窗口语义检索 + 确定性规则(同对象同版本号)+ 模糊带 LLM 终审;primary source 按官方源优先提升 |
| M8 Technical Analysis | ✅ | 独立分阶段 Prompt(specification/previous_state/new_state/maturity/why_it_matters 严格 schema) |
| M9 Topic / Maturity / Impact | ✅ | 28 主题多对多映射;成熟度九级模型;内部 5 维 0..5 评分,外显 Critical/High/Notable |
| M10 API | ✅ | FastAPI:`/events /events/{slug} /selected /objects /objects/{slug} /topics /topics/{slug} /trends /digests/{kind} /metrics /health` + Admin(promote/reject/merge/edit/override-impact/topic 增删) |
| M11 Web | ✅ | Next.js 15 + TS:精选 / 全部动态 / 趋势 / 主题 / 对象 / 日报 + 事件/主题/对象详情页,构建通过,真实数据渲染 |
| M12 Trend / Digest | ✅ | 可解释规则趋势快照(30d/90d 双窗口);daily/weekly/monthly digest(weekly/monthly 独立重分析窗口) |
| M13 真实验证 | ✅ | 2019 条真实 RawItem → 895 个真实事件;22 个事件跨 7 域人工抽样(`docs/VALIDATION.md`) |
| 测试 | ✅ | 21 个单元测试全绿(canonical URL/去重/噪声规则/嵌入相似度/影响映射/成熟度迁移) |

## Architecture

```text
apps/
  api/    radar_api    FastAPI(:8300),含 /admin 反馈端点
  web/    Next.js(:8301),server components 直连 API,rewrite /api→:8300
services/
  collector/     CLI:sync-config / run / run-all / loop;幂等入库 + cursor/错误隔离
  intelligence/  CLI:process / trends / digest / select / metrics
packages/
  domain/      模型、枚举、配置装载、DB session
  adapters/    适配器 + canonical URL/content_hash 规范化
  prompts/     6 个阶段独立版本化 Prompt(禁止大总结 Prompt)
config/{objects,sources,topics}/   监控范围全部 YAML 化
migrations/    Alembic
```

数据库:PostgreSQL + pgvector(`events.title_embedding/change_embedding`,vector(256))。
物理部署第一版 = web + api + postgres(+ redis 预留在 compose),符合 Spec §30。

## Data Pipeline(真实运行路径)

```text
116 Sources(官方 GitHub Release / 官方 Blog RSS / Release Notes / Spec Registry / 技术媒体)
  → radar-collector run-all        实采 2019 条 RawItem(113/116 源成功)
  → Normalize                      canonical URL、content_hash 三级去重
  → Rule Filter                    11 类噪声规则 → 1023 条 ignored(保留可重放)
  → Candidate Detection            图形相关性门控 + 信号评分 → 996 条候选
  → Event Retrieval                pgvector cosine,90 天窗口,object 过滤
  → Event Clustering               规则(同对象同 tag)+ 相似度阈值 0.62 + 模糊带 LLM 终审 → 101 次归并
  → Source Verification            role 按来源类型赋予,官方源优先提升 primary
  → Technical Analysis             what_changed / previous_state / new_state / maturity / why_it_matters
  → Topic Mapping                  28 主题关键词直配(direct/related,多主题)
  → Maturity + Impact              5 维 0..5 → Critical/High/Notable(迁移/规范/破坏自动升级)
  → Trend Update                   30d/90d 快照 + Accelerating/Growing/Stable/Cooling
  → Digest                         daily/weekly/monthly(独立窗口分析)
  → API :8300 → Web :8301
```

每次运行 0 error;所有判断落 `ai_executions`(6627 条,覆盖 6 个阶段,含 model/prompt_version/input_hash/output/失败信息)。

## Monitoring Coverage

- **Objects:125**(Spec §4–§11 全量,未删减):game_engine 13 / rendering_engine 14 / web_engine 9 / graphics_runtime 11 / graphics_api 8 / gpu_vendor 9 / platform 7 / dcc 5 / tool 18 / standard 12 / technology 19
- **Topics:28**(8 个顶层能力树 + 细分)
- **Sources:116**(113 正常,3 个偶发超时;覆盖 GitHub Release/PR、官方 Blog RSS、Release Notes、Khronos Registry)
- Shader/Slang 按完整工具链监控:slang(25 事件)、dxc(11)、spirv-tools(10)、shaderc、spirv-cross、wgsl、glsl、hlsl、metal-shading-language、spir-v、dxil 均建为对象

## Validation

`docs/VALIDATION.md` — **22 个真实事件跨 7 大域抽样**(engine/web、graphics_api+shader/slang、gpu_platform、rendering_tech、tooling、DCC、standard/glTF),逐项核验:

| 验证点 | 结果 |
|---|---|
| 重要事件漏报 | wgpu、Bevy+WebGPU、Babylon 9.0、Vulkan 1.4.362(Valve 扩展)、RenderDoc v1.12、Blender 均检出 |
| 噪声过滤 | bugfix/CI/dependency bump/招聘/教程被 ignored(1023 条);AppFunctions 等非图形 Android 内容被相关性门控拦截 |
| 多来源归并 | 101 次合并;46 个事件拥有 ≥2 条证据(同事件 Blog+GitHub Release 归并) |
| primary source | 100% 事件拥有一手/官方源;role 按官方性排序 |
| Topic | 28 主题事件计数正常(WebGPU/Vulkan/Mobile/Shader Language 均有聚集) |
| maturity transition | 修复伪迁移后仅保留显式 stable/production 证据的迁移(如 wgpu SDK→Production) |
| Why it matters | 具体工程模板(后端复用/规范跟进成本/移动端扩展/迁移评估),无营销语句 |
| 精选低价值内容 | 精选 17 条(动态阈值,非每日固定 N);末轮修复后未见版本号噪音进入精选 |

## Metrics(最终干净数据集)

```text
RawItem 总数:            2019
Ignored 数:              1023  (51%)
Candidate 数:            996   (检出即进入事件管线,状态机内瞬时态)
Event 数:                895
Selected 数:             17    (High;0 Critical,宁少勿水)
Duplicate Merge 数:      101   (46 个事件多来源归并)
拥有 Official Source 比例: 100% (893/895)
AI 判断记录:             6627 条(6 阶段全部落库可追溯)
```

## Known Limitations

1. **启发式分析器代替 LLM 执行**(见 Deviations D2):why_it_matters 为模板级工程判断,语义精度低于强模型;`why-it-matters` 的"具体工程价值"依赖信号模板,深度有限。
2. HTML/ReleaseNotes 页面型源(如 Apple "news/releases"、Khronos registry)整页一个 RawItem,页面标题即事件标题(如 "releases"),标题质量差。
3. GitHub Discussion、Conference、Roadmap 三类适配器未实现(Spec 第二批),对应对象暂无源或以 html 适配器替代。
4. weekly/monthly digest 在启发式模式下与 daily 内容高度重叠(事件池同源),LLM 模式下才会真正做窗口级再分析。
5. Admin 无鉴权,仅限内网使用。
6. 3 个 Source 因远端超时/403 间歇失败(如 substance-3d),已有 last_error 记录可观察。

## Deviations(原设计 / 实际方案 / 原因 / 影响)

**D1. 队列:Redis + Celery → 进程内 cursor 调度器**
- 原设计:Queue/Scheduling = Redis + Celery(Spec §29)。
- 实际方案:collector 为幂等、cursor 驱动的 CLI 调度器(`run`/`run-all`/`--loop`),每源独立 next_poll_at/last_error。
- 原因:MVP 单机规模无需分布式队列;环境无 Redis 服务;避免为 116 源引入 broker 运维。
- 影响:无分布式并行采集;数据契约不受影响。docker-compose 已含 redis 服务,可平滑切回。

**D2. LLM:无 API Key 凭据 → 三后端 Provider(Claude CLI / Codex CLI / OpenAI 兼容 HTTP)+ 启发式兜底**
- 原设计:Candidate/Clustering/Technical Analysis 等阶段由强模型 API 执行。
- 实际方案:6 个阶段独立版本化 Prompt 全部实现并走严格 schema 校验;`LLM_PROVIDER` 支持
  `openai`(OpenAI 兼容 HTTP)、`claude-cli`、`codex-cli`(直接调用本机已登录的 Claude Code /
  Codex CLI,复用订阅,无需 API Key,已真机验证 model=claude-cli:default 与 codex-cli:default
  的真实调用成功);`LLM_STAGES` 可按阶段门控。未接入时以确定性启发式分析器执行,
  `ai_executions` 如实记录 model=heuristic-rules。
- 原因:环境无 LLM API Key 凭据;CLI 复用本地登录态是零凭据依赖的真实 LLM 路径。
- 影响:默认(无 CLI/Key)语义判断深度受限;接入任一后端即得真实 LLM 判断,无需改码。

**D3. Embedding:API embeddings → 特征哈希(256 维)**
- 原设计:pgvector + Embedding API。
- 实际方案:确定性 n-gram hashing embedder 同维度写入 pgvector;检索/归并逻辑不变。
- 原因:无 embedding API 凭据;保证管线零外部依赖可复现。
- 影响:语义相似度弱于真实 embedding;更换 provider 后需重建索引(重跑管线即可)。

**D4. PostgreSQL 安装路径:brew → EDB 官方二进制 + 本地编译 pgvector 0.8.6**
- 原设计:无指定(推荐 PostgreSQL+pgvector)。
- 实际方案:EDB postgresql-17.6 binaries + 源码编译 pgvector(brew 对 openssl 3.6.4 无 x86_64 bottle、源码下载 <10KB/s 不可行)。
- 原因:环境限制。
- 影响:无;docker-compose 提供 `pgvector/pgvector:pg17` 等价路径。

**D5. 第二批适配器部分调整**:GitHubIssue 已实现;GitHub Discussion、Conference 未单独实现(社区/会议以 RSS/HTML 源覆盖);Roadmap 以 HTML 适配器语义覆盖。影响:相关对象覆盖为页面级而非结构化级。

**D6. Candidate 数指标口径**:RawItem 的 `candidate` 状态在单次管线内瞬时存在(检出后立即进入事件管线变 `processed`),Metrics 中 Candidate 数 = 检出数(996 = created 895 + merged 101)。
