import io
import os
from typing import Tuple

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image

# .envファイルを読み込む
load_dotenv()


class ImageService:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket_name = os.getenv("S3_ASSETS_BUCKET")
        if not self.bucket_name:
            raise ValueError(
                "S3_ASSETS_BUCKET environment variable is not set")

    def create_thumbnail(self, image_data: bytes) -> bytes:
        """画像データからサムネイルを作成する"""
        image = Image.open(io.BytesIO(image_data))
        # アスペクト比を保持しながらリサイズ
        image.thumbnail((540, 960))
        thumb_io = io.BytesIO()
        image.save(thumb_io, format=image.format)
        return thumb_io.getvalue()

    def upload_image(self, image_data: bytes, object_key: str) -> bool:
        """画像をS3にアップロードする"""
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=image_data,
                ContentType='image/jpeg'
            )
            return True
        except ClientError:
            return False

    def get_image_url(self, object_key: str) -> str:
        """画像のURLを取得する"""
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=3600  # 1時間有効
            )
            return url
        except ClientError:
            return ""

    def analyze_tree_vitality(self, image_data: bytes) -> Tuple[float, bool]:
        """
        桜の木の画像から元気度を分析する
        Returns:
            Tuple[float, bool]: (元気度, 木が検出できたかどうか)
        Note:
            現状はモック実装
        """
        # TODO: 実際の画像解析モデルを実装
        return 4.2, True

    def analyze_stem(self, image_data: bytes) -> Tuple[bool, int, bool, float]:
        """
        幹の画像から情報を分析する
        Returns:
            Tuple[bool, int, bool, float]:
                (幹が検出できたか, 幹の模様スコア, 缶が検出できたか, 推定樹齢)
        Note:
            現状はモック実装
        """
        # TODO: 実際の画像解析モデルを実装
        return True, 3, True, 45.0
