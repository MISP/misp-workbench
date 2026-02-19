import * as Yup from "yup";
import ipRegex from "ip-regex";

export const AttributeSchema = Yup.object().shape({
  attribute: Yup.object().shape({
    value: Yup.string().required(),
    timestamp: Yup.number(),
    distribution: Yup.number().required(),
    disable_correlation: Yup.boolean().required(),
    category: Yup.string().required(),
    type: Yup.string().required(),
    first_seen: Yup.string().nullable(),
    last_seen: Yup.string().nullable(),
  }),
});

export const getAttributeTypeValidationSchema = (type) => {
  if (type === "ip-src" || type === "ip-dst") {
    return AttributeSchema.concat(
      Yup.object().shape({
        attribute: Yup.object().shape({
          value: Yup.string()
            .test("ip-or-cidr", "Invalid IP address or CIDR.", (value) => {
              if (!value) return false;
              const parts = value.split("/");
              if (parts.length === 1) {
                return ipRegex({ exact: true }).test(value);
              }
              if (parts.length === 2) {
                const [ip, prefix] = parts;
                const prefixNum = parseInt(prefix, 10);
                if (ipRegex.v4({ exact: true }).test(ip)) {
                  return prefixNum >= 0 && prefixNum <= 32;
                }
                if (ipRegex.v6({ exact: true }).test(ip)) {
                  return prefixNum >= 0 && prefixNum <= 128;
                }
              }
              return false;
            })
            .required(),
        }),
      }),
    );
  }

  if (type === "email") {
    return AttributeSchema.concat(
      Yup.object().shape({
        attribute: Yup.object().shape({
          value: Yup.string().email().required(),
        }),
      }),
    );
  }

  if (type === "url") {
    return AttributeSchema.concat(
      Yup.object().shape({
        attribute: Yup.object().shape({
          value: Yup.string().url().required(),
        }),
      }),
    );
  }

  return AttributeSchema;
};
