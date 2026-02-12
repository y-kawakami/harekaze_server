from typing import Optional

from pydantic import BaseModel, Field

from app.interfaces.schemas.fullview_validation import (
    FullviewValidationResponse,
)


class BlurPrivacyResponse(BaseModel):
    image_url: str = Field(..., description="ぼかし処理後の画像のURL")
    thumb_url: str = Field(..., description="ぼかし処理後のサムネイル画像のURL")

    class Config:
        from_attributes = True


class StemAnalysisResponse(BaseModel):
    """幹の画像解析結果"""
    texture: Optional[int] = Field(
        None, description="幹の模様（1:滑らか~5:ガサガサ）", ge=1, le=5)
    texture_real: Optional[float] = Field(
        None, description="幹の模様（実数値）", ge=1, le=5)
    can_detected: bool = Field(..., description="350ml缶の検出有無（樹齢推定に使用）")
    circumference: Optional[float] = Field(None, description="幹周（cm）（樹齢推定に使用）")
    age: Optional[int] = Field(None, description="推定樹齢（最終値）")
    age_texture: Optional[int] = Field(None, description="推定樹齢（幹の模様を使用）")
    age_circumference: Optional[int] = Field(None, description="推定樹齢（幹径を使用）")
    analysis_image_url: Optional[str] = Field(
        None, description="解析結果画像のURL（デバッグ用）")


class TreeVitalityResponse(BaseModel):
    """桜の木全体の活力解析結果"""
    vitality: Optional[int] = Field(
        None, description="総合元気度（1:元気～5:元気がない）", ge=1, le=5)
    vitality_real: Optional[float] = Field(
        None, description="総合元気度（実数値）", ge=1, le=5)
    vitality_bloom: Optional[int] = Field(
        None, description="開花時元気度（1:元気～5:元気がない）", ge=1, le=5)
    vitality_bloom_real: Optional[float] = Field(
        None, description="開花時元気度（実数値）", ge=1, le=5)
    vitality_bloom_weight: Optional[float] = Field(
        None, description="開花時元気度の重み", ge=0, le=1)
    vitality_noleaf: Optional[int] = Field(
        None, description="葉なし時元気度（1:元気～5:元気がない）", ge=1, le=5)
    vitality_noleaf_real: Optional[float] = Field(
        None, description="葉なし時元気度（実数値）", ge=1, le=5)
    vitality_noleaf_weight: Optional[float] = Field(
        None, description="葉なし時元気度の重み", ge=0, le=1)
    bloom_image_url: Optional[str] = Field(
        None, description="開花時解析画像のURL（デバッグ用）")
    noleaf_image_url: Optional[str] = Field(
        None, description="葉なし時解析画像のURL（デバッグ用）")
    fullview_validation: Optional[FullviewValidationResponse] = Field(
        None, description="全景バリデーション結果（未実行時は None）")
