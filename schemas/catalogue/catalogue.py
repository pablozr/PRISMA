from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseCatalogueQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000)


class CataloguePaginationQueryRequest(BaseCatalogueQueryRequest):
    pass


class CatalogueUnitsQueryRequest(BaseCatalogueQueryRequest):
    centro_ids: Optional[list[int]] = None

    @field_validator("centro_ids")
    @classmethod
    def normalize_centro_ids(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        return normalize_positive_ids(value)


class CatalogueCoursesQueryRequest(BaseCatalogueQueryRequest):
    unidade_ids: Optional[list[int]] = None

    @field_validator("unidade_ids")
    @classmethod
    def normalize_unidade_ids(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        return normalize_positive_ids(value)


def normalize_positive_ids(value: Optional[list[int]]) -> Optional[list[int]]:
    if value is None:
        return None

    normalized = sorted(set(value))
    if any(item <= 0 for item in normalized):
        raise ValueError("Os IDs devem ser inteiros positivos.")

    return normalized or None


def build_catalogue_pagination_query_request(limit: int = 50, offset: int = 0) -> CataloguePaginationQueryRequest:
    return CataloguePaginationQueryRequest(limit=limit, offset=offset)


def build_catalogue_units_query_request(
    centro_ids: Optional[list[int]] = None,
    limit: int = 50,
    offset: int = 0,
) -> CatalogueUnitsQueryRequest:
    return CatalogueUnitsQueryRequest(centro_ids=centro_ids, limit=limit, offset=offset)


def build_catalogue_courses_query_request(
    unidade_ids: Optional[list[int]] = None,
    limit: int = 50,
    offset: int = 0,
) -> CatalogueCoursesQueryRequest:
    return CatalogueCoursesQueryRequest(unidade_ids=unidade_ids, limit=limit, offset=offset)
