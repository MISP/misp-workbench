import * as Yup from "yup";

export const EventSchema = Yup.object().shape({
    event: Yup.object().shape({
        info: Yup.string().required(),
        uuid: Yup.string().nullable().uuid(),
        analysis: Yup.number().required(),
        distribution: Yup.number().required(),
        threat_level: Yup.number().required(),
        date: Yup.lazy(value => value ? Yup.date() : Yup.string().nullable()),
        extends_uuid: Yup.lazy(value => value ? Yup.string().uuid() : Yup.string().nullable())
    }),
});