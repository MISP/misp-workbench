import json
import logging
from functools import lru_cache

import requests
from app.models import module as module_models
from app.schemas import module as module_schemas
from app.settings import Settings, get_settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_modules_service_url(settings: Settings = get_settings()):
    return f"http://{settings.Modules.host}:{settings.Modules.port}"


@lru_cache
def get_modules(db: Session, enabled: bool = None):
    modules = []

    # get modules from api
    req = requests.get(f"{get_modules_service_url()}/modules")

    rawModules = json.loads(req.text)

    # get configured modules from db
    db_module_configs = db.query(module_models.ModuleSettings).all()

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
            input=(
                rawModule["mispattributes"]["input"]
                if "input" in rawModule["mispattributes"]
                else (
                    rawModule["mispattributes"]["inputSource"]
                    if "inputSource" in rawModule["mispattributes"]
                    else []
                )
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
            user_config=(
                rawModule["mispattributes"]["userConfig"]
                if "userConfig" in rawModule["mispattributes"]
                else None
            ),
        )

        db_module_config = next(
            (m for m in db_module_configs if m.module_name == rawModule["name"]), None
        )

        module = module_schemas.Module(
            name=rawModule["name"],
            type=rawModule["type"],
            misp_attributes=moduleAttributes,
            meta=moduleMeta,
            enabled=(db_module_config.enabled if db_module_config else False),
            config=db_module_config.config if db_module_config else None,
        )

        modules.append(module)

    if enabled is not None:
        modules = [m for m in modules if m.enabled == enabled]

    return modules


def get_module_config(db: Session, module_name: str):
    db_module_config = (
        db.query(module_models.ModuleSettings)
        .filter_by(module_name=module_name)
        .first()
    )

    return db_module_config if db_module_config else None


def update_module(
    db: Session,
    module_name: str,
    module: module_schemas.ModuleSettingsUpdate,
):
    # get module by name
    db_module_config = get_module_config(db, module_name)

    if db_module_config is None:
        db_module_config = module_models.ModuleSettings(
            module_name=module_name, config={}
        )

    if module.enabled is not None:
        db_module_config.enabled = module.enabled

    if module.config is not None:
        db_module_config.config = module.config

    db.add(db_module_config)
    db.commit()
    db.refresh(db_module_config)

    return True


def query_module(
    db: Session,
    query: module_schemas.ModuleQuery,
):

    db_module_config = get_module_config(db, query.module)

    if db_module_config.enabled is not True:
        raise Exception("Module is not enabled")

    url = f"{get_modules_service_url()}/query"
    logger.info("query misp-module: %s" % query.module)
    req = requests.post(url, query.json())

    return req.json()
