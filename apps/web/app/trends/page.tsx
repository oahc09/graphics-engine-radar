import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TrendsPage() {
  const data = await api.trends();
  const trends = data?.trends || [];
  return (
    <div>
      <h1>趋势</h1>
      <p className="meta-line">
        基于 Important Event Count、Unique Object Count、Maturity Transition、30d/90d
        Velocity 的可解释规则,不使用浏览量。
      </p>
      {trends.map((t) => (
        <div key={t.topic_slug} className="trend-row">
          <span className={`state state-${t.state.toLowerCase()}`}>{t.state}</span>
          <b>{t.topic_name}</b>
          <span className="meta-line" style={{ margin: 0 }}>
            30d events={t.event_count_30d} important={t.important_event_count_30d} objects=
            {t.unique_object_count_30d} maturity↑={t.maturity_transition_count_30d} adoption=
            {t.adoption_count_30d}
          </span>
        </div>
      ))}
      {!trends.length && <p className="empty">趋势快照尚未生成,运行 intelligence trends 后可见。</p>}
    </div>
  );
}
