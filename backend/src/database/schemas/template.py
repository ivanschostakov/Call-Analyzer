from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from src.enums import DEFAULT_COMPANY_TEMPLATE


class TemplateBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    name: str
    description: str | None = None
    instructions: str = DEFAULT_COMPANY_TEMPLATE.instructions


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int | None = None
    name: str | None = None
    description: str | None = None
    instructions: str | None = None

    @model_validator(mode="after")
    def validate_instructions(self) -> "TemplateUpdate":
        if "instructions" in self.model_fields_set and self.instructions is None:
            raise ValueError("instructions cannot be null")
        return self


class TemplateRead(TemplateBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    created_at: datetime
    updated_at: datetime
