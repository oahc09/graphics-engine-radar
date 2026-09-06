export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8300";

export type EventData = {
  id: string;
  slug: string;
  title: string;
  summary: string;
  event_type: string;
  change_signal: string;
  change: string;
  why_it_matters: string;
  who_should_care: string;
  impact_level: string;
  confidence: number;
  maturity_from: string | null;
  maturity_to: string | null;
  first_seen_at: string | null;
  published_at: string | null;
  status: string;
  object_slug: string | null;
  topics: { slug: string; name: string; relation: string }[];
  sources?: {
    role: string;
    type: string;
    url: string | null;
    title: string;
    published_at: string | null;
  }[];
};

export type ObjectData = {
  slug: string;
  name: string;
  type: string;
  domain: string;
  description: string;
  official_url: string | null;
  github_repo: string | null;
};

export type TopicData = {
  slug: string;
  name: string;
  parent: string | null;
  description: string;
  event_count: number;
};

export type TrendData = {
  topic_slug: string;
  topic_name: string;
  state: string;
  event_count_30d: number;
  important_event_count_30d: number;
  unique_object_count_30d: number;
  maturity_transition_count_30d: number;
  adoption_count_30d: number;
};

async function apiFetch<T>(path: string, revalidate = 60): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate },
      headers: { accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const api = {
  selected: () =>
    apiFetch<{ count: number; events: EventData[] }>("/selected", 30),
  events: (params: Record<string, string | undefined> = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v) qs.set(k, v);
    }
    return apiFetch<{ total: number; events: EventData[] }>(
      `/events?${qs.toString()}`,
      30
    );
  },
  event: (slug: string) => apiFetch<EventData>(`/events/${slug}`, 30),
  objects: (params: Record<string, string | undefined> = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v) qs.set(k, v);
    }
    return apiFetch<{ count: number; objects: ObjectData[] }>(
      `/objects?${qs.toString()}`,
      300
    );
  },
  object: (slug: string) =>
    apiFetch<ObjectData & { events: EventData[]; sources: unknown[] }>(
      `/objects/${slug}`,
      60
    ),
  topics: () => apiFetch<{ count: number; topics: TopicData[] }>("/topics", 300),
  topic: (slug: string) =>
    apiFetch<TopicData & { events: EventData[]; trend?: TrendData }>(
      `/topics/${slug}`,
      60
    ),
  trends: () => apiFetch<{ trends: TrendData[] }>("/trends", 60),
  digest: (kind: "daily" | "weekly" | "monthly") =>
    apiFetch<{ title: string; body: string; date: string }>(
      `/digests/${kind}`,
      60
    ),
  metrics: () => apiFetch<Record<string, number>>("/metrics", 30),
};
