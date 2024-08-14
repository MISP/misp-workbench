import * as Yup from "yup";

export const FeedSchema = Yup.object().shape({
    feed: Yup.object().shape({
        name: Yup.string().required(),
        url: Yup.string().url().required(),
        provider: Yup.string().required(),
    }),
});