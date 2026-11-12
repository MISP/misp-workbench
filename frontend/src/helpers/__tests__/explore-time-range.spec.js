// @vitest-environment node
import { describe, expect, it } from "vitest";
import {
  timeRangeFromQuery,
  timeRangeLabel,
} from "@/helpers/explore-time-range";

describe("timeRangeFromQuery", () => {
  it("is All time for range=all", () => {
    expect(timeRangeFromQuery({ range: "all", from: "now-7d" })).toBeNull();
  });

  it("leaves the default when the link says nothing", () => {
    expect(timeRangeFromQuery({})).toBeUndefined();
    expect(timeRangeFromQuery({ q: "x", tab: "indicators" })).toBeUndefined();
  });

  it("takes a relative range, named when it is a quick one", () => {
    expect(timeRangeFromQuery({ from: "now-90d" })).toEqual({
      mode: "relative",
      label: "Last 90 days",
      from: "now-90d",
      to: "now",
    });
    expect(timeRangeFromQuery({ from: "now-3d", to: "now" })).toEqual({
      mode: "relative",
      from: "now-3d",
      to: "now",
    });
  });

  it("takes dates as an absolute range", () => {
    expect(
      timeRangeFromQuery({ from: "2026-01-01T00:00:00", to: "2026-02-01" }),
    ).toEqual({
      mode: "absolute",
      from: "2026-01-01T00:00:00",
      to: "2026-02-01",
    });
  });

  it("ignores bounds it can't read", () => {
    expect(timeRangeFromQuery({ from: "yesterday-ish" })).toBeUndefined();
    expect(timeRangeFromQuery({ from: "now-7d", to: "soon" })).toBeUndefined();
    expect(timeRangeFromQuery({ from: ["now-7d"] })).toBeUndefined();
  });
});

describe("timeRangeLabel", () => {
  it("reads All time without a range", () => {
    expect(timeRangeLabel(null)).toBe("All time");
  });

  it("uses the range's name, or its bounds", () => {
    expect(timeRangeLabel({ label: "Last 30 days" })).toBe("Last 30 days");
    expect(
      timeRangeLabel({ mode: "relative", from: "now-3d", to: "now" }),
    ).toBe("now-3d → now");
  });
});
