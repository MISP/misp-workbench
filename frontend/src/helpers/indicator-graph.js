/**
 * Nodes and edges of an indicator's graph (GET /indicators/{uuid}/graph):
 * what it is derived from.
 *
 *   indicator → attribute → event
 *   indicator → attribute → object → event   (the attribute sits in an object)
 *
 * An object's other attributes are its context; they are only drawn when asked
 * (`showSiblings`), hanging off the object. Events left out by the cap are
 * summed up in one "more" node rather than dropped silently.
 */
export function buildIndicatorGraph(graph, { showSiblings = false } = {}) {
  const nodes = [];
  const edges = [];
  if (!graph?.indicator) return { nodes, edges };

  const indicatorId = `indicator:${graph.indicator.uuid}`;
  nodes.push({
    id: indicatorId,
    data: {
      kind: "indicator",
      label: graph.indicator.value,
      type: graph.indicator.type,
    },
  });

  const events = new Map(graph.events.map((e) => [e.uuid, e]));
  const objects = new Map(graph.objects.map((o) => [o.uuid, o]));
  const drawnEvents = new Set();
  const drawnObjects = new Set();

  const eventNode = (uuid) => {
    const id = `event:${uuid}`;
    if (!drawnEvents.has(uuid)) {
      drawnEvents.add(uuid);
      const event = events.get(uuid);
      nodes.push({
        id,
        data: {
          kind: "event",
          label: event?.info || String(uuid).slice(0, 8),
          uuid,
          event,
          route: `/events/${uuid}`,
        },
      });
    }
    return id;
  };

  const attributeNode = (attribute, kind) => ({
    id: `attribute:${attribute.uuid}`,
    data: {
      kind,
      label: attribute.value,
      type: attribute.type,
      attribute,
      route: `/attributes/${attribute.uuid}`,
    },
  });

  const objectNode = (uuid) => {
    const id = `object:${uuid}`;
    if (drawnObjects.has(uuid)) return id;
    drawnObjects.add(uuid);
    const object = objects.get(uuid);
    nodes.push({
      id,
      data: {
        kind: "object",
        label: object.name || "object",
        uuid,
        object,
        route: `/objects/${uuid}`,
      },
    });
    if (object.event_uuid && events.has(object.event_uuid)) {
      edges.push({
        from: id,
        to: eventNode(object.event_uuid),
        data: { kind: "membership" },
      });
    }
    if (showSiblings) {
      for (const sibling of object.attributes) {
        nodes.push(attributeNode(sibling, "sibling"));
        edges.push({
          from: id,
          to: `attribute:${sibling.uuid}`,
          data: { kind: "context" },
        });
      }
    }
    return id;
  };

  for (const attribute of graph.attributes) {
    nodes.push(attributeNode(attribute, "attribute"));
    const id = `attribute:${attribute.uuid}`;
    edges.push({ from: indicatorId, to: id, data: { kind: "derived" } });

    if (attribute.object_uuid && objects.has(attribute.object_uuid)) {
      edges.push({
        from: id,
        to: objectNode(attribute.object_uuid),
        data: { kind: "membership" },
      });
    } else if (attribute.event_uuid && events.has(attribute.event_uuid)) {
      edges.push({
        from: id,
        to: eventNode(attribute.event_uuid),
        data: { kind: "membership" },
      });
    }
  }

  if (graph.omitted_events > 0) {
    const id = `more:${graph.indicator.uuid}`;
    nodes.push({
      id,
      data: {
        kind: "more",
        label: `+${graph.omitted_events} more ${
          graph.omitted_events === 1 ? "event" : "events"
        }`,
      },
    });
    edges.push({ from: indicatorId, to: id, data: { kind: "more" } });
  }

  return { nodes, edges };
}
