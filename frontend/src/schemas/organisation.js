import * as Yup from "yup";

export const OrganisationSchema = Yup.object().shape({
  organisation: Yup.object().shape({
    name: Yup.string().required(),
    description: Yup.string().nullable(),
    type: Yup.string().nullable(),
    local: Yup.boolean().required(),
    nationality: Yup.string(),
    sector: Yup.string(),
    uuid: Yup.string().nullable().uuid(),
    restricted_to_domain: Yup.string(),
    landing_page: Yup.string(),
  }),
});
