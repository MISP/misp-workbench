// @vitest-environment node
import { describe, expect, it, vi } from "vitest";

vi.mock("@/helpers/fetch-wrapper", () => ({ fetchWrapper: { get: vi.fn() } }));

const { forbiddenHost, hostMatches, sourceUrlProblem } = await import(
  "@/helpers/outbound"
);

describe("forbiddenHost", () => {
  it.each([
    "127.0.0.1",
    "127.9.9.9",
    "169.254.169.254",
    "0.0.0.0",
    "224.0.0.1",
    "localhost",
    "api.localhost",
    "[::1]",
    "[::]",
    "[fe80::1]",
    "[::ffff:7f00:1]",
    "[::ffff:a9fe:a9fe]",
  ])("%s is never fetched from", (host) => {
    expect(forbiddenHost(host)).toBe(true);
  });

  it.each([
    "10.0.0.5",
    "192.168.1.1",
    "8.8.8.8",
    "example.com",
    "[2001:db8::1]",
  ])("%s is fine", (host) => {
    expect(forbiddenHost(host)).toBe(false);
  });
});

describe("hostMatches", () => {
  it("matches like the API's fnmatch", () => {
    expect(hostMatches("urlhaus.abuse.ch", "*.abuse.ch")).toBe(true);
    expect(hostMatches("URLhaus.Abuse.CH", "*.abuse.ch")).toBe(true);
    expect(hostMatches("abuse.ch", "*.abuse.ch")).toBe(false);
    expect(hostMatches("google.com", "google.com")).toBe(true);
    expect(hostMatches("googleXcom", "google.com")).toBe(false);
  });
});

describe("sourceUrlProblem", () => {
  it("says nothing about an empty field or an allowed URL", () => {
    expect(sourceUrlProblem("", ["google.com"], "feeds")).toBeNull();
    expect(
      sourceUrlProblem("https://google.com/list.txt", ["google.com"], "feeds"),
    ).toBeNull();
    // No allowlist set (or not known yet): any host.
    expect(sourceUrlProblem("https://example.com/", [], "feeds")).toBeNull();
    expect(sourceUrlProblem("https://example.com/", null, "feeds")).toBeNull();
  });

  it("flags a host outside the allowlist, as the API words it", () => {
    expect(
      sourceUrlProblem("https://example.com/feed", ["google.com"], "feeds"),
    ).toBe(
      "example.com isn't a host feeds may fetch from; an admin allows hosts in the runtime settings (feeds.source_hosts)",
    );
    expect(
      sourceUrlProblem("https://misp.other.org", ["misp.ours.org"], "servers"),
    ).toContain("servers.source_hosts");
  });

  it("flags addresses no fetch may reach, whatever the allowlist", () => {
    expect(
      sourceUrlProblem("http://169.254.169.254/latest/", ["*"], "feeds"),
    ).toContain("may never fetch from");
    // URL() normalises 2130706433 to 127.0.0.1.
    expect(sourceUrlProblem("http://2130706433/", [], "feeds")).toContain(
      "127.0.0.1",
    );
  });

  it("flags what isn't an http(s) URL", () => {
    expect(sourceUrlProblem("example.com/feed", [], "feeds")).toContain(
      "Not a URL",
    );
    expect(sourceUrlProblem("ftp://example.com/", [], "feeds")).toContain(
      "http(s)",
    );
  });
});
