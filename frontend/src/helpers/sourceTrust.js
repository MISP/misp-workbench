/**
 * A source's indicator scoring settings (score modifier and cap) that differ
 * from the defaults, as short phrases for a collapsed section's summary.
 */
export function sourceTrustSummary(modifier, cap) {
  const parts = [];
  if (modifier) {
    parts.push(`score modifier ${modifier > 0 ? "+" : ""}${modifier}`);
  }
  if (cap !== null && cap !== undefined) {
    parts.push(`score cap ${cap}`);
  }
  return parts;
}
