import functools
import json
import os

RELATIONSHIPS_DEFINITION = "app/submodules/misp-objects/relationships/definition.json"


@functools.lru_cache(maxsize=1)
def get_local_relationship_types() -> list[dict]:
    """
    The MISP relationship vocabulary, used to populate the relationship type
    picker. Read from the misp-objects submodule, which ships it, so the list
    tracks whatever revision the submodule is pinned to.

    Callers may also send a type outside this list -- MISP allows free-form
    relationship types, and one arriving over sync must not be rejected.
    """
    if not os.path.exists(RELATIONSHIPS_DEFINITION):
        return []

    with open(RELATIONSHIPS_DEFINITION) as fh:
        definition = json.load(fh)

    return sorted(
        (
            {
                "name": value["name"],
                "description": value.get("description"),
            }
            for value in definition.get("values", [])
            if value.get("name")
        ),
        key=lambda value: value["name"],
    )
