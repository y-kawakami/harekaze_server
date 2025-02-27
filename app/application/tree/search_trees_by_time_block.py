from datetime import datetime, time, timedelta
from typing import List

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import CensorshipStatus, Tree
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import (TimeRangeTreeItem,
                                         TimeRangeTreesResponse)


def search_trees_by_time_block(
    db: Session,
    image_service: ImageService,
    municipality_service: MunicipalityService,
    reference_time: time,
    per_block_limit: int = 10,
    censorship_status: int = CensorshipStatus.APPROVED
) -> TimeRangeTreesResponse:
    """
    指定された時間帯のブロックごとの桜の木情報を取得する

    Args:
        db (Session): データベースセッション
        image_service (ImageService): 画像サービス
        municipality_service (MunicipalityService): 自治体サービス
        reference_time (time): 基準時刻
        per_block_limit (int): ブロックごとの最大取得件数
        censorship_status (int): 検閲ステータス

    Returns:
        TimeRangeTreesResponse: 時間帯別ブロック別の桜の木情報
    """
    # 1ヶ月前の日付を計算
    one_month_ago = datetime.now() - timedelta(days=30)

    # 時間範囲の計算（基準時刻から1時間前まで）
    end_time = reference_time
    start_time = (datetime.combine(datetime.today(),
                  end_time) - timedelta(hours=1)).time()

    # リポジトリのインスタンス化
    repo = TreeRepository(db)

    # 各ブロックの検索
    blocks = ["A", "B", "C"]
    block_trees = repo.find_trees_by_time_range_block(
        db, reference_time, one_month_ago, blocks, per_block_limit, censorship_status
    )

    # レスポンスを構築
    response = TimeRangeTreesResponse(
        a_block=_create_block_response(
            block_trees.get("A", []), image_service),
        b_block=_create_block_response(
            block_trees.get("B", []), image_service),
        c_block=_create_block_response(
            block_trees.get("C", []), image_service),
        reference_time=reference_time,
        start_time=start_time,
        end_time=end_time
    )

    return response


def _create_block_response(
    trees: List[Tree],
    image_service: ImageService
) -> List[TimeRangeTreeItem]:
    """
    ブロックごとのレスポンスを作成する

    Args:
        block_data (Tuple[List[Tree], int]): ブロックのデータ（樹木リストと総数）
        image_service (ImageService): 画像サービス

    Returns:
        BlockItemsResponse: ブロックごとのレスポンス
    """

    items = []
    for tree in trees:
        # 全体写真を取得
        entire_tree = None
        if tree.entire_tree:
            entire_tree = tree.entire_tree

        if not entire_tree:
            logger.warning(f"Tree {tree.uid} has no entire_tree")
            continue

        # 画像URLを取得
        image_url = image_service.get_image_url(entire_tree.image_obj_key)
        thumb_url = image_service.get_image_url(entire_tree.thumb_obj_key)

        # アイテムを作成
        item = TimeRangeTreeItem(
            uid=tree.uid,
            latitude=tree.latitude,
            longitude=tree.longitude,
            location=tree.location,
            prefecture_code=tree.prefecture_code,
            municipality_code=tree.municipality_code,
            block=tree.block,
            photo_date=tree.photo_date,
            photo_time=tree.photo_time,
            image_url=image_url,
            thumb_url=thumb_url
        )
        items.append(item)

    return items
