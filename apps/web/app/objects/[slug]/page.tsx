import { EventCard } from "@/components/EventCard";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

type SourceRow = {
  type: string;
  url: string | null;
  adapter: string;
  enabled: boolean;
  last_success_at: string | null;
  last_error: string | null;
};

export default async function ObjectPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const obj = await api.object(slug);
  if (!obj) {
    return <p className="empty">对象不存在或 API 不可用。</p>;
  }
  const sources = (obj.sources as SourceRow[]) || [];
  return (
    <div>
      <h1>{obj.name}</h1>
      <p className="meta-line">
        {obj.type} · {obj.domain}
        {obj.official_url && (
          <>
            {" · "}
            <a href={obj.official_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
              official ↗
            </a>
          </>
        )}
        {obj.github_repo && ` · github: ${obj.github_repo}`}
      </p>
      <p>{obj.description}</p>

      <h2>最近重要变化</h2>
      <div className="grid">
        {(obj.events || []).map((e) => (
          <EventCard key={e.slug} event={e} detailed />
        ))}
      </div>
      {!obj.events?.length && <p className="empty">暂无事件。</p>}

      <h2>Sources</h2>
      {sources.map((s, i) => (
        <div key={i} className="list-row">
          <b>{s.type}</b>
          <span className="meta-line" style={{ margin: 0 }}>
            {s.url} · adapter={s.adapter} · {s.enabled ? "enabled" : "disabled"}
            {s.last_error ? ` · last_error: ${s.last_error.slice(0, 80)}` : ""}
          </span>
        </div>
      ))}
      {!sources.length && <p className="empty">该对象尚未配置 Source(可逐步补充)。</p>}
    </div>
  );
}
