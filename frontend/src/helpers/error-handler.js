export const errorHandler = {
  transformApiToFormErrors,
};

function transformApiToFormErrors(errors) {
  if (!Array.isArray(errors)) {
    return {};
  }
  const formErrors = {};
  errors.forEach((error) => {
    formErrors[[`attribute.${error.loc[1]}`]] = error.msg;
  });
  return formErrors;
}
