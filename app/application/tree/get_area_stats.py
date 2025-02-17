from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import (InvalidParamError,
                                        MunicipalityNotFoundError,
                                        PrefectureNotFoundError)
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import AreaStatsImage, AreaStatsResponse


def get_area_stats(
    db: Session,
    prefecture_code: Optional[str],
    municipality_code: Optional[str],
    image_service: ImageService,
    municipality_service: MunicipalityService,
) -> AreaStatsResponse:
    """指定された地域の統計情報を取得する

    Args:
        db (Session): データベースセッション
        prefecture_code (Optional[str]): 都道府県コード
        municipality_code (Optional[str]): 市区町村コード
        image_service (ImageService): 画像サービス

    Returns:
        AreaStatsResponse: 地域の統計情報
            - 基本統計情報（total_trees, location等）
            - 元気度の分布（vitality1_count等）
            - 樹齢の分布（age20_count等）
            - 問題の分布（hole_count等）
            - 位置情報（latitude, longitude）
            - 画像情報（hole_images, tengusu_images, mushroom_images, kobu_images）

    Raises:
        InvalidParamError: 都道府県コードと市区町村コードの両方が指定されていない場合
        TreeNotFoundError: 指定された地域の統計情報が見つからない場合
    """
    # prefecture_codeとmunicipality_codeのいずれか一方のみが指定されていることをチェック
    if prefecture_code is not None and municipality_code is not None:
        logger.error("都道府県コードと市区町村コードのいずれか一方のみを指定する必要があります")
        raise InvalidParamError(
            reason="都道府県コードと市区町村コードのいずれか一方のみを指定してください"
        )

    logger.info(
        f"地域の統計情報取得開始: prefecture_code={prefecture_code}, municipality_code={municipality_code}")

    if not municipality_code and not prefecture_code:
        logger.error("都道府県コードと市区町村コードの両方が指定されていません")
        raise InvalidParamError(
            reason="都道府県コードまたは市区町村コードのいずれかを指定してください"
        )

    repository = TreeRepository(db)

    # 基本的な統計情報を取得
    latitude = 0.0
    longitude = 0.0
    location = ''
    stats = repository.get_area_stats(
        prefecture_code=prefecture_code, municipality_code=municipality_code)

    if municipality_code:
        municipality = municipality_service.get_municipality_by_code(
            municipality_code)
        if not municipality:
            raise MunicipalityNotFoundError(
                municipality_code=municipality_code)
        latitude = municipality.latitude
        longitude = municipality.longitude
        location = municipality.jititai
    else:
        # 都道府県の統計情報を取得
        assert prefecture_code is not None  # この時点でprefecture_codeはNoneではない
        prefecture = municipality_service.get_prefecture_by_code(
            prefecture_code)
        if not prefecture:
            raise PrefectureNotFoundError(prefecture_code=prefecture_code)
        latitude = prefecture.latitude
        longitude = prefecture.longitude
        location = prefecture.name

    if not stats:
        logger.warning(f"市区町村の統計情報が見つかりません: code={municipality_code}")
        response = AreaStatsResponse.get_default()
        response.location = location
        response.latitude = latitude
        response.longitude = longitude
        return response

    # 関連エンティティの情報を取得
    related_entities = repository.list_tree_related_entities_in_region(
        prefecture_code=prefecture_code,
        municipality_code=municipality_code
    )

    logger.info(
        f"関連エンティティの取得完了: "
        f"stem_holes={len(related_entities.stem_holes)}件, "
        f"tengus={len(related_entities.tengus)}件, "
        f"mushrooms={len(related_entities.mushrooms)}件, "
        f"kobus={len(related_entities.kobus)}件"
    )

    # 画像情報のリストを作成
    hole_images = [
        AreaStatsImage(
            id=str(hole.uid),
            image_url=image_service.get_image_url(str(hole.image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(hole.thumb_obj_key))
        )
        for hole in related_entities.stem_holes
    ]

    tengusu_images = [
        AreaStatsImage(
            id=str(tengu.uid),
            image_url=image_service.get_image_url(str(tengu.image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tengu.thumb_obj_key))
        )
        for tengu in related_entities.tengus
    ]

    mushroom_images = [
        AreaStatsImage(
            id=str(mushroom.uid),
            image_url=image_service.get_image_url(str(mushroom.image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(mushroom.thumb_obj_key))
        )
        for mushroom in related_entities.mushrooms
    ]

    kobu_images = [
        AreaStatsImage(
            id=str(kobu.uid),
            image_url=image_service.get_image_url(str(kobu.image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(kobu.thumb_obj_key))
        )
        for kobu in related_entities.kobus
    ]

    # 統計情報を作成
    response = AreaStatsResponse(
        total_trees=stats.total_trees,
        location=location,
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
        # 問題の分布（関連エンティティの実際の件数を使用）
        hole_count=len(related_entities.stem_holes),
        tengusu_count=len(related_entities.tengus),
        mushroom_count=len(related_entities.mushrooms),
        kobu_count=len(related_entities.kobus),
        # 位置情報
        latitude=latitude,
        longitude=longitude,
        # 画像情報
        hole_images=hole_images,
        tengusu_images=tengusu_images,
        mushroom_images=mushroom_images,
        kobu_images=kobu_images
    )

    logger.info(f"統計情報の取得が完了: location={location}")
    return response
