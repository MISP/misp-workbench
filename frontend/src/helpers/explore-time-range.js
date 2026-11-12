// Explore's time range: `null` is All time (no range), otherwise
// `{ mode: "relative" | "absolute", label?, from, to }`, with relative bounds
// written as `now`, `now-30d`, ... and absolute ones as dates.

export const QUICK_TIME_RANGES = [
  { label: "Last 15 minutes", from: "now-15m", to: "now" },
  { label: "Last 30 minutes", from: "now-30m", to: "now" },
  { label: "Last 1 hour", from: "now-1h", to: "now" },
  { label: "Last 4 hours", from: "now-4h", to: "now" },
  { label: "Last 12 hours", from: "now-12h", to: "now" },
  { label: "Last 24 hours", from: "now-24h", to: "now" },
  { label: "Last 7 days", from: "now-7d", to: "now" },
  { label: "Last 30 days", from: "now-30d", to: "now" },
  { label: "Last 90 days", from: "now-90d", to: "now" },
  { label: "Last 1 year", from: "now-1y", to: "now" },
];

export const DEFAULT_TIME_RANGE = {
  mode: "relative",
  label: "Last 30 days",
  from: "now-30d",
  to: "now",
};

export const ALL_TIME_LABEL = "All time";

const RELATIVE = /^now(?:-\d+[smhdwMy])?$/;

function isBound(value) {
  return (
    typeof value === "string" &&
    (RELATIVE.test(value) || !Number.isNaN(Date.parse(value)))
  );
}

/**
 * The time range a link asks for in its query string:
 *
 * - `range=all`: All time (`null`), for links whose query is self-contained,
 *   such as a detection profile's, which carries its own age rule;
 * - `from` (and optionally `to`, default `now`): `now-90d`, or a date;
 * - neither (or invalid bounds): `undefined`, the page's default applies.
 */
export function timeRangeFromQuery(query = {}) {
  if (query.range === "all") return null;
  const { from } = query;
  const to = query.to ?? "now";
  if (!isBound(from) || !isBound(to)) return undefined;
  const relative = RELATIVE.test(from) && RELATIVE.test(to);
  const quick = QUICK_TIME_RANGES.find((r) => r.from === from && r.to === to);
  return {
    mode: relative ? "relative" : "absolute",
    ...(quick ? { label: quick.label } : {}),
    from,
    to,
  };
}

/** What the picker shows for a range. */
export function timeRangeLabel(range) {
  if (!range) return ALL_TIME_LABEL;
  if (range.label) return range.label;
  if (range.mode === "absolute") {
    const f = range.from ? new Date(range.from).toLocaleString() : "?";
    const t = range.to ? new Date(range.to).toLocaleString() : "?";
    return `${f} → ${t}`;
  }
  return `${range.from} → ${range.to}`;
}
