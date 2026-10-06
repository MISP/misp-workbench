// @vitest-environment node
// Pure helpers: no DOM needed, and jsdom is not a dependency.
import { describe, expect, it } from "vitest";
import { correlationHelper } from "@/helpers/correlations";

const JA4 = "t13d1516h2_8daaf6152771_b186095e22b6";

function correlation(overrides = {}) {
  return {
    _source: {
      target_attribute_uuid: "attr-2",
      target_attribute_type: "text",
      target_attribute_value: JA4,
      target_event_uuid: "event-2",
      match_type: "ja4",
      ja4_variant: "JA4",
      score: 1,
      ...overrides,
    },
  };
}

describe("matchLabel", () => {
  it("adds the JA4+ variant when known", () => {
    expect(correlationHelper.matchLabel({ type: "ja4", variant: "JA4S" })).toBe(
      "ja4 · JA4S",
    );
  });

  it("is the bare type otherwise", () => {
    expect(correlationHelper.matchLabel({ type: "ja4" })).toBe("ja4");
    expect(correlationHelper.matchLabel({ type: "term" })).toBe("term");
  });
});

describe("mergeCorrelatedAttributes", () => {
  it("carries the variant of each match", () => {
    const [merged] = correlationHelper.mergeCorrelatedAttributes([
      correlation(),
    ]);

    expect(merged.matches).toEqual([{ type: "ja4", score: 1, variant: "JA4" }]);
  });

  it("labels a fingerprint by its variant rather than its text type", () => {
    const [fingerprint, domain] = correlationHelper.mergeCorrelatedAttributes([
      correlation(),
      correlation({
        target_attribute_uuid: "attr-3",
        target_attribute_type: "domain",
        target_attribute_value: "evil.com",
        match_type: "term",
        ja4_variant: undefined,
        score: 0.5,
      }),
    ]);

    expect(fingerprint).toMatchObject({ type: "text", typeLabel: "JA4" });
    expect(domain).toMatchObject({ type: "domain", typeLabel: "domain" });
  });
});

describe("typeLabel", () => {
  it("is the JA4+ variant of a ja4 match", () => {
    expect(correlationHelper.typeLabel("text", correlation()._source)).toBe(
      "JA4",
    );
  });

  it("falls back to JA4+ when the variant is unknown", () => {
    expect(
      correlationHelper.typeLabel(
        "text",
        correlation({ ja4_variant: undefined })._source,
      ),
    ).toBe("JA4+");
  });

  it("is the attribute type for any other match", () => {
    expect(
      correlationHelper.typeLabel(
        "text",
        correlation({ match_type: "term" })._source,
      ),
    ).toBe("text");
  });
});

describe("matchesQuery", () => {
  it("finds a correlation by its JA4+ variant", () => {
    expect(
      correlationHelper.matchesQuery(
        correlation({ ja4_variant: "JA4H" })._source,
        "ja4h",
      ),
    ).toBe(true);
  });
});

describe("ja4PivotQuery", () => {
  it("queries the indexed fingerprint", () => {
    expect(
      correlationHelper.ja4PivotQuery({
        value: JA4.toUpperCase(),
        expanded: { ja4: { value: JA4, variant: "JA4" } },
      }),
    ).toBe(`expanded.ja4.value:"${JA4}"`);
  });

  it("escapes what would end the phrase", () => {
    expect(
      correlationHelper.ja4PivotQuery({
        expanded: { ja4: { value: 'a"b\\c' } },
      }),
    ).toBe('expanded.ja4.value:"a\\"b\\\\c"');
  });

  it("is null for anything but a fingerprint", () => {
    expect(correlationHelper.ja4PivotQuery({ value: "evil.com" })).toBeNull();
    expect(correlationHelper.ja4PivotQuery({ expanded: {} })).toBeNull();
    expect(correlationHelper.ja4PivotQuery(null)).toBeNull();
  });
});
