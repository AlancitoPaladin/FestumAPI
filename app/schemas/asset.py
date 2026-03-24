from pydantic import BaseModel, Field


class SignedAssetResponse(BaseModel):
    key: str = Field(..., min_length=1, max_length=1024)
    url: str = Field(..., min_length=1, max_length=4096)
    expires_at: str = Field(..., min_length=20, max_length=40)
