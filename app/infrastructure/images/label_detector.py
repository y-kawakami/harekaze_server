import io
from typing import (Any, Dict, List, Optional, Set, Tuple, TypedDict, Union,
                    cast)

import aioboto3
from botocore.exceptions import ClientError
from PIL import Image

from app.domain.models.bounding_box import BoundingBox


# Rekognitionのレスポンス型の代替定義
class BoundingBoxDict(TypedDict, total=False):
    Width: float
    Height: float
    Left: float
    Top: float


class InstanceDict(TypedDict, total=False):
    BoundingBox: BoundingBoxDict
    Confidence: float


class LabelDict(TypedDict, total=False):
    Name: str
    Confidence: float
    Instances: List[InstanceDict]


class RekognitionResponseDict(TypedDict, total=False):
    Labels: List[LabelDict]


class LabelDetector:
    """
    AWS Rekognitionのラベル検出機能を使用して、
    画像内の特定ラベル（人物、缶など）のバウンディングボックスを検出するクラス
    """

    def __init__(self, min_confidence: float = 50.0):
        """
        初期化メソッド

        Args:
            min_confidence (float): ラベル検出の最小信頼度閾値（0〜100）
        """
        self.min_confidence = min_confidence

        # Rekognitionクライアントの初期化はここで行わず、必要時に初期化
        self._rekognition_client = None
        self._session = None

    async def _get_rekognition_client(self):
        """
        AWS Rekognitionクライアントを取得する（必要に応じて初期化）

        Returns:
            aioboto3.client: Rekognitionクライアント
        """
        if self._session is None:
            self._session = aioboto3.Session()

        if self._rekognition_client is None:
            self._rekognition_client = self._session.client(
                'rekognition', region_name='ap-northeast-1')

        return self._rekognition_client

    async def detect(self, pil_image: Image.Image, target_labels: List[str], max_labels: int = 100) -> Dict[str, List[BoundingBox]]:
        """
        PIL画像を入力として、AWS Rekognitionを使用して指定されたラベル検出を行う

        Args:
            pil_image (PIL.Image.Image): 検出対象の画像
            target_labels (List[str]): 検出対象のラベル名のリスト
            max_labels (int, optional): 検出する最大ラベル数。デフォルトは100

        Returns:
            Dict[str, List[BoundingBox]]: ラベル名をキー、バウンディングボックスのリストを値とする辞書
        """
        # 大文字小文字の違いを吸収するため、ラベル名を小文字に変換して内部的に保持
        target_labels_lower: Set[str] = {
            label.lower() for label in target_labels}

        # PIL画像をバイトストリームに変換
        img_byte_arr = io.BytesIO()
        pil_image.save(
            img_byte_arr, format=pil_image.format if pil_image.format else 'JPEG')
        img_bytes = img_byte_arr.getvalue()

        try:
            # Rekognitionクライアントを取得
            async with await self._get_rekognition_client() as rekognition:
                # Rekognition APIを呼び出して画像分析
                response = await rekognition.detect_labels(
                    Image={'Bytes': img_bytes},
                    MaxLabels=max_labels,
                    Features=['GENERAL_LABELS']  # 一般的なラベル検出
                )

                # 指定されたラベルのバウンディングボックスを抽出
                return self.extract_label_bounding_boxes(cast(Dict[str, Any], response), target_labels, target_labels_lower)

        except ClientError as e:
            # エラーハンドリング
            print(f"AWS Rekognition APIエラー: {e}")
            return {label: [] for label in target_labels}
        except Exception as e:
            # その他のエラー
            print(f"予期しないエラー: {e}")
            return {label: [] for label in target_labels}

    def extract_label_bounding_boxes(self, response: Dict[str, Any], target_labels: List[str], target_labels_lower: Set[str]) -> Dict[str, List[BoundingBox]]:
        """
        AWS Rekognitionのレスポンスから指定されたラベルのバウンディングボックス情報を抽出する

        Args:
            response (Dict[str, Any]): AWS Rekognitionのレスポンス
            target_labels (List[str]): 検出対象のラベル名のリスト
            target_labels_lower (Set[str]): 小文字に変換した検出対象のラベル名のセット

        Returns:
            Dict[str, List[BoundingBox]]: ラベル名をキー、バウンディングボックスのリストを値とする辞書
        """
        results: Dict[str, List[BoundingBox]] = {}

        # レスポンス内のラベルを検索
        for label in response.get("Labels", []):
            label_name = label["Name"]

            # ターゲットラベルかどうかを確認（大文字小文字を区別しない）
            label_name_lower = label_name.lower()
            if label_name_lower in target_labels_lower:
                # 元のケースでのラベル名を取得（表示用）
                original_label = next(
                    label for label in target_labels if label.lower() == label_name_lower)

                results[original_label] = []

                # 該当ラベルの全インスタンスに対して
                for instance in label.get("Instances", []):
                    confidence = instance.get("Confidence", 0)

                    # 信頼度が閾値以上の場合のみ追加
                    if confidence >= self.min_confidence:
                        bbox_dict = instance.get("BoundingBox", {})
                        bbox = BoundingBox.from_dict(
                            cast(Dict[str, Any], bbox_dict), confidence)
                        results[original_label].append(bbox)

        # 各ラベルごとに信頼度の高い順にソート
        for label in results:
            results[label].sort(key=lambda x: x.confidence, reverse=True)

        return results

    async def detect_labels(self, rekognition_response: Dict[str, Any], target_labels: List[str]) -> Dict[str, List[BoundingBox]]:
        """
        AWS Rekognitionのレスポンスから指定されたラベルを検出する

        Args:
            rekognition_response (Dict[str, Any]): AWS Rekognitionのレスポンス
            target_labels (List[str]): 検出対象のラベル名のリスト

        Returns:
            Dict[str, List[BoundingBox]]: ラベル名をキー、バウンディングボックスのリストを値とする辞書
        """
        target_labels_lower: Set[str] = {
            label.lower() for label in target_labels}
        return self.extract_label_bounding_boxes(rekognition_response, target_labels, target_labels_lower)

    def format_bounding_boxes(self,
                              bboxes: Union[List[BoundingBox], Dict[str, List[BoundingBox]]],
                              image_width: Optional[int] = None,
                              image_height: Optional[int] = None) -> Union[List[Tuple], Dict[str, List[Tuple]]]:
        """
        バウンディングボックスのリストを別のフォーマットに変換する
        画像の幅と高さが指定された場合、絶対座標に変換

        Args:
            bboxes (Union[List[BoundingBox], Dict[str, List[BoundingBox]]]):
                バウンディングボックスのリスト、またはラベル名をキー、バウンディングボックスのリストを値とする辞書
            image_width (Optional[int]): 元画像の幅
            image_height (Optional[int]): 元画像の高さ

        Returns:
            Union[List[Tuple], Dict[str, List[Tuple]]]:
                変換されたバウンディングボックス情報のリスト、またはラベル名をキーとする辞書
                各要素は (x1, y1, x2, y2, confidence) の形式
        """
        if isinstance(bboxes, dict):
            # 辞書の場合は各ラベルごとに処理
            result: Dict[str, List[Tuple]] = {}
            for label, bbox_list in bboxes.items():
                result[label] = self._format_bbox_list(
                    bbox_list, image_width, image_height)
            return result
        else:
            # リストの場合はそのまま処理
            return self._format_bbox_list(bboxes, image_width, image_height)

    def _format_bbox_list(self,
                          bboxes: List[BoundingBox],
                          image_width: Optional[int] = None,
                          image_height: Optional[int] = None) -> List[Tuple]:
        """
        バウンディングボックスのリストを別のフォーマットに変換する（内部ヘルパーメソッド）

        Args:
            bboxes (List[BoundingBox]): バウンディングボックスのリスト
            image_width (Optional[int]): 元画像の幅
            image_height (Optional[int]): 元画像の高さ

        Returns:
            List[Tuple]: 変換されたバウンディングボックス情報のリスト
                各要素は (x1, y1, x2, y2, confidence) の形式
        """
        formatted_boxes = []

        for bbox in bboxes:
            corners = bbox.to_corners(image_width, image_height)
            formatted_boxes.append((*corners, bbox.confidence))

        return formatted_boxes


async def get_label_detector() -> LabelDetector:
    """LabelDetectorのインスタンスを取得する"""
    return LabelDetector()
