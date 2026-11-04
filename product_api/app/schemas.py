from pydantic import BaseModel


class ProductSpecification(BaseModel):
    name: str
    value: str | None


class Product(BaseModel):
    manufactorer: str | None
    model_name: str | None
    category: str | None
    specifications: list[ProductSpecification]


class SpecificationSummary(BaseModel):
    name: str
    values: list[str]
    categories: list[str]
