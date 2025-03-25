export const authHelper = {
  hasScope,
};

function hasScope(scopes, scope) {
  return (
    scopes.includes("*") ||
    scopes.includes(scope.split(":")[0] + ":*") ||
    scopes.includes(scope)
  );
}
