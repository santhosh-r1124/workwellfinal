from pydantic import BaseModel, Field


class ConsentSettings(BaseModel):
    working_hours: bool = True
    break_patterns: bool = True
    application_categories: bool = True
    typing_dynamics: bool = True
    calendar_metadata: bool = False
    webcam: bool = False
    raw_keyboard: bool = False
    audio_recording: bool = False


class ConsentUpdate(BaseModel):
    enabled: bool


class ConsentEventOut(BaseModel):
    source: str
    action: str
    previous_value: bool | None
    new_value: bool
    created_at: str

    model_config = {"from_attributes": True}


class DataSourceInfo(BaseModel):
    key: str
    label: str
    category: str
    what: str
    why: str
    where: str
    retention: str
    who_can_access: str
    default_enabled: bool
    collectible: bool
    enabled: bool = Field(description="Current consent state for this employee")
