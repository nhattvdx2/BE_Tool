from pydantic import BaseModel


class VoiceLimitResponse(BaseModel):
    username: str
    screenid: str
    number_limit: int


class UploadResponse(BaseModel):
    filename: str
    path: str
    size: int
