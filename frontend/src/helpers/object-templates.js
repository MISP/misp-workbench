import * as Yup from "yup";
import { ObjectSchema } from "@/schemas/object";

export const objectTemplatesHelper = {
  getObjectTemplateSchema,
  validateObject,
};

// MISP templates have two kinds of requirement: every relation in required
// must be present, and at least one of those in requiredOneOf. Either list may
// be empty or missing.
function getObjectTemplateSchema(template) {
  const required = template.required || [];
  const requiredOneOf = template.requiredOneOf || [];
  const relations = (attributes) =>
    (attributes || []).map((attribute) => attribute.object_relation);

  return Yup.object().shape({
    attributes: Yup.array()
      .test(
        "all-required",
        `The object must contain an attribute for each of the following: ${required.join(
          ", ",
        )}`,
        (attributes) =>
          required.every((relation) =>
            relations(attributes).includes(relation),
          ),
      )
      .test(
        "at-least-one-required",
        `The object must contain at least one attribute for one of the following: ${requiredOneOf.join(
          ", ",
        )}`,
        (attributes) =>
          requiredOneOf.length === 0 ||
          requiredOneOf.some((relation) =>
            relations(attributes).includes(relation),
          ),
      )
      .test(
        "not-empty",
        "The object must contain at least one attribute",
        (attributes) => (attributes || []).length > 0,
      ),
  });
}

function validateObject(template, object) {
  return new Promise((resolve, reject) => {
    const schema = getObjectTemplateSchema(template);
    ObjectSchema.concat(schema)
      .validate(object)
      .then((validObject) => {
        resolve(validObject);
      })
      .catch((error) => {
        reject(error);
      });
  });
}
