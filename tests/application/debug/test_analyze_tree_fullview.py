"""analyze_tree_app に全景バリデーション結果を追加するテスト

既存の元気度判定デバッグのアプリケーションロジックに
全景バリデーション結果を含めるテスト。
Requirements: 5.1, 5.2
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.services.fullview_validation_service import (
    FullviewValidationResult,
    FullviewValidationService,
)


@pytest.mark.unit
class TestAnalyzeTreeAppWithFullview:
    """analyze_tree_app の全景バリデーション統合テスト"""

    @pytest.fixture
    def mock_fv_service(self) -> FullviewValidationService:
        service = AsyncMock(spec=FullviewValidationService)
        return service

    @pytest.fixture
    def mock_image_service(self):
        service = MagicMock()
        service.get_contents_bucket_name.return_value = "test-bucket"
        service.get_full_object_key.return_value = "full/key"
        service.upload_image = AsyncMock(return_value=True)
        service.get_image_url.return_value = "http://example.com/img"
        return service

    @pytest.fixture
    def mock_label_detector(self):
        return AsyncMock()

    @pytest.fixture
    def mock_ai_service(self):
        service = AsyncMock()
        bloom_result = MagicMock()
        bloom_result.vitality = 2
        bloom_result.vitality_real = 2.0
        bloom_result.debug_image_key = "debug_bloom.jpg"
        service.analyze_tree_vitality_bloom.return_value = bloom_result

        noleaf_result = MagicMock()
        noleaf_result.vitality = 3
        noleaf_result.vitality_real = 3.0
        noleaf_result.debug_image_key = "debug_noleaf.jpg"
        service.analyze_tree_vitality_noleaf.return_value = noleaf_result
        return service

    @pytest.mark.asyncio
    async def test_response_contains_fullview_validation(
        self,
        mock_fv_service: FullviewValidationService,
        mock_image_service,
        mock_label_detector,
        mock_ai_service,
    ):
        """レスポンスに fullview_validation フィールドが含まれる"""
        from app.application.debug.analyze_tree import (
            analyze_tree_app,
        )

        assert isinstance(mock_fv_service.validate, AsyncMock)
        mock_fv_service.validate.return_value = FullviewValidationResult(
            is_valid=True,
            reason="桜の木全体が適切に収まっています。",
            confidence=0.95,
        )

        result = await analyze_tree_app(
            image_data=b"fake-image-data",
            image_service=mock_image_service,
            label_detector=mock_label_detector,
            ai_service=mock_ai_service,
            fullview_validation_service=mock_fv_service,
        )

        assert result.fullview_validation is not None
        assert result.fullview_validation.is_valid is True
        assert result.fullview_validation.reason == (
            "桜の木全体が適切に収まっています。"
        )
        assert result.fullview_validation.confidence == 0.95

    @pytest.mark.asyncio
    async def test_fullview_ng_result_included(
        self,
        mock_fv_service: FullviewValidationService,
        mock_image_service,
        mock_label_detector,
        mock_ai_service,
    ):
        """NG 判定結果もレスポンスに含まれる"""
        from app.application.debug.analyze_tree import (
            analyze_tree_app,
        )

        assert isinstance(mock_fv_service.validate, AsyncMock)
        mock_fv_service.validate.return_value = FullviewValidationResult(
            is_valid=False,
            reason="枝の先端部分のみが写っています。",
            confidence=0.88,
        )

        result = await analyze_tree_app(
            image_data=b"fake-image-data",
            image_service=mock_image_service,
            label_detector=mock_label_detector,
            ai_service=mock_ai_service,
            fullview_validation_service=mock_fv_service,
        )

        assert result.fullview_validation is not None
        assert result.fullview_validation.is_valid is False
        assert result.fullview_validation.confidence == 0.88

    @pytest.mark.asyncio
    async def test_fullview_none_without_service(
        self,
        mock_image_service,
        mock_label_detector,
        mock_ai_service,
    ):
        """サービス未指定時は fullview_validation が None"""
        from app.application.debug.analyze_tree import (
            analyze_tree_app,
        )

        result = await analyze_tree_app(
            image_data=b"fake-image-data",
            image_service=mock_image_service,
            label_detector=mock_label_detector,
            ai_service=mock_ai_service,
        )

        assert result.fullview_validation is None
