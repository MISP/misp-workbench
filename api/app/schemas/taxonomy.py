from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaxonomyBase(BaseModel):
    namespace: str
    description: str
    version: int
    enabled: bool
    exclusive: bool
    required: bool
    highlighted: bool


class TaxonomyUpdate(BaseModel):
    enabled: Optional[bool] = None
    exclusive: Optional[bool] = None
    highlighted: Optional[bool] = None
    enabled: Optional[bool] = None


class TaxonomyPredicateBase(BaseModel):
    taxonomy_id: int
    value: str
    expanded: str
    colour: Optional[str]
    description: Optional[str]
    exclusive: Optional[bool]
    numerical_value: Optional[int]


class TaxonomyEntryBase(BaseModel):
    taxonomy_predicate_id: int
    value: str
    expanded: str
    colour: Optional[str]
    description: Optional[str]
    numerical_value: Optional[int]


class TaxonomyEntry(TaxonomyEntryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TaxonomyPredicate(TaxonomyPredicateBase):
    id: int
    entries: list[TaxonomyEntry] = []
    model_config = ConfigDict(from_attributes=True)


class Taxonomy(TaxonomyBase):
    id: int
    predicates: list[TaxonomyPredicate] = []
    model_config = ConfigDict(from_attributes=True)
