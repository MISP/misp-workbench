// @vitest-environment node
import { describe, expect, it } from "vitest";
import { buildIndicatorGraph } from "@/helpers/indicator-graph";

const attribute = (uuid, event_uuid, extra = {}) => ({
  uuid,
  type: "domain",
  value: "graph.example.org",
  category: "Network activity",
  to_ids: true,
  tags: [],
  event_uuid,
  object_uuid: null,
  object_relation: null,
  ...extra,
});

const GRAPH = {
  indicator: { uuid: "i", type: "domain", value: "graph.example.org" },
  attributes: [
    attribute("a1", "e1"),
    attribute("a2", "e2", { object_uuid: "o1", object_relation: "domain" }),
  ],
  objects: [
    {
      uuid: "o1",
      name: "domain-ip",
      event_uuid: "e2",
      attributes: [
        attribute("s1", "e2", {
          type: "ip-dst",
          value: "203.0.113.9",
          object_uuid: "o1",
          object_relation: "ip",
        }),
      ],
      attribute_count: 1,
    },
  ],
  events: [
    { uuid: "e2", info: "Event B" },
    { uuid: "e1", info: "Event A" },
  ],
  omitted_events: 0,
};

const pairs = ({ edges }) => edges.map((e) => `${e.from} → ${e.to}`).sort();

describe("buildIndicatorGraph", () => {
  it("draws plain attributes to their event, object ones through the object", () => {
    expect(pairs(buildIndicatorGraph(GRAPH))).toEqual(
      [
        "indicator:i → attribute:a1",
        "attribute:a1 → event:e1",
        "indicator:i → attribute:a2",
        "attribute:a2 → object:o1",
        "object:o1 → event:e2",
      ].sort(),
    );
  });

  it("links nodes to their pages", () => {
    const routes = Object.fromEntries(
      buildIndicatorGraph(GRAPH).nodes.map((n) => [n.id, n.data.route]),
    );
    expect(routes["event:e1"]).toBe("/events/e1");
    expect(routes["object:o1"]).toBe("/objects/o1");
    expect(routes["attribute:a2"]).toBe("/attributes/a2");
    expect(routes["indicator:i"]).toBeUndefined();
  });

  it("draws an object's other attributes only when asked", () => {
    const ids = (g) => g.nodes.map((n) => n.id);
    expect(ids(buildIndicatorGraph(GRAPH))).not.toContain("attribute:s1");
    const expanded = buildIndicatorGraph(GRAPH, { showSiblings: true });
    expect(ids(expanded)).toContain("attribute:s1");
    expect(pairs(expanded)).toContain("object:o1 → attribute:s1");
  });

  it("sums up the events left out", () => {
    const { nodes } = buildIndicatorGraph({ ...GRAPH, omitted_events: 3 });
    expect(nodes.find((n) => n.data.kind === "more").data.label).toBe(
      "+3 more events",
    );
  });

  it("draws just the indicator when there is nothing behind it", () => {
    const { nodes, edges } = buildIndicatorGraph({
      indicator: GRAPH.indicator,
      attributes: [],
      objects: [],
      events: [],
      omitted_events: 0,
    });
    expect(nodes.map((n) => n.id)).toEqual(["indicator:i"]);
    expect(edges).toEqual([]);
  });
});
