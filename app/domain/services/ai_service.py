import os
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from app.domain.models.bounding_box import BoundingBox

# .envファイルを読み込む
load_dotenv()


@dataclass
class StemAnalysisResult:
    """茎分析の結果を表すデータクラス"""
    diameter_mm: float
    smoothness: int
    smoothness_real: float
    smoothness_probs: List[float]
    debug_image_key: Optional[str] = None


@dataclass
class StemAnalysisResponse:
    """茎分析の結果を表すデータクラス"""
    status: str
    data: Optional[StemAnalysisResult] = None


@dataclass
class TreeVitalityBloomResult:
    """木の活力（開花時）分析の結果を表すデータクラス"""
    vitality: int
    vitality_real: float
    vitality_probs: List[float]
    debug_image_key: Optional[str] = None


@dataclass
class TreeVitalityBloomResponse:
    """木の活力（開花時）分析のレスポンスを表すデータクラス"""
    status: str
    data: Optional[TreeVitalityBloomResult] = None


@dataclass
class TreeVitalityNoleafResult:
    """木の活力（葉無し時期）分析の結果を表すデータクラス"""
    vitality: int
    vitality_real: float
    vitality_probs: List[float]
    debug_image_key: Optional[str] = None


@dataclass
class TreeVitalityNoleafResponse:
    """木の活力（葉無し時期）分析のレスポンスを表すデータクラス"""
    status: str
    data: Optional[TreeVitalityNoleafResult] = None


class AIService:
    """
    AI分析サービスクラス

    REST API経由で画像分析サービスを呼び出すための機能を提供します。
    茎の分析、木の活力（開花時/葉無し時期）分析を行うメソッドを提供します。

    環境変数：
        AI_API_ENDPOINT: APIエンドポイントのベースURL（例: https://api.example.com）
    """

    def __init__(
        self,
        region_name: str = os.getenv("AWS_REGION", "ap-northeast-1"),
        endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL"),
        api_endpoint: str = os.getenv(
            "AI_API_ENDPOINT", '')
    ):
        self.api_endpoint = api_endpoint
        if not self.api_endpoint:
            logger.warning("AI_API_ENDPOINTが設定されていません")

        # APIパスの設定
        self.api_path_stem = "/analyze/image/stem"
        self.api_path_vitality_bloom = "/analyze/image/vitality/bloom"
        self.api_path_vitality_noleaf = "/analyze/image/vitality/noleaf"

        # S3関連の設定（S3からの画像取得などで必要な場合）
        self.region_name = region_name
        self.endpoint_url = endpoint_url

    async def analyze_stem(
        self,
        image_bytes: bytes,
        filename: str,
        can_bbox: Optional[BoundingBox],
        can_width_mm: Optional[float],
        output_bucket: str,
        output_key: str
    ) -> StemAnalysisResult:
        """
        茎分析用のAPIを呼び出し、結果を処理する

        Args:
            image_bytes: 分析する画像のバイトデータ
            filename: ファイル名（拡張子を含む）
            can_bbox: 缶のバウンディングボックス情報（BoundingBoxオブジェクト）
            can_width_mm: 缶の幅（mm単位）
            output_bucket: 結果画像を保存するS3バケット名
            output_key: 出力ファイルのキー

        Returns:
            StemAnalysisResult: 茎分析の結果

        Raises:
            ValueError: APIの呼び出しに失敗した場合
            ValueError: APIエンドポイントが設定されていない場合
        """
        if not self.api_endpoint:
            raise ValueError("AI_API_ENDPOINTが設定されていません")

        # APIに渡すデータを作成
        data = {
            'can_width_mm': str(can_width_mm) if can_width_mm is not None else None,
            'output_bucket': output_bucket,
            'output_key': output_key
        }

        # 缶のバウンディングボックス情報を個別のパラメータとして設定
        if can_bbox is not None:
            bbox_dict = can_bbox.to_dict()
            data['can_left'] = str(bbox_dict['left'])
            data['can_top'] = str(bbox_dict['top'])
            data['can_width'] = str(bbox_dict['width'])
            data['can_height'] = str(bbox_dict['height'])
            data['can_confidence'] = str(bbox_dict['confidence'])

        # APIを呼び出す
        response = await self._call_api_with_bytes(self.api_path_stem, data, image_bytes, filename)

        # APIからのレスポンスを解析
        if isinstance(response, dict) and 'status' in response and 'data' in response:
            result = response.get('data', {})
        else:
            # 古い形式のレスポンスの場合は、responseそのものがデータ
            result = response

        # 結果を解析してデータクラスで返す
        return StemAnalysisResult(
            diameter_mm=result.get('diameter_mm', 0.0),
            smoothness=result.get('smoothness', 0),
            smoothness_real=result.get('smoothness_real', 0.0),
            smoothness_probs=result.get('smoothness_probs', []),
            debug_image_key=result.get('debug_image_key')
        )

    async def analyze_tree_vitality_bloom(
        self,
        image_bytes: bytes,
        filename: str,
        output_bucket: str,
        output_key: str
    ) -> TreeVitalityBloomResult:
        """
        木の活力（開花時）分析用のAPIを呼び出し、結果を処理する

        Args:
            image_bytes: 分析する画像のバイトデータ
            filename: ファイル名（拡張子を含む）
            output_bucket: 結果画像を保存するS3バケット名
            output_key: 出力ファイルのキー

        Returns:
            TreeVitalityBloomResult: 木の活力分析の結果

        Raises:
            ValueError: APIの呼び出しに失敗した場合
            ValueError: APIエンドポイントが設定されていない場合
        """
        if not self.api_endpoint:
            raise ValueError("AI_API_ENDPOINTが設定されていません")

        # APIに渡すデータを作成
        data = {
            'output_bucket': output_bucket,
            'output_key': output_key
        }

        # APIを呼び出す
        response = await self._call_api_with_bytes(self.api_path_vitality_bloom, data, image_bytes, filename)

        # APIからのレスポンスを解析
        if isinstance(response, dict) and 'status' in response and 'data' in response:
            result = response.get('data', {})
        else:
            # 古い形式のレスポンスの場合は、responseそのものがデータ
            result = response

        # 結果を解析してデータクラスで返す
        return TreeVitalityBloomResult(
            vitality=result.get('vitality', 0),
            vitality_real=result.get('vitality_real', 0.0),
            vitality_probs=result.get('vitality_probs', []),
            debug_image_key=result.get('debug_image_key')
        )

    async def analyze_tree_vitality_noleaf(
        self,
        image_bytes: bytes,
        filename: str,
        output_bucket: str,
        output_key: str
    ) -> TreeVitalityNoleafResult:
        """
        木の活力（葉無し時期）分析用のAPIを呼び出し、結果を処理する

        Args:
            image_bytes: 分析する画像のバイトデータ
            filename: ファイル名（拡張子を含む）
            output_bucket: 結果画像を保存するS3バケット名
            output_key: 出力ファイルのキー

        Returns:
            TreeVitalityNoleafResult: 木の活力分析の結果

        Raises:
            ValueError: APIの呼び出しに失敗した場合
            ValueError: APIエンドポイントが設定されていない場合
        """
        if not self.api_endpoint:
            raise ValueError("AI_API_ENDPOINTが設定されていません")

        # APIに渡すデータを作成
        data = {
            'output_bucket': output_bucket,
            'output_key': output_key
        }

        # APIを呼び出す
        response = await self._call_api_with_bytes(self.api_path_vitality_noleaf, data, image_bytes, filename)

        # APIからのレスポンスを解析
        if isinstance(response, dict) and 'status' in response and 'data' in response:
            result = response.get('data', {})
        else:
            # 古い形式のレスポンスの場合は、responseそのものがデータ
            result = response

        # 結果を解析してデータクラスで返す
        return TreeVitalityNoleafResult(
            vitality=result.get('vitality', 0),
            vitality_real=result.get('vitality_real', 0.0),
            vitality_probs=result.get('vitality_probs', []),
            debug_image_key=result.get('debug_image_key')
        )

    async def _call_api_with_bytes(
        self,
        api_path: str,
        data: dict,
        image_bytes: bytes,
        filename: str
    ) -> dict:
        """
        REST APIを呼び出す共通メソッド（バイトデータを含めて送信）

        Args:
            api_path: APIのパス（/analyze/image/stemなど）
            data: APIに送信するデータ
            image_bytes: 送信する画像のバイトデータ
            filename: ファイル名（拡張子を含む）

        Returns:
            dict: APIの応答データ

        Raises:
            ValueError: APIの呼び出しに失敗した場合
        """
        url = f"{self.api_endpoint}{api_path}"

        # 空のデータを除外
        data = {k: v for k, v in data.items() if v is not None}

        try:
            # マルチパートフォームデータとして送信
            async with aiohttp.ClientSession() as session:
                # マルチパートフォームデータを作成
                form_data = aiohttp.FormData()

                # 各フィールドをフォームデータに追加
                for key, value in data.items():
                    form_data.add_field(key, value)

                # 画像バイトデータを追加
                content_type = self._get_content_type_from_filename(filename)
                form_data.add_field('file',
                                    image_bytes,
                                    filename=filename,
                                    content_type=content_type)

                # マルチパートフォームデータとして送信
                async with session.post(url, data=form_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"API呼び出しがエラーを返しました: ステータス {response.status}, {error_text}")
                        raise ValueError(
                            f"API呼び出しがエラーを返しました: ステータス {response.status}, {error_text}")

                    result = await response.json()
                    return result
        except aiohttp.ClientError as e:
            logger.error(f"API呼び出しに失敗しました: {e}")
            raise ValueError(f"API呼び出しに失敗しました: {e}")

    def _get_content_type_from_filename(self, filename: str) -> str:
        """ファイル名から適切なContent-Typeを取得する"""
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.jpg' or ext == '.jpeg':
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        elif ext == '.gif':
            return 'image/gif'
        elif ext == '.bmp':
            return 'image/bmp'
        elif ext == '.webp':
            return 'image/webp'
        else:
            return 'application/octet-stream'  # 不明な場合のデフォルト


# シングルトンパターンを実装
_ai_service_instance = None


def get_ai_service() -> AIService:
    """
    AI関連のサービスを取得する
    一度だけインスタンスを生成し、以降は同じインスタンスを再利用します
    """
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
