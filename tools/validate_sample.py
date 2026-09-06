#!/usr/bin/env python3
"""Sample real events across all monitoring domains for manual validation
(spec: 10-20 real events covering Engine / Web Graphics / Graphics API /
GPU-Platform / Shader-Slang / DCC-Blender / Tooling / Standard-glTF).

Outputs docs/VALIDATION.md.
"""

from __future__ import annotations

import sys
from collections import defaultdict

sys.path.insert(0, "/Users/caohao/Documents/AIWork/GraphicsEngineRadar")

from sqlalchemy import func, or_  # noqa: E402

from radar_domain.db import session_scope  # noqa: E402
from radar_domain.models import Event, EventSource, Object, RawItem, Source  # noqa: E402

DOMAINS = ["engine", "graphics_api", "gpu_platform", "rendering_tech",
           "tooling", "content_pipeline", "standard"]

# manual high-value watches per domain for the sampling report
WATCH = {
    "engine": ["wgpu", "threejs", "babylonjs", "godot", "bevy", "galacean", "playcanvas"],
    "graphics_api": ["vulkan", "webgpu", "direct3d-12", "metal", "opengl", "slang"],
    "gpu_platform": ["nvidia", "amd", "mesa", "android"],
    "rendering_tech": ["slang", "dlss", "3d-gaussian-splatting"],
    "tooling": ["renderdoc", "tracy", "dxc", "gfxreconstruct"],
    "content_pipeline": ["blender", "openusd"],
    "standard": ["gltf", "materialx", "ktx", "meshoptimizer"],
}


def _v(x):
    return x.value if hasattr(x, "value") else (x or "—")


def main() -> None:
    lines = ["# 真实事件端到端抽样验证\n"]
    total = 0
    with session_scope() as session:
        for domain in DOMAINS:
            objs = session.query(Object).filter(
                Object.domain == domain, Object.active.is_(True)).all()
            slugs = {o.slug for o in objs}
            watch_slugs = [s for s in WATCH.get(domain, []) if s in slugs]
            picks = []
            for slug in watch_slugs:
                obj = session.query(Object).filter(Object.slug == slug).first()
                ev = (
                    session.query(Event)
                    .filter(Event.object_id == obj.id,
                            or_(Event.impact_level.in_(("High", "Critical")),
                                Event.maturity_to.isnot(None)))
                    .order_by(Event.first_seen_at.desc())
                    .first()
                ) if obj else None
                if ev is None and obj:
                    ev = (
                        session.query(Event)
                        .filter(Event.object_id == obj.id)
                        .order_by(Event.first_seen_at.desc())
                        .first()
                    )
                if ev:
                    picks.append((obj, ev))
            if not picks:
                evs = (
                    session.query(Event).join(Object, Event.object_id == Object.id)
                    .filter(Object.domain == domain)
                    .order_by(Event.first_seen_at.desc()).limit(2).all()
                )
                picks = [(e.object, e) for e in evs]
            lines.append(f"\n## Domain: {domain}\n")
            for obj, ev in picks:
                total += 1
                srcs = (
                    session.query(EventSource, RawItem, Source)
                    .join(RawItem, EventSource.raw_item_id == RawItem.id)
                    .join(Source, RawItem.source_id == Source.id)
                    .filter(EventSource.event_id == ev.id).all()
                )
                src_desc = "; ".join(
                    f"{_v(link.role)}/{_v(s.type)}: {r.title[:50]}" for link, r, s in srcs[:4])
                lines.append(
                    f"### [{_v(ev.impact_level)}] {ev.title}\n"
                    f"- object: {obj.slug} ({_v(obj.type)}) | signal: {_v(ev.change_signal)} "
                    f"| type: {_v(ev.event_type)}\n"
                    f"- maturity: {_v(ev.maturity_from)} -> {_v(ev.maturity_to)}\n"
                    f"- what changed: {ev.change[:200]}\n"
                    f"- why it matters: {ev.why_it_matters[:300]}\n"
                    f"- sources ({len(srcs)}): {src_desc}\n"
                )
    lines.append(f"\n\nTotal sampled events: {total}\n")
    out = "\n".join(lines)
    with open("docs/VALIDATION.md", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"sampled {total} events -> docs/VALIDATION.md")


if __name__ == "__main__":
    main()
