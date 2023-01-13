import * as Yup from "yup";

export const ServerSchema = Yup.object().shape({
    server: Yup.object().shape({
        name: Yup.string().required(),
        url: Yup.string().required(),
        authkey: Yup.string().required(),
        org_id: Yup.number().required(),
        push: Yup.boolean().required(),
        pull: Yup.boolean().required(),
        push_sightings: Yup.boolean().required(),
        push_galaxy_clusters: Yup.boolean().required(),
        pull_galaxy_clusters: Yup.boolean().required(),
        remote_org_id: Yup.number().required(),
        publish_without_email: Yup.boolean().required(),
        unpublish_event: Yup.boolean().required(),
        self_signed: Yup.boolean().required(),
        internal: Yup.boolean().required(),
        skip_proxy: Yup.boolean().required(),
        caching_enabled: Yup.boolean().required(),
        priority: Yup.number().required(),
    }),
});