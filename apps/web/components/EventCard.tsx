import Link from "next/link";
import type { EventData } from "@/lib/api";

const SIGNAL_STYLE: Record<string, string> = {
  NEW: "sig-new",
  EXPAND: "sig-expand",
  ADOPT: "sig-adopt",
  MATURE: "sig-mature",
  SPEC: "sig-spec",
  PERF: "sig-perf",
  BREAK: "sig-break",
};

export function EventCard({ event, detailed = false }: { event: EventData; detailed?: boolean }) {
  const date = (event.published_at || event.first_seen_at || "").slice(0, 10);
  const primary = event.sources?.find((s) => s.role === "primary") || event.sources?.[0];
  return (
    <article className="card">
      <div className="card-head">
        <span className={`signal ${SIGNAL_STYLE[event.change_signal] || ""}`}>
          [{event.change_signal}]
        </span>
        {event.object_slug && (
          <Link className="obj-chip" href={`/objects/${event.object_slug}`}>
            {event.object_slug}
          </Link>
        )}
        <span className="impact impact-{event.impact_level.toLowerCase()}">{event.impact_level}</span>
        <span className="date">{date}</span>
      </div>
      <h3>
        <Link href={`/events/${event.slug}`}>{event.title}</Link>
      </h3>
      {detailed && <p className="what">{event.change || event.summary}</p>}
      {event.why_it_matters && (
        <p className="why">
          <strong>Why it matters</strong> {event.why_it_matters}
        </p>
      )}
      <div className="card-foot">
        <span className="topics">
          {event.topics?.slice(0, 4).map((t) => (
            <Link key={t.slug} href={`/topics/${t.slug}`} className="topic-chip">
              {t.name}
            </Link>
          ))}
        </span>
        {primary && (
          <span className="src">
            {primary.role === "primary" ? "Official" : "Source"} · {primary.type}
            {primary.url && (
              <a href={primary.url} target="_blank" rel="noreferrer">
                ↗
              </a>
            )}
          </span>
        )}
      </div>
    </article>
  );
}
