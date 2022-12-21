import * as Yup from "yup";

export const UserSchema = Yup.object().shape({
    user: Yup.object().shape({
        email: Yup.string().email().required(),
        org_id: Yup.number().required(),
        role_id: Yup.number().required(),
    }),
});