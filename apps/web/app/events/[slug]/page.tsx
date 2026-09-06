import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function EventPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const event = await api.event(slug);
  if (!event) {
    return <p className="empty">事件不存在或 API 不可用。</p>;
  }
  return (
    <div>
      <p className="meta-line">
        [{event.change_signal}] {event.event_type} · {event.impact_level} ·{" "}
        {event.status}
      </p>
      <h1>{event.title}</h1>
      {event.maturity_to && (
        <p className="meta-line">
          成熟度: {event.maturity_from || "—"} → {event.maturity_to}
        </p>
      )}
      <article className="prose">
        <h3>What happened</h3>
        <p>{event.summary}</p>
        <h3>What changed</h3>
        <p>{event.change}</p>
        {event.why_it_matters && (
          <>
            <h3>Why it matters</h3>
            <p>{event.why_it_matters}</p>
          </>
        )}
        {event.who_should_care && (
          <>
            <h3>Who should care</h3>
            <p>{event.who_should_care}</p>
          </>
        )}
      </article>
      <h2>Sources</h2>
      {(event.sources || []).map((s, i) => (
        <div key={i} className="list-row">
          <b>{s.role}</b>
          <span>{s.type}</span>
          {s.url && (
            <a href={s.url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
              打开来源 ↗
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
