import * as Yup from "yup";

export const ServerSchema = Yup.object().shape({
  server: Yup.object().shape({
    name: Yup.string().required(),
    url: Yup.string().url().required(),
    authkey: Yup.string().required(),
    org_id: Yup.number().required(),
    push: Yup.boolean().default(false),
    pull: Yup.boolean().default(false),
    pull_rules: Yup.object().required(),
    push_sightings: Yup.boolean().default(false),
    push_galaxy_clusters: Yup.boolean().default(false),
    pull_galaxy_clusters: Yup.boolean().default(false),
    remote_org_id: Yup.number().required(),
    publish_without_email: Yup.boolean().default(false),
    unpublish_event: Yup.boolean().default(false),
    self_signed: Yup.boolean().default(false),
    internal: Yup.boolean().default(false),
    skip_proxy: Yup.boolean().default(false),
    caching_enabled: Yup.boolean().default(false),
    priority: Yup.number().required(),
  }),
});
