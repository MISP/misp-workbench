from typing import Optional, Union

from pydantic import BaseModel, ConfigDict


class ModuleAttributes(BaseModel):
    inputSource: Optional[list[str]]
    output: Optional[list[str]]
    format: Optional[str]
    userConfig: Optional[dict]

    model_config = ConfigDict(from_attributes=True)


class ModuleMeta(BaseModel):
    version: Optional[str]
    author: str
    description: str
    module_type: list[str]
    config: Union[Optional[list[str]], Optional[dict]]


class ModuleBase(BaseModel):
    name: str
    type: str
    mispattributes: ModuleAttributes
    meta: ModuleMeta
    enabled: bool
    config: Optional[dict]


class ModuleSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[dict] = None


class Module(ModuleBase):
    model_config = ConfigDict(from_attributes=True)


class ModuleQuery(BaseModel):
    module: str
    attribute: dict
    config: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)
