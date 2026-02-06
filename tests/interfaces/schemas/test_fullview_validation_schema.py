"""FullviewValidationResponse スキーマのユニットテスト

Requirements: 1.2, 1.3, 1.4
"""

import pytest
from pydantic import ValidationError

from app.interfaces.schemas.fullview_validation import FullviewValidationResponse


@pytest.mark.unit
class TestFullviewValidationResponse:
    """FullviewValidationResponse スキーマのテスト"""

    def test_valid_ok_response(self):
        """OK レスポンスを作成できる"""
        response = FullviewValidationResponse(
            is_valid=True,
            reason="桜の木全体が適切に収まっています。",
            confidence=0.95,
        )

        assert response.is_valid is True
        assert response.reason == "桜の木全体が適切に収まっています。"
        assert response.confidence == 0.95

    def test_valid_ng_response(self):
        """NG レスポンスを作成できる"""
        response = FullviewValidationResponse(
            is_valid=False,
            reason="枝の先端部分のみが写っています。",
            confidence=0.88,
        )

        assert response.is_valid is False

    def test_confidence_minimum_zero(self):
        """信頼度の下限は 0.0"""
        response = FullviewValidationResponse(
            is_valid=True,
            reason="テスト",
            confidence=0.0,
        )

        assert response.confidence == 0.0

    def test_confidence_maximum_one(self):
        """信頼度の上限は 1.0"""
        response = FullviewValidationResponse(
            is_valid=True,
            reason="テスト",
            confidence=1.0,
        )

        assert response.confidence == 1.0

    def test_confidence_below_minimum_raises_error(self):
        """信頼度が 0.0 未満の場合はバリデーションエラー"""
        with pytest.raises(ValidationError):
            FullviewValidationResponse(
                is_valid=True,
                reason="テスト",
                confidence=-0.1,
            )

    def test_confidence_above_maximum_raises_error(self):
        """信頼度が 1.0 超の場合はバリデーションエラー"""
        with pytest.raises(ValidationError):
            FullviewValidationResponse(
                is_valid=True,
                reason="テスト",
                confidence=1.1,
            )

    def test_serialization(self):
        """JSON シリアライゼーションが正しい"""
        response = FullviewValidationResponse(
            is_valid=True,
            reason="適切な全景写真です。",
            confidence=0.95,
        )
        data = response.model_dump()

        assert data == {
            "is_valid": True,
            "reason": "適切な全景写真です。",
            "confidence": 0.95,
        }
