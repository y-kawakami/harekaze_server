"""FullviewValidationService のユニットテスト

Bedrock Converse API を使用した桜全景バリデーションのテスト。
Requirements: 1.1-1.4, 2.1-2.4, 6.1-6.4
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.services.fullview_validation_service import (
    FullviewValidationResult,
    FullviewValidationService,
    get_fullview_validation_service,
)


@pytest.fixture
def service() -> FullviewValidationService:
    """テスト用 FullviewValidationService"""
    return FullviewValidationService(
        region_name="ap-northeast-1",
        model_id="test-model-id",
    )


@pytest.fixture
def dummy_image_bytes() -> bytes:
    """テスト用のダミー画像バイト列"""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG-like bytes


def _make_bedrock_ok_response(
    is_valid: bool = True,
    reason: str = "桜の木全体が適切に収まっています。",
    confidence: float = 0.95,
) -> dict[str, list[dict[str, list[dict[str, str | dict[str, str | dict[str, bool | str | float]]]]]]]:
    """Bedrock Converse API の正常レスポンスを生成する"""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "test-id",
                            "name": "fullview_validation",
                            "input": {
                                "is_valid": is_valid,
                                "reason": reason,
                                "confidence": confidence,
                            },
                        }
                    }
                ],
            }
        },
        "stopReason": "tool_use",
    }


@pytest.mark.unit
class TestFullviewValidationResult:
    """FullviewValidationResult データクラスのテスト"""

    def test_ok_result(self):
        """OK 判定結果を作成できる"""
        result = FullviewValidationResult(
            is_valid=True,
            reason="桜の木全体が適切に収まっています。",
            confidence=0.95,
        )

        assert result.is_valid is True
        assert result.reason == "桜の木全体が適切に収まっています。"
        assert result.confidence == 0.95

    def test_ng_result(self):
        """NG 判定結果を作成できる"""
        result = FullviewValidationResult(
            is_valid=False,
            reason="枝の先端部分のみが写っています。",
            confidence=0.88,
        )

        assert result.is_valid is False
        assert result.reason == "枝の先端部分のみが写っています。"
        assert result.confidence == 0.88

    def test_confidence_range_zero(self):
        """信頼度 0.0 の結果を作成できる"""
        result = FullviewValidationResult(
            is_valid=True,
            reason="テスト",
            confidence=0.0,
        )

        assert result.confidence == 0.0

    def test_confidence_range_one(self):
        """信頼度 1.0 の結果を作成できる"""
        result = FullviewValidationResult(
            is_valid=True,
            reason="テスト",
            confidence=1.0,
        )

        assert result.confidence == 1.0


@pytest.mark.unit
class TestFullviewValidationServiceInit:
    """FullviewValidationService 初期化のテスト"""

    def test_default_region(self):
        """デフォルトリージョンが設定される"""
        with patch.dict("os.environ", {}, clear=False):
            service = FullviewValidationService()
            assert service.region_name == "ap-northeast-1"

    def test_custom_model_id(self):
        """カスタムモデル ID を設定できる"""
        service = FullviewValidationService(model_id="custom-model")
        assert service.model_id == "custom-model"

    def test_default_model_id(self):
        """デフォルトモデル ID が APAC クロスリージョン推論プロファイル"""
        with patch.dict("os.environ", {}, clear=False):
            service = FullviewValidationService()
            assert "apac.anthropic.claude-sonnet-4-5-20250929-v1:0" == service.model_id


@pytest.mark.unit
class TestFullviewValidationServiceValidate:
    """FullviewValidationService.validate() のテスト"""

    @pytest.mark.asyncio
    async def test_validate_ok_result(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """OK 判定結果を正しく返却する (Requirements 1.1, 1.2, 2.4)"""
        mock_client = AsyncMock()
        mock_client.converse.return_value = _make_bedrock_ok_response(
            is_valid=True,
            reason="桜の木全体が幹から樹冠まで適切に収まっています。",
            confidence=0.95,
        )
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            result = await service.validate(dummy_image_bytes, "jpeg")

        assert result.is_valid is True
        assert result.confidence == 0.95
        assert "適切" in result.reason

    @pytest.mark.asyncio
    async def test_validate_ng_result(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """NG 判定結果を正しく返却する (Requirements 1.2, 2.1)"""
        mock_client = AsyncMock()
        mock_client.converse.return_value = _make_bedrock_ok_response(
            is_valid=False,
            reason="枝の先端部分のみが写っており、幹が確認できません。",
            confidence=0.88,
        )
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            result = await service.validate(dummy_image_bytes, "jpeg")

        assert result.is_valid is False
        assert result.confidence == 0.88
        assert "枝" in result.reason

    @pytest.mark.asyncio
    async def test_validate_returns_reason_text(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """判定理由を自然言語テキストで返却する (Requirements 1.3)"""
        mock_client = AsyncMock()
        mock_client.converse.return_value = _make_bedrock_ok_response(
            reason="木の幹から樹冠まで全体が確認でき、全景写真として適切です。",
        )
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            result = await service.validate(dummy_image_bytes, "jpeg")

        assert isinstance(result.reason, str)
        assert len(result.reason) > 0

    @pytest.mark.asyncio
    async def test_validate_returns_confidence(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """信頼度を 0.0〜1.0 の数値で返却する (Requirements 1.4)"""
        mock_client = AsyncMock()
        mock_client.converse.return_value = _make_bedrock_ok_response(
            confidence=0.92,
        )
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            result = await service.validate(dummy_image_bytes, "jpeg")

        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_validate_fail_open_on_api_error(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """Bedrock API エラー時はフェイルオープン (Requirements 6.2)"""
        mock_client = AsyncMock()
        mock_client.converse.side_effect = Exception("Bedrock API error")
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            result = await service.validate(dummy_image_bytes, "jpeg")

        assert result.is_valid is True
        assert result.confidence == 0.0
        assert "エラー" in result.reason

    @pytest.mark.asyncio
    async def test_validate_fail_open_on_parse_error(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """レスポンスパース失敗時はフェイルオープン"""
        mock_client = AsyncMock()
        # toolUse が含まれない不正なレスポンス
        mock_client.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "判定結果です"}],
                }
            },
            "stopReason": "end_turn",
        }
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            result = await service.validate(dummy_image_bytes, "jpeg")

        assert result.is_valid is True
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_validate_calls_converse_with_correct_params(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """Converse API を正しいパラメータで呼び出す (Requirements 6.1, 6.4)"""
        mock_client = AsyncMock()
        mock_client.converse.return_value = _make_bedrock_ok_response()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            await service.validate(dummy_image_bytes, "jpeg")

        mock_client.converse.assert_called_once()
        call_kwargs = mock_client.converse.call_args[1]

        # modelId の確認
        assert call_kwargs["modelId"] == "test-model-id"

        # temperature の確認
        assert call_kwargs["inferenceConfig"]["temperature"] == 0.0

        # toolConfig の確認
        assert "toolConfig" in call_kwargs
        tools = call_kwargs["toolConfig"]["tools"]
        assert len(tools) == 1
        assert tools[0]["toolSpec"]["name"] == "fullview_validation"

        # toolChoice の確認
        assert call_kwargs["toolConfig"]["toolChoice"]["tool"]["name"] == "fullview_validation"

        # 画像データの確認
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        user_content = messages[0]["content"]
        image_block = user_content[0]
        assert image_block["image"]["format"] == "jpeg"
        assert image_block["image"]["source"]["bytes"] == dummy_image_bytes

    @pytest.mark.asyncio
    async def test_validate_uses_bedrock_runtime_client(self, service: FullviewValidationService, dummy_image_bytes: bytes):
        """bedrock-runtime クライアントを使用する"""
        mock_client = AsyncMock()
        mock_client.converse.return_value = _make_bedrock_ok_response()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None

        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_context
            mock_session_class.return_value = mock_session

            await service.validate(dummy_image_bytes, "jpeg")

        mock_session.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="ap-northeast-1",
        )


@pytest.mark.unit
class TestGetFullviewValidationService:
    """get_fullview_validation_service ファクトリ関数のテスト"""

    def test_returns_service_instance(self):
        """FullviewValidationService インスタンスを返す"""
        service = get_fullview_validation_service()
        assert isinstance(service, FullviewValidationService)
