from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=500)


class VerifiedUser(BaseModel):
    username: str


class VerifyResponse(BaseModel):
    valid: bool
    user: VerifiedUser
