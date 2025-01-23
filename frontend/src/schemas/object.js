import * as Yup from "yup";

export const ObjectSchema = Yup.object().shape({
  object: Yup.object().shape({}),
});
