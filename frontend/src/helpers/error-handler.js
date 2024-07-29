export const errorHandler = {
    transformApiToFormErrors,
};

function transformApiToFormErrors(errors) {
    if (!Array.isArray(errors)) {
        return {};
    }
    let formErrors = {};
    errors.forEach((error) => {
        formErrors[[`attribute.${error.loc[1]}`]] = error.msg;
    });
    return formErrors;
}