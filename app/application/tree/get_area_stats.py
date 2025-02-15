from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import InvalidParamError, TreeNotFoundError
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import AreaStatsResponse


def get_area_stats(
    db: Session,
    prefecture_code: Optional[str],
    municipality_code: Optional[str],
) -> AreaStatsResponse:
    """
    指定された地域（都道府県または市区町村）の統計情報を取得する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        prefecture_code (Optional[str]): 都道府県コード（JIS X 0401に準拠）
        municipality_code (Optional[str]): 市区町村コード（JIS X 0402に準拠）

    Returns:
        AreaStatsResponse: 地域の統計情報

    Raises:
        InvalidParamError: 都道府県コードと市区町村コードの両方が指定されていない場合
        TreeNotFoundError: 指定された地域の統計情報が見つからない場合
    """
    logger.info(
        f"地域の統計情報取得開始: prefecture_code={prefecture_code}, municipality_code={municipality_code}")

    if not municipality_code and not prefecture_code:
        logger.error("都道府県コードと市区町村コードの両方が指定されていません")
        raise InvalidParamError(
            reason="都道府県コードまたは市区町村コードのいずれかを指定してください"
        )

    repository = TreeRepository(db)

    if municipality_code:
        # 市区町村の統計情報を取得
        stats = repository.get_municipality_stats(municipality_code)
        if not stats:
            logger.warning(f"市区町村の統計情報が見つかりません: code={municipality_code}")
            raise TreeNotFoundError(tree_id=municipality_code)
    else:
        # 都道府県の統計情報を取得
        assert prefecture_code is not None  # この時点でprefecture_codeはNoneではない
        stats = repository.get_prefecture_stats(prefecture_code)
        if not stats:
            logger.warning(f"都道府県の統計情報が見つかりません: code={prefecture_code}")
            raise TreeNotFoundError(tree_id=prefecture_code)

    logger.info(f"統計情報の取得が完了: location={stats.location}")

    return AreaStatsResponse(
        total_trees=stats.total_trees,
        location=stats.location,
        # 元気度の分布
        vitality1_count=stats.vitality1_count,
        vitality2_count=stats.vitality2_count,
        vitality3_count=stats.vitality3_count,
        vitality4_count=stats.vitality4_count,
        vitality5_count=stats.vitality5_count,
        # 樹齢の分布
        age20_count=stats.age20_count,
        age30_count=stats.age30_count,
        age40_count=stats.age40_count,
        age50_count=stats.age50_count,
        age60_count=stats.age60_count,
        # 問題の分布
        hole_count=stats.hole_count,
        tengusu_count=stats.tengus_count,
        mushroom_count=stats.mushroom_count,
        # 位置情報
        latitude=stats.latitude,
        longitude=stats.longitude,
    )
