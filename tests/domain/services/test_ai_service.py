"""AIService の新モデル呼び出し対応テスト

3分咲き・5分咲きモデルの API 呼び出しメソッドと
結果データクラスをテストする。
Requirements: 3.2, 3.3, 3.5
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.domain.services.ai_service import (AIService,
                                            TreeVitalityBloom30Result,
                                            TreeVitalityBloom50Result)


@pytest.mark.unit
class TestTreeVitalityBloom30Result:
    """TreeVitalityBloom30Result データクラスのテスト (Req 3.5)"""

    def test_create_result(self):
        """全フィールドを持つインスタンスを作成できること"""
        result = TreeVitalityBloom30Result(
            vitality=3,
            vitality_real=3.2,
            vitality_probs=[0.1, 0.2, 0.4, 0.2, 0.1],
            debug_image_key="s3://bucket/key.jpg",
        )
        assert result.vitality == 3
        assert result.vitality_real == 3.2
        assert result.vitality_probs == [0.1, 0.2, 0.4, 0.2, 0.1]
        assert result.debug_image_key == "s3://bucket/key.jpg"

    def test_debug_image_key_default_none(self):
        """debug_image_key のデフォルトが None であること"""
        result = TreeVitalityBloom30Result(
            vitality=4,
            vitality_real=4.1,
            vitality_probs=[0.0, 0.1, 0.1, 0.6, 0.2],
        )
        assert result.debug_image_key is None


@pytest.mark.unit
class TestTreeVitalityBloom50Result:
    """TreeVitalityBloom50Result データクラスのテスト (Req 3.5)"""

    def test_create_result(self):
        """全フィールドを持つインスタンスを作成できること"""
        result = TreeVitalityBloom50Result(
            vitality=2,
            vitality_real=2.5,
            vitality_probs=[0.1, 0.4, 0.3, 0.1, 0.1],
            debug_image_key="s3://bucket/key50.jpg",
        )
        assert result.vitality == 2
        assert result.vitality_real == 2.5
        assert result.vitality_probs == [0.1, 0.4, 0.3, 0.1, 0.1]
        assert result.debug_image_key == "s3://bucket/key50.jpg"

    def test_debug_image_key_default_none(self):
        """debug_image_key のデフォルトが None であること"""
        result = TreeVitalityBloom50Result(
            vitality=5,
            vitality_real=4.8,
            vitality_probs=[0.0, 0.0, 0.1, 0.1, 0.8],
        )
        assert result.debug_image_key is None


@pytest.mark.unit
class TestAIServiceBloom30:
    """AIService.analyze_tree_vitality_bloom_30 のテスト (Req 3.2)"""

    def test_api_path_constant(self):
        """bloom_30 の API パスが正しく設定されること"""
        service = AIService(api_endpoint="http://test")
        assert service.api_path_vitality_bloom_30 == (
            "/analyze/image/vitality/bloom_30_percent"
        )

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_path(self):
        """正しい API パスで _call_api_with_bytes を呼び出すこと"""
        service = AIService(api_endpoint="http://test")
        mock_response = {
            "status": "success",
            "data": {
                "vitality": 3,
                "vitality_real": 3.1,
                "vitality_probs": [0.1, 0.2, 0.4, 0.2, 0.1],
                "debug_image_key": "debug/key.jpg",
            },
        }
        with patch.object(
            service,
            "_call_api_with_bytes",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_call:
            await service.analyze_tree_vitality_bloom_30(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
            mock_call.assert_called_once_with(
                "/analyze/image/vitality/bloom_30_percent",
                {"output_bucket": "bucket", "output_key": "key"},
                b"fake_image",
                "test.jpg",
            )

    @pytest.mark.asyncio
    async def test_returns_correct_result_new_format(self):
        """新形式レスポンスから正しい結果を返すこと"""
        service = AIService(api_endpoint="http://test")
        mock_response = {
            "status": "success",
            "data": {
                "vitality": 4,
                "vitality_real": 4.2,
                "vitality_probs": [0.0, 0.1, 0.1, 0.6, 0.2],
                "debug_image_key": "debug/bloom30.jpg",
            },
        }
        with patch.object(
            service,
            "_call_api_with_bytes",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.analyze_tree_vitality_bloom_30(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
            assert isinstance(result, TreeVitalityBloom30Result)
            assert result.vitality == 4
            assert result.vitality_real == 4.2
            assert result.vitality_probs == [0.0, 0.1, 0.1, 0.6, 0.2]
            assert result.debug_image_key == "debug/bloom30.jpg"

    @pytest.mark.asyncio
    async def test_returns_correct_result_legacy_format(self):
        """レガシー形式レスポンスから正しい結果を返すこと"""
        service = AIService(api_endpoint="http://test")
        mock_response = {
            "vitality": 2,
            "vitality_real": 2.3,
            "vitality_probs": [0.1, 0.5, 0.2, 0.1, 0.1],
        }
        with patch.object(
            service,
            "_call_api_with_bytes",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.analyze_tree_vitality_bloom_30(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
            assert isinstance(result, TreeVitalityBloom30Result)
            assert result.vitality == 2
            assert result.vitality_real == 2.3
            assert result.debug_image_key is None

    @pytest.mark.asyncio
    async def test_raises_without_endpoint(self):
        """API エンドポイント未設定時に ValueError を送出すること"""
        service = AIService(api_endpoint="")
        with pytest.raises(ValueError, match="AI_API_ENDPOINT"):
            await service.analyze_tree_vitality_bloom_30(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )


@pytest.mark.unit
class TestAIServiceBloom50:
    """AIService.analyze_tree_vitality_bloom_50 のテスト (Req 3.3)"""

    def test_api_path_constant(self):
        """bloom_50 の API パスが正しく設定されること"""
        service = AIService(api_endpoint="http://test")
        assert service.api_path_vitality_bloom_50 == (
            "/analyze/image/vitality/bloom_50_percent"
        )

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_path(self):
        """正しい API パスで _call_api_with_bytes を呼び出すこと"""
        service = AIService(api_endpoint="http://test")
        mock_response = {
            "status": "success",
            "data": {
                "vitality": 5,
                "vitality_real": 4.9,
                "vitality_probs": [0.0, 0.0, 0.0, 0.1, 0.9],
                "debug_image_key": "debug/key50.jpg",
            },
        }
        with patch.object(
            service,
            "_call_api_with_bytes",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_call:
            await service.analyze_tree_vitality_bloom_50(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
            mock_call.assert_called_once_with(
                "/analyze/image/vitality/bloom_50_percent",
                {"output_bucket": "bucket", "output_key": "key"},
                b"fake_image",
                "test.jpg",
            )

    @pytest.mark.asyncio
    async def test_returns_correct_result_new_format(self):
        """新形式レスポンスから正しい結果を返すこと"""
        service = AIService(api_endpoint="http://test")
        mock_response = {
            "status": "success",
            "data": {
                "vitality": 1,
                "vitality_real": 1.3,
                "vitality_probs": [0.7, 0.2, 0.1, 0.0, 0.0],
                "debug_image_key": "debug/bloom50.jpg",
            },
        }
        with patch.object(
            service,
            "_call_api_with_bytes",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.analyze_tree_vitality_bloom_50(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
            assert isinstance(result, TreeVitalityBloom50Result)
            assert result.vitality == 1
            assert result.vitality_real == 1.3
            assert result.vitality_probs == [0.7, 0.2, 0.1, 0.0, 0.0]
            assert result.debug_image_key == "debug/bloom50.jpg"

    @pytest.mark.asyncio
    async def test_returns_correct_result_legacy_format(self):
        """レガシー形式レスポンスから正しい結果を返すこと"""
        service = AIService(api_endpoint="http://test")
        mock_response = {
            "vitality": 3,
            "vitality_real": 3.0,
            "vitality_probs": [0.1, 0.2, 0.4, 0.2, 0.1],
        }
        with patch.object(
            service,
            "_call_api_with_bytes",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.analyze_tree_vitality_bloom_50(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
            assert isinstance(result, TreeVitalityBloom50Result)
            assert result.vitality == 3
            assert result.vitality_real == 3.0
            assert result.debug_image_key is None

    @pytest.mark.asyncio
    async def test_raises_without_endpoint(self):
        """API エンドポイント未設定時に ValueError を送出すること"""
        service = AIService(api_endpoint="")
        with pytest.raises(ValueError, match="AI_API_ENDPOINT"):
            await service.analyze_tree_vitality_bloom_50(
                image_bytes=b"fake_image",
                filename="test.jpg",
                output_bucket="bucket",
                output_key="key",
            )
