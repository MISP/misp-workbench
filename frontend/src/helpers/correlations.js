export const correlationHelper = {
  mergeCorrelatedAttributes,
  groupByEvent,
  isApproximateMatch,
  matchesQuery,
  matchLabel,
  typeLabel,
  ja4PivotQuery,
};

// Match types that found a value without matching it exactly, so a reader has
// to check the hit before trusting it.
const APPROXIMATE_MATCH_TYPES = ["fuzzy", "prefix"];

function isApproximateMatch(matchType) {
  return APPROXIMATE_MATCH_TYPES.includes(matchType);
}

/**
 * How a match reads in the UI: its type, plus the JA4+ variant a ja4 match
 * found when it is known.
 */
function matchLabel(match) {
  return match.variant ? `${match.type} · ${match.variant}` : match.type;
}

/**
 * How an attribute's type reads next to a correlation. MISP has no JA4+ type,
 * so a fingerprint is a plain text attribute; a ja4 match says what it really
 * is, its variant when known.
 */
function typeLabel(type, correlation) {
  if (correlation?.match_type === "ja4") {
    return correlation.ja4_variant || "JA4+";
  }
  return type;
}

/**
 * The Explore query finding every attribute indexed with the same JA4+
 * fingerprint, or null when the attribute is not one. The indexed value is
 * already lower cased, which is what makes the pivot ignore case.
 */
function ja4PivotQuery(attribute) {
  const value = attribute?.expanded?.ja4?.value;
  if (!value) {
    return null;
  }

  return `expanded.ja4.value:"${value.replace(/["\\]/g, "\\$&")}"`;
}

/**
 * Whether a correlation document matches a free text needle. The needle is
 * expected to be lower cased already.
 */
function matchesQuery(source, needle) {
  if (!needle) {
    return true;
  }

  return [
    source.target_attribute_value,
    source.target_attribute_type,
    source.target_event_uuid,
    source.match_type,
    source.ja4_variant,
  ].some((field) =>
    String(field ?? "")
      .toLowerCase()
      .includes(needle),
  );
}

/**
 * Correlations are stored as one document per matched pair, so an attribute
 * matched by several match types shows up several times. Merge them into one
 * entry per correlated attribute, carrying every match that found it.
 *
 * @param {Array} correlations raw OpenSearch correlation hits
 * @returns {Array} one entry per target attribute, best scoring first
 */
function mergeCorrelatedAttributes(correlations) {
  const merged = new Map();

  for (const correlation of correlations || []) {
    const source = correlation._source;

    let attribute = merged.get(source.target_attribute_uuid);
    if (!attribute) {
      attribute = {
        uuid: source.target_attribute_uuid,
        type: source.target_attribute_type,
        typeLabel: source.target_attribute_type,
        value: source.target_attribute_value,
        eventUuid: source.target_event_uuid,
        matches: [],
        seenAt: null,
      };
      merged.set(attribute.uuid, attribute);
    }

    if (source.match_type === "ja4") {
      attribute.typeLabel = typeLabel(attribute.type, source);
    }

    attribute.matches.push({
      type: source.match_type,
      score: source.score,
      variant: source.ja4_variant,
    });

    const seenAt = source["@timestamp"];
    if (seenAt && (!attribute.seenAt || seenAt > attribute.seenAt)) {
      attribute.seenAt = seenAt;
    }
  }

  return [...merged.values()].sort(
    (a, b) => bestScore(b) - bestScore(a) || a.value.localeCompare(b.value),
  );
}

function bestScore(attribute) {
  return Math.max(...attribute.matches.map((match) => match.score ?? 0));
}

/**
 * Bucket merged correlated attributes by the event holding them, busiest event
 * first.
 */
function groupByEvent(attributes) {
  const groups = new Map();

  for (const attribute of attributes) {
    let group = groups.get(attribute.eventUuid);
    if (!group) {
      group = { eventUuid: attribute.eventUuid, attributes: [] };
      groups.set(group.eventUuid, group);
    }

    group.attributes.push(attribute);
  }

  return [...groups.values()].sort(
    (a, b) =>
      b.attributes.length - a.attributes.length ||
      a.eventUuid.localeCompare(b.eventUuid),
  );
}
