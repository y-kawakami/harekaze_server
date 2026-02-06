import os
import time as time_module
from dataclasses import dataclass
from typing import Final, Literal

import aioboto3
from loguru import logger
from types_aiobotocore_bedrock_runtime.type_defs import (
    ContentBlockOutputTypeDef, ContentBlockTypeDef, ConverseResponseTypeDef,
    ImageBlockTypeDef, ImageSourceTypeDef, InferenceConfigurationTypeDef,
    MessageTypeDef, SystemContentBlockTypeDef, ToolChoiceTypeDef,
    ToolConfigurationTypeDef, ToolTypeDef)

ImageFormatType = Literal["gif", "jpeg", "png", "webp"]

SYSTEM_PROMPT: Final[str] = (
    "あなたは桜の木の写真を評価する画像判定の専門家です。\n"
    "与えられた画像が「桜の木の全景写真」として適切かどうかを判定してください。\n"
    "\n"
    "判定は厳密に以下の基準に従ってください。"
)

USER_PROMPT: Final[str] = (
    "この画像が桜の木の全景写真として適切かどうかを判定してください。\n"
    "\n"
    "## OK判定の条件\n"
    "以下の条件をすべて満たす場合、OKと判定してください:\n"
    "- 桜の木の幹（根元付近）から樹冠（木の上部）まで、木全体の形が概ね確認できる\n"
    "- 木の主要な構造（幹・主枝・樹冠）が画像フレーム内に概ね収まっている\n"
    "\n"
    "## NG判定の条件\n"
    "以下のいずれかに該当する場合、NGと判定してください:\n"
    "\n"
    "1. **枝先端のみ**: 幹が写っておらず、枝の先端部分や花のクローズアップのみが写っている\n"
    "2. **寄りすぎ**: 幹や枝に寄りすぎており、木全体の形状（シルエット）が把握できない\n"
    "3. **はみ出し**: 木の主要部分（幹・主枝・樹冠）が画像フレームから大きくはみ出しており、"
    "全体像が確認できない\n"
    "\n"
    "## 判定の注意事項\n"
    "- 木の一部（枝先や根元）が多少フレームから切れていても、"
    "全体の形状が把握できればOKとしてください\n"
    "- 複数の桜の木が写っている場合、主要な1本の全景が確認できればOKとしてください\n"
    "- 桜の木以外の被写体（建物、人物など）が写り込んでいても、"
    "桜の木の全景が確認できればOKとしてください\n"
    "- 画像が不鮮明・暗い等の品質問題はこの判定の対象外です（OKとしてください）\n"
    "\n"
    "判定結果をfullview_validationツールで返却してください。"
)

FULLVIEW_VALIDATION_TOOL: Final[ToolTypeDef] = {
    "toolSpec": {
        "name": "fullview_validation",
        "description": "桜の全景バリデーション判定結果を返却する",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "is_valid": {
                        "type": "boolean",
                        "description": "桜の木全体が適切に写っているか",
                    },
                    "reason": {
                        "type": "string",
                        "description": "判定理由の説明",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "判定の信頼度（0.0〜1.0）",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["is_valid", "reason", "confidence"],
            }
        },
    }
}

DEFAULT_MODEL_ID: Final[str] = "apac.anthropic.claude-sonnet-4-5-20250929-v1:0"


@dataclass
class FullviewValidationResult:
    """全景バリデーションの判定結果"""
    is_valid: bool
    reason: str
    confidence: float


class FullviewValidationService:
    """AWS Bedrock Converse API を使用した桜の全景バリデーションサービス"""

    region_name: str
    model_id: str

    def __init__(
        self,
        region_name: str | None = None,
        model_id: str | None = None,
    ) -> None:
        self.region_name = region_name or os.getenv(
            "AWS_REGION", "ap-northeast-1"
        )
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", DEFAULT_MODEL_ID
        )

    async def validate(
        self,
        image_bytes: bytes,
        image_format: ImageFormatType,
    ) -> FullviewValidationResult:
        """画像が桜の全景として適切かを判定する

        Args:
            image_bytes: 画像データのバイト列
            image_format: 画像フォーマット（"jpeg", "png", "gif", "webp"）

        Returns:
            FullviewValidationResult: 判定結果
        """
        start_time = time_module.time()
        try:
            session = aioboto3.Session()
            async with session.client(
                "bedrock-runtime",
                region_name=self.region_name,
            ) as bedrock_client:
                system_blocks: list[SystemContentBlockTypeDef] = [
                    {"text": SYSTEM_PROMPT}
                ]
                image_source: ImageSourceTypeDef = {"bytes": image_bytes}
                image_block: ImageBlockTypeDef = {
                    "format": image_format,
                    "source": image_source,
                }
                content_block: ContentBlockTypeDef = {"image": image_block}
                text_block: ContentBlockTypeDef = {"text": USER_PROMPT}
                messages: list[MessageTypeDef] = [
                    {
                        "role": "user",
                        "content": [content_block, text_block],
                    }
                ]
                inference_config: InferenceConfigurationTypeDef = {
                    "temperature": 0.0,
                    "maxTokens": 512,
                }
                tool_choice: ToolChoiceTypeDef = {
                    "tool": {"name": "fullview_validation"},
                }
                tool_config: ToolConfigurationTypeDef = {
                    "tools": [FULLVIEW_VALIDATION_TOOL],
                    "toolChoice": tool_choice,
                }

                response: ConverseResponseTypeDef = (
                    await bedrock_client.converse(
                        modelId=self.model_id,
                        system=system_blocks,
                        messages=messages,
                        inferenceConfig=inference_config,
                        toolConfig=tool_config,
                    )
                )

            result = self._parse_response(response)
            elapsed_ms = (time_module.time() - start_time) * 1000
            logger.info(
                "全景バリデーション完了: "
                + f"is_valid={result.is_valid}, "
                + f"confidence={result.confidence:.2f}, "
                + f"elapsed={elapsed_ms:.2f}ms"
            )
            return result

        except Exception as e:
            elapsed_ms = (time_module.time() - start_time) * 1000
            logger.error(
                "全景バリデーション Bedrock API エラー: "
                + f"{e}, elapsed={elapsed_ms:.2f}ms"
            )
            return FullviewValidationResult(
                is_valid=True,
                reason="Bedrock API エラーのためスキップ",
                confidence=0.0,
            )

    def _parse_response(
        self,
        response: ConverseResponseTypeDef,
    ) -> FullviewValidationResult:
        """Bedrock Converse API のレスポンスをパースする

        Args:
            response: Bedrock Converse API のレスポンス

        Returns:
            FullviewValidationResult: パースされた判定結果

        Note:
            パース失敗時はフェイルオープン結果を返却する
        """
        try:
            output = response["output"]
            message = output.get("message")
            if message is None:
                logger.warning("Bedrock レスポンスに message が含まれていません")
                return self._fail_open_result()

            content_blocks: list[ContentBlockOutputTypeDef] = message[
                "content"
            ]

            for block in content_blocks:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    # Any required: Bedrock SDK の ToolUseBlockOutputTypeDef
                    # は input を dict[str, Any] として定義している
                    tool_input = tool_use["input"]

                    # Any required: Bedrock SDK の型定義が
                    # tool_input を dict[str, Any] として定義
                    ti: dict[str, bool | str | float] = (
                        tool_input
                    )
                    is_valid = bool(ti["is_valid"])
                    reason = str(ti["reason"])
                    confidence_raw = float(ti["confidence"])
                    confidence = max(0.0, min(1.0, confidence_raw))

                    return FullviewValidationResult(
                        is_valid=is_valid,
                        reason=reason,
                        confidence=confidence,
                    )

            # toolUse が見つからない場合
            logger.warning(
                "Bedrock レスポンスに toolUse が含まれていません"
            )
            return self._fail_open_result()

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Bedrock レスポンスのパースに失敗: {e}")
            return self._fail_open_result()

    @staticmethod
    def _fail_open_result() -> FullviewValidationResult:
        """フェイルオープン結果を返却する"""
        return FullviewValidationResult(
            is_valid=True,
            reason="レスポンス解析エラーのためスキップ",
            confidence=0.0,
        )


# シングルトンパターン
_fullview_validation_service_instance: FullviewValidationService | None = None


def get_fullview_validation_service() -> FullviewValidationService:
    """FullviewValidationService のインスタンスを取得する"""
    global _fullview_validation_service_instance
    if _fullview_validation_service_instance is None:
        _fullview_validation_service_instance = FullviewValidationService()
    return _fullview_validation_service_instance
