import json
import os
from dataclasses import dataclass
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
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
class TreeVitalityBloomResult:
    """木の活力（開花時）分析の結果を表すデータクラス"""
    vitality: int
    vitality_real: float
    vitality_probs: List[float]
    debug_image_key: Optional[str] = None


@dataclass
class TreeVitalityNoleafResult:
    """木の活力（葉無し時期）分析の結果を表すデータクラス"""
    vitality: int
    vitality_real: float
    vitality_probs: List[float]
    debug_image_key: str


class LambdaService:
    def __init__(
        self,
        region_name: str = os.getenv("AWS_REGION", "ap-northeast-1"),
        endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL"),
        analyze_stem_function_name: str = os.getenv(
            "LAMBDA_NAME_STEM", ''),
        analyze_tree_vitality_bloom_function_name: str = os.getenv(
            "LAMBDA_NAME_TREE_VITALITY_BLOOM", ''),
        analyze_tree_vitality_noleaf_function_name: str = os.getenv(
            "LAMBDA_NAME_TREE_VITALITY_NOLEAF", ''),
    ):
        self.lambda_client = boto3.client(
            'lambda',
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        self.analyze_stem_function_name = analyze_stem_function_name
        self.analyze_tree_vitality_bloom_function_name = analyze_tree_vitality_bloom_function_name
        self.analyze_tree_vitality_noleaf_function_name = analyze_tree_vitality_noleaf_function_name

    def analyze_stem(
        self,
        s3_bucket: str,
        s3_key: str,
        can_bbox: Optional[BoundingBox],
        output_bucket: str,
        output_key: str
    ) -> StemAnalysisResult:
        """
        茎分析用のLambda関数を呼び出し、結果を処理する

        Args:
            s3_bucket: 入力画像が格納されているS3バケット名
            s3_key: 入力画像のS3キー
            can_bbox: 缶のバウンディングボックス情報（BoundingBoxオブジェクト）
            output_bucket: 結果画像を保存するS3バケット名（省略時は入力バケットと同じ）
            output_prefix: 出力ファイルのプレフィックス

        Returns:
            StemAnalysisResult: 茎分析の結果

        Raises:
            ClientError: Lambda関数の呼び出しに失敗した場合
            ValueError: Lambdaからエラーレスポンスが返された場合
            ValueError: 分析用の関数名が設定されていない場合
        """
        if not self.analyze_stem_function_name:
            raise ValueError("茎分析用のLambda関数名が設定されていません")

        # BoundingBoxオブジェクトを辞書形式に変換（to_dict()メソッドを使用）
        can_bbox_payload = None
        if can_bbox is not None:
            bbox_dict = can_bbox.to_dict()

            # Lambda関数に必要なフィールドだけを含める
            can_bbox_payload = {
                'left': bbox_dict['left'],
                'top': bbox_dict['top'],
                'width': bbox_dict['width'],
                'height': bbox_dict['height'],
                'confidence': bbox_dict['confidence']
            }

        # Lambdaに渡すペイロードを作成
        payload = {
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'can_bbox': can_bbox_payload,
            'output_bucket': output_bucket,
            'output_key': output_key
        }

        # Lambda関数を呼び出す
        response = self.invoke_lambda(self.analyze_stem_function_name, payload)

        # レスポンスを処理
        if response.get('StatusCode') != 200:
            logger.error(f"Lambda関数がエラーを返しました: {response}")
            raise ValueError(f"Lambda関数がエラーを返しました: {response}")

        # レスポンスのペイロードを取得
        payload = response.get('Payload')
        if payload is None:
            raise ValueError("Lambda関数からペイロードが返されませんでした")

        payload_bytes = payload.read()
        result = json.loads(payload_bytes.decode('utf-8'))

        # エラーがあれば例外を発生
        if result.get('statusCode') != 200:
            error_message = json.loads(result.get(
                'body', '{}')).get('error', '不明なエラー')
            logger.error(f"Lambda関数の実行中にエラーが発生しました: {error_message}")
            raise ValueError(f"Lambda関数の実行中にエラーが発生しました: {error_message}")

        # 結果を解析してデータクラスで返す
        result_body = json.loads(result.get('body', '{}'))
        return StemAnalysisResult(
            diameter_mm=result_body.get('diameter_mm'),
            smoothness=result_body.get('smoothness'),
            smoothness_real=result_body.get('smoothness_real'),
            smoothness_probs=result_body.get('smoothness_probs'),
            debug_image_key=result_body.get('debug_image_key')
        )

    def analyze_tree_vitality_bloom(
        self,
        s3_bucket: str,
        s3_key: str,
        output_bucket: str,
        output_key: str
    ) -> TreeVitalityBloomResult:
        """
        木の活力（開花時）分析用のLambda関数を呼び出し、結果を処理する

        Args:
            s3_bucket: 入力画像が格納されているS3バケット名
            s3_key: 入力画像のS3キー
            can_bbox: 缶のバウンディングボックス情報（BoundingBoxオブジェクト、省略可）
            output_bucket: 結果画像を保存するS3バケット名（省略時は入力バケットと同じ）
            output_prefix: 出力ファイルのプレフィックス

        Returns:
            TreeVitalityBloomResult: 木の活力分析の結果

        Raises:
            ClientError: Lambda関数の呼び出しに失敗した場合
            ValueError: Lambdaからエラーレスポンスが返された場合
            ValueError: 分析用の関数名が設定されていない場合
        """
        if not self.analyze_tree_vitality_bloom_function_name:
            raise ValueError("木の活力（開花時）分析用のLambda関数名が設定されていません")

        # Lambdaに渡すペイロードを作成
        payload = {
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'output_bucket': output_bucket,
            'output_key': output_key
        }

        # Lambda関数を呼び出す
        response = self.invoke_lambda(
            self.analyze_tree_vitality_bloom_function_name, payload)

        # レスポンスを処理
        if response.get('StatusCode') != 200:
            logger.error(f"Lambda関数がエラーを返しました: {response}")
            raise ValueError(f"Lambda関数がエラーを返しました: {response}")

        # レスポンスのペイロードを取得
        payload = response.get('Payload')
        if payload is None:
            raise ValueError("Lambda関数からペイロードが返されませんでした")

        payload_bytes = payload.read()
        result = json.loads(payload_bytes.decode('utf-8'))

        print(result)

        # エラーがあれば例外を発生
        if result.get('statusCode') != 200:
            error_message = json.loads(result.get(
                'body', '{}')).get('error', '不明なエラー')
            logger.error(f"Lambda関数の実行中にエラーが発生しました: {error_message}")
            raise ValueError(f"Lambda関数の実行中にエラーが発生しました: {error_message}")

        # 結果を解析してデータクラスで返す
        result_body = json.loads(result.get('body', '{}'))
        return TreeVitalityBloomResult(
            vitality=result_body.get('vitality'),
            vitality_real=result_body.get('vitality_real'),
            vitality_probs=result_body.get('vitality_probs'),
            debug_image_key=result_body.get('debug_image_key')
        )

    def analyze_tree_vitality_noleaf(
        self,
        s3_bucket: str,
        s3_key: str,
        output_bucket: str,
        output_key: str
    ) -> TreeVitalityNoleafResult:
        """
        木の活力（葉無し時期）分析用のLambda関数を呼び出し、結果を処理する

        Args:
            s3_bucket: 入力画像が格納されているS3バケット名
            s3_key: 入力画像のS3キー
            can_bbox: 缶のバウンディングボックス情報（BoundingBoxオブジェクト、省略可）
            output_bucket: 結果画像を保存するS3バケット名（省略時は入力バケットと同じ）
            output_prefix: 出力ファイルのプレフィックス

        Returns:
            TreeVitalityNoleafResult: 木の活力分析の結果

        Raises:
            ClientError: Lambda関数の呼び出しに失敗した場合
            ValueError: Lambdaからエラーレスポンスが返された場合
            ValueError: 分析用の関数名が設定されていない場合
        """
        if not self.analyze_tree_vitality_noleaf_function_name:
            raise ValueError("木の活力（葉無し時期）分析用のLambda関数名が設定されていません")

        # Lambdaに渡すペイロードを作成
        payload = {
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'output_bucket': output_bucket,
            'output_key': output_key
        }

        # Lambda関数を呼び出す
        response = self.invoke_lambda(
            self.analyze_tree_vitality_noleaf_function_name, payload)

        # レスポンスを処理
        if response.get('StatusCode') != 200:
            logger.error(f"Lambda関数がエラーを返しました: {response}")
            raise ValueError(f"Lambda関数がエラーを返しました: {response}")

        # レスポンスのペイロードを取得
        payload = response.get('Payload')
        if payload is None:
            raise ValueError("Lambda関数からペイロードが返されませんでした")

        payload_bytes = payload.read()
        result = json.loads(payload_bytes.decode('utf-8'))

        # エラーがあれば例外を発生
        if result.get('statusCode') != 200:
            error_message = json.loads(result.get(
                'body', '{}')).get('error', '不明なエラー')
            logger.error(f"Lambda関数の実行中にエラーが発生しました: {error_message}")
            raise ValueError(f"Lambda関数の実行中にエラーが発生しました: {error_message}")

        # 結果を解析してデータクラスで返す
        result_body = json.loads(result.get('body', '{}'))
        return TreeVitalityNoleafResult(
            vitality=result_body.get('vitality'),
            vitality_real=result_body.get('vitality_real'),
            vitality_probs=result_body.get('vitality_probs'),
            debug_image_key=result_body.get('debug_image_key')
        )

    def invoke_lambda(
        self,
        function_name: str,
        payload: dict
    ) -> dict:
        """Lambda関数を呼び出す"""
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
        except ClientError as e:
            logger.error(f"Lambda関数の呼び出しに失敗しました: {e}")
            raise e
        else:
            return response


def get_lambda_service() -> LambdaService:
    return LambdaService()
