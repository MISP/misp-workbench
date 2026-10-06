/**
 * JA4+ fingerprint shapes, kept in step with api/app/services/ja4.py and the
 * misp-attributes_ja4 ingest pipeline, which decide what gets indexed and
 * correlated as a fingerprint. Here they only steer what the forms suggest.
 */

export const JA4_OBJECT_RELATION = "ja4-fingerprint";

// Only the variants distinctive enough to tell apart from arbitrary text; JA4L,
// JA4T, JA4TS and JA4TScan are short runs of digits, recognised only from the
// ja4-fingerprint relation.
export const JA4_PATTERNS = [
  [
    "JA4",
    /^[tqd][0-9a-z]{2}[di][0-9]{4}[0-9a-z]{2}_[0-9a-f]{12}_[0-9a-f]{12}$/,
  ],
  ["JA4S", /^[tqd][0-9a-z]{2}[0-9]{2}[0-9a-z]{2}_[0-9a-f]{4}_[0-9a-f]{12}$/],
  [
    "JA4H",
    /^[a-z]{2}[0-9]{2}[cn][rn][0-9]{2}[0-9a-z]{4}_[0-9a-f]{12}_[0-9a-f]{12}_[0-9a-f]{12}$/,
  ],
  ["JA4X", /^[0-9a-f]{12}_[0-9a-f]{12}_[0-9a-f]{12}$/],
  ["JA4SSH", /^c[0-9]+s[0-9]+_c[0-9]+s[0-9]+_c[0-9]+s[0-9]+$/],
];

// Every JA4+ variant, hashed or not, is built from these.
const JA4_CHARACTERS = /^[0-9a-z_-]+$/;

export function normalizeJa4(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase();
}

/** The variant a value is shaped like, or null. */
export function detectJa4Variant(value) {
  const normalized = normalizeJa4(value);
  const match = JA4_PATTERNS.find(([, pattern]) => pattern.test(normalized));
  return match ? match[0] : null;
}

/**
 * Whether a value could be a fingerprint of any variant. Lenient on purpose:
 * it catches pasted noise (labels, quotes, spaces) without rejecting the
 * variants that have no recognisable shape.
 */
export function couldBeJa4(value) {
  return JA4_CHARACTERS.test(normalizeJa4(value));
}
