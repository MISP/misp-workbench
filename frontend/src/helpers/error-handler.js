export const errorHandler = {
    transformApiToFormErrors,
};

function transformApiToFormErrors(errors) {
    let formErrors = {};
    errors.forEach((error) => {
        formErrors[[`attribute.${error.loc[1]}`]] = error.msg;
    });
    return formErrors;
}