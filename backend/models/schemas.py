from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    trend_id: str
    top_k: int = 4


class GenerateRequest(BaseModel):
    trend_id: str


class PublishRequest(BaseModel):
    post: str | None = None  # defaults to last generated post


class AutomationUpdate(BaseModel):
    enabled: bool
    scheduled_time: str = "19:00"
