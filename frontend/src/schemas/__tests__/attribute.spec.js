// @vitest-environment node
import { describe, expect, it } from "vitest";
import { getAttributeTypeValidationSchema } from "@/schemas/attribute";

const attribute = (value) => ({
  attribute: {
    value,
    distribution: 0,
    disable_correlation: false,
    category: "Network activity",
    type: "text",
  },
});

describe("ja4-fingerprint values", () => {
  const schema = getAttributeTypeValidationSchema("text", "ja4-fingerprint");

  it("accepts a fingerprint of any variant", async () => {
    await expect(
      schema.isValid(attribute("T13D1516H2_8DAAF6152771_B186095E22B6")),
    ).resolves.toBe(true);
    await expect(schema.isValid(attribute("4289_64"))).resolves.toBe(true);
  });

  it("rejects pasted noise", async () => {
    await expect(
      schema.isValid(attribute("ja4=t13d1516h2_8daaf6152771_b186095e22b6")),
    ).resolves.toBe(false);
  });

  it("leaves other text alone", async () => {
    await expect(
      getAttributeTypeValidationSchema("text", "comment").isValid(
        attribute("ja4=anything goes"),
      ),
    ).resolves.toBe(true);
  });
});
