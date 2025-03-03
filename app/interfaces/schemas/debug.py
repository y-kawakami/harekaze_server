from pydantic import BaseModel, Field


class BlurPrivacyResponse(BaseModel):
    image_url: str = Field(..., description="画像のURL")

    class Config:
        from_attributes = True
