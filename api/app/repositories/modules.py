import json
from functools import lru_cache

import requests
from app.models import module as module_models
from app.schemas import module as module_schemas
from app.settings import Settings, get_settings
from sqlalchemy.orm import Session


@lru_cache
def get_modules(db: Session, settings: Settings = get_settings()):
    modules = []

    # get modules from api
    modules_url = f"http://{settings.Modules.host}:{settings.Modules.port}/modules"
    req = requests.get(modules_url)

    rawModules = json.loads(req.text)

    # get configured modules from db
    db_modules = db.query(module_models.ModuleSettings).all()

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

        db_module = next(
            (m for m in db_modules if m.module_name == rawModule["name"]), None
        )

        module = module_schemas.Module(
            name=rawModule["name"],
            type=rawModule["type"],
            mispattributes=moduleAttributes,
            meta=moduleMeta,
            enabled=(db_module.enabled if db_module else False),
            config=db_module.config if db_module else None,
        )

        modules.append(module)

    return modules


def update_module(
    db: Session,
    module_name: str,
    module: module_schemas.ModuleSettingsUpdate,
):
    # get module by name
    db_module = (
        db.query(module_models.ModuleSettings)
        .filter_by(module_name=module_name)
        .first()
    )

    if db_module is None:
        db_module = module_models.ModuleSettings(module_name=module_name, config={})

    if module.enabled is not None:
        db_module.enabled = module.enabled

    if module.config is not None:
        db_module.config = module.config

    db.add(db_module)
    db.commit()
    db.refresh(db_module)

    return True


def query_module(
    module_name: str,
    query: module_schemas.ModuleQuery,
):
    return {"module_name": module_name, "query": query.dict()}
