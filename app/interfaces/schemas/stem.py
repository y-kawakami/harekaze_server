from typing import Optional

from pydantic import BaseModel, Field


class StemResponse(BaseModel):
    texture: int = Field(..., description="幹の模様(1:滑らか~5:ガサガサ)")
    can_detected: bool = Field(..., description="350ml缶の検出の有無")
    circumference: Optional[float] = Field(None, description="幹周(cm)")
    age: int = Field(..., description="樹齢")
