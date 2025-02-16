import pytest
from fastapi import status

from app.infrastructure.geocoding.geocoding_service import Address


@pytest.mark.api
class TestTreeAPI:
    def test_create_tree_success(
        self,
        client,
        mock_current_user,
        mock_geocoding_service,
        mock_image_service,
        test_image_data
    ):
        """正常系: 桜の木の写真を登録できることを確認"""
        # モックの設定
        mock_geocoding_service.get_address.return_value = Address(
            country="日本",
            prefecture="東京都",
            prefecture_code="13",
            municipality="渋谷区",
            municipality_code="13113",
            detail="東京都渋谷区代々木"
        )

        # リクエストデータの準備
        files = {
            'image': ('test.jpg', test_image_data, 'image/jpeg')
        }
        data = {
            'latitude': 35.6580,
            'longitude': 139.7016,
            'contributor': 'テスト太郎'
        }

        # テスト実行
        response = client.post("/api/tree/entire", files=files, data=data)

        # レスポンスの検証
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['prefecture'] == "東京都"
        assert response_data['municipality'] == "渋谷区"

    def test_create_tree_invalid_location(
        self,
        client,
        mock_current_user,
        mock_geocoding_service,
        mock_image_service,
        test_image_data
    ):
        """異常系: 無効な位置情報の場合"""
        # モックの設定
        mock_geocoding_service.get_address.return_value = Address(
            None, None, None, None, None, None
        )

        # リクエストデータの準備
        files = {
            'image': ('test.jpg', test_image_data, 'image/jpeg')
        }
        data = {
            'latitude': 0.0,  # 無効な緯度
            'longitude': 0.0,  # 無効な経度
            'contributor': 'テスト太郎'
        }

        # テスト実行
        response = client.post("/api/tree/entire", files=files, data=data)

        # レスポンスの検証
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("missing_field", ['latitude', 'longitude', 'image', 'contributor'])
    def test_create_tree_missing_required_field(
        self,
        client,
        mock_current_user,
        mock_geocoding_service,
        mock_image_service,
        test_image_data,
        missing_field
    ):
        """異常系: 必須フィールドが欠けている場合"""
        # リクエストデータの準備
        files = {
            'image': ('test.jpg', test_image_data, 'image/jpeg')
        }
        data = {
            'latitude': 35.6580,
            'longitude': 139.7016,
            'contributor': 'テスト太郎'
        }

        # 指定されたフィールドを削除
        if missing_field == 'image':
            files.pop('image')
        else:
            data.pop(missing_field)

        # テスト実行
        response = client.post("/api/tree/entire", files=files, data=data)

        # レスポンスの検証
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
