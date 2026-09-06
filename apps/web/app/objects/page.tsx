import Link from "next/link";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const TYPE_LABELS: Record<string, string> = {
  game_engine: "Game Engine",
  rendering_engine: "Rendering Engine",
  web_engine: "Web Engine",
  graphics_runtime: "Graphics Runtime",
  graphics_api: "Graphics API",
  gpu_vendor: "GPU Vendor",
  platform: "Platform",
  dcc: "DCC",
  tool: "Tool",
  standard: "Standard",
  technology: "Technology",
};

export default async function ObjectsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const data = await api.objects({ type: sp.type });
  const objects = data?.objects || [];
  const types = Array.from(new Set(objects.map((o) => o.type)));
  return (
    <div>
      <h1>对象</h1>
      <p className="meta-line">共监控 {objects.length} 个对象,全部配置化。</p>
      <div className="filters">
        <Link href="/objects" className={!sp.type ? "on" : ""}>全部</Link>
        {types.map((t) => (
          <Link key={t} href={`/objects?type=${t}`} className={sp.type === t ? "on" : ""}>
            {TYPE_LABELS[t] || t}
          </Link>
        ))}
      </div>
      <div className="grid">
        {objects.map((o) => (
          <Link key={o.slug} href={`/objects/${o.slug}`} className="card">
            <h3>{o.name}</h3>
            <p className="what">{o.description}</p>
            <div className="card-foot">
              <span>{TYPE_LABELS[o.type] || o.type}</span>
              <span>{o.domain}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
