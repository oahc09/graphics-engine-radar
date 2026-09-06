# 真实事件端到端抽样验证


## Domain: engine

### [High] v0.19.3
- object: wgpu (graphics_runtime) | signal: MATURE | type: VERSION_RELEASE
- maturity: SDK -> Production
- what changed: wgpu: v0.19.3
- why it matters: wgpu 为 WEBGPU 引入/扩展了后端支持, 意味着基于该渲染路径的引擎可以减少自行维护平台 fallback backend 的成本。 技术成熟度从 SDK 迁移到 Production: 这意味着该技术开始从试验阶段进入可评估/可生产的阶段, 是决定是否投入工程资源进行集成的关键节点。
- sources (1): official/github_release: v0.19.3

### [Notable] 8.56.1
- object: babylonjs (web_engine) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: Babylon.js: 8.56.1
- why it matters: 该变化改变了 Babylon.js 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: 8.56.1

### [Notable] 3.1.2-stable
- object: godot (game_engine) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: Godot: 3.1.2-stable
- why it matters: 该变化改变了 Godot 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: 3.1.2-stable

### [High] Bevy + WebGPU
- object: bevy (game_engine) | signal: NEW | type: FEATURE_ADDED
- maturity: — -> —
- what changed: Bevy: Bevy + WebGPU
- why it matters: 这是规范/扩展层面的变化,影响所有计划跟进实现的驱动与引擎团队; 跟进节奏决定了后续跨硬件一致性的验证成本。
- sources (1): official/official_blog: Bevy + WebGPU

### [Notable] v1.4.0-alpha.2
- object: galacean (web_engine) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: Galacean Engine: v1.4.0-alpha.2
- why it matters: 该变化改变了 Galacean Engine 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: v1.4.0-alpha.2

### [Notable] v2.12.0
- object: playcanvas (web_engine) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: PlayCanvas: v2.12.0
- why it matters: 该变化改变了 PlayCanvas 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: v2.12.0


## Domain: graphics_api

### [High] Vulkan 1.4.362 Released With New Extension Developed By Valve
- object: vulkan (graphics_api) | signal: SPEC | type: SPEC_CHANGE
- maturity: — -> —
- what changed: Vulkan: Vulkan 1.4.362 Released With New Extension Developed By Valve
- why it matters: 这是规范/扩展层面的变化,影响所有计划跟进实现的驱动与引擎团队; 跟进节奏决定了后续跨硬件一致性的验证成本。
- sources (1): community/community: Vulkan 1.4.362 Released With New Extension Develop

### [High] Add extension `subgroup-size-control`
- object: webgpu (graphics_api) | signal: SPEC | type: SPEC_CHANGE
- maturity: — -> —
- what changed: WebGPU: Add extension `subgroup-size-control`
- why it matters: 这是规范/扩展层面的变化,影响所有计划跟进实现的驱动与引擎团队; 跟进节奏决定了后续跨硬件一致性的验证成本。
- sources (1): supporting/github_pr: Add extension `subgroup-size-control`

### [Notable] Partial Graphics Programs
- object: direct3d-12 (graphics_api) | signal: NEW | type: FEATURE_ADDED
- maturity: — -> —
- what changed: Direct3D 12: Partial Graphics Programs
- why it matters: 该变化改变了 Direct3D 12 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/official_blog: Partial Graphics Programs

### [High] releases
- object: metal (graphics_api) | signal: NEW | type: FEATURE_ADDED
- maturity: — -> —
- what changed: Metal: releases
- why it matters: 变化覆盖移动平台(Ios、Macos、Visionos), 属于 Desktop → Mobile 方向的扩展信号; 面向移动端交付的团队需要评估该能力在目标 GPU 上的可用性。
- sources (1): official/release_notes: releases

### [Notable] Graphics Programming Conference 2025
- object: slang (tool) | signal: NEW | type: FEATURE_ADDED
- maturity: — -> —
- what changed: Slang: Graphics Programming Conference 2025
- why it matters: 该变化改变了 Slang 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/official_blog: Graphics Programming Conference 2025


## Domain: gpu_platform

### [Notable] Wine 11.17 Released With Initial Support For Display Mode Emulation
- object: arm-mali (gpu_vendor) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: ARM / Mali / Immortalis: Wine 11.17 Released With Initial Support For Display Mode Emulation
- why it matters: 该变化改变了 ARM / Mali / Immortalis 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): community/community: Wine 11.17 Released With Initial Support For Displ


## Domain: rendering_tech

### [Notable] CUDA Python 1.0: Stable APIs, One Foundation, Full Platform Access
- object: dlss (technology) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: DLSS: CUDA Python 1.0: Stable APIs, One Foundation, Full Platform Access
- why it matters: 这是规范/扩展层面的变化,影响所有计划跟进实现的驱动与引擎团队; 跟进节奏决定了后续跨硬件一致性的验证成本。
- sources (1): official/official_blog: CUDA Python 1.0: Stable APIs, One Foundation, Full


## Domain: tooling

### [Notable] Version v0.92
- object: renderdoc (tool) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: RenderDoc: Version v0.92
- why it matters: 该变化改变了 RenderDoc 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: Version v0.92

### [Notable] Tracy Profiler 0.13.1
- object: tracy (tool) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: Tracy Profiler: Tracy Profiler 0.13.1
- why it matters: 变化覆盖移动平台(Android、Macos), 属于 Desktop → Mobile 方向的扩展信号; 面向移动端交付的团队需要评估该能力在目标 GPU 上的可用性。
- sources (1): official/github_release: Tracy Profiler 0.13.1

### [Notable] DX Compiler release for April 2021
- object: dxc (tool) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: DXC: DX Compiler release for April 2021
- why it matters: 该变化改变了 DXC 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: DX Compiler release for April 2021

### [Notable] Release v0.9.16.1
- object: gfxreconstruct (tool) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: gfxreconstruct: Release v0.9.16.1
- why it matters: 变化覆盖移动平台(Android), 属于 Desktop → Mobile 方向的扩展信号; 面向移动端交付的团队需要评估该能力在目标 GPU 上的可用性。
- sources (1): official/github_release: Release v0.9.16.1


## Domain: content_pipeline

### [Notable] Blender Lab Activity Report – Q1 2026
- object: blender (dcc) | signal: NEW | type: FEATURE_ADDED
- maturity: — -> —
- what changed: Blender: Blender Lab Activity Report – Q1 2026
- why it matters: 该变化改变了 Blender 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/official_blog: Blender Lab Activity Report – Q1 2026


## Domain: standard

### [Notable] glTF
- object: gltf (standard) | signal: NEW | type: FEATURE_ADDED
- maturity: — -> —
- what changed: glTF: glTF
- why it matters: 这是规范/扩展层面的变化,影响所有计划跟进实现的驱动与引擎团队; 跟进节奏决定了后续跨硬件一致性的验证成本。
- sources (1): official/spec_registry: glTF

### [Notable] Version 1.35.4
- object: materialx (standard) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: MaterialX: Version 1.35.4
- why it matters: 该变化改变了 MaterialX 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: Version 1.35.4

### [Notable] v4.3.0-beta1
- object: ktx (standard) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: KTX: v4.3.0-beta1
- why it matters: 该变化改变了 KTX 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: v4.3.0-beta1

### [Notable] v0.10
- object: meshoptimizer (standard) | signal: NEW | type: VERSION_RELEASE
- maturity: — -> —
- what changed: meshoptimizer: v0.10
- why it matters: 该变化改变了 meshoptimizer 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。
- sources (1): official/github_release: v0.10



Total sampled events: 22
