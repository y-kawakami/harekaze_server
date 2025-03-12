import io
import os
import random
from typing import Optional, Tuple

import aioboto3
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from loguru import logger
from PIL import Image

# .envファイルを読み込む
load_dotenv()


TREE_IMAGE_PREFIX = "sakura_camera/media/trees"


class ImageService:
    def __init__(
        self,
        bucket_name: str = os.getenv("S3_CONTENTS_BUCKET", "kkcraft-samples"),
        region_name: str = os.getenv("AWS_REGION", "ap-northeast-1"),
        endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL"),
        app_host: str | None = os.getenv("APP_HOST"),
    ):
        self.s3_client = boto3.client(
            's3',
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        if not self.bucket_name:
            raise ValueError(
                "S3_CONTENTS_BUCKET environment variable is not set")
        self.app_host = app_host
        self._async_s3_client = None

    async def get_async_s3_client(self):
        """非同期S3クライアントを取得する（遅延初期化）"""
        if self._async_s3_client is None:
            self._async_s3_client = aioboto3.Session().client(
                's3',
                region_name=self.region_name,
                endpoint_url=self.endpoint_url
            )
        return self._async_s3_client

    def create_thumbnail_from_pil(self, image: Image.Image) -> bytes:
        # アスペクト比を保持しながらリサイズ
        thumb = image.copy()
        thumb.thumbnail((540, 960))
        thumb_io = io.BytesIO()
        thumb.save(thumb_io, format=image.format if image.format else 'JPEG')
        return thumb_io.getvalue()

    def bytes_to_pil(self, image_data: bytes) -> Image.Image:
        """バイナリデータをPILの画像に変換する"""
        return Image.open(io.BytesIO
                          (image_data))

    def pil_to_bytes(self, image: Image.Image, format: Optional[str]) -> bytes:
        """PILの画像をバイナリデータに変換する"""
        image_io = io.BytesIO()
        image.save(image_io, format=format if format else image.format)
        return image_io.getvalue()

    def create_thumbnail(self, image_data: bytes) -> bytes:
        """画像データからサムネイルを作成する"""
        image = Image.open(io.BytesIO(image_data))
        # アスペクト比を保持しながらリサイズ
        image.thumbnail((540, 960))
        thumb_io = io.BytesIO()
        image.save(thumb_io, format=image.format if image.format else 'JPEG')
        return thumb_io.getvalue()

    async def upload_image(self, image_data: bytes, object_key: str) -> bool:
        """画像をS3にアップロードする（非同期版）"""
        try:
            async with aioboto3.Session().client(
                's3',
                region_name=self.region_name,
                endpoint_url=self.endpoint_url
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=f'{TREE_IMAGE_PREFIX}/{object_key}',
                    Body=image_data,
                    ContentType='image/jpeg',
                    # ACL='public-read'
                )
            return True
        except ClientError as e:
            logger.error(f"Upload Image Client Error (Async): {e}")
            logger.exception(e)
            return False

    def get_contents_bucket_name(self) -> str:
        return self.bucket_name

    def get_full_object_key(self, object_key: str) -> str:
        return f'{TREE_IMAGE_PREFIX}/{object_key}'

    def get_image_url(self, object_key: str) -> str:
        """画像のURLを取得する"""
        if not object_key:
            return ""
        return f'{self.app_host}/{TREE_IMAGE_PREFIX}/{object_key}'
        # return f"https://{self.bucket_name}.s3.ap-northeast-1.amazonaws.com/{TREE_IMAGE_PREFIX}/{object_key}"

    def get_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        署名付きURLを取得する
        Args:
            object_key: S3のオブジェクトキー
            expires_in: 有効期限（秒）。デフォルトは1時間
        Returns:
            署名付きURL
        """
        if not object_key:
            return ""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': f'{TREE_IMAGE_PREFIX}/{object_key}'
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError:
            return ""

    def analyze_tree_vitality(self, image_data: bytes) -> Tuple[int, bool]:
        """
        桜の木の画像から元気度を分析する
        Returns:
            Tuple[float, bool]: (元気度, 木が検出できたかどうか)
        Note:
            現状はモック実装
        """
        # TODO: 実際の画像解析モデルを実装
        return random.randint(1, 5), True

    # def analyze_stem(self, image_data: bytes) -> Tuple[bool, int, bool, float]:
    #    """
    #    幹の画像から情報を分析する
    #    Returns:
    #        Tuple[bool, int, bool, float]:
    #            (幹が検出できたか, 幹の模様スコア, 缶が検出できたか, 推定樹齢)
    #    Note:
    #        現状はモック実装
    #    """
    #    # TODO: 実際の画像解析モデルを実装
    #    return True, 3, True, 45.0

    def analyze_stem_image(self, image_data: bytes) -> Tuple[int, bool, Optional[float], int]:
        """幹の写真を解析する"""
        # TODO: 解析処理を実装する
        smoothness = random.randint(1, 5)
        can_detected = bool(random.getrandbits(1))
        diameter_mm = random.uniform(10, 40) if can_detected else None
        age = random.randint(10, 100)
        return smoothness, can_detected, diameter_mm, age

    async def delete_image(self, object_key: str) -> bool:
        """S3から画像を削除する（非同期版）"""
        try:
            async with aioboto3.Session().client(
                's3',
                region_name=self.region_name,
                endpoint_url=self.endpoint_url
            ) as s3_client:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=f'{TREE_IMAGE_PREFIX}/{object_key}'
                )
            return True
        except ClientError as e:
            logger.error(f"Delete Image Client Error (Async): {e}")
            logger.exception(e)
            return False

    def resize_pil_image(self, image: Image.Image, max_size: int) -> Image.Image:
        """
        PILイメージを長辺がmax_sizeになるようにリサイズする

        Args:
            image (Image.Image): リサイズする元の画像
            max_size (int): 長辺の最大サイズ（ピクセル）

        Returns:
            Image.Image: リサイズされた画像
        """
        width, height = image.size

        # 既に指定サイズ以下の場合はそのまま返す
        if width <= max_size and height <= max_size:
            return image

        # 長辺を基準にアスペクト比を維持してリサイズ
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def get_image_service() -> "ImageService":
    """画像サービスのインスタンスを取得する"""
    return ImageService()
