import json
import os

OBJECTS_DIR = "app/submodules/misp-objects/objects"


# @lru_cache
def get_local_object_templates():
    """
    Load the object templates the misp-objects submodule ships.

    Every template lives at `objects/<name>/definition.json`. Anything without
    one is skipped: the submodule also ships nested `icon/` directories, and
    walking into those raised FileNotFoundError, which surfaced as a 500 on
    /object-templates -- reported in the browser as a CORS failure, since
    CORSMiddleware does not add its headers to an unhandled exception.
    """
    templates = []

    for template_dir in sorted(os.listdir(OBJECTS_DIR)):
        template_def = os.path.join(OBJECTS_DIR, template_dir, "definition.json")
        if not os.path.isfile(template_def):
            continue

        with open(template_def) as raw_template_file:
            raw_template = json.load(raw_template_file)

        attributes = []
        for name, attribute in raw_template["attributes"].items():
            attributes.append(
                {
                    "name": name,
                    "description": attribute.get("description"),
                    "disable_correlation": attribute.get("disable_correlation", False),
                    "misp_attribute": attribute["misp-attribute"],
                    "multiple": attribute.get("multiple", False),
                    "ui_priority": attribute.get("ui-priority", 0),
                    "sane_default": attribute.get("sane_default"),
                }
            )

        templates.append(
            {
                "uuid": raw_template["uuid"],
                "name": raw_template["name"],
                "description": raw_template["description"],
                "meta_category": raw_template["meta-category"],
                "version": raw_template["version"],
                "attributes": attributes,
                "requiredOneOf": raw_template.get("requiredOneOf", []),
            }
        )

    templates = sorted(templates, key=lambda d: d["name"])

    return templates
