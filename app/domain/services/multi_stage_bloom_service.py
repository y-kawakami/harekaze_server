"""多段階開花モデルの開花段階判定サービス

撮影場所・日時から開花段階を判定し、呼び出すべきモデルとブレンド重みを返却する。
Requirements: 1.2-1.10, 2.2-2.4
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from loguru import logger

from app.domain.services.bloom_state_service import get_bloom_state_service

BloomStage = Literal[
    "branch_only",
    "early_blend",
    "bloom_30",
    "bloom_50",
    "full_bloom",
    "late_blend",
]

ModelType = Literal["noleaf", "bloom_30", "bloom_50", "bloom"]

LATE_BLEND_DAYS = 10


@dataclass
class ModelWeight:
    """モデル種別と重みのペア"""

    model: ModelType
    weight: float  # 0.0 ~ 1.0


@dataclass
class BloomStageResult:
    """開花段階 + 使用モデルリスト"""

    stage: BloomStage
    models: list[ModelWeight]
    # models の weight 合計は常に 1.0


class MultiStageBloomService:
    """多段階開花モデルの開花段階判定サービス

    撮影場所・日時から6段階の開花段階を判定し、
    呼び出すべき AI モデルとブレンド重みを返却する。
    純粋な計算サービスであり、副作用なし。
    """

    def determine_bloom_stage(
        self,
        flowering_date: date,
        full_bloom_date: date,
        full_bloom_end_date: date,
        prefecture_code: str | None,
        photo_date: date,
    ) -> BloomStageResult | None:
        """開花段階を判定し、使用モデルと重みを返却する。

        Args:
            flowering_date: 開花予想日
            full_bloom_date: 満開開始予想日
            full_bloom_end_date: 満開終了予想日
            prefecture_code: 都道府県コード（"01"-"47"）
            photo_date: 撮影日

        Returns:
            BloomStageResult または None（判定不能時）
        """
        if prefecture_code is None:
            logger.warning("都道府県コードが未指定のためフォールバック")
            return None

        bloom_state_service = get_bloom_state_service()
        offsets = bloom_state_service.get_prefecture_offsets(
            prefecture_code
        )
        if offsets is None:
            logger.warning(
                f"都道府県コード {prefecture_code} のオフセットが取得できないためフォールバック"
            )
            return None

        if offsets.flowering_to_full_bloom == 0:
            logger.warning(
                "開花→満開の基準期間が0のためフォールバック"
            )
            return None

        # オフセット補正比率を算出 (Req 2.2, 2.3)
        actual_days = (full_bloom_date - flowering_date).days
        ratio = actual_days / offsets.flowering_to_full_bloom

        # 補正済みオフセット（日数、浮動小数点）
        corrected_3bu_days = offsets.flowering_to_3bu * ratio
        corrected_5bu_days = offsets.flowering_to_5bu * ratio

        # 撮影日の開花予想日からの経過日数
        days_from_flowering = (photo_date - flowering_date).days
        # 撮影日の満開終了日からの経過日数
        days_from_full_bloom_end = (
            photo_date - full_bloom_end_date
        ).days
        # 満開開始日までの日数
        days_to_full_bloom = (full_bloom_date - flowering_date).days

        # 6段階の開花段階判定 (Req 1.4-1.10)
        if days_from_flowering < 0:
            # 開花予想日より前 (Req 1.4)
            return BloomStageResult(
                stage="branch_only",
                models=[ModelWeight(model="noleaf", weight=1.0)],
            )

        if days_from_flowering < corrected_3bu_days:
            # 開花ブレンド期間 (Req 1.5)
            progress = (
                days_from_flowering / corrected_3bu_days
                if corrected_3bu_days > 0
                else 0.0
            )
            return BloomStageResult(
                stage="early_blend",
                models=[
                    ModelWeight(
                        model="noleaf", weight=1.0 - progress
                    ),
                    ModelWeight(
                        model="bloom_30", weight=progress
                    ),
                ],
            )

        if days_from_flowering < corrected_5bu_days:
            # 3分咲き (Req 1.6)
            return BloomStageResult(
                stage="bloom_30",
                models=[
                    ModelWeight(model="bloom_30", weight=1.0)
                ],
            )

        if days_from_flowering < days_to_full_bloom:
            # 5分咲き (Req 1.7)
            return BloomStageResult(
                stage="bloom_50",
                models=[
                    ModelWeight(model="bloom_50", weight=1.0)
                ],
            )

        if days_from_full_bloom_end < 0:
            # 満開 (Req 1.8)
            return BloomStageResult(
                stage="full_bloom",
                models=[ModelWeight(model="bloom", weight=1.0)],
            )

        if days_from_full_bloom_end < LATE_BLEND_DAYS:
            # 満開後ブレンド期間 (Req 1.9)
            progress = days_from_full_bloom_end / LATE_BLEND_DAYS
            return BloomStageResult(
                stage="late_blend",
                models=[
                    ModelWeight(
                        model="bloom", weight=1.0 - progress
                    ),
                    ModelWeight(
                        model="noleaf", weight=progress
                    ),
                ],
            )

        # 満開終了+10日以降は枝のみ (Req 1.10)
        return BloomStageResult(
            stage="branch_only",
            models=[ModelWeight(model="noleaf", weight=1.0)],
        )


_multi_stage_bloom_service_instance: (
    MultiStageBloomService | None
) = None


def get_multi_stage_bloom_service() -> MultiStageBloomService:
    """MultiStageBloomService のシングルトンインスタンスを取得"""
    global _multi_stage_bloom_service_instance
    if _multi_stage_bloom_service_instance is None:
        _multi_stage_bloom_service_instance = (
            MultiStageBloomService()
        )
    return _multi_stage_bloom_service_instance
