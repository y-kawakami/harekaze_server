"""ImageService のユニットテスト

S3 画像連携機能のテスト。
Requirements: 8.1-8.5
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_s3_client():
    """モック化された S3 クライアント"""
    return MagicMock()


@pytest.fixture
def image_service(mock_s3_client):
    """テスト用 ImageService（S3 クライアントをモック）"""
    with patch("boto3.client") as mock_client:
        mock_client.return_value = mock_s3_client
        from app.domain.services.image_service import ImageService

        service = ImageService(
            bucket_name="hrkz-prd-s3-contents",
            region_name="ap-northeast-1",
            endpoint_url=None,
            app_host="https://example.com",
        )
        service.s3_client = mock_s3_client
        return service


@pytest.mark.unit
class TestImageServiceGetImageUrl:
    """get_image_url メソッドのテスト"""

    def test_get_image_url_returns_correct_url(self, image_service):
        """正しい URL が生成される"""
        url = image_service.get_image_url("test/image.jpg")

        assert (
            url
            == "https://example.com/sakura_camera/media/trees/test/image.jpg"
        )

    def test_get_image_url_empty_key_returns_empty_string(self, image_service):
        """空のオブジェクトキーの場合は空文字を返す"""
        url = image_service.get_image_url("")

        assert url == ""

    def test_get_image_url_none_key_returns_empty_string(self, image_service):
        """None のオブジェクトキーの場合は空文字を返す"""
        url = image_service.get_image_url(None)

        assert url == ""


@pytest.mark.unit
class TestImageServiceGetPresignedUrl:
    """get_presigned_url メソッドのテスト"""

    def test_get_presigned_url_returns_signed_url(
        self, image_service, mock_s3_client
    ):
        """署名付き URL が生成される"""
        mock_s3_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/bucket/key?signature=xxx"
        )

        url = image_service.get_presigned_url("test/image.jpg")

        assert url == "https://s3.amazonaws.com/bucket/key?signature=xxx"
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "hrkz-prd-s3-contents",
                "Key": "sakura_camera/media/trees/test/image.jpg",
            },
            ExpiresIn=3600,
        )

    def test_get_presigned_url_custom_expiry(
        self, image_service, mock_s3_client
    ):
        """有効期限をカスタム指定できる"""
        mock_s3_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/bucket/key?signature=xxx"
        )

        image_service.get_presigned_url("test/image.jpg", expires_in=7200)

        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "hrkz-prd-s3-contents",
                "Key": "sakura_camera/media/trees/test/image.jpg",
            },
            ExpiresIn=7200,
        )

    def test_get_presigned_url_empty_key_returns_empty_string(
        self, image_service
    ):
        """空のオブジェクトキーの場合は空文字を返す"""
        url = image_service.get_presigned_url("")

        assert url == ""

    def test_get_presigned_url_none_key_returns_empty_string(
        self, image_service
    ):
        """None のオブジェクトキーの場合は空文字を返す"""
        url = image_service.get_presigned_url(None)

        assert url == ""

    def test_get_presigned_url_client_error_returns_empty_string(
        self, image_service, mock_s3_client
    ):
        """S3 クライアントエラー時は空文字を返す"""
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey"}},
            operation_name="generate_presigned_url",
        )

        url = image_service.get_presigned_url("nonexistent/image.jpg")

        assert url == ""


@pytest.mark.unit
class TestImageServiceFullObjectKey:
    """get_full_object_key メソッドのテスト"""

    def test_get_full_object_key_returns_correct_path(self, image_service):
        """正しいフルパスが生成される"""
        key = image_service.get_full_object_key("test/image.jpg")

        assert key == "sakura_camera/media/trees/test/image.jpg"

    def test_get_full_object_key_s3_path_format(self, image_service):
        """S3 パス形式が正しい（Requirements 8.2）"""
        key = image_service.get_full_object_key("abc123.jpg")

        assert key == "sakura_camera/media/trees/abc123.jpg"


@pytest.mark.unit
class TestImageServiceBucketName:
    """get_contents_bucket_name メソッドのテスト"""

    def test_get_contents_bucket_name_returns_bucket(self, image_service):
        """バケット名を取得できる（Requirements 8.1）"""
        bucket = image_service.get_contents_bucket_name()

        assert bucket == "hrkz-prd-s3-contents"
