"""MultiStageBloomService のテスト

多段階開花モデルの開花段階判定ロジックをテストする。
Requirements: 1.2-1.10, 2.2-2.4
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.domain.services.multi_stage_bloom_service import (
    ModelWeight,
    BloomStageResult,
    MultiStageBloomService,
    get_multi_stage_bloom_service,
)
from app.domain.services.bloom_state_service import PrefectureOffsets


@pytest.mark.unit
class TestBloomStageResult:
    """BloomStageResult データクラスのテスト"""

    def test_single_model_result(self):
        """単一モデルの結果を作成できること"""
        result = BloomStageResult(
            stage="branch_only",
            models=[ModelWeight(model="noleaf", weight=1.0)],
        )
        assert result.stage == "branch_only"
        assert len(result.models) == 1
        assert result.models[0].model == "noleaf"
        assert result.models[0].weight == 1.0

    def test_blend_result(self):
        """ブレンドモデルの結果を作成できること"""
        result = BloomStageResult(
            stage="early_blend",
            models=[
                ModelWeight(model="noleaf", weight=0.6),
                ModelWeight(model="bloom_30", weight=0.4),
            ],
        )
        assert result.stage == "early_blend"
        assert len(result.models) == 2
        total_weight = sum(m.weight for m in result.models)
        assert abs(total_weight - 1.0) < 1e-9


@pytest.mark.unit
class TestDetermineBloomStageBasic:
    """determine_bloom_stage の基本的な6段階判定テスト (Req 1.4-1.10)"""

    @pytest.fixture
    def service(self):
        """BloomStateService をモックした MultiStageBloomService"""
        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ) as mock_get:
            mock_bss = MagicMock()
            # 青森県相当: 3bu=2日, 5bu=3日, full_bloom=5日
            mock_bss.get_prefecture_offsets.return_value = (
                PrefectureOffsets(
                    flowering_to_3bu=2,
                    flowering_to_5bu=3,
                    flowering_to_full_bloom=5,
                    end_to_hanawakaba=5,
                    end_to_hanomi=10,
                )
            )
            mock_get.return_value = mock_bss
            svc = MultiStageBloomService()
            yield svc

    def test_branch_only_before_flowering(self, service):
        """開花予想日より前は「枝のみ」(Req 1.4)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 16),
        )
        assert result is not None
        assert result.stage == "branch_only"
        assert len(result.models) == 1
        assert result.models[0].model == "noleaf"
        assert result.models[0].weight == 1.0

    def test_early_blend_at_flowering_date(self, service):
        """開花予想日当日は「開花ブレンド」(Req 1.5)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 17),
        )
        assert result is not None
        assert result.stage == "early_blend"
        assert len(result.models) == 2
        # 開花日当日: noleaf=1.0, bloom_30=0.0
        noleaf = next(m for m in result.models if m.model == "noleaf")
        bloom_30 = next(
            m for m in result.models if m.model == "bloom_30"
        )
        assert noleaf.weight == 1.0
        assert bloom_30.weight == 0.0

    def test_early_blend_midpoint(self, service):
        """開花ブレンド期間の中間点 (Req 1.5)"""
        # ratio=1.0 なので corrected_3bu=2日
        # 開花日+1日 → progress = 1/2 = 0.5
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 18),
        )
        assert result is not None
        assert result.stage == "early_blend"
        noleaf = next(m for m in result.models if m.model == "noleaf")
        bloom_30 = next(
            m for m in result.models if m.model == "bloom_30"
        )
        assert abs(noleaf.weight - 0.5) < 1e-9
        assert abs(bloom_30.weight - 0.5) < 1e-9

    def test_bloom_30_at_corrected_3bu_date(self, service):
        """補正済み3分咲きオフセット日は「3分咲き」(Req 1.6)"""
        # ratio=1.0, corrected_3bu=2日 → 4/17+2 = 4/19
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 19),
        )
        assert result is not None
        assert result.stage == "bloom_30"
        assert len(result.models) == 1
        assert result.models[0].model == "bloom_30"
        assert result.models[0].weight == 1.0

    def test_bloom_50_at_corrected_5bu_date(self, service):
        """補正済み5分咲きオフセット日は「5分咲き」(Req 1.7)"""
        # ratio=1.0, corrected_5bu=3日 → 4/17+3 = 4/20
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 20),
        )
        assert result is not None
        assert result.stage == "bloom_50"
        assert len(result.models) == 1
        assert result.models[0].model == "bloom_50"
        assert result.models[0].weight == 1.0

    def test_bloom_50_last_day(self, service):
        """満開開始前日は「5分咲き」(Req 1.7)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 21),
        )
        assert result is not None
        assert result.stage == "bloom_50"

    def test_full_bloom_at_start(self, service):
        """満開開始予想日は「満開」(Req 1.8)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 22),
        )
        assert result is not None
        assert result.stage == "full_bloom"
        assert len(result.models) == 1
        assert result.models[0].model == "bloom"
        assert result.models[0].weight == 1.0

    def test_full_bloom_last_day(self, service):
        """満開終了予想日の前日は「満開」(Req 1.8)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 25),
        )
        assert result is not None
        assert result.stage == "full_bloom"

    def test_late_blend_at_full_bloom_end(self, service):
        """満開終了予想日当日は「満開後ブレンド」(Req 1.9)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 26),
        )
        assert result is not None
        assert result.stage == "late_blend"
        assert len(result.models) == 2
        # 満開終了日当日: bloom=1.0, noleaf=0.0
        bloom = next(m for m in result.models if m.model == "bloom")
        noleaf = next(m for m in result.models if m.model == "noleaf")
        assert bloom.weight == 1.0
        assert noleaf.weight == 0.0

    def test_late_blend_midpoint(self, service):
        """満開後ブレンド期間の中間点 (Req 1.9)"""
        # 満開終了日+5日 → progress = 5/10 = 0.5
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 5, 1),
        )
        assert result is not None
        assert result.stage == "late_blend"
        bloom = next(m for m in result.models if m.model == "bloom")
        noleaf = next(m for m in result.models if m.model == "noleaf")
        assert abs(bloom.weight - 0.5) < 1e-9
        assert abs(noleaf.weight - 0.5) < 1e-9

    def test_late_blend_last_day(self, service):
        """満開終了+9日は「満開後ブレンド」(Req 1.9)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 5, 5),
        )
        assert result is not None
        assert result.stage == "late_blend"
        bloom = next(m for m in result.models if m.model == "bloom")
        noleaf = next(m for m in result.models if m.model == "noleaf")
        assert abs(bloom.weight - 0.1) < 1e-9
        assert abs(noleaf.weight - 0.9) < 1e-9

    def test_branch_only_after_late_blend(self, service):
        """満開終了+10日以降は「枝のみ」(Req 1.10)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 5, 6),
        )
        assert result is not None
        assert result.stage == "branch_only"
        assert result.models[0].model == "noleaf"

    def test_branch_only_far_after_season(self, service):
        """シーズン終了後は「枝のみ」(Req 1.10)"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 7, 1),
        )
        assert result is not None
        assert result.stage == "branch_only"


@pytest.mark.unit
class TestOffsetCorrection:
    """オフセット補正比率のテスト (Req 2.2, 2.3)"""

    def _make_service_with_offsets(
        self, flowering_to_3bu: int, flowering_to_5bu: int,
        flowering_to_full_bloom: int,
    ) -> MultiStageBloomService:
        """指定オフセットでモック済みサービスを作成"""
        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ) as mock_get:
            mock_bss = MagicMock()
            mock_bss.get_prefecture_offsets.return_value = (
                PrefectureOffsets(
                    flowering_to_3bu=flowering_to_3bu,
                    flowering_to_5bu=flowering_to_5bu,
                    flowering_to_full_bloom=flowering_to_full_bloom,
                    end_to_hanawakaba=5,
                    end_to_hanomi=10,
                )
            )
            mock_get.return_value = mock_bss
            return MultiStageBloomService()

    def test_ratio_1_0(self):
        """補正比率 1.0（実際期間 = 基準期間）"""
        # 基準: flowering_to_full_bloom=5
        # 実際: (4/22-4/17)=5 → ratio=5/5=1.0
        # corrected_3bu=2*1.0=2, corrected_5bu=3*1.0=3
        service = self._make_service_with_offsets(2, 3, 5)
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 22),
            full_bloom_end_date=date(2025, 4, 26),
            prefecture_code="02",
            photo_date=date(2025, 4, 19),  # 4/17+2 → bloom_30
        )
        assert result is not None
        assert result.stage == "bloom_30"

    def test_ratio_1_4(self):
        """補正比率 1.4（実際期間が基準より長い）"""
        # 基準: flowering_to_full_bloom=5
        # 実際: (4/24-4/17)=7 → ratio=7/5=1.4
        # corrected_3bu=2*1.4=2.8, corrected_5bu=3*1.4=4.2
        # 4/17+2.8=2.8日後 → photo_date=4/19(2日後)はearly_blend
        service = self._make_service_with_offsets(2, 3, 5)
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 24),
            full_bloom_end_date=date(2025, 4, 28),
            prefecture_code="02",
            photo_date=date(2025, 4, 19),
        )
        assert result is not None
        # 2日経過 < 2.8日(corrected_3bu) → early_blend
        assert result.stage == "early_blend"

    def test_ratio_1_4_bloom_30(self):
        """補正比率 1.4 で3分咲きに入るケース"""
        # corrected_3bu=2.8, corrected_5bu=4.2
        # 4/17+3日=4/20(3日後), 3 >= 2.8 → bloom_30
        service = self._make_service_with_offsets(2, 3, 5)
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 24),
            full_bloom_end_date=date(2025, 4, 28),
            prefecture_code="02",
            photo_date=date(2025, 4, 20),
        )
        assert result is not None
        assert result.stage == "bloom_30"

    def test_ratio_0_7(self):
        """補正比率 0.7（実際期間が基準より短い）"""
        # 基準: flowering_to_full_bloom=10
        # 実際: (4/24-4/17)=7 → ratio=7/10=0.7
        # corrected_3bu=4*0.7=2.8, corrected_5bu=6*0.7=4.2
        # 4/17+3日=4/20(3日後), 3 >= 2.8 → bloom_30
        service = self._make_service_with_offsets(4, 6, 10)
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 24),
            full_bloom_end_date=date(2025, 4, 28),
            prefecture_code="02",
            photo_date=date(2025, 4, 20),
        )
        assert result is not None
        assert result.stage == "bloom_30"

    def test_ratio_0_7_bloom_50(self):
        """補正比率 0.7 で5分咲きに入るケース"""
        # corrected_3bu=2.8, corrected_5bu=4.2
        # 4/17+5日=4/22(5日後), 5 >= 4.2 → bloom_50
        service = self._make_service_with_offsets(4, 6, 10)
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 17),
            full_bloom_date=date(2025, 4, 24),
            full_bloom_end_date=date(2025, 4, 28),
            prefecture_code="02",
            photo_date=date(2025, 4, 22),
        )
        assert result is not None
        assert result.stage == "bloom_50"


@pytest.mark.unit
class TestBlendWeights:
    """ブレンド重みの線形補間精度テスト (Req 4.1-4.4)"""

    @pytest.fixture
    def service(self):
        """ブレンドテスト用サービス"""
        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ) as mock_get:
            mock_bss = MagicMock()
            # 3bu=4日, 5bu=6日, full_bloom=10日
            mock_bss.get_prefecture_offsets.return_value = (
                PrefectureOffsets(
                    flowering_to_3bu=4,
                    flowering_to_5bu=6,
                    flowering_to_full_bloom=10,
                    end_to_hanawakaba=5,
                    end_to_hanomi=10,
                )
            )
            mock_get.return_value = mock_bss
            svc = MultiStageBloomService()
            yield svc

    def test_early_blend_start(self, service):
        """開花ブレンド開始時: noleaf=1.0, bloom_30=0.0"""
        # ratio=1.0 (10/10), corrected_3bu=4
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 4, 10),  # 0日目
        )
        assert result is not None
        assert result.stage == "early_blend"
        noleaf = next(m for m in result.models if m.model == "noleaf")
        bloom_30 = next(
            m for m in result.models if m.model == "bloom_30"
        )
        assert noleaf.weight == 1.0
        assert bloom_30.weight == 0.0

    def test_early_blend_quarter(self, service):
        """開花ブレンド 1/4 時点: noleaf=0.75, bloom_30=0.25"""
        # 1日目/4日 = 0.25
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 4, 11),  # 1日目
        )
        assert result is not None
        assert result.stage == "early_blend"
        noleaf = next(m for m in result.models if m.model == "noleaf")
        bloom_30 = next(
            m for m in result.models if m.model == "bloom_30"
        )
        assert abs(noleaf.weight - 0.75) < 1e-9
        assert abs(bloom_30.weight - 0.25) < 1e-9

    def test_early_blend_half(self, service):
        """開花ブレンド中間点: noleaf=0.5, bloom_30=0.5"""
        # 2日目/4日 = 0.5
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 4, 12),  # 2日目
        )
        assert result is not None
        assert result.stage == "early_blend"
        noleaf = next(m for m in result.models if m.model == "noleaf")
        bloom_30 = next(
            m for m in result.models if m.model == "bloom_30"
        )
        assert abs(noleaf.weight - 0.5) < 1e-9
        assert abs(bloom_30.weight - 0.5) < 1e-9

    def test_early_blend_three_quarter(self, service):
        """開花ブレンド 3/4 時点: noleaf=0.25, bloom_30=0.75"""
        # 3日目/4日 = 0.75
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 4, 13),  # 3日目
        )
        assert result is not None
        assert result.stage == "early_blend"
        noleaf = next(m for m in result.models if m.model == "noleaf")
        bloom_30 = next(
            m for m in result.models if m.model == "bloom_30"
        )
        assert abs(noleaf.weight - 0.25) < 1e-9
        assert abs(bloom_30.weight - 0.75) < 1e-9

    def test_late_blend_start(self, service):
        """満開後ブレンド開始時: bloom=1.0, noleaf=0.0"""
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 4, 25),  # 満開終了日
        )
        assert result is not None
        assert result.stage == "late_blend"
        bloom = next(m for m in result.models if m.model == "bloom")
        noleaf = next(m for m in result.models if m.model == "noleaf")
        assert bloom.weight == 1.0
        assert noleaf.weight == 0.0

    def test_late_blend_half(self, service):
        """満開後ブレンド中間点: bloom=0.5, noleaf=0.5"""
        # 5日目/10日 = 0.5
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 4, 30),  # 満開終了+5日
        )
        assert result is not None
        assert result.stage == "late_blend"
        bloom = next(m for m in result.models if m.model == "bloom")
        noleaf = next(m for m in result.models if m.model == "noleaf")
        assert abs(bloom.weight - 0.5) < 1e-9
        assert abs(noleaf.weight - 0.5) < 1e-9

    def test_late_blend_near_end(self, service):
        """満開後ブレンド終了直前: bloom=0.1, noleaf=0.9"""
        # 9日目/10日 = 0.9
        result = service.determine_bloom_stage(
            flowering_date=date(2025, 4, 10),
            full_bloom_date=date(2025, 4, 20),
            full_bloom_end_date=date(2025, 4, 25),
            prefecture_code="02",
            photo_date=date(2025, 5, 4),  # 満開終了+9日
        )
        assert result is not None
        assert result.stage == "late_blend"
        bloom = next(m for m in result.models if m.model == "bloom")
        noleaf = next(m for m in result.models if m.model == "noleaf")
        assert abs(bloom.weight - 0.1) < 1e-9
        assert abs(noleaf.weight - 0.9) < 1e-9

    def test_weight_sum_always_1(self, service):
        """全段階で重み合計が 1.0 であること"""
        dates = [
            date(2025, 4, 9),   # branch_only (before)
            date(2025, 4, 10),  # early_blend start
            date(2025, 4, 12),  # early_blend mid
            date(2025, 4, 14),  # bloom_30
            date(2025, 4, 16),  # bloom_50
            date(2025, 4, 20),  # full_bloom
            date(2025, 4, 25),  # late_blend start
            date(2025, 4, 30),  # late_blend mid
            date(2025, 5, 5),   # branch_only (after)
        ]
        for photo_date in dates:
            result = service.determine_bloom_stage(
                flowering_date=date(2025, 4, 10),
                full_bloom_date=date(2025, 4, 20),
                full_bloom_end_date=date(2025, 4, 25),
                prefecture_code="02",
                photo_date=photo_date,
            )
            assert result is not None
            total = sum(m.weight for m in result.models)
            assert abs(total - 1.0) < 1e-9, (
                f"photo_date={photo_date}, stage={result.stage}, "
                f"total_weight={total}"
            )


@pytest.mark.unit
class TestFallbackConditions:
    """フォールバック条件（None 返却）テスト (Req 2.4)"""

    def test_prefecture_code_none(self):
        """都道府県コードが None の場合は None を返す"""
        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ) as mock_get:
            mock_bss = MagicMock()
            mock_get.return_value = mock_bss
            service = MultiStageBloomService()

            result = service.determine_bloom_stage(
                flowering_date=date(2025, 4, 17),
                full_bloom_date=date(2025, 4, 22),
                full_bloom_end_date=date(2025, 4, 26),
                prefecture_code=None,
                photo_date=date(2025, 4, 20),
            )
            assert result is None

    def test_offsets_not_found(self):
        """都道府県オフセットが取得できない場合は None を返す"""
        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ) as mock_get:
            mock_bss = MagicMock()
            mock_bss.get_prefecture_offsets.return_value = None
            mock_get.return_value = mock_bss
            service = MultiStageBloomService()

            result = service.determine_bloom_stage(
                flowering_date=date(2025, 4, 17),
                full_bloom_date=date(2025, 4, 22),
                full_bloom_end_date=date(2025, 4, 26),
                prefecture_code="47",
                photo_date=date(2025, 4, 20),
            )
            assert result is None

    def test_flowering_to_full_bloom_zero(self):
        """基準期間が 0 の場合は None を返す"""
        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ) as mock_get:
            mock_bss = MagicMock()
            mock_bss.get_prefecture_offsets.return_value = (
                PrefectureOffsets(
                    flowering_to_3bu=2,
                    flowering_to_5bu=3,
                    flowering_to_full_bloom=0,
                    end_to_hanawakaba=5,
                    end_to_hanomi=10,
                )
            )
            mock_get.return_value = mock_bss
            service = MultiStageBloomService()

            result = service.determine_bloom_stage(
                flowering_date=date(2025, 4, 17),
                full_bloom_date=date(2025, 4, 22),
                full_bloom_end_date=date(2025, 4, 26),
                prefecture_code="02",
                photo_date=date(2025, 4, 20),
            )
            assert result is None


@pytest.mark.unit
class TestSingleton:
    """シングルトンパターンのテスト"""

    def test_singleton_returns_same_instance(self):
        """get_multi_stage_bloom_service は同じインスタンスを返す"""
        import app.domain.services.multi_stage_bloom_service as mod
        mod._multi_stage_bloom_service_instance = None

        with patch(
            "app.domain.services.multi_stage_bloom_service"
            ".get_bloom_state_service"
        ):
            service1 = get_multi_stage_bloom_service()
            service2 = get_multi_stage_bloom_service()
            assert service1 is service2
