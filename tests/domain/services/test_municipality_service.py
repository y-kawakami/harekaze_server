import pytest

from app.domain.services.municipality_service import MunicipalityService


@pytest.mark.unit
class TestMunicipalityService:
    @pytest.fixture
    def service(self):
        return MunicipalityService()

    def test_get_prefecture_code(self, service):
        """都道府県名から都道府県コードを取得できることを確認"""
        assert service.get_prefecture_code("東京都") == "13"
        assert service.get_prefecture_code("北海道") == "01"
        assert service.get_prefecture_code("大阪府") == "27"
        assert service.get_prefecture_code("存在しない県") is None

    def test_find_municipality_shibuya(self, service):
        """東京都渋谷区の住所から市区町村を特定できることを確認"""
        result = service.find_municipality("東京都渋谷区代々木")
        assert result is not None
        assert result.code == "131130"
        assert result.jititai == "渋谷区"

    def test_find_municipality_kawasaki(self, service):
        """神奈川県川崎市の住所から市区町村を特定できることを確認"""
        result = service.find_municipality("神奈川県川崎市麻生区百合ヶ丘2-9-3")
        assert result is not None
        assert result.code == "141305"
        assert result.jititai == "川崎市"

    def test_find_municipality_not_found(self, service):
        """存在しない住所の場合はNoneが返されることを確認"""
        result = service.find_municipality("存在しない住所")
        assert result is None
