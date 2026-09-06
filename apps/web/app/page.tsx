import Link from "next/link";
import { EventCard } from "@/components/EventCard";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [selected, trends, events, metrics] = await Promise.all([
    api.selected(),
    api.trends(),
    api.events({}),
    api.metrics(),
  ]);

  const accelerating = (trends?.trends || [])
    .filter((t) => t.state === "Accelerating" || t.state === "Growing")
    .slice(0, 6);
  const major = (events?.events || [])
    .filter((e) => e.impact_level === "Critical" || e.maturity_to)
    .slice(0, 4);

  return (
    <div>
      <section className="hero">
        <h1>Graphics Engine Radar</h1>
        <p>图形引擎每天都在变化。</p>
        <p>
          我们持续监控引擎、Graphics API、GPU、渲染技术和工具链。AI
          帮你过滤噪声,只留下真正值得关注的变化。
        </p>
        {metrics && (
          <p className="meta-line">
            已监控 {metrics.raw_item_total} 条原始动态,沉淀 {metrics.event_total} 个技术事件
            {metrics.selected ? `,精选 ${metrics.selected} 条` : ""}。
          </p>
        )}
      </section>

      <section className="section">
        <h2>今日精选</h2>
        <p className="sub">今天真正值得图形工程师看的变化(数量动态,宁少勿水)。</p>
        {selected?.events?.length ? (
          <div className="grid">
            {selected.events.slice(0, 9).map((e) => (
              <EventCard key={e.slug} event={e} detailed />
            ))}
          </div>
        ) : (
          <p className="empty">暂无精选事件 — 管线尚未产出或今日无足够重要变化。</p>
        )}
      </section>

      <section className="section">
        <h2>正在加速</h2>
        <p className="sub">基于事件数、对象数、成熟度迁移的趋势判断,而非浏览量。</p>
        {accelerating.length ? (
          accelerating.map((t) => (
            <Link key={t.topic_slug} href={`/topics/${t.topic_slug}`} className="trend-row">
              <span className={`state state-${t.state.toLowerCase()}`}>{t.state}</span>
              <b>{t.topic_name}</b>
              <span className="meta-line" style={{ margin: 0 }}>
                30天 {t.event_count_30d} 事件 / {t.important_event_count_30d} 重要 /
                {t.unique_object_count_30d} 对象
              </span>
            </Link>
          ))
        ) : (
          <p className="empty">趋势数据生成中。</p>
        )}
      </section>

      <section className="section">
        <h2>重大技术演进</h2>
        <p className="sub">架构变化、规范变化与成熟度迁移。</p>
        {major.length ? (
          <div className="grid">
            {major.map((e) => (
              <EventCard key={e.slug} event={e} />
            ))}
          </div>
        ) : (
          <p className="empty">暂无重大演进事件。</p>
        )}
      </section>

      <section className="section">
        <h2>全部有效动态</h2>
        <p className="sub">
          <Link href="/events">查看全部 →</Link>
        </p>
        <div className="grid">
          {(events?.events || []).slice(0, 6).map((e) => (
            <EventCard key={e.slug} event={e} />
          ))}
        </div>
      </section>
    </div>
  );
}
