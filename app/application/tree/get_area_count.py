from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import InvalidParamError
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import AreaCountResponse


def get_area_count(
    db: Session,
    area_type: str,
    latitude: float,
    longitude: float,
    radius: float,
    vitality_min: Optional[int],
    vitality_max: Optional[int],
    age_min: Optional[int],
    age_max: Optional[int],
    has_hole: Optional[bool],
    has_tengusu: Optional[bool],
    has_mushroom: Optional[bool],
) -> AreaCountResponse:
    """
    エリア（都道府県または市区町村）ごとの桜の本数を取得する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        area_type (str): 集計レベル（'prefecture'または'municipality'）
        latitude (float): 検索の中心となる緯度
        longitude (float): 検索の中心となる経度
        radius (float): 検索範囲（メートル）
        vitality_min (Optional[int]): 元気度の最小値（1-5）
        vitality_max (Optional[int]): 元気度の最大値（1-5）
        age_min (Optional[int]): 樹齢の最小値（年）
        age_max (Optional[int]): 樹齢の最大値（年）
        has_hole (Optional[bool]): 幹の穴の有無
        has_tengusu (Optional[bool]): テングス病の有無
        has_mushroom (Optional[bool]): キノコの有無

    Returns:
        AreaCountResponse: エリアごとの集計結果

    Raises:
        InvalidParamError: パラメータが不正な場合
    """
    logger.info(
        f"エリアごとの桜の本数取得開始: area_type={area_type}, lat={latitude}, lon={longitude}, radius={radius}m")

    # area_typeのバリデーション
    if area_type not in ['prefecture', 'municipality']:
        logger.error(f"不正なarea_type: {area_type}")
        raise InvalidParamError(
            reason="area_typeは'prefecture'または'municipality'を指定してください",
            param_name="area_type"
        )

    # パラメータのログ出力
    logger.debug(f"検索条件: vitality_min={vitality_min}, vitality_max={vitality_max}, "
                 f"age_min={age_min}, age_max={age_max}, "
                 f"has_hole={has_hole}, has_tengusu={has_tengusu}, has_mushroom={has_mushroom}")

    repository = TreeRepository(db)

    # レンジパラメータの構築
    vitality_range = None
    if vitality_min is not None or vitality_max is not None:
        vitality_range = (
            vitality_min or 1,
            vitality_max or 5
        )
        logger.debug(f"元気度範囲を設定: {vitality_range}")

    age_range = None
    if age_min is not None or age_max is not None:
        age_range = (
            age_min or 0,
            age_max or 1000
        )
        logger.debug(f"樹齢範囲を設定: {age_range}")

    # エリアごとの集計を取得
    area_counts = repository.get_area_counts(
        area_type=area_type,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        vitality_range=vitality_range,
        age_range=age_range,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom
    )

    if not area_counts:
        logger.info("指定された条件に一致する桜は見つかりませんでした")
        return AreaCountResponse(total=0, areas=[])

    # 合計を計算
    total = sum(area.count for area in area_counts)
    logger.info(f"集計完了: 合計{total}件のデータを取得")

    return AreaCountResponse(total=total, areas=area_counts)
