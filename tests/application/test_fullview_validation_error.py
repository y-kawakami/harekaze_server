"""FullviewValidationError のユニットテスト

全景バリデーション NG 判定時の例外クラスのテスト。
Requirements: 3.2, 3.3
"""

import pytest

from app.application.exceptions import (
    ApplicationError,
    FullviewValidationError,
)


@pytest.mark.unit
class TestFullviewValidationError:
    """FullviewValidationError 例外クラスのテスト"""

    def test_inherits_application_error(self):
        """ApplicationError を継承している"""
        error = FullviewValidationError(
            reason="枝の先端のみ",
            confidence=0.88,
        )
        assert isinstance(error, ApplicationError)

    def test_error_code_is_114(self):
        """エラーコードが 114 である"""
        error = FullviewValidationError(
            reason="枝の先端のみ",
            confidence=0.88,
        )
        assert error.error_code == 114

    def test_status_is_400(self):
        """ステータスが 400 である"""
        error = FullviewValidationError(
            reason="枝の先端のみ",
            confidence=0.88,
        )
        assert error.status == 400

    def test_reason_is_set(self):
        """reason が正しく設定される"""
        reason = "枝の先端部分のみが写っており、全体像が確認できません。"
        error = FullviewValidationError(
            reason=reason,
            confidence=0.88,
        )
        assert error.reason == reason

    def test_details_contains_validation_reason(self):
        """details に validation_reason が含まれる"""
        reason = "枝の先端のみ"
        error = FullviewValidationError(
            reason=reason,
            confidence=0.88,
        )
        assert error.details is not None
        assert error.details["validation_reason"] == reason

    def test_details_contains_confidence(self):
        """details に confidence が含まれる"""
        error = FullviewValidationError(
            reason="枝の先端のみ",
            confidence=0.88,
        )
        assert error.details is not None
        assert error.details["confidence"] == 0.88

    def test_str_returns_reason(self):
        """str() で reason が返却される"""
        reason = "枝の先端のみ"
        error = FullviewValidationError(
            reason=reason,
            confidence=0.88,
        )
        assert str(error) == reason

    def test_confidence_zero(self):
        """信頼度 0.0 を設定できる"""
        error = FullviewValidationError(
            reason="テスト",
            confidence=0.0,
        )
        assert error.details is not None
        assert error.details["confidence"] == 0.0

    def test_confidence_one(self):
        """信頼度 1.0 を設定できる"""
        error = FullviewValidationError(
            reason="テスト",
            confidence=1.0,
        )
        assert error.details is not None
        assert error.details["confidence"] == 1.0
