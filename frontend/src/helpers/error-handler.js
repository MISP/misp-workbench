export const errorHandler = {
  transformApiToFormErrors,
};

/**
 * A rejected request's error as text: the API's `detail` is a message, or for
 * a request that failed validation, a list of `{loc, msg}`.
 */
export function errorMessage(error) {
  if (Array.isArray(error)) {
    return error
      .map((e) => {
        const where = (e?.loc || []).slice(1).join(".");
        return where ? `${where}: ${e?.msg}` : e?.msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof error === "string") return error;
  return error?.message || String(error);
}

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
