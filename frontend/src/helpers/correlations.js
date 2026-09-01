export const correlationHelper = {
  mergeCorrelatedAttributes,
  groupByEvent,
  isApproximateMatch,
  matchesQuery,
};

// Match types that found a value without matching it exactly, so a reader has
// to check the hit before trusting it.
const APPROXIMATE_MATCH_TYPES = ["fuzzy", "prefix"];

function isApproximateMatch(matchType) {
  return APPROXIMATE_MATCH_TYPES.includes(matchType);
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
        value: source.target_attribute_value,
        eventUuid: source.target_event_uuid,
        matches: [],
        seenAt: null,
      };
      merged.set(attribute.uuid, attribute);
    }

    attribute.matches.push({
      type: source.match_type,
      score: source.score,
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
