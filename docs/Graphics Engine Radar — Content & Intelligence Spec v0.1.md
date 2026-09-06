# Graphics Engine Radar

Version: `v0.1`  
Status: Implementation Baseline

## 1. 产品定义

Graphics Engine Radar 是面向图形引擎与实时渲染研发人员的技术情报系统。

目标不是聚合更多新闻，而是：

> 每天监控图形引擎领域的新变化，用 AI 去掉重复、营销和低价值信息，只留下真正可能影响技术能力、工程实现、技术选型和未来趋势的变化。

核心链路：

```text
全量监控
→ 发现变化
→ 去噪
→ 事件归并
→ 技术理解
→ 工程价值判断
→ 技术演进追踪
→ 精选发布
```

产品最终回答四个问题：

```text
What happened?
发生了什么？

What changed?
真正改变了什么能力？

Why it matters?
为什么图形工程师应该关注？

Where is it going?
它代表什么技术演进趋势？
```

---

# 2. 核心原则

## 2.1 Event First

系统的核心数据不是 `Article`，而是：

```text
Event
```

多个信息源：

```text
Release Notes
GitHub Release
GitHub PR
官方 Blog
规范更新
厂商公告
媒体报道
社区讨论
```

可能描述同一个事件。

最终只生成：

```text
N RawItems
    ↓
1 Event
```

Article 只是证据。

Event 才是产品。

---

## 2.2 全量监控，事件级筛选

不对监控对象做 P0/P1/P2。

进入监控范围的对象都持续抓取。

```text
Object 不分重要程度

Event 判断重要程度
```

例如：

```text
Unity 普通 bugfix
→ Drop

冷门 Renderer 新增完整 WebGPU backend
→ Selected
```

对象热度不能替代技术价值。

---

## 2.3 一手源优先

证据优先级：

```text
Specification / Registry
Official Release Notes
Official GitHub Release
Merged PR
Official Engineering Blog
Official Developer Statement
Technical Media
Community
转载
```

二手媒体用于发现。

社区用于趋势信号。

事实尽可能回溯到官方来源。

---

# 3. 监控范围

系统保持四个一级技术域。

```text
1. Engine
2. Graphics API
3. GPU & Platform
4. Rendering Technology
```

另外存在三个横向监控域：

```text
5. Graphics Tooling
6. DCC / Asset / Content Pipeline
7. Cross-cutting Signal
```

---

# 4. Engine

## 4.1 Game Engine

```text
Unreal Engine
Unity
Cocos Creator
Godot
O3DE
Flax Engine
Bevy
Defold
Stride
Wicked Engine
CryEngine
Fyrox
GameMaker
```

持续补充新的活跃引擎。

---

## 4.2 Rendering Engine / Graphics Framework

```text
Filament
bgfx
Diligent Engine
The Forge
Magnum
Ogre-Next
Horde3D
Falcor
NVRHI
sokol
Skia
Skia Graphite
SDL GPU
Mesa
```

---

## 4.3 Web Graphics Engine

```text
Three.js
Babylon.js
PlayCanvas
Galacean Engine
PixiJS
Phaser
CesiumJS
MapLibre GL JS
React Three Fiber
```

重点监控：

```text
WebGPU
GPU Driven
Compute
Shader
Material
Rendering Pipeline
Performance
Backend Architecture
```

而不是普通 Web framework API 变化。

---

## 4.4 Platform Graphics Runtime

```text
ANGLE
Dawn
wgpu
wgpu-native
Flutter Impeller
Qt RHI / QRhi
Chromium Graphics
WebKit Graphics
Android HWUI
Android Skia
RealityKit
SceneKit
Mesa
```

这类项目虽然不一定叫 Engine，但其变化直接影响图形 Runtime，因此属于核心范围。

---

# 5. Graphics API

核心 API：

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

---

## 5.1 Vulkan

监控：

```text
Vulkan Specification
Vulkan Extensions
Vulkan Registry
Vulkan Roadmap
Vulkan Profiles
Vulkan SDK
Validation Layers
SPIR-V
Vulkan Video
CTS
Driver Enablement
```

---

## 5.2 OpenGL

完整纳入：

```text
OpenGL Specification
OpenGL Extensions
OpenGL Registry
GLSL Specification

OpenGL ES Specification
OpenGL ES Extensions

EGL Specification
EGL Extensions
```

GLX / WGL 相关变化如果影响引擎 runtime 同样纳入。

---

## 5.3 DirectX

```text
Direct3D 12
DXGI
Agility SDK
Shader Model
DXIL
DXC
DirectStorage
DirectSR
Work Graphs
DRED
```

---

## 5.4 Metal

```text
Metal API
Metal Shading Language
MetalFX
Ray Tracing
Mesh Shading
Dynamic Caching
GPU Tooling
Apple GPU capabilities
```

---

## 5.5 WebGPU

```text
WebGPU Specification
WGSL
Dawn
wgpu
Browser Enablement
Native WebGPU
CTS
Engine Adoption
```

---

# 6. Shader Language / IR

独立 Topic：

```text
GLSL
HLSL
Slang
WGSL
Metal Shading Language

SPIR-V
DXIL
```

相关工具：

```text
DXC
shaderc
SPIRV-Tools
SPIRV-Cross
Slang compiler
```

`Slang` 按完整 Shader Toolchain 监控，而不是只作为语法语言。

重点追踪：

```text
Cross-platform compilation
Module system
Generics
Reflection
Shader linking
Backend support
SPIR-V / DXIL / Metal output
Compiler performance
```

---

# 7. GPU & Platform

GPU Vendor：

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

重点监控：

```text
新 GPU 图形能力
新 Extension
Driver Enablement
SDK
Ray Tracing
Mesh Shader
VRS
Neural Graphics
Upscaling
Frame Generation
Compression
Performance
Power
Profiling tools
```

不以普通硬件发布、价格、游戏跑分为核心内容。

---

## 7.1 Platform

```text
Android
Windows
Linux
macOS
iOS
visionOS
Web
```

重点包括：

Android：

```text
Vulkan
ANGLE
HWUI
SurfaceFlinger
AGI
GPU Driver
ADPF
Graphics APIs
```

Windows：

```text
D3D12
DXGI
WDDM
Agility SDK
DirectSR
Work Graphs
GPU scheduling
```

Linux：

```text
Mesa
RADV
ANV
NVK
DRM/KMS
Wayland graphics stack
```

Web：

```text
Chromium
Dawn
WebGPU
WebGL
WebKit
Firefox / Gecko graphics
```

---

# 8. Rendering Technology

## 8.1 Rendering Architecture

```text
RHI
Render Graph
Frame Graph
GPU Scene
Bindless
Descriptor Model
Pipeline Management
Shader Pipeline
Multithreaded Rendering
Async Compute
Async Upload
GPU Scheduling
Persistent GPU Data
```

## 8.2 Geometry

```text
GPU Driven Rendering
Mesh Shader
Task Shader
Meshlet
Virtual Geometry
GPU Culling
Occlusion Culling
LOD
Geometry Compression
Nanite-like Rendering
```

## 8.3 Lighting & Shading

```text
PBR
Real-time GI
Path Tracing
Ray Tracing
ReSTIR
Radiance Cache
DDGI
Probe GI
Screen-space GI
Material System
Shader System
```

## 8.4 Image Reconstruction

```text
Temporal Upscaling
DLSS
FSR
XeSS
MetalFX
TSR
Frame Generation
Ray Reconstruction
Denoising
Dynamic Resolution
```

## 8.5 Neural Graphics

```text
Neural Rendering
Neural Shading
Neural Texture Compression
Neural Material
Neural Reconstruction
Neural Radiance Cache

3D Gaussian Splatting
4D Gaussian Splatting
NeRF
Neural Fields
Radiance Fields
```

纯论文默认不过滤进入精选。

必须出现至少一种工程化信号：

```text
Open Source
SDK
Standard
Engine Integration
Production Usage
GPU Vendor Support
Cross-platform Implementation
```

---

# 9. Graphics Tooling

完整纳入：

```text
RenderDoc
NVIDIA Nsight Graphics
NVIDIA Nsight Systems
PIX
AMD Radeon GPU Profiler
AMD Radeon Raytracing Analyzer
Intel GPA
Android GPU Inspector
Arm Performance Studio
Xcode GPU Tools
Tracy
Superluminal
gfxreconstruct

DXC
Slang
shaderc
SPIRV-Tools
SPIRV-Cross
```

只重点展示：

```text
新 API 支持
新 GPU 支持
新的 GPU 分析能力
Shader 调试突破
Capture / Replay 改进
重大性能分析能力
新的跨平台能力
```

普通 UI、稳定性修复等进入全部动态或过滤。

---

# 10. DCC / Content Pipeline

纳入：

```text
Blender
Houdini
Maya
3ds Max
Substance 3D
```

Blender 重点监控：

```text
Eevee
Cycles GPU
Vulkan
Geometry Nodes
GPU Compositor
Shader
Material
glTF
USD
Geometry processing
GPU acceleration
Asset Pipeline
```

只有与实时图形、资产生产、GPU、Shader、引擎 Pipeline 有关系的事件进入 Radar。

Blender 官方版本体系和 Release Notes 足够稳定，适合作为结构化长期信源。

---

# 11. Asset / Standard

```text
glTF
OpenUSD / USD
MaterialX
OpenPBR
KTX
Basis Universal
Draco
meshoptimizer
OpenEXR
OpenImageIO
MDL
OSL
```

重点监控：

```text
新 Extension
新 Runtime Capability
GPU-friendly Representation
Compression
Streaming
Material interoperability
Engine Adoption
DCC Adoption
```

---

# 12. Event Taxonomy

系统统一使用以下事件类型。

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

同时生成 Change Signal：

```text
NEW
EXPAND
ADOPT
MATURE
SPEC
PERF
BREAK
```

例如：

```text
EXPAND
Desktop → Mobile

ADOPT
SDK → Engine

MATURE
Experimental → Production
```

---

# 13. 默认噪声规则

以下内容默认过滤：

```text
普通 bugfix
Dependency bump
CI
文档 typo
小规模 refactor
代码格式
普通 crash 修复
普通 Issue
普通 commit
招聘
市场活动
游戏发布
美术展示
Shader 教程
培训课程
无技术信息的营销内容
重复转载
缺少依据的性能宣传
纯论文
```

但规则过滤不能永久删除 RawItem。

统一保存为：

```text
ignored
```

未来算法升级可以重新分析。

---

# 14. Cross-cutting Signal

这是系统区别于普通新闻聚合器的关键能力。

检测状态迁移：

```text
Research
    ↓
Prototype
    ↓
Open Source
    ↓
SDK
    ↓
Standard
    ↓
Engine Integration
    ↓
Production
    ↓
Cross-platform
    ↓
Mainstream
```

以及：

```text
Desktop → Mobile

Vendor-specific → Cross-vendor

Experimental → Stable

API Feature → Driver Support

Driver Support → Engine Adoption

Engine Adoption → Production
```

出现这种迁移时自动提高事件价值。

---

# 15. Topic Taxonomy

Topic 是长期技术能力树，而不是新闻栏目。

顶层：

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

Event 可以同时属于多个 Topic。

例如：

```text
Qualcomm 新增 Mobile Mesh Shader

topics:
- Mesh Shader
- GPU Driven Rendering
- Vulkan
- Mobile Rendering
- Android
```

---

# 16. 数据模型

核心实体：

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
```

---

## Object

```yaml
id:
slug:
name:
type:
domain:
description:
official_url:
github_repo:
aliases:
active:
created_at:
updated_at:
```

`type` 示例：

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

```yaml
id:
object_id:

type:
url:

adapter:
config:

poll_interval:
last_cursor:
last_success_at:

enabled:
created_at:
updated_at:
```

Source Type：

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

采集层原始数据。

```yaml
id:
source_id:

external_id:
url:

title:
content:
author:

published_at:
fetched_at:

content_hash:
language:

raw_payload:

filter_status:
filter_reason:
```

状态：

```text
new
ignored
candidate
processed
```

---

## Event

真正产品数据。

```yaml
id:
slug:

title:
summary:

event_type:
change_signal:

change:
why_it_matters:

impact_level:
confidence:

maturity_from:
maturity_to:

first_seen_at:
published_at:
updated_at:

status:
```

`status`：

```text
candidate
verified
published
rejected
merged
```

---

## EventSource

```yaml
event_id:
raw_item_id:

role:
confidence:
```

role：

```text
primary
official
supporting
community
discovery
```

---

## EventTopic

```yaml
event_id:
topic_id:

relation:
confidence:
```

relation：

```text
direct
affected
enabled
adopted
related
```

---

# 17. Impact 模型

第一版不使用看似精确的 `87/100`。

只显示：

```text
Critical
High
Notable
```

内部仍保存五维评分：

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

精选不是简单按总分排序。

增加强规则：

```text
Maturity Transition
Cross-platform Expansion
Major Architecture Change
Major Standard Change
```

满足这些条件可直接提高等级。

---

# 18. AI Pipeline

最终流水线：

```text
Collect
   ↓
Normalize
   ↓
Rule Filter
   ↓
Candidate Detection
   ↓
Event Retrieval
   ↓
Event Clustering
   ↓
Source Verification
   ↓
Technical Analysis
   ↓
Topic Mapping
   ↓
Maturity Analysis
   ↓
Impact Evaluation
   ↓
Trend Update
   ↓
Publish
```

---

# 19. Collect

绝对不要实现一个万能 Crawler。

使用 Adapter 架构：

```text
GitHubAdapter
RSSAdapter
ReleaseNotesAdapter
SpecRegistryAdapter
BlogAdapter
HTMLAdapter
ConferenceAdapter
CommunityAdapter
```

接口统一：

```text
fetch(cursor) -> RawItem[]
```

---

# 20. GitHub Adapter

GitHub 是整个系统最重要的自动化来源之一。

优先抓：

```text
Releases
Tags
Merged PR
Selected Issues
Discussions
Roadmap
```

GitHub 官方 REST API 可以直接获取公开 Release，并提供 Release、PullRequest、Issue、Discussion 等事件类型，因此适合作为稳定的结构化采集源。

不默认扫描每个 Commit。

每个项目支持配置：

```yaml
repository: gfx-rs/wgpu

watch:
  releases: true

  pull_requests:
    merged_only: true

    keywords:
      - vulkan
      - metal
      - dx12
      - webgpu
      - bindless
      - ray tracing
      - mesh shader
      - backend
      - render graph
```

还可以定义：

```yaml
labels:
directories:
authors:
```

---

# 21. Candidate Detection

第一轮不能直接使用最昂贵模型。

流程：

```text
Rules
↓
Lightweight Classification
↓
Strong Model
```

候选判断只问：

```text
是否包含新的：

Capability
Platform Support
API Support
Architecture
Specification
Performance
Tooling
Technology Adoption
```

输出：

```json
{
  "candidate": true,
  "reason": "New WebGPU rendering backend"
}
```

---

# 22. Event Retrieval

这是比普通 RAG 更关键的一步。

处理 Candidate 之前，先查询：

```text
过去 30~90 天
```

是否已经存在相似 Event。

检索字段：

```text
Object
Technology
Platform
Title embedding
Change embedding
Aliases
```

避免 AI 把同一事件重复创建。

---

# 23. Event Clustering

判断多个 RawItem 是否属于一个 Event。

例如：

```text
GitHub Release
Official Blog
Release Notes
Phoronix
Reddit
```

最终：

```text
1 Event

primary_source:
Official Release Notes

supporting:
GitHub Release

community_signal:
Reddit
```

Cluster 建议：

```text
规则匹配
+
Embedding similarity
+
LLM final decision
```

避免只靠向量距离。

---

# 24. Technical Analysis

强模型只处理已经通过 Candidate 的内容。

固定输出：

```yaml
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

禁止让模型只是：

```text
“请总结文章”
```

核心 Prompt 应围绕：

```text
这项能力以前存在吗？

真正改变的 subsystem 是什么？

是新的技术能力，
还是只是包装和营销？

影响哪些 Engine / API / Platform？

是否产生技术成熟度迁移？

一个图形引擎工程师是否需要现在知道？
```

---

# 25. Trend Engine

趋势不能使用页面浏览量作为主要依据。

使用：

```text
Important Event Count
Unique Object Count
Unique Vendor Count
Platform Expansion
Maturity Transition
Adoption Count
30d / 90d Velocity
```

状态：

```text
Accelerating
Growing
Stable
Cooling
Research-heavy
```

例如：

```text
WebGPU

30d:
8 significant events
4 engines
3 platforms
2 maturity transitions

Trend:
Accelerating
```

---

# 26. 首页精选

数量动态。

不要每日固定 10 条。

例如：

```text
今天真正值得看：3 条
```

完全合法。

精选规则：

至少满足之一：

```text
产生新能力
改变架构
进入新平台
进入新引擎
发生规范变化
产生明显性能变化
出现技术成熟度迁移
形成跨厂商采用
形成趋势转折信号
```

---

# 27. 页面 IA

主导航保持克制：

```text
精选
全部动态
趋势
主题
对象
日报
```

---

## 精选

回答：

> 今天有什么是图形工程师真正应该知道的？

Card：

```text
[EXPAND] [WebGPU]

Galacean Engine adds ...

发生了什么
...

Why it matters
...

影响
Web · Rendering Architecture

Official · GitHub
```

---

## 全部动态

通过基础有效性判断但没有进入精选的 Event。

支持过滤：

```text
Engine
API
GPU
Technology
Platform
Event Type
Topic
Date
```

---

## Topic

例如：

```text
/topics/webgpu
/topics/3dgs
/topics/neural-rendering
/topics/gpu-driven
```

展示：

```text
当前成熟阶段
最近重要 Event
关键 Object
30 / 90 天趋势
技术 Timeline
相关 Topic
```

---

## Object

例如：

```text
/objects/unreal-engine
/objects/vulkan
/objects/qualcomm-adreno
/objects/blender
```

展示：

```text
最近变化
关键能力
关联 Topics
Event Timeline
Source
```

---

# 28. Daily / Weekly / Monthly

日报：

```text
今天发生什么
```

周报：

```text
本周真正有哪些技术变化
```

月报：

```text
哪些技术明显在推进
哪些趋势发生阶段变化
```

Weekly / Monthly 绝不能简单拼 Daily。

必须重新分析整个时间窗口。

---

# 29. 推荐技术架构

第一版优先简单、可扩展：

```text
Frontend
Next.js

Backend API
FastAPI

Database
PostgreSQL

Vector
pgvector

Queue / Scheduler
Redis + Celery
或
Redis + RQ

Crawler
Python

AI Pipeline
Python

Storage
PostgreSQL
+
Object Storage（必要时保存原始快照）
```

第一版没必要立即上：

```text
Kafka
Elasticsearch
Neo4j
复杂微服务
```

---

# 30. 服务拆分

逻辑拆分：

```text
collector
normalizer
filter
event-engine
intelligence
trend-engine
publisher
api
web
```

物理部署第一版可以只有：

```text
web
api
worker
postgres
redis
```

不要过早微服务化。

---

# 31. 目录建议

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
```

监控对象不要硬编码。

采用配置驱动：

```text
config/objects
config/sources
```

---

# 32. Source 配置示例

```yaml
id: blender

name: Blender

type: dcc

sources:
  - type: release_notes
    url: ...

  - type: github_release
    repo: blender/blender

  - type: official_blog
    url: ...

topics:
  - rendering
  - vulkan
  - asset-pipeline
  - geometry
```

新增对象主要是新增配置，而不是修改程序。

---

# 33. 抓取频率

不要求实时。

建议：

```text
GitHub Releases       1h
重要 GitHub PR        2h
RSS / Blog            2h
Specification         6h
Release Notes         6h
Community             4h
Conference            12h
```

图形领域的价值在筛选质量，不在秒级速度。

---

# 34. 失败设计

所有采集任务必须：

```text
idempotent
retryable
cursor-based
observable
```

每个 Source 保存：

```text
last_cursor
last_success_at
last_error
next_poll_at
```

一个 Source 失败不能影响其他 Source。

---

# 35. 去重键

RawItem：

```text
source_id + external_id
```

无 external id：

```text
canonical_url
```

仍然没有：

```text
content_hash
```

Event 层再做语义去重。

---

# 36. AI 可追溯性

每个 AI 判断必须保存：

```text
model
prompt_version
input_hash
output
created_at
```

尤其保存：

```text
why selected
why rejected
```

后续才能发现：

> 为什么某条真正重要的图形新闻被过滤掉？

这是长期提高 Signal Quality 的关键数据。

---

# 37. 人工能力

第一版必须保留：

```text
Promote to Selected
Remove from Selected
Merge Events
Split Event
Edit Topic
Edit Object
Override Impact
```

不是因为系统依赖人工运营，而是为了：

```text
获取训练 / 调优反馈
```

用户行为逐渐形成：

```text
Graphics Intelligence Feedback Dataset
```

---

# 38. 第一阶段不要做

暂不需要：

```text
复杂 Knowledge Graph
用户推荐算法
社交系统
评论
复杂账号体系
APP
实时 Push
秒级抓取
Kafka
多 Agent 自主研究
全网搜索引擎
```

这些不会决定产品第一阶段是否成功。

---

# 39. 第一阶段必须做好的东西

只有六件：

```text
1. Monitoring Coverage
监控范围是否够完整

2. Source Reliability
是否稳定抓到一手变化

3. Event Deduplication
同一事件是否只出现一次

4. Noise Filtering
是否真的能把垃圾过滤掉

5. Why It Matters
判断是否具有图形工程价值

6. Topic Memory
能否形成长期技术演进记录
```

---

# 40. MVP 验收指标

不是 PV。

核心指标：

```text
Coverage Recall
重要事件漏报率

Noise Rate
精选中的低价值事件比例

Duplicate Rate
重复 Event 比例

Primary Source Rate
拥有一手信源的 Event 比例

Topic Accuracy
Topic 分类正确率

Why-it-matters Quality
工程判断准确程度
```

目标方向：

```text
宁愿精选少，
不能精选水。

宁愿全部动态稍多，
不能漏掉真正重要的技术变化。
```

---

# 41. 产品护城河

长期竞争力不是 Crawler。

Crawler 很容易复制。

真正积累的是：

```text
Object Database
+
Source Database
+
Historical Events
+
Topic Evolution
+
Technology Relationships
+
Graphics-specific Judgment Data
```

几年后系统能够回答：

```text
WebGPU 是如何一步步进入主流引擎的？

Mobile Ray Tracing 什么时候真正开始普及？

3DGS 从研究到标准化经历了哪些节点？

过去三年图形引擎为什么逐渐转向 GPU Driven？

Slang 的采用为什么开始加速？

Vulkan Descriptor Model 如何演进？
```

这时它就不再是：

```text
Graphics News
```

而是：

```text
Graphics Technology Intelligence
```

---

# 42. 最终产品定位

首页承诺：

> 图形引擎每天都在变化。  
> 我们持续监控引擎、Graphics API、GPU、渲染技术和工具链。  
> AI 帮你过滤噪声，只留下真正值得关注的变化。

内部产品原则则只有一句：

> Don't rank news. Detect meaningful changes in graphics technology.