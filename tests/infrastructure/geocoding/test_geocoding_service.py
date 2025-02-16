from unittest.mock import Mock

import pytest

from app.infrastructure.geocoding.geocoding_service import (Address,
                                                            GeocodingService)


@pytest.mark.unit
class TestGeocodingService:
    @pytest.fixture
    def mock_gmaps_client(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_municipality_service, mock_gmaps_client, monkeypatch):
        """環境変数とGoogle Maps APIをモック化したGeocodingServiceを作成"""
        monkeypatch.setenv('GEOCODING_API_KEY', 'dummy_api_key')
        service = GeocodingService(mock_municipality_service)
        service.client = mock_gmaps_client
        return service

    def test_get_address_success(self, service, mock_gmaps_client, mock_municipality_service):
        """正常系: 緯度経度から住所情報を取得できることを確認"""
        # Google Maps APIのモックレスポンスを設定
        mock_gmaps_client.reverse_geocode.return_value = [{
            'address_components': [
                {'long_name': '日本', 'types': ['country']},
                {'long_name': '東京都', 'types': ['administrative_area_level_1']},
                {'long_name': '渋谷区', 'types': ['locality']},
                {'long_name': '代々木', 'types': ['sublocality_level_1']}
            ]
        }]

        # MunicipalityServiceのモックレスポンスを設定
        mock_municipality = Mock()
        mock_municipality.code = "13113"
        mock_municipality.jititai = "渋谷区"
        mock_municipality_service.find_municipality.return_value = mock_municipality
        mock_municipality_service.get_prefecture_code.return_value = "13"

        # テスト実行
        result = service.get_address(35.6580, 139.7016)

        # 検証
        assert isinstance(result, Address)
        assert result.country == "日本"
        assert result.prefecture == "東京都"
        assert result.prefecture_code == "13"
        assert result.municipality == "渋谷区"
        assert result.municipality_code == "13113"
        assert result.detail is not None and "東京都渋谷区代々木" in result.detail

    def test_get_address_api_error(self, service, mock_gmaps_client):
        """異常系: API呼び出しでエラーが発生した場合"""
        mock_gmaps_client.reverse_geocode.side_effect = Exception("API Error")

        result = service.get_address(35.6580, 139.7016)

        assert isinstance(result, Address)
        assert result.country is None
        assert result.prefecture is None
        assert result.prefecture_code is None
        assert result.municipality is None
        assert result.municipality_code is None
        assert result.detail is None

    def test_get_address_no_results(self, service, mock_gmaps_client):
        """異常系: 結果が空の場合"""
        mock_gmaps_client.reverse_geocode.return_value = []

        result = service.get_address(35.6580, 139.7016)

        assert isinstance(result, Address)
        assert result.country is None
        assert result.prefecture is None
        assert result.prefecture_code is None
        assert result.municipality is None
        assert result.municipality_code is None
        assert result.detail is None
