import pytest
from dotenv import load_dotenv

from app.domain.services.municipality_service import MunicipalityService
from app.infrastructure.geocoding.geocoding_service import (Address,
                                                            GeocodingService)


@pytest.mark.unit
class TestGeocodingService:
    @pytest.fixture
    def municipality_service(self):
        """実際のMunicipalityServiceインスタンスを使用"""
        return MunicipalityService()

    @pytest.fixture
    def service(self, municipality_service):
        """実際のGeocodingServiceを使用"""
        load_dotenv()  # .envファイルから環境変数を読み込む
        return GeocodingService(municipality_service)

    def test_get_address_shibuya(self, service):
        """正常系: 渋谷の緯度経度から住所情報を取得できることを確認"""
        # 渋谷スクランブル交差点付近の座標
        result = service.get_address(35.6580, 139.7016)

        # 検証
        assert isinstance(result, Address)
        assert result.country == "日本"
        assert result.prefecture == "東京都"
        assert result.prefecture_code == "13"
        assert result.municipality == "渋谷区"
        assert result.municipality_code == "131130"
        assert result.detail is not None
        assert "東京都渋谷区" in result.detail

    def test_get_address_kawasaki(self, service):
        """正常系: 川崎の緯度経度から住所情報を取得できることを確認"""
        # 川崎市麻生区の座標
        result = service.get_address(35.6027, 139.5168)

        # 検証
        assert isinstance(result, Address)
        assert result.country == "日本"
        assert result.prefecture == "神奈川県"
        assert result.prefecture_code == "14"
        assert result.municipality == "川崎市"
        assert result.municipality_code == "141305"
        assert result.detail is not None
        assert "神奈川県川崎市" in result.detail

    def test_get_address_invalid_location(self, service):
        """異常系: 無効な座標の場合"""
        # 明らかに無効な座標（太平洋の真ん中）
        result = service.get_address(0.0, -160.0)

        assert isinstance(result, Address)
        assert result.country is None
        assert result.prefecture is None
        assert result.prefecture_code is None
        assert result.municipality is None
        assert result.municipality_code is None
        assert result.detail is None
