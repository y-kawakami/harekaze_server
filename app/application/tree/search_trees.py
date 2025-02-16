from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.domain.constants.anonymous import filter_anonymous
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import TreeSearchResponse, TreeSearchResult


def search_trees(
    db: Session,
    image_service: ImageService,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = None,
    municipality_code: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    vitality_min: Optional[int] = None,
    vitality_max: Optional[int] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    has_hole: Optional[bool] = None,
    has_tengusu: Optional[bool] = None,
    has_mushroom: Optional[bool] = None,
) -> TreeSearchResponse:
    """
    全ユーザから投稿された桜の情報の検索を行う。

    Args:
        db (Session): データベースセッション
        image_service (ImageService): 画像サービス
        latitude (Optional[float]): 検索の中心となる緯度
        longitude (Optional[float]): 検索の中心となる経度
        radius (Optional[float]): 検索範囲（メートル）
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

    Returns:
        TreeSearchResponse: 検索結果

    Raises:
        HTTPException: 検索条件が不正な場合
    """
    # 検索条件のバリデーション
    if municipality_code is None and (latitude is None or longitude is None or radius is None):
        raise HTTPException(
            status_code=400,
            detail="市区町村コード、もしくは緯度・経度・検索範囲のいずれかを指定してください"
        )

    if municipality_code is not None and (latitude is not None or longitude is not None or radius is not None):
        raise HTTPException(
            status_code=400,
            detail="市区町村コードと位置検索（緯度・経度・検索範囲）は同時に指定できません"
        )

    logger.info(
        "木の検索を開始: {}",
        "市区町村コード={}".format(municipality_code) if municipality_code else "位置=({}, {}), 範囲={}m".format(
            latitude, longitude, radius)
    )

    # 元気度の範囲を設定
    vitality_range = None
    if vitality_min is not None or vitality_max is not None:
        vitality_range = (
            vitality_min or 1,
            vitality_max or 5
        )
        logger.debug(f"元気度の範囲を指定: {vitality_range}")

    age_range = None
    if age_min is not None or age_max is not None:
        age_range = (
            age_min or 0,
            age_max or 1000
        )
        logger.debug(f"年齢の範囲を指定: {age_range}")

    # リポジトリで検索を実行
    repository = TreeRepository(db)
    trees, total = repository.search_trees(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        municipality_code=municipality_code,
        vitality_range=vitality_range,
        age_range=age_range,
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
            contributor=filter_anonymous(
                tree.contributor) if tree.contributor else None,
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
