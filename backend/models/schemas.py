from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    trend_id: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9\-]+$")
    top_k: int = Field(default=4, ge=1, le=8)


class GenerateRequest(BaseModel):
    trend_id: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9\-]+$")


class PublishRequest(BaseModel):
    post: str | None = Field(default=None, max_length=5000)


class AutomationUpdate(BaseModel):
    enabled: bool
    scheduled_time: str = Field(default="19:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
