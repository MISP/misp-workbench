// @vitest-environment node
import { describe, expect, it } from "vitest";
import { errorMessage } from "@/helpers/error-handler";

describe("errorMessage", () => {
  it("keeps the API's message", () => {
    expect(
      errorMessage(
        "example.com isn't a host feeds may fetch from; an admin allows hosts in the runtime settings (feeds.source_hosts)",
      ),
    ).toContain("feeds.source_hosts");
  });

  it("spells out validation errors", () => {
    expect(
      errorMessage([
        { loc: ["body", "url"], msg: "Field required" },
        { loc: ["body", "settings", "csvConfig"], msg: "Invalid" },
      ]),
    ).toBe("url: Field required; settings.csvConfig: Invalid");
  });

  it("reads errors and anything else", () => {
    expect(errorMessage(new Error("Network down"))).toBe("Network down");
    expect(errorMessage(503)).toBe("503");
  });
});
