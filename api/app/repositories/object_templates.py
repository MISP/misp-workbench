import json
import os
from functools import lru_cache


@lru_cache
def get_object_templates():

    templates = []
    objects_dir = "/code/app/submodules/misp-objects/objects"

    for root, dirs, __ in os.walk(objects_dir):
        for template_dir in dirs:
            template_def = os.path.join(root, template_dir, "definition.json")
            raw_template = open(template_def)
            raw_template = json.load(raw_template)

            attributes = []
            for name, attribute in raw_template["attributes"].items():
                attributes.append(
                    {
                        "name": name,
                        "description": attribute.get("description"),
                        "disable_correlation": attribute.get(
                            "disable_correlation", False
                        ),
                        "misp_attribute": attribute["misp-attribute"],
                        "multiple": attribute.get("multiple", False),
                        "ui_priority": attribute.get("ui-priority", 0),
                    }
                )

            template = {
                "uuid": raw_template["uuid"],
                "name": raw_template["name"],
                "meta_category": raw_template["meta-category"],
                "version": raw_template["version"],
                "attributes": attributes,
            }

            templates.append(template)

    return templates
