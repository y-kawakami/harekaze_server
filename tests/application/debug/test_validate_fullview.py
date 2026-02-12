"""validate_fullview デバッグ用アプリケーションロジックのユニットテスト

全景バリデーションのみを単独実行するデバッグ用ユースケースのテスト。
Requirements: 4.1, 4.3
"""

import pytest
from unittest.mock import AsyncMock

from app.domain.services.fullview_validation_service import (
    FullviewValidationResult,
    FullviewValidationService,
)
from app.interfaces.schemas.fullview_validation import (
    FullviewValidationResponse,
)


@pytest.mark.unit
class TestValidateFullviewApp:
    """validate_fullview_app のテスト"""

    @pytest.fixture
    def mock_service(self) -> FullviewValidationService:
        service = AsyncMock(spec=FullviewValidationService)
        return service

    @pytest.mark.asyncio
    async def test_returns_ok_result(
        self,
        mock_service: FullviewValidationService,
    ):
        """OK 判定結果を FullviewValidationResponse で返却する"""
        from app.application.debug.validate_fullview import (
            validate_fullview_app,
        )

        assert isinstance(mock_service.validate, AsyncMock)
        mock_service.validate.return_value = FullviewValidationResult(
            is_valid=True,
            reason="桜の木全体が適切に収まっています。",
            confidence=0.95,
        )

        result = await validate_fullview_app(
            image_data=b"fake-image-data",
            fullview_validation_service=mock_service,
        )

        assert isinstance(result, FullviewValidationResponse)
        assert result.is_valid is True
        assert result.reason == "桜の木全体が適切に収まっています。"
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_returns_ng_result(
        self,
        mock_service: FullviewValidationService,
    ):
        """NG 判定結果を FullviewValidationResponse で返却する"""
        from app.application.debug.validate_fullview import (
            validate_fullview_app,
        )

        assert isinstance(mock_service.validate, AsyncMock)
        mock_service.validate.return_value = FullviewValidationResult(
            is_valid=False,
            reason="枝の先端部分のみが写っています。",
            confidence=0.88,
        )

        result = await validate_fullview_app(
            image_data=b"fake-image-data",
            fullview_validation_service=mock_service,
        )

        assert isinstance(result, FullviewValidationResponse)
        assert result.is_valid is False
        assert result.reason == "枝の先端部分のみが写っています。"
        assert result.confidence == 0.88

    @pytest.mark.asyncio
    async def test_calls_validate_with_jpeg(
        self,
        mock_service: FullviewValidationService,
    ):
        """サービスの validate を jpeg フォーマットで呼び出す"""
        from app.application.debug.validate_fullview import (
            validate_fullview_app,
        )

        assert isinstance(mock_service.validate, AsyncMock)
        mock_service.validate.return_value = FullviewValidationResult(
            is_valid=True,
            reason="OK",
            confidence=0.9,
        )

        image_data = b"test-image-bytes"
        await validate_fullview_app(
            image_data=image_data,
            fullview_validation_service=mock_service,
        )

        mock_service.validate.assert_called_once_with(
            image_bytes=image_data,
            image_format="jpeg",
        )

    @pytest.mark.asyncio
    async def test_does_not_run_other_analysis(
        self,
        mock_service: FullviewValidationService,
    ):
        """元気度判定やその他の解析処理を実行しない"""
        from app.application.debug.validate_fullview import (
            validate_fullview_app,
        )

        assert isinstance(mock_service.validate, AsyncMock)
        mock_service.validate.return_value = FullviewValidationResult(
            is_valid=True,
            reason="OK",
            confidence=0.9,
        )

        result = await validate_fullview_app(
            image_data=b"fake-image-data",
            fullview_validation_service=mock_service,
        )

        # validate のみが呼ばれたことを確認
        assert mock_service.validate.call_count == 1
        # 返却型が FullviewValidationResponse であること
        assert isinstance(result, FullviewValidationResponse)
