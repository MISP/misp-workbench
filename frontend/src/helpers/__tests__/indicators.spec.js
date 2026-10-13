// @vitest-environment node
import { describe, expect, it } from "vitest";
import { detectAttribute, refang } from "@/helpers/indicators";

describe("refang", () => {
  it.each([
    ["hxxps://evil[.]example/x", "https://evil.example/x"],
    ["hXXp://evil(.)example", "http://evil.example"],
    ["1.2.3[.]4", "1.2.3.4"],
    ["bob[@]example[dot]com", "bob@example.com"],
    ["fxp://files{.}example[:]21", "ftp://files.example:21"],
    ["https://example.com", "https://example.com"],
  ])("%s", (value, expected) => {
    expect(refang(value)).toBe(expected);
  });
});

describe("detectAttribute", () => {
  it.each([
    ["1.2.3.4", "ip-dst", false],
    ["1.2.3[.]4", "ip-dst", true],
    ["10.0.0.0/8", "ip-dst", false],
    ["2001:db8::1", "ip-dst", false],
    ["2001:db8::/32", "ip-dst", false],
    ["::ffff:192.0.2.1", "ip-dst", false],
    ["203.0.113.5:8080", "ip-dst|port", false],
    ["203.0.113[.]5:8080", "ip-dst|port", true],
    ["[2001:db8::1]:443", "ip-dst|port", false],
    ["hxxps://evil[.]example/login", "url", true],
    ["https://evil.example/login", "url", false],
    ["evil[.]example", "domain", true],
    ["sub.Evil.Example.", "domain", false],
    ["bob[@]example[.]com", "email-src", true],
    ["d41d8cd98f00b204e9800998ecf8427e", "md5", false],
    ["da39a3ee5e6b4b0d3255bfef95601890afd80709", "sha1", false],
    [
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "sha256",
      false,
    ],
    ["a".repeat(128), "sha512", false],
    ["CVE-2021-44228", "vulnerability", false],
    ["t13d1516h2_8daaf6152771_b186095e22b6", "text", false],
  ])("%s is %s", (value, type, defanged) => {
    const detected = detectAttribute(value);
    expect(detected.type).toBe(type);
    expect(detected.defanged).toBe(defanged);
  });

  it("gives the value as it will be stored", () => {
    expect(detectAttribute(" hxxp://a[.]example ").value).toBe(
      "http://a.example",
    );
  });

  it.each(["", "   ", "hello world", "300.1.1.1", "1.2.3.4/33", "abc"])(
    "%j is not recognised",
    (value) => {
      expect(detectAttribute(value)).toBeNull();
    },
  );
});
