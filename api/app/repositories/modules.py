import json
from functools import lru_cache

import requests
from app.schemas import module as module_schemas


@lru_cache
def get_modules():
    modules = []

    # get modules from api
    req = requests.get("http://modules:6666/modules")

    rawModules = json.loads(req.text)

    for rawModule in rawModules:
        moduleMeta = module_schemas.ModuleMeta(
            version=(
                str(rawModule["meta"]["version"])
                if "version" in rawModule["meta"]
                else None
            ),
            author=rawModule["meta"]["author"],
            description=rawModule["meta"]["description"],
            module_type=rawModule["meta"]["module-type"],
            config=(
                rawModule["meta"]["config"] if "config" in rawModule["meta"] else None
            ),
        )

        moduleAttributes = module_schemas.ModuleAttributes(
            inputSource=(
                rawModule["mispattributes"]["inputSource"]
                if "inputSource" in rawModule["mispattributes"]
                else []
            ),
            output=(
                rawModule["mispattributes"]["output"]
                if "output" in rawModule["mispattributes"]
                else []
            ),
            format=(
                rawModule["mispattributes"]["format"]
                if "format" in rawModule["mispattributes"]
                else None
            ),
            userConfig=(
                rawModule["mispattributes"]["userConfig"]
                if "userConfig" in rawModule["mispattributes"]
                else None
            ),
        )

        module = module_schemas.Module(
            name=rawModule["name"],
            type=rawModule["type"],
            mispattributes=moduleAttributes,
            meta=moduleMeta,
        )

        modules.append(module)

    return modules
