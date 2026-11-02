"""Validated ML API contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(default="", max_length=500)
    content: str = Field(default="", max_length=50_000)

    @model_validator(mode="after")
    def require_text(self):
        if not self.title and not self.content:
            raise ValueError("At least one of title or content must contain text")
        return self


class CategoryScore(BaseModel):
    category: str
    value: float


class ClassificationResponse(BaseModel):
    predicted_category: str
    model_id: str
    model_version: str
    scores: list[CategoryScore]
    score_type: Literal["decision_function", "probability"]
    calibrated_probability: bool
    input_characters: int


class ModelInfoResponse(BaseModel):
    algorithm: str
    model_id: str
    model_version: str
    training_dataset: str
    supported_categories: list[str]
    artifact_available: bool
    score_semantics: str
