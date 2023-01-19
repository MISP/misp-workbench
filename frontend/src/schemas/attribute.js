import * as Yup from "yup";

export const AttributeSchema = Yup.object().shape({
    attribute: Yup.object().shape({
        value: Yup.string().required(),
        timestamp: Yup.number().required(),
        distribution: Yup.number().required(),
        disable_correlation: Yup.boolean().required(),
        category: Yup.string().required(),
        type: Yup.string().required(),
        value: Yup.string().required()
    }),
});