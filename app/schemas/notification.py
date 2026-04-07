from pydantic import BaseModel, Field


class DeviceTokenRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=4096)
    platform: str = Field(..., pattern="^(android|ios)$")


class DeviceTokenDeleteRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=4096)


class DeviceTokenResponse(BaseModel):
    ok: bool = True
    token: str
    platform: str


class DeviceTokenDeleteResponse(BaseModel):
    deleted: bool = True
