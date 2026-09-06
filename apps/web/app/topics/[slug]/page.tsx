import { EventCard } from "@/components/EventCard";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TopicPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const topic = await api.topic(slug);
  if (!topic) {
    return <p className="empty">主题不存在或 API 不可用。</p>;
  }
  const trend = topic.trend;
  return (
    <div>
      <h1>{topic.name}</h1>
      {trend && (
        <p className="meta-line">
          <span className={`state state-${trend.state.toLowerCase()}`}>{trend.state}</span>
          <span style={{ marginLeft: 10 }}>
            30d: {trend.event_count_30d} 事件 / {trend.important_event_count_30d} 重要 /
            {trend.unique_object_count_30d} 对象 / {trend.maturity_transition_count_30d} 成熟度迁移
          </span>
        </p>
      )}
      <p className="meta-line">{topic.description}</p>
      <h2>技术 Timeline(最近事件)</h2>
      <div className="grid">
        {(topic.events || []).map((e) => (
          <EventCard key={e.slug} event={e} detailed />
        ))}
      </div>
      {!topic.events?.length && <p className="empty">该主题暂无事件。</p>}
    </div>
  );
}
