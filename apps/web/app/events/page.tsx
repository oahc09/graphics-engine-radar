import { EventCard } from "@/components/EventCard";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const TYPES = ["VERSION_RELEASE", "FEATURE_ADDED", "CAPABILITY_ENABLED", "SPEC_CHANGE", "TOOLCHAIN_CHANGE"];

export default async function EventsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const data = await api.events(sp);

  return (
    <div>
      <h1>全部动态</h1>
      <p className="meta-line">
        通过基础有效性判断但未一定进入精选的技术事件。共 {data?.total ?? 0} 条。
      </p>
      <div className="filters">
        <a href="/events" className={!sp.event_type ? "on" : ""}>全部类型</a>
        {TYPES.map((t) => (
          <a key={t} href={`/events?event_type=${t}`} className={sp.event_type === t ? "on" : ""}>
            {t.replace("_", " ").toLowerCase()}
          </a>
        ))}
        <span style={{ margin: "0 4px" }} />
        <a href="/events?impact=Critical" className={sp.impact === "Critical" ? "on" : ""}>Critical</a>
        <a href="/events?impact=High" className={sp.impact === "High" ? "on" : ""}>High</a>
      </div>
      <div className="grid">
        {(data?.events || []).map((e) => (
          <EventCard key={e.slug} event={e} detailed />
        ))}
      </div>
      {!data?.events?.length && <p className="empty">暂无事件,等待管线运行。</p>}
    </div>
  );
}
