# Graphics Engine Radar — Implementation Plan & Agent Prompt v0.1

## 0. 任务定位

你正在实施一个已经完成产品设计的项目：

`Graphics Engine Radar`

它不是普通新闻聚合站，而是：

> 持续监控图形引擎、Graphics API、GPU、渲染技术、工具链和 DCC/资产生态，通过规则与 AI 过滤噪声、归并重复来源，最终只保留真正会影响图形工程研发判断的技术变化。

现有产品设计已经确定。

不要重新讨论产品方向，不要自行缩减监控范围，不要把系统改造成普通 RSS / 新闻聚合器。

核心原则：

```text
RawItem != Event

Article / Release / PR / Blog
只是证据

Event
才是最终产品数据
```

完整链路：

```text
Collect
→ Normalize
→ Rule Filter
→ Candidate Detection
→ Event Retrieval
→ Event Clustering
→ Source Verification
→ Technical Analysis
→ Topic Mapping
→ Maturity Analysis
→ Impact Evaluation
→ Trend Update
→ Publish
```

---

# 1. 实施目标

完成一个可运行的 MVP。

最终必须跑通真实数据端到端：

```text
真实 GitHub / RSS / Release Notes
        ↓
RawItem
        ↓
Noise Filter
        ↓
Candidate
        ↓
Event Dedup / Cluster
        ↓
Technical Analysis
        ↓
Why it matters
        ↓
Topic
        ↓
Impact
        ↓
Web 首页
```

不能只完成：

```text
页面 Mock
数据库 Schema
Crawler Demo
Prompt 示例
```

必须形成完整闭环。

---

# 2. 推荐技术栈

除非现有仓库已经确定其他合理技术，不要擅自更换。

```text
Frontend:
Next.js + TypeScript

Backend:
FastAPI + Python

Database:
PostgreSQL

Vector:
pgvector

Queue / Scheduling:
Redis + Celery

Collector:
Python

AI Pipeline:
Python

ORM:
SQLAlchemy

Migration:
Alembic
```

第一阶段不要引入：

```text
Kafka
Neo4j
Elasticsearch
复杂微服务
多 Agent runtime
Kubernetes
```

---

# 3. 项目结构

推荐：

```text
graphics-radar/

apps/
  web/
  api/

services/
  collector/
  intelligence/

packages/
  domain/
  adapters/
  prompts/

config/
  objects/
  sources/
  topics/

migrations/

tests/

docker-compose.yml
README.md
.env.example
```

如果已有仓库结构，优先保持现有结构，不进行无关重构。

---

# 4. Phase 1 — Domain Model & Database

优先完成数据底座。

实现：

```text
Object
Source
RawItem
Event
Topic
EventSource
EventTopic
TrendSnapshot
DailyDigest
AIExecution
```

## Object

字段至少包含：

```text
id
slug
name
type
domain
description
official_url
github_repo
aliases
active
created_at
updated_at
```

type 支持：

```text
game_engine
rendering_engine
web_engine
graphics_runtime
graphics_api
gpu_vendor
platform
dcc
tool
standard
technology
```

---

## Source

```text
id
object_id
type
url
adapter
config
poll_interval
last_cursor
last_success_at
last_error
next_poll_at
enabled
created_at
updated_at
```

支持 source type：

```text
github_release
github_pr
github_issue
github_discussion
rss
release_notes
official_blog
spec_registry
documentation
roadmap
conference
community
html
```

---

## RawItem

```text
id
source_id
external_id
url
canonical_url
title
content
author
published_at
fetched_at
content_hash
language
raw_payload
filter_status
filter_reason
created_at
```

filter_status：

```text
new
ignored
candidate
processed
```

---

## Event

```text
id
slug
title
summary

event_type
change_signal

change
why_it_matters
who_should_care

impact_level
confidence

maturity_from
maturity_to

first_seen_at
published_at
updated_at

status
```

event_type：

```text
VERSION_RELEASE
FEATURE_ADDED
CAPABILITY_ENABLED
ARCHITECTURE_CHANGE
SPEC_CHANGE
PERFORMANCE_CHANGE
QUALITY_CHANGE
TOOLCHAIN_CHANGE
TECHNOLOGY_ADOPTION
BREAKING_CHANGE
```

change_signal：

```text
NEW
EXPAND
ADOPT
MATURE
SPEC
PERF
BREAK
```

impact_level：

```text
Critical
High
Notable
```

status：

```text
candidate
verified
published
rejected
merged
```

---

## AIExecution

所有 AI 调用必须可追踪。

```text
id
pipeline_stage
model
prompt_version
input_hash
input_payload
output_payload
success
error
created_at
```

这不是可选功能。

后续需要知道：

```text
为什么某条被过滤？
为什么某两条被合并？
为什么它被判定为 High？
```

---

# 5. Phase 2 — Monitoring Configuration

监控对象必须配置化。

不要硬编码到 Collector。

使用：

```text
config/objects/
config/sources/
config/topics/
```

例如：

```yaml
id: blender
name: Blender
type: dcc
domain: content_pipeline

sources:
  - type: release_notes
    url: ...

  - type: github_release
    repo: blender/blender

topics:
  - vulkan
  - rendering
  - asset-pipeline
  - geometry
```

必须覆盖现有 Spec 已确定范围。

至少包括：

## Engine

```text
Unreal Engine
Unity
Cocos Creator
Godot
O3DE
Flax
Bevy
Defold
Stride
Wicked Engine
CryEngine

Filament
bgfx
Diligent Engine
The Forge
Magnum
Ogre-Next
Falcor
NVRHI
sokol
Skia
Graphite
SDL GPU
Mesa

Three.js
Babylon.js
PlayCanvas
Galacean Engine
PixiJS
Phaser
CesiumJS

ANGLE
Dawn
wgpu
Flutter Impeller
Qt RHI
Chromium Graphics
WebKit Graphics
Android HWUI
RealityKit
```

## Graphics API

```text
Vulkan
Direct3D 12
Metal
OpenGL
OpenGL ES
WebGPU
WebGL
EGL
```

Shader / IR：

```text
GLSL
HLSL
Slang
WGSL
Metal Shading Language
SPIR-V
DXIL
```

## GPU

```text
NVIDIA
AMD
Intel
Qualcomm / Adreno
ARM / Mali / Immortalis
Apple GPU
Imagination / PowerVR
Samsung / Xclipse
Broadcom / VideoCore
```

## DCC / Tools / Standards

```text
Blender
Houdini
Maya
3ds Max
Substance 3D

RenderDoc
Nsight Graphics
Nsight Systems
PIX
RGP
RRA
Intel GPA
AGI
Arm Performance Studio
Xcode GPU Tools
Tracy
Superluminal

glTF
OpenUSD
MaterialX
OpenPBR
KTX
Basis Universal
Draco
meshoptimizer
OpenEXR
OpenImageIO
```

不允许因为第一版工作量大而偷偷删除这些对象。

可以逐步补 Source，但 Object 范围要先建立完整。

---

# 6. Phase 3 — Collector Framework

实现 Adapter Interface。

推荐：

```python
class SourceAdapter:
    async def fetch(
        self,
        source: Source,
        cursor: str | None
    ) -> FetchResult:
        ...
```

FetchResult：

```text
items
next_cursor
metadata
```

首批必须实现：

```text
GitHubReleaseAdapter
RSSAdapter
ReleaseNotesAdapter
```

第二批：

```text
GitHubPRAdapter
SpecRegistryAdapter
OfficialBlogAdapter
HTMLAdapter
```

Collector 必须具备：

```text
idempotent
retryable
cursor-based
observable
```

单个 source 失败不能影响其他 source。

---

# 7. GitHub Collector

GitHub 不抓全部 commit。

优先抓：

```text
Releases
Tags
Merged PR
Important Issues
Discussions
```

GitHub PR 支持配置：

```yaml
watch:
  releases: true

  pull_requests:
    merged_only: true

    keywords:
      - vulkan
      - metal
      - dx12
      - webgpu
      - opengl
      - bindless
      - ray tracing
      - mesh shader
      - render graph
      - renderer
      - backend
      - shader
      - gpu
      - performance
```

支持：

```text
labels
authors
directories
keywords
```

但第一版不要过度复杂化。

---

# 8. Phase 4 — Normalize & Dedup Raw Data

统一 RawItem。

必须保证：

```text
同一个 GitHub Release
不会重复进入数据库
```

去重优先级：

```text
source_id + external_id
↓
canonical_url
↓
content_hash
```

HTML 内容抓取后做 canonical normalization。

不能因为 query string 不同产生重复 RawItem。

---

# 9. Phase 5 — Rule Filter

这是第一层廉价过滤。

默认识别并过滤：

```text
dependency bump
CI
typo
documentation-only
formatting
minor refactor
ordinary crash fix
ordinary bugfix
job post
marketing campaign
game launch
art showcase
basic tutorial
course
duplicate repost
```

但：

```text
不要 delete RawItem
```

设置：

```text
filter_status = ignored
filter_reason = ...
```

未来算法升级可以重跑。

---

# 10. Phase 6 — Candidate Detection

Rules 之后进入轻量 AI 分类。

目标不是总结，而是判断：

```text
这是不是一个值得进一步分析的技术变化？
```

固定输出结构：

```json
{
  "candidate": true,
  "reason": "...",
  "signals": [
    "CAPABILITY",
    "ARCHITECTURE"
  ]
}
```

Signals：

```text
CAPABILITY
PLATFORM_SUPPORT
API_SUPPORT
ARCHITECTURE
SPECIFICATION
PERFORMANCE
QUALITY
TOOLING
ADOPTION
BREAKING_CHANGE
```

所有 AI 输出使用结构化 schema 校验。

无效 JSON 不直接进入下一阶段。

---

# 11. Phase 7 — Existing Event Retrieval

Candidate 进入强模型之前，必须查询历史 Event。

默认时间窗：

```text
90 days
```

使用：

```text
Object
Topic
Technology
Platform
Embedding similarity
Aliases
```

pgvector 保存：

```text
title_embedding
change_embedding
```

查询目标：

```text
这是一个新的 Event，
还是已有 Event 的新证据？
```

---

# 12. Phase 8 — Event Clustering

组合：

```text
Deterministic rules
+
Embedding similarity
+
LLM final judgment
```

不能只用 embedding。

示例：

```text
Blender Blog
Blender Release Notes
GitHub Release
媒体报道
Reddit
```

最终：

```text
1 Event
```

EventSource role：

```text
primary
official
supporting
community
discovery
```

系统优先选择一手源作为 primary。

---

# 13. Phase 9 — Technical Analysis

这是系统最重要的 AI Prompt。

禁止：

```text
Summarize this article
```

必须围绕技术变化分析。

输入：

```text
RawItems
Existing related events
Object metadata
Topic candidates
```

输出严格 schema：

```yaml
title:

what_changed:
previous_state:
new_state:

event_type:
change_signal:

objects:
topics:
platforms:
technologies:

maturity_from:
maturity_to:

why_it_matters:
who_should_care:

evidence:
confidence:
```

重点判断：

```text
这项能力以前是否存在？

是第一次实现，
还是只是营销重新包装？

真正改变哪个 subsystem？

是否影响：
Engine
API
GPU
Platform
Architecture
Workflow

是否发生：
Research → Open Source
Open Source → SDK
SDK → Standard
Standard → Engine
Engine → Production
Desktop → Mobile
Vendor-specific → Cross-vendor
Experimental → Stable
```

---

# 14. Why It Matters 质量要求

这是产品核心。

不要生成：

```text
“This is an important update that improves graphics performance.”
```

这是失败。

应该类似：

```text
首次让该渲染路径在 Android/Vulkan 上进入正式支持，
减少移动端引擎维护独立 fallback backend 的需要，
同时也是该技术从 Desktop 向 Mobile 扩展的信号。
```

要求：

```text
具体
工程化
说明影响对象
说明变化原因
避免营销语言
```

---

# 15. Phase 10 — Topic Mapping

Topic 体系：

```text
Rendering Architecture
Geometry
Lighting & Shading
GPU Execution
Resource & Asset
Image Reconstruction
Neural Graphics
Platform & Runtime
```

细分必须支持：

```text
Render Graph
RHI
Bindless
GPU Scene
GPU Driven
Mesh Shader
Virtual Geometry
Ray Tracing
Real-time GI
ReSTIR
WebGPU
Vulkan
3DGS
Neural Rendering
Neural Texture Compression
Temporal Upscaling
Frame Generation
Mobile Rendering
...
```

Event 支持多 Topic。

不要强制单分类。

---

# 16. Phase 11 — Maturity Model

统一 maturity：

```text
Research
Prototype
Open Source
SDK
Standard
Engine Integration
Production
Cross-platform
Mainstream
```

若 Event 产生：

```text
maturity_from != maturity_to
```

则属于重要信号。

例如：

```text
SDK
→ Engine Integration
```

或：

```text
Desktop Production
→ Mobile Production
```

---

# 17. Phase 12 — Impact

内部评分五维：

```text
Capability Impact
Engineering Impact
Adoption Signal
Scope
Evidence Confidence
```

每项：

```text
0..5
```

UI 不显示 87/100。

最终映射：

```text
Critical
High
Notable
```

不能仅简单平均。

以下事件自动提升：

```text
Major Architecture Change
Major Standard Change
Maturity Transition
Cross-platform Expansion
Cross-vendor Adoption
Breaking Change
```

---

# 18. Phase 13 — Trend Engine

Topic Trend 使用：

```text
Important Event Count
Unique Object Count
Unique Vendor Count
Platform Expansion
Maturity Transition
Adoption Count
30d Velocity
90d Velocity
```

状态：

```text
Accelerating
Growing
Stable
Cooling
Research-heavy
```

第一版允许使用明确、简单、可解释的规则。

不要上复杂 ML。

---

# 19. Phase 14 — Backend API

至少实现：

```text
GET /events
GET /events/{slug}

GET /selected

GET /objects
GET /objects/{slug}

GET /topics
GET /topics/{slug}

GET /trends

GET /digests/daily
GET /digests/weekly
GET /digests/monthly
```

Filter：

```text
domain
object
topic
event_type
impact
platform
date
```

---

# 20. Phase 15 — Web

参考：

```text
https://aihot.virxact.com/
```

复刻：

```text
整体信息层级
导航结构
内容密度
卡片组织方式
时间流设计
主题页逻辑
```

不要机械像素复制品牌、Logo、文字或版权素材。

主题改成 Graphics Engine Radar。

主导航：

```text
精选
全部动态
趋势
主题
对象
日报
```

---

# 21. 首页

首页第一屏必须非常明确：

```text
Graphics Engine Radar

图形引擎每天都在变化。

我们持续监控引擎、Graphics API、
GPU、渲染技术和工具链。

AI 帮你过滤噪声，
只留下真正值得关注的变化。
```

核心模块：

```text
今日精选
正在加速
全部有效动态
重大技术演进
```

---

# 22. Event Card

必须包含：

```text
Change Signal
Object / Topic
时间

标题

What changed
一句话

Why it matters
1~3 句

Impact
平台 / Topic

Source
```

例如：

```text
[EXPAND] WebGPU

Galacean Engine ...

What changed
...

Why it matters
WebGPU 进一步进入生产级 Web 引擎，
是从浏览器能力向 Engine Runtime 扩散的信号。

High

Web · Rendering Architecture

Official · GitHub
```

不要让 Card 变成长文章。

---

# 23. Topic Page

例如：

```text
/topics/webgpu
```

展示：

```text
当前状态
Maturity
Trend

30d / 90d Event

关键 Object

Technical Timeline

关联 Topic
```

目标：

```text
用户能看懂这个技术是如何演进的
```

而不是只看到相关新闻列表。

---

# 24. Object Page

例如：

```text
/objects/blender
```

展示：

```text
Object Overview

最近重要变化

技术能力变化

关联 Topic

Timeline

Sources
```

---

# 25. Admin / Feedback

第一版需要最小后台。

支持：

```text
Promote Event
Reject Event
Merge Event
Split Event
Edit Event
Edit Topic
Override Impact
```

目的是记录：

```text
AI 判断哪里错了
```

形成后续反馈数据。

不是做完整 CMS。

---

# 26. Daily Digest

每天动态生成。

不能强制固定条数。

```text
今天真正值得看：3 条
```

完全正常。

Daily：

```text
今天发生了什么
```

Weekly：

```text
本周真正发生了哪些变化
```

Monthly：

```text
哪些技术正在明显推进
```

Weekly / Monthly 必须重新分析时间窗口。

禁止简单 concatenate Daily。

---

# 27. Seed Data

Web 开发阶段可以使用 seed。

但最终验收必须换真实数据。

建议先使用真实项目：

```text
Blender
Godot
Filament
DiligentEngine
wgpu
Dawn
Three.js
Babylon.js
Galacean
RenderDoc
Slang
Vulkan ecosystem
```

覆盖：

```text
Engine
API
Web
DCC
Tool
Shader
```

---

# 28. 测试要求

不要求为了形式做巨大测试体系。

但以下必须覆盖：

## Unit

```text
RawItem dedup
canonical URL
Rule filter
Impact mapping
Maturity transition
```

## Integration

```text
GitHub API
→ RawItem

RSS
→ RawItem

Candidate
→ Event

Multiple RawItems
→ One Event
```

## End-to-End

至少选择 10~20 个真实图形事件验证：

```text
Source
→ Collector
→ Filter
→ Cluster
→ Analysis
→ DB
→ API
→ Web
```

---

# 29. AI Pipeline 回归集

建立：

```text
tests/fixtures/intelligence/
```

至少包含：

```text
明显重要 Event
普通 Bugfix
营销稿
重复报道
重大 API 变化
重大 Engine Feature
Mobile enablement
GitHub PR
规范 Extension
DCC Rendering Change
```

目标不是只测 JSON 格式。

要验证：

```text
Should Select
Should Ignore
Should Merge
Should Promote
```

---

# 30. 验收标准

MVP 完成时必须给出实际数据。

至少汇报：

```text
总 RawItem 数
Ignored 数
Candidate 数
Event 数
Selected 数
Duplicate Merge 数
拥有 Official Source 比例
```

并人工抽样验证：

```text
重要事件是否漏掉
垃圾是否进入精选
重复是否正确归并
Topic 是否准确
Why it matters 是否有工程价值
```

不能只回复：

```text
BUILD SUCCESS
```

---

# 31. 第一阶段完成 Definition of Done

只有同时满足以下条件才算完成：

```text
[ ] 数据模型完成
[ ] migrations 可执行
[ ] 监控 Object 配置完成
[ ] GitHub Collector 可运行
[ ] RSS Collector 可运行
[ ] Release Notes Collector 可运行
[ ] Rule Filter 工作
[ ] Candidate Detection 工作
[ ] Event Dedup / Cluster 工作
[ ] Technical Analysis 工作
[ ] Topic Mapping 工作
[ ] Impact 工作
[ ] Why it matters 工作
[ ] API 工作
[ ] Web 工作
[ ] 真实数据端到端跑通
[ ] 10~20 个真实 Event 人工验证
[ ] README 含启动与架构说明
```

---

# 32. 实施顺序

严格按以下顺序推进：

```text
M0 Repository / Environment
        ↓
M1 Domain Model + Database
        ↓
M2 Monitoring Config
        ↓
M3 Collector Framework
        ↓
M4 GitHub / RSS / ReleaseNotes
        ↓
M5 Normalize + Rule Filter
        ↓
M6 Candidate Detection
        ↓
M7 Event Retrieval / Cluster
        ↓
M8 Technical Analysis
        ↓
M9 Topic / Maturity / Impact
        ↓
M10 API
        ↓
M11 Web
        ↓
M12 Trend / Digest
        ↓
M13 Real-world Validation
```

Web 页面骨架可以与 M3~M9 并行开发。

但最终必须接真实 API。

---

# 33. 工作纪律

执行过程中：

- 不重新设计已经明确的产品方向。
- 不随意减少监控范围。
- 不因为方便把 Event 简化成 Article。
- 不把所有 AI Pipeline 合成一个大 Prompt。
- 不扫描每一个 GitHub commit。
- 不过早做微服务。
- 不引入与 MVP 无关的大型基础设施。
- 不把营销热度作为 Impact。
- 不把用户阅读量作为 Trend 的核心指标。
- 不为了每天固定数量而降低精选阈值。

遇到可逆的技术细节：

> 采用合理默认继续实现。

只有以下情况才需要暂停：

```text
涉及数据破坏
需要新的外部权限 / Credential
现有仓库约束与本方案发生不可兼容冲突
关键技术条件实际上无法实现
```

---

# 34. 最终交付格式

完成后提交一份：

```text
IMPLEMENTATION_REPORT.md
```

必须包含：

## Implemented

完成了什么。

## Architecture

最终架构。

## Data Pipeline

真实数据从 Source 到 Web 的实际路径。

## Monitoring Coverage

已经配置多少 Object / Source。

## Validation

真实 Event 验证结果。

## Metrics

RawItem / Candidate / Event / Selected / Merge 数据。

## Known Limitations

明确没有完成什么。

## Deviations

如果偏离本 Spec：

```text
原设计
实际方案
偏离原因
影响
```

不允许静默偏离。

---

# 35. 最终目标

不要以：

```text
网站能打开
```

作为成功。

最终目标是：

> 打开 Graphics Engine Radar 后，用户每天只需要几分钟，就能知道图形引擎领域真正发生了哪些值得关注的技术变化，并能够长期看到 WebGPU、3DGS、GPU Driven、Neural Rendering 等技术如何从早期探索逐渐进入标准、引擎和生产环境。

产品核心：

```text
Coverage
+
Noise Filtering
+
Engineering Judgment
+
Long-term Technology Memory
```

其中最重要的是：

```text
Engineering Judgment
```

和：

```text
Long-term Technology Memory
```