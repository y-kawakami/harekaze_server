from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import TreeSearchResponse, TreeSearchResult


def search_trees(
    db: Session,
    current_user: User,
    latitude: float,
    longitude: float,
    radius: float,
    municipality_code: Optional[str],
    page: int,
    per_page: int,
    vitality_min: Optional[int],
    vitality_max: Optional[int],
    age_min: Optional[int],
    age_max: Optional[int],
    has_hole: Optional[bool],
    has_tengusu: Optional[bool],
    has_mushroom: Optional[bool],
    image_service: ImageService,
) -> TreeSearchResponse:
    """
    全ユーザから投稿された桜の情報の検索を行う。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        latitude (float): 検索の中心となる緯度
        longitude (float): 検索の中心となる経度
        radius (float): 検索範囲（メートル）
        municipality_code (Optional[str]): 市区町村コード（JIS X 0402に準拠）
        page (int): ページ番号
        per_page (int): 1ページあたりの件数
        vitality_min (Optional[int]): 元気度の最小値（1-5）
        vitality_max (Optional[int]): 元気度の最大値（1-5）
        age_min (Optional[int]): 年齢の最小値（0-100）
        age_max (Optional[int]): 年齢の最大値（0-1000）
        has_hole (Optional[bool]): 幹の穴の有無
        has_tengusu (Optional[bool]): テングス病の有無
        has_mushroom (Optional[bool]): キノコの有無
        image_service (ImageService): 画像サービス

    Returns:
        TreeSearchResponse: 検索結果
    """
    logger.info(
        f"木の検索を開始: 位置=({latitude}, {longitude}), 範囲={radius}m")

    # 元気度の範囲を設定
    vitality_range = None
    if vitality_min is not None or vitality_max is not None:
        vitality_range = (
            vitality_min or 1,
            vitality_max or 5
        )
        logger.debug(f"元気度の範囲を指定: {vitality_range}")

    # リポジトリで検索を実行
    repository = TreeRepository(db)
    trees, total = repository.search_trees(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        vitality_range=vitality_range,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom,
        offset=(page - 1) * per_page,
        limit=per_page
    )
    logger.info(f"検索完了: {total}件中{len(trees)}件を取得")

    # レスポンスの作成
    return TreeSearchResponse(
        total=total,
        trees=[TreeSearchResult(
            id=tree.uid,
            tree_number=f"#{tree.id}",
            contributor=tree.contributor,
            vitality=tree.vitality,
            image_thumb_url=image_service.get_image_url(tree.thumb_obj_key),
            latitude=tree.latitude,
            longitude=tree.longitude,
            location=tree.location,
            prefecture_code=tree.prefecture_code or None,
            municipality_code=tree.municipality_code or None,
            created_at=tree.created_at,
            age=tree.stem.age if tree.stem else None
        ) for tree in trees]
    )
