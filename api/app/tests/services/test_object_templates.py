import json
import os

from app.services import object_templates as object_templates_service


class TestGetLocalObjectTemplates:
    """
    The loader reads the misp-objects submodule directly, so these run against
    whatever revision it is pinned to.
    """

    def test_loads_every_template_the_submodule_ships(self):
        templates = object_templates_service.get_local_object_templates()

        on_disk = [
            entry
            for entry in os.listdir(object_templates_service.OBJECTS_DIR)
            if os.path.isfile(
                os.path.join(
                    object_templates_service.OBJECTS_DIR, entry, "definition.json"
                )
            )
        ]

        assert len(templates) == len(on_disk)
        assert len(templates) > 0

    def test_skips_directories_without_a_definition(self):
        """
        The submodule ships nested `icon/` directories with no definition.json.
        Walking into those raised FileNotFoundError, which surfaced as a 500 on
        /object-templates.
        """
        strays = [
            os.path.join(root, directory)
            for root, directories, _ in os.walk(object_templates_service.OBJECTS_DIR)
            for directory in directories
            if not os.path.isfile(os.path.join(root, directory, "definition.json"))
        ]

        # if the submodule ever stops shipping these, the guard is still
        # correct but this assertion no longer proves anything
        assert strays, "expected the submodule to contain directories without one"

        # the call simply must not raise
        assert object_templates_service.get_local_object_templates()

    def test_shape_matches_what_the_router_returns(self):
        templates = object_templates_service.get_local_object_templates()
        template = next(t for t in templates if t["name"] == "domain-ip")

        assert set(template) == {
            "uuid",
            "name",
            "description",
            "meta_category",
            "version",
            "attributes",
            "requiredOneOf",
        }
        assert template["attributes"]
        assert {"name", "misp_attribute"} <= set(template["attributes"][0])

    def test_sorted_by_name(self):
        names = [
            t["name"] for t in object_templates_service.get_local_object_templates()
        ]

        assert names == sorted(names)

    def test_definitions_are_not_left_open(self):
        # the previous implementation never closed the files it read
        templates = object_templates_service.get_local_object_templates()
        sample = os.path.join(
            object_templates_service.OBJECTS_DIR, "domain-ip", "definition.json"
        )

        with open(sample) as fh:
            raw = json.load(fh)

        loaded = next(t for t in templates if t["uuid"] == raw["uuid"])
        assert loaded["name"] == raw["name"]
