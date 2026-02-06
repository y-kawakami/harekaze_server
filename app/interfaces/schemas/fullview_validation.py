from pydantic import BaseModel, Field


class FullviewValidationResponse(BaseModel):
    """全景バリデーション結果"""
    is_valid: bool = Field(
        ..., description="全景として適切か（True=OK, False=NG）")
    reason: str = Field(
        ..., description="判定理由")
    confidence: float = Field(
        ..., description="信頼度（0.0〜1.0）", ge=0.0, le=1.0)
