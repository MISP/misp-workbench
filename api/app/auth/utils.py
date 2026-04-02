def role_has_scope(role_scopes: list[str], scope: str) -> bool:
    resource = scope.split(":")[0]
    return (
        "*" in role_scopes
        or f"{resource}:*" in role_scopes
        or scope in role_scopes
    )
