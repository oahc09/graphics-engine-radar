import Link from "next/link";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TopicsPage() {
  const data = await api.topics();
  const topics = data?.topics || [];
  return (
    <div>
      <h1>主题</h1>
      <p className="meta-line">长期技术能力树,而不是新闻栏目。共 {topics.length} 个主题。</p>
      <div className="grid">
        {topics.map((t) => (
          <Link key={t.slug} href={`/topics/${t.slug}`} className="card">
            <h3>{t.name}</h3>
            <p className="what">{t.description || t.slug}</p>
            <div className="card-foot">
              <span>{t.event_count} events</span>
              {t.parent && <span>parent: {t.parent}</span>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
