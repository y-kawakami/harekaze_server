"""BloomStateService のテスト

BloomStateService の8段階開花状態判定ロジックをテストする。
Requirements: 1.1-1.13
"""

import pytest
from datetime import date
from unittest.mock import patch

from app.domain.services.bloom_state_service import (
    BloomStateService,
    BLOOM_STATUS_LABELS,
    PrefectureOffsets,
    get_bloom_state_service,
)


@pytest.mark.unit
class TestBloomStatusLabels:
    """BLOOM_STATUS_LABELS の定義テスト (Req 1.1)"""

    def test_all_8_statuses_defined(self):
        """8つのステータスが定義されていること"""
        expected_statuses = [
            "before_bloom",
            "blooming",
            "30_percent",
            "50_percent",
            "full_bloom",
            "falling",
            "with_leaves",
            "leaves_only",
        ]
        assert set(BLOOM_STATUS_LABELS.keys()) == set(expected_statuses)

    def test_labels_are_japanese(self):
        """ラベルが日本語であること"""
        assert BLOOM_STATUS_LABELS["before_bloom"] == "開花前"
        assert BLOOM_STATUS_LABELS["blooming"] == "開花"
        assert BLOOM_STATUS_LABELS["30_percent"] == "3分咲き"
        assert BLOOM_STATUS_LABELS["50_percent"] == "5分咲き"
        assert BLOOM_STATUS_LABELS["full_bloom"] == "8分咲き（満開）"
        assert BLOOM_STATUS_LABELS["falling"] == "散り始め"
        assert BLOOM_STATUS_LABELS["with_leaves"] == "花＋若葉（葉桜）"
        assert BLOOM_STATUS_LABELS["leaves_only"] == "葉のみ"


@pytest.mark.unit
class TestPrefectureOffsets:
    """PrefectureOffsets データクラスのテスト (Req 1.3)"""

    def test_create_offsets(self):
        """オフセット値を持つインスタンスを作成できること"""
        offsets = PrefectureOffsets(
            flowering_to_3bu=2,
            flowering_to_5bu=3,
            end_to_hanawakaba=5,
            end_to_hanomi=10,
        )
        assert offsets.flowering_to_3bu == 2
        assert offsets.flowering_to_5bu == 3
        assert offsets.end_to_hanawakaba == 5
        assert offsets.end_to_hanomi == 10


@pytest.mark.unit
class TestBloomStateServiceCSVParsing:
    """BloomStateService の CSV 読み込みテスト (Req 1.2)"""

    def test_load_csv_and_get_prefecture_offsets(self):
        """CSVを読み込み、都道府県別オフセットを取得できること"""
        service = BloomStateService()

        # 青森県（02）のオフセットを取得
        offsets = service.get_prefecture_offsets("02")
        assert offsets is not None
        # 青森県データ: 開花4/17, 3分咲き4/19, 5分咲き4/20, 満開4/22, 散り始め4/27, 花＋若葉5/2, 葉のみ5/7
        # flowering_to_3bu = 4/19 - 4/17 = 2日
        assert offsets.flowering_to_3bu == 2
        # flowering_to_5bu = 4/20 - 4/17 = 3日
        assert offsets.flowering_to_5bu == 3
        # 散り始め4/27 -> 花＋若葉5/2: end_to_hanawakaba = 5/2 - 4/27 = 5日
        assert offsets.end_to_hanawakaba == 5
        # 散り始め4/27 -> 葉のみ5/7: end_to_hanomi = 5/7 - 4/27 = 10日
        assert offsets.end_to_hanomi == 10

    def test_okinawa_returns_none(self):
        """沖縄県（47）はデータがないため None を返すこと (Req 1.13)"""
        service = BloomStateService()
        offsets = service.get_prefecture_offsets("47")
        assert offsets is None

    def test_unknown_prefecture_returns_none(self):
        """存在しない都道府県コードは None を返すこと (Req 1.13)"""
        service = BloomStateService()
        offsets = service.get_prefecture_offsets("99")
        assert offsets is None


@pytest.mark.unit
class TestBloomStateServiceCalculation:
    """BloomStateService の開花状態計算テスト (Req 1.4-1.11)"""

    @pytest.fixture
    def service_with_mock(self):
        """FloweringDateServiceをモックしたBloomStateServiceを作成"""
        service = BloomStateService()
        return service

    def test_before_bloom(self, service_with_mock):
        """開花予想日より前は「開花前」を返すこと (Req 1.4)"""
        service = service_with_mock

        # 青森県の開花予想日を4/17とモック
        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),  # 開花予想日
                date(2025, 4, 22),  # 満開開始予想日
                date(2025, 4, 26),  # 満開終了予想日
            )

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 16),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "before_bloom"

    def test_blooming(self, service_with_mock):
        """開花日から3分咲きオフセット-1日までは「開花」を返すこと (Req 1.5)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 青森県のオフセット: flowering_to_3bu = 2
            # 開花日4/17から4/18(4/17+2-1)まで「開花」

            # 開花日当日
            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 17),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "blooming"

            # 開花日+1日
            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 18),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "blooming"

    def test_30_percent(self, service_with_mock):
        """3分咲き期間は「3分咲き」を返すこと (Req 1.6)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 青森県: flowering_to_3bu=2, flowering_to_5bu=3
            # 3分咲き期間: 4/17+2 = 4/19（1日間）

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 19),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "30_percent"

    def test_50_percent(self, service_with_mock):
        """5分咲き期間は「5分咲き」を返すこと (Req 1.7)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 青森県: flowering_to_5bu=3, 満開開始4/22
            # 5分咲き期間: 4/17+3=4/20 から 4/21（満開開始-1）まで

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 20),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "50_percent"

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 21),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "50_percent"

    def test_full_bloom(self, service_with_mock):
        """満開期間は「8分咲き（満開）」を返すこと (Req 1.8)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 満開期間: 4/22 から 4/25（満開終了-1）まで

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 22),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "full_bloom"

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 25),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "full_bloom"

    def test_falling(self, service_with_mock):
        """散り始め期間は「散り始め」を返すこと (Req 1.9)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 青森県: end_to_hanawakaba=5
            # 散り始め期間: 4/26 から 4/30（4/26+5-1）まで

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 26),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "falling"

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 30),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "falling"

    def test_with_leaves(self, service_with_mock):
        """花＋若葉期間は「花＋若葉（葉桜）」を返すこと (Req 1.10)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 青森県: end_to_hanawakaba=5, end_to_hanomi=10
            # 花＋若葉期間: 5/1（4/26+5）から 5/5（4/26+10-1）まで

            result = service.calculate_bloom_status(
                photo_date=date(2025, 5, 1),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "with_leaves"

            result = service.calculate_bloom_status(
                photo_date=date(2025, 5, 5),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "with_leaves"

    def test_leaves_only(self, service_with_mock):
        """葉のみ期間は「葉のみ」を返すこと (Req 1.11)"""
        service = service_with_mock

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (
                date(2025, 4, 17),
                date(2025, 4, 22),
                date(2025, 4, 26),
            )
            # 青森県: end_to_hanomi=10
            # 葉のみ: 5/6（4/26+10）以降

            result = service.calculate_bloom_status(
                photo_date=date(2025, 5, 6),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "leaves_only"

            result = service.calculate_bloom_status(
                photo_date=date(2025, 6, 1),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result == "leaves_only"


@pytest.mark.unit
class TestBloomStateServiceNullCases:
    """BloomStateService の NULL ケーステスト (Req 1.12, 1.13)"""

    def test_no_flowering_date_returns_none(self):
        """開花予想日が取得できない場合は None を返すこと (Req 1.12)"""
        service = BloomStateService()

        with patch.object(
            service, "_get_flowering_dates"
        ) as mock_dates:
            mock_dates.return_value = (None, None, None)

            result = service.calculate_bloom_status(
                photo_date=date(2025, 4, 20),
                latitude=40.8,
                longitude=140.7,
                prefecture_code="02",
            )
            assert result is None

    def test_okinawa_prefecture_returns_none(self):
        """沖縄県は None を返すこと (Req 1.13)"""
        service = BloomStateService()

        result = service.calculate_bloom_status(
            photo_date=date(2025, 4, 20),
            latitude=26.2,
            longitude=127.7,
            prefecture_code="47",
        )
        assert result is None

    def test_none_prefecture_code_returns_none(self):
        """都道府県コードが None の場合は None を返すこと"""
        service = BloomStateService()

        result = service.calculate_bloom_status(
            photo_date=date(2025, 4, 20),
            latitude=35.6,
            longitude=139.7,
            prefecture_code=None,
        )
        assert result is None


@pytest.mark.unit
class TestBloomStateServiceSingleton:
    """シングルトンパターンのテスト"""

    def test_singleton_returns_same_instance(self):
        """get_bloom_state_service は同じインスタンスを返すこと"""
        # シングルトンインスタンスをリセット
        import app.domain.services.bloom_state_service as module
        module._bloom_state_service_instance = None

        service1 = get_bloom_state_service()
        service2 = get_bloom_state_service()
        assert service1 is service2
