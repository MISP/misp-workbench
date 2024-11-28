from pydantic import BaseModel, ConfigDict


class TaxonomyBase(BaseModel):
    namespace: str
    description: str
    version: int
    enabled: bool
    exclusive: bool
    required: bool
    highlighted: bool


class Taxonomy(TaxonomyBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TaxonomyPredicateBase(BaseModel):
    taxonomy_id: int
    value: str
    expanded: str
    colour: str
    description: str
    exclusive: bool
    numerical_value: int


class TaxonomyPredicate(TaxonomyPredicateBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TaxonomyEntryBase(BaseModel):
    taxonomy_predicate_id: int
    value: str
    expanded: str
    colour: str
    description: str
    numerical_value: int


class TaxonomyEntry(TaxonomyEntryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
