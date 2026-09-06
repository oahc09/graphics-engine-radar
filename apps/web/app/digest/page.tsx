import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

const KINDS = ["daily", "weekly", "monthly"] as const;

export default async function DigestPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const kind = (KINDS.includes(sp.kind as never) ? sp.kind : "daily") as
    | "daily"
    | "weekly"
    | "monthly";
  const digest = await api.digest(kind);

  return (
    <div>
      <h1>日报</h1>
      <div className="filters">
        {KINDS.map((k) => (
          <a key={k} href={`/digest?kind=${k}`} className={kind === k ? "on" : ""}>
            {k}
          </a>
        ))}
      </div>
      {digest ? (
        <article className="prose">
          <h2>{digest.title}</h2>
          <p className="meta-line">{digest.date?.slice(0, 10)}</p>
          {digest.body.split("\n\n").map((p, i) => (
            <p key={i} dangerouslySetInnerHTML={{ __html: renderMd(p) }} />
          ))}
        </article>
      ) : (
        <p className="empty">
          尚未生成 {kind} digest。运行 `uv run radar-intelligence digest --kind {kind}`。
        </p>
      )}
    </div>
  );
}

function renderMd(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/\n/g, "<br/>");
}
