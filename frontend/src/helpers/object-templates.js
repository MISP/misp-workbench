import * as Yup from "yup";
import { ObjectSchema } from "@/schemas/object";

export const objectTemplatesHelper = {
  getObjectTemplateSchema,
  validateObject,
};

function getObjectTemplateSchema(template) {
  return Yup.object().shape({
    attributes: Yup.array().test(
      "at-least-one-required-type",
      `The object must contain at least one attribute with a type matching one of the following: ${template.requiredOneOf.join(
        ", ",
      )}`,
      (attributes) =>
        attributes &&
        attributes.some((attribute) =>
          template.requiredOneOf.includes(attribute.object_relation),
        ),
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
