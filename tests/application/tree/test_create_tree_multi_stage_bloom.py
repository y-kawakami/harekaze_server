"""create_tree の多段階開花モデル統合テスト

多段階判定→条件付きモデル呼び出し→DB保存のフロー全体を検証する。
Requirements: 1.1, 1.2, 3.1-3.4, 4.1, 4.5, 5.1-5.4, 6.1-6.4
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.tree.create_tree import create_tree
from app.domain.services.ai_service import (TreeVitalityBloom30Result,
                                            TreeVitalityBloom50Result,
                                            TreeVitalityBloomResult,
                                            TreeVitalityNoleafResult)
from app.domain.services.multi_stage_bloom_service import (BloomStageResult,
                                                           ModelWeight)
from app.interfaces.schemas.tree import TreeResponse


def _make_mock_address() -> MagicMock:
    addr = MagicMock()
    addr.country = "日本"
    addr.detail = "東京都千代田区"
    addr.prefecture_code = "13"
    addr.municipality_code = "13101"
    addr.block = "千代田1-1"
    return addr


def _make_mock_spot() -> MagicMock:
    spot = MagicMock()
    spot.flowering_date = date(2025, 3, 24)
    spot.full_bloom_date = date(2025, 3, 30)
    spot.full_bloom_end_date = date(2025, 4, 3)
    spot.estimate_vitality.return_value = (0.5, 0.5)
    return spot


def _noleaf_result(
    vitality: int = 3, real: float = 3.2,
) -> TreeVitalityNoleafResult:
    return TreeVitalityNoleafResult(
        vitality=vitality,
        vitality_real=real,
        vitality_probs=[0.1, 0.1, 0.5, 0.2, 0.1],
    )


def _bloom_result(
    vitality: int = 4, real: float = 3.8,
) -> TreeVitalityBloomResult:
    return TreeVitalityBloomResult(
        vitality=vitality,
        vitality_real=real,
        vitality_probs=[0.05, 0.1, 0.15, 0.5, 0.2],
    )


def _bloom30_result(
    vitality: int = 3, real: float = 3.4,
) -> TreeVitalityBloom30Result:
    return TreeVitalityBloom30Result(
        vitality=vitality,
        vitality_real=real,
        vitality_probs=[0.1, 0.1, 0.4, 0.3, 0.1],
    )


def _bloom50_result(
    vitality: int = 4, real: float = 3.6,
) -> TreeVitalityBloom50Result:
    return TreeVitalityBloom50Result(
        vitality=vitality,
        vitality_real=real,
        vitality_probs=[0.05, 0.1, 0.25, 0.4, 0.2],
    )


def _make_mock_tree() -> MagicMock:
    tree = MagicMock()
    tree.uid = "test-uid"
    tree.id = 1
    tree.latitude = 35.0
    tree.longitude = 139.0
    tree.location = "東京都千代田区"
    tree.prefecture_code = "13"
    tree.municipality_code = "13101"
    tree.photo_date = datetime.now(timezone.utc)
    tree.entire_tree = None
    return tree


def _make_mock_services() -> dict[str, MagicMock]:
    """テスト用モックサービス群"""
    db = MagicMock()
    user = MagicMock()
    user.id = 1

    image_svc = MagicMock()
    image_svc.bytes_to_pil.return_value = MagicMock(
        format="JPEG"
    )
    image_svc.pil_to_bytes.return_value = b"jpeg"
    image_svc.upload_image = AsyncMock(return_value=True)
    image_svc.create_thumbnail.return_value = b"thumb"
    image_svc.get_contents_bucket_name.return_value = "bkt"
    image_svc.get_full_object_key.return_value = "full-key"

    geocoding_svc = MagicMock()
    geocoding_svc.get_address.return_value = (
        _make_mock_address()
    )

    label_det = MagicMock()
    label_det.detect = AsyncMock(
        return_value={"Tree": [MagicMock()]}
    )

    fds = MagicMock()
    fds.find_nearest_spot.return_value = _make_mock_spot()

    ai_svc = MagicMock()
    ai_svc.analyze_tree_vitality_noleaf = AsyncMock(
        return_value=_noleaf_result()
    )
    ai_svc.analyze_tree_vitality_bloom = AsyncMock(
        return_value=_bloom_result()
    )
    ai_svc.analyze_tree_vitality_bloom_30 = AsyncMock(
        return_value=_bloom30_result()
    )
    ai_svc.analyze_tree_vitality_bloom_50 = AsyncMock(
        return_value=_bloom50_result()
    )

    fv_svc = MagicMock()
    from app.domain.services.fullview_validation_service import \
        FullviewValidationResult
    fv_svc.validate = AsyncMock(
        return_value=FullviewValidationResult(
            is_valid=True, reason="OK", confidence=0.95,
        )
    )
    fv_svc.model_id = "test-model"

    fv_log = MagicMock()
    fv_log.create.return_value = MagicMock()

    msb_svc = MagicMock()

    return {
        "db": db,
        "current_user": user,
        "image_service": image_svc,
        "geocoding_service": geocoding_svc,
        "label_detector": label_det,
        "flowering_date_service": fds,
        "ai_service": ai_svc,
        "fullview_validation_service": fv_svc,
        "fullview_validation_log_repository": fv_log,
        "multi_stage_bloom_service": msb_svc,
    }


async def _run_create_tree(
    mocks: dict[str, MagicMock],
    mock_tree: MagicMock | None = None,
) -> tuple[TreeResponse, MagicMock]:
    """create_tree を実行し (result, repo_mock) を返す"""
    if mock_tree is None:
        mock_tree = _make_mock_tree()

    with patch(
        "app.application.tree.create_tree.TreeRepository"
    ) as repo_cls:
        repo = MagicMock()
        repo.create_tree.return_value = mock_tree
        repo_cls.return_value = repo

        result = await create_tree(
            db=mocks["db"],
            current_user=mocks["current_user"],
            latitude=35.0,
            longitude=139.0,
            image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
            contributor=None,
            image_service=mocks["image_service"],
            geocoding_service=mocks["geocoding_service"],
            label_detector=mocks["label_detector"],
            flowering_date_service=(
                mocks["flowering_date_service"]
            ),
            ai_service=mocks["ai_service"],
            fullview_validation_service=(
                mocks["fullview_validation_service"]
            ),
            fullview_validation_log_repository=(
                mocks["fullview_validation_log_repository"]
            ),
            multi_stage_bloom_service=(
                mocks["multi_stage_bloom_service"]
            ),
            photo_date="2025-03-28T12:00:00+09:00",
        )
        return result, repo


# =========================================================
# 1. 単一モデル段階のテスト (Req 3.1-3.4, 5.1-5.4)
# =========================================================
@pytest.mark.unit
class TestSingleModelStage:
    """単一モデル段階でのAPI呼び出しとDB保存"""

    @pytest.mark.asyncio
    async def test_branch_only_calls_noleaf_only(self):
        """枝のみ段階: noleaf のみ呼び出す (Req 3.1)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="branch_only",
                    models=[
                        ModelWeight(model="noleaf", weight=1.0)
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_noleaf.assert_called_once()
        ai.analyze_tree_vitality_bloom.assert_not_called()
        ai.analyze_tree_vitality_bloom_30.assert_not_called()
        ai.analyze_tree_vitality_bloom_50.assert_not_called()

    @pytest.mark.asyncio
    async def test_bloom_30_calls_bloom_30_only(self):
        """3分咲き段階: bloom_30 のみ呼び出す (Req 3.2)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_30",
                    models=[
                        ModelWeight(
                            model="bloom_30", weight=1.0
                        )
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_bloom_30.assert_called_once()
        ai.analyze_tree_vitality_noleaf.assert_not_called()
        ai.analyze_tree_vitality_bloom.assert_not_called()
        ai.analyze_tree_vitality_bloom_50.assert_not_called()

    @pytest.mark.asyncio
    async def test_bloom_50_calls_bloom_50_only(self):
        """5分咲き段階: bloom_50 のみ呼び出す (Req 3.3)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_50",
                    models=[
                        ModelWeight(
                            model="bloom_50", weight=1.0
                        )
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_bloom_50.assert_called_once()
        ai.analyze_tree_vitality_noleaf.assert_not_called()
        ai.analyze_tree_vitality_bloom.assert_not_called()
        ai.analyze_tree_vitality_bloom_30.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_bloom_calls_bloom_only(self):
        """満開段階: bloom のみ呼び出す (Req 3.4)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="full_bloom",
                    models=[
                        ModelWeight(model="bloom", weight=1.0)
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_bloom.assert_called_once()
        ai.analyze_tree_vitality_noleaf.assert_not_called()
        ai.analyze_tree_vitality_bloom_30.assert_not_called()
        ai.analyze_tree_vitality_bloom_50.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_model_db_weights(self):
        """単一モデルの weight 保存 (Req 5.4)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_30",
                    models=[
                        ModelWeight(
                            model="bloom_30", weight=1.0
                        )
                    ],
                )
        )

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        assert kw["vitality_bloom_30_weight"] == 1.0
        assert kw["vitality_noleaf_weight"] == 0.0
        assert kw["vitality_bloom_weight"] == 0.0
        assert kw["vitality_bloom_50_weight"] == 0.0

    @pytest.mark.asyncio
    async def test_single_model_db_vitality(self):
        """単一モデルの vitality 保存 (Req 5.1, 5.2)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_50",
                    models=[
                        ModelWeight(
                            model="bloom_50", weight=1.0
                        )
                    ],
                )
        )

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        # bloom_50 の結果が保存される
        assert kw["vitality_bloom_50"] == 4
        assert kw["vitality_bloom_50_real"] == 3.6
        # 未呼び出しモデルは None
        assert kw["vitality_bloom_30"] is None
        assert kw["vitality_noleaf"] is None
        assert kw["vitality_bloom"] is None
        # 最終 vitality
        assert kw["vitality"] == 4
        assert kw["vitality_real"] == 3.6


# =========================================================
# 2. ブレンド段階のテスト (Req 4.1-4.6)
# =========================================================
@pytest.mark.unit
class TestBlendStage:
    """ブレンド段階でのモデル呼び出しとブレンド計算"""

    @pytest.mark.asyncio
    async def test_early_blend_calls_two_models(self):
        """開花ブレンド: noleaf + bloom_30 (Req 4.1)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="early_blend",
                    models=[
                        ModelWeight(
                            model="noleaf", weight=0.6
                        ),
                        ModelWeight(
                            model="bloom_30", weight=0.4
                        ),
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_noleaf.assert_called_once()
        ai.analyze_tree_vitality_bloom_30.assert_called_once()
        ai.analyze_tree_vitality_bloom.assert_not_called()
        ai.analyze_tree_vitality_bloom_50.assert_not_called()

    @pytest.mark.asyncio
    async def test_early_blend_vitality_calc(self):
        """開花ブレンドの vitality_real 計算 (Req 4.5)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="early_blend",
                    models=[
                        ModelWeight(
                            model="noleaf", weight=0.6
                        ),
                        ModelWeight(
                            model="bloom_30", weight=0.4
                        ),
                    ],
                )
        )
        # noleaf=3.2, bloom_30=3.4
        # expected = 3.2*0.6 + 3.4*0.4 = 1.92 + 1.36 = 3.28
        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        expected = 3.2 * 0.6 + 3.4 * 0.4
        assert abs(kw["vitality_real"] - expected) < 1e-9
        assert kw["vitality"] == round(expected)

    @pytest.mark.asyncio
    async def test_late_blend_calls_bloom_and_noleaf(self):
        """満開後ブレンド: bloom + noleaf (Req 4.3)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="late_blend",
                    models=[
                        ModelWeight(
                            model="bloom", weight=0.7
                        ),
                        ModelWeight(
                            model="noleaf", weight=0.3
                        ),
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_bloom.assert_called_once()
        ai.analyze_tree_vitality_noleaf.assert_called_once()
        ai.analyze_tree_vitality_bloom_30.assert_not_called()
        ai.analyze_tree_vitality_bloom_50.assert_not_called()

    @pytest.mark.asyncio
    async def test_late_blend_vitality_calc(self):
        """満開後ブレンドの vitality_real 計算 (Req 4.5)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="late_blend",
                    models=[
                        ModelWeight(
                            model="bloom", weight=0.7
                        ),
                        ModelWeight(
                            model="noleaf", weight=0.3
                        ),
                    ],
                )
        )
        # bloom=3.8, noleaf=3.2
        # expected = 3.8*0.7 + 3.2*0.3 = 2.66 + 0.96 = 3.62
        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        expected = 3.8 * 0.7 + 3.2 * 0.3
        assert abs(kw["vitality_real"] - expected) < 1e-9
        assert kw["vitality"] == round(expected)

    @pytest.mark.asyncio
    async def test_blend_db_weights(self):
        """ブレンド時の weight 保存 (Req 5.3)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="early_blend",
                    models=[
                        ModelWeight(
                            model="noleaf", weight=0.6
                        ),
                        ModelWeight(
                            model="bloom_30", weight=0.4
                        ),
                    ],
                )
        )

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        assert kw["vitality_noleaf_weight"] == 0.6
        assert kw["vitality_bloom_30_weight"] == 0.4
        assert kw["vitality_bloom_weight"] == 0.0
        assert kw["vitality_bloom_50_weight"] == 0.0

    @pytest.mark.asyncio
    async def test_blend_db_model_results(self):
        """ブレンド時の各モデル結果保存 (Req 5.2)"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="early_blend",
                    models=[
                        ModelWeight(
                            model="noleaf", weight=0.6
                        ),
                        ModelWeight(
                            model="bloom_30", weight=0.4
                        ),
                    ],
                )
        )

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        assert kw["vitality_noleaf"] == 3
        assert kw["vitality_noleaf_real"] == 3.2
        assert kw["vitality_bloom_30"] == 3
        assert kw["vitality_bloom_30_real"] == 3.4
        # 未呼び出しは None
        assert kw["vitality_bloom"] is None
        assert kw["vitality_bloom_50"] is None

    @pytest.mark.asyncio
    async def test_vitality_clamped_1_to_5(self):
        """vitality は 1〜5 にクランプ (Req 4.6)"""
        mocks = _make_mock_services()
        mocks["ai_service"].analyze_tree_vitality_noleaf = (
            AsyncMock(return_value=_noleaf_result(5, 5.0))
        )
        mocks["ai_service"].analyze_tree_vitality_bloom_30 = (
            AsyncMock(return_value=_bloom30_result(5, 5.0))
        )
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="early_blend",
                    models=[
                        ModelWeight(
                            model="noleaf", weight=0.5
                        ),
                        ModelWeight(
                            model="bloom_30", weight=0.5
                        ),
                    ],
                )
        )

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        assert 1 <= kw["vitality"] <= 5


# =========================================================
# 3. フォールバックテスト (Req 6.1, 6.2)
# =========================================================
@pytest.mark.unit
class TestFallback:
    """determine_bloom_stage が None → 従来ブレンド"""

    @pytest.mark.asyncio
    async def test_fallback_calls_both_legacy_models(self):
        """フォールバック時は noleaf + bloom を呼び出す"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = None

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        ai.analyze_tree_vitality_noleaf.assert_called_once()
        ai.analyze_tree_vitality_bloom.assert_called_once()
        ai.analyze_tree_vitality_bloom_30.assert_not_called()
        ai.analyze_tree_vitality_bloom_50.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_uses_estimate_vitality(self):
        """フォールバック時は estimate_vitality を使用"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = None
        spot = mocks["flowering_date_service"] \
            .find_nearest_spot.return_value
        spot.estimate_vitality.return_value = (0.3, 0.7)

        _ = await _run_create_tree(mocks)

        spot.estimate_vitality.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_vitality_calc(self):
        """フォールバック時の vitality 計算"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = None
        spot = mocks["flowering_date_service"] \
            .find_nearest_spot.return_value
        spot.estimate_vitality.return_value = (0.3, 0.7)
        # noleaf=3.2, bloom=3.8
        # expected = 3.2*0.3 + 3.8*0.7 = 0.96 + 2.66 = 3.62

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        expected = 3.2 * 0.3 + 3.8 * 0.7
        assert abs(kw["vitality_real"] - expected) < 1e-9

    @pytest.mark.asyncio
    async def test_fallback_bloom30_50_weights_null(self):
        """フォールバック時 bloom_30/50 weight は None"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = None

        _, repo = await _run_create_tree(mocks)

        kw = repo.create_tree.call_args[1]
        assert kw["vitality_bloom_30_weight"] is None
        assert kw["vitality_bloom_50_weight"] is None


# =========================================================
# 4. AI API 失敗テスト (Req 6.3)
# =========================================================
@pytest.mark.unit
class TestAIAPIFailure:
    """新モデル API 失敗時のエラーハンドリング"""

    @pytest.mark.asyncio
    async def test_bloom_30_api_failure_raises(self):
        """bloom_30 API 失敗時はエラーが発生する"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_30",
                    models=[
                        ModelWeight(
                            model="bloom_30", weight=1.0
                        )
                    ],
                )
        )
        mocks["ai_service"].analyze_tree_vitality_bloom_30 = (
            AsyncMock(side_effect=Exception("API Error"))
        )

        with pytest.raises(Exception, match="API Error"):
            await _run_create_tree(mocks)

    @pytest.mark.asyncio
    async def test_bloom_50_api_failure_raises(self):
        """bloom_50 API 失敗時はエラーが発生する"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_50",
                    models=[
                        ModelWeight(
                            model="bloom_50", weight=1.0
                        )
                    ],
                )
        )
        mocks["ai_service"].analyze_tree_vitality_bloom_50 = (
            AsyncMock(side_effect=Exception("API Error"))
        )

        with pytest.raises(Exception, match="API Error"):
            await _run_create_tree(mocks)


# =========================================================
# 5. API 呼び出し回数テスト
# =========================================================
@pytest.mark.unit
class TestAPICallCounts:
    """段階ごとの API 呼び出し回数"""

    @pytest.mark.asyncio
    async def test_single_stage_one_api_call(self):
        """単一モデル段階: API 1回"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="full_bloom",
                    models=[
                        ModelWeight(model="bloom", weight=1.0)
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        total = (
            ai.analyze_tree_vitality_noleaf.call_count
            + ai.analyze_tree_vitality_bloom.call_count
            + ai.analyze_tree_vitality_bloom_30.call_count
            + ai.analyze_tree_vitality_bloom_50.call_count
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_blend_stage_two_api_calls(self):
        """ブレンド段階: API 2回"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="early_blend",
                    models=[
                        ModelWeight(
                            model="noleaf", weight=0.5
                        ),
                        ModelWeight(
                            model="bloom_30", weight=0.5
                        ),
                    ],
                )
        )

        _ = await _run_create_tree(mocks)

        ai = mocks["ai_service"]
        total = (
            ai.analyze_tree_vitality_noleaf.call_count
            + ai.analyze_tree_vitality_bloom.call_count
            + ai.analyze_tree_vitality_bloom_30.call_count
            + ai.analyze_tree_vitality_bloom_50.call_count
        )
        assert total == 2


# =========================================================
# 6. TreeResponse の検証
# =========================================================
@pytest.mark.unit
class TestTreeResponse:
    """create_tree が正しい TreeResponse を返す"""

    @pytest.mark.asyncio
    async def test_returns_tree_response(self):
        """多段階モデルフローで TreeResponse を返す"""
        mocks = _make_mock_services()
        mocks["multi_stage_bloom_service"] \
            .determine_bloom_stage.return_value = (
                BloomStageResult(
                    stage="bloom_30",
                    models=[
                        ModelWeight(
                            model="bloom_30", weight=1.0
                        )
                    ],
                )
        )

        result, _ = await _run_create_tree(mocks)

        assert result is not None
        assert result.id == "test-uid"
