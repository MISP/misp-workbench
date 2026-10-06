// @vitest-environment node
import { describe, expect, it } from "vitest";
import { objectTemplatesHelper } from "@/helpers/object-templates";

const valid = (template, relations) =>
  objectTemplatesHelper.getObjectTemplateSchema(template).isValid({
    attributes: relations.map((object_relation) => ({ object_relation })),
  });

describe("object template requirements", () => {
  it("needs every relation in required", async () => {
    const ja4Plus = {
      required: ["ja4-fingerprint", "ja4-type"],
      requiredOneOf: [],
    };

    await expect(valid(ja4Plus, ["ja4-fingerprint"])).resolves.toBe(false);
    await expect(valid(ja4Plus, ["ja4-fingerprint", "ja4-type"])).resolves.toBe(
      true,
    );
  });

  it("needs one relation in requiredOneOf", async () => {
    const domainIp = { requiredOneOf: ["domain", "ip"] };

    await expect(valid(domainIp, ["port"])).resolves.toBe(false);
    await expect(valid(domainIp, ["ip"])).resolves.toBe(true);
  });

  it("needs some attribute when the template requires none", async () => {
    await expect(valid({}, [])).resolves.toBe(false);
    await expect(valid({}, ["text"])).resolves.toBe(true);
  });
});
