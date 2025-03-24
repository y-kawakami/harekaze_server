from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.application.admin.common import create_tree_censor_item
from app.domain.models.models import (CensorshipStatus, EntireTree, Kobu,
                                      Mushroom, Stem, StemHole, Tengus, Tree)
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService
from app.interfaces.schemas.admin import SortOrder, TreeCensorItem
from app.interfaces.schemas.tree import TreeListItem


def get_tree_list(
    db: Session,
    municipality_service: MunicipalityService,
    image_service: ImageService,
    begin_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    municipality: Optional[str] = None,
    tree_censorship_status: Optional[List[int]] = None,
    detail_censorship_status: Optional[List[int]] = None,
    order_by: Optional[SortOrder] = None,
    page: int = 1,
    per_page: int = 20
) -> Tuple[int, List[TreeCensorItem]]:
    """
    投稿一覧を取得する

    Args:
        db: DBセッション
        municipality_service: 自治体サービス
        image_service: 画像サービス
        begin_date: 検索開始日時
        end_date: 検索終了日時
        municipality: 自治体名（部分一致で検索）
        tree_censorship_status: 全体の検閲ステータスリスト
        detail_censorship_status: 詳細の検閲ステータスリスト
        page: ページ番号
        per_page: 1ページあたりの件数

    Returns:
        Tuple[int, List[TreeCensorItem]]: 総件数と投稿一覧
    """
    # 基本クエリ
    query = db.query(Tree)

    # 日付フィルタ
    if begin_date:
        query = query.filter(Tree.created_at >= begin_date)
    if end_date:
        query = query.filter(Tree.created_at <= end_date)

    # 自治体名によるフィルタ
    if municipality:
        # 自治体名のキーワードで部分一致検索を行い、自治体コードのリストを取得
        municipality_codes = municipality_service.find_municipality_codes_by_keyword(
            municipality)

        if municipality_codes:
            query = query.filter(
                Tree.municipality_code.in_(municipality_codes))

    # 全体検閲ステータスフィルタ
    if tree_censorship_status:
        query = query.filter(
            Tree.censorship_status.in_(tree_censorship_status))

    # 詳細検閲ステータスフィルタ
    if detail_censorship_status:
        detail_conditions = []

        # Tree.contributor_censorship_status
        detail_conditions.append(
            Tree.contributor_censorship_status.in_(detail_censorship_status))

        # 関連テーブルの検閲ステータス
        # EntireTreeの検閲ステータス
        detail_conditions.append(
            Tree.id.in_(
                db.query(EntireTree.tree_id)
                .filter(EntireTree.censorship_status.in_(detail_censorship_status))
                .scalar_subquery()
            )
        )

        # Stemの検閲ステータス
        detail_conditions.append(
            Tree.id.in_(
                db.query(Stem.tree_id)
                .filter(Stem.censorship_status.in_(detail_censorship_status))
                .scalar_subquery()
            )
        )

        # StemHoleの検閲ステータス
        detail_conditions.append(
            Tree.id.in_(
                db.query(StemHole.tree_id)
                .filter(StemHole.censorship_status.in_(detail_censorship_status))
                .scalar_subquery()
            )
        )

        # Mushroomの検閲ステータス
        detail_conditions.append(
            Tree.id.in_(
                db.query(Mushroom.tree_id)
                .filter(Mushroom.censorship_status.in_(detail_censorship_status))
                .scalar_subquery()
            )
        )

        # Tengusの検閲ステータス
        detail_conditions.append(
            Tree.id.in_(
                db.query(Tengus.tree_id)
                .filter(Tengus.censorship_status.in_(detail_censorship_status))
                .scalar_subquery()
            )
        )

        # Kobuの検閲ステータス
        detail_conditions.append(
            Tree.id.in_(
                db.query(Kobu.tree_id)
                .filter(Kobu.censorship_status.in_(detail_censorship_status))
                .scalar_subquery()
            )
        )

        # ORで結合
        query = query.filter(or_(*detail_conditions))

    # 関連テーブルをプリロード
    query = query.options(
        joinedload(Tree.entire_tree),
        joinedload(Tree.stem),
        joinedload(Tree.stem_holes),
        joinedload(Tree.tengus),
        joinedload(Tree.mushrooms),
        joinedload(Tree.kobus)
    )

    # 総件数を取得
    total_count = query.count()

    # ページネーション
    offset = (page - 1) * per_page

    if order_by == SortOrder.CREATED_BY_ASC:
        query = query.order_by(Tree.created_at.asc())
    else:
        query = query.order_by(Tree.created_at.desc()).offset(
            offset).limit(per_page)

    trees = query.all()

    # レスポンスデータの作成
    items = []
    for tree in trees:
        item = create_tree_censor_item(
            tree, image_service, municipality_service)
        items.append(item)

    return total_count, items


def get_approved_tree_list(
    db: Session,
    municipality_service: MunicipalityService,
    image_service: ImageService,
    begin_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    municipality: Optional[str] = None,
    page: int = 1,
    per_page: int = 20
) -> Tuple[int, List[TreeListItem]]:
    """
    検閲済みの投稿一覧を取得する（管理者用）

    Args:
        db: DBセッション
        municipality_service: 自治体サービス
        image_service: 画像サービス
        begin_date: 検索開始日時
        end_date: 検索終了日時
        municipality: 自治体名（部分一致で検索）
        page: ページ番号
        per_page: 1ページあたりの件数

    Returns:
        Tuple[int, List[TreeListItem]]: 総件数と投稿一覧
    """
    # 基本クエリ
    query = db.query(Tree)

    # 検閲済みのもののみ取得
    query = query.filter(Tree.censorship_status == CensorshipStatus.APPROVED)

    # 日付フィルタ
    if begin_date:
        query = query.filter(Tree.created_at >= begin_date)
    if end_date:
        query = query.filter(Tree.created_at <= end_date)

    # 自治体名によるフィルタ
    if municipality:
        # 自治体名のキーワードで部分一致検索を行い、自治体コードのリストを取得
        municipality_codes = municipality_service.find_municipality_codes_by_keyword(
            municipality)

        if municipality_codes:
            query = query.filter(
                Tree.municipality_code.in_(municipality_codes))
        else:
            # 自治体名が見つからない場合は空の結果を返す
            return 0, []

    # 関連テーブルをプリロード
    query = query.options(
        joinedload(Tree.entire_tree),
        joinedload(Tree.stem),
        joinedload(Tree.stem_holes),
        joinedload(Tree.tengus),
        joinedload(Tree.mushrooms),
        joinedload(Tree.kobus)
    )

    # 総件数を取得
    total_count = query.count()

    # ページネーション
    offset = (page - 1) * per_page
    query = query.order_by(Tree.created_at.desc()).offset(
        offset).limit(per_page)

    trees = query.all()

    # レスポンスデータの作成
    items = []
    for tree in trees:
        # 自治体名を取得
        municipality = None
        if tree.municipality_code:
            municipality_obj = municipality_service.get_municipality_by_code(
                tree.municipality_code)
            if municipality_obj:
                municipality = municipality_obj.full_name()

        # 投稿者名は検閲済みの場合のみ表示
        contributor = None
        if tree.contributor_censorship_status == CensorshipStatus.APPROVED:
            contributor = tree.contributor

        # 桜全体画像の情報
        entire_tree_thumb_url = None
        if (tree.entire_tree and
                tree.entire_tree.censorship_status == CensorshipStatus.APPROVED):
            entire_tree_thumb_url = image_service.get_image_url(
                tree.entire_tree.thumb_obj_key)

        # 幹の画像情報
        stem_thumb_url = None
        if (tree.stem and
                tree.stem.censorship_status == CensorshipStatus.APPROVED):
            stem_thumb_url = image_service.get_image_url(
                tree.stem.thumb_obj_key)

        # 幹の穴の画像情報
        stem_hole_thumb_url = None
        if (tree.stem_holes and
            len(tree.stem_holes) > 0 and
                tree.stem_holes[0].censorship_status == CensorshipStatus.APPROVED):
            stem_hole_thumb_url = image_service.get_image_url(
                tree.stem_holes[0].thumb_obj_key)

        # テングス病の画像情報
        tengusu_thumb_url = None
        if (tree.tengus and
            len(tree.tengus) > 0 and
                tree.tengus[0].censorship_status == CensorshipStatus.APPROVED):
            tengusu_thumb_url = image_service.get_image_url(
                tree.tengus[0].thumb_obj_key)

        # キノコの画像情報
        mushroom_thumb_url = None
        if (tree.mushrooms and
            len(tree.mushrooms) > 0 and
                tree.mushrooms[0].censorship_status == CensorshipStatus.APPROVED):
            mushroom_thumb_url = image_service.get_image_url(
                tree.mushrooms[0].thumb_obj_key)

        # こぶの画像情報
        kobu_thumb_url = None
        if (tree.kobus and
            len(tree.kobus) > 0 and
                tree.kobus[0].censorship_status == CensorshipStatus.APPROVED):
            kobu_thumb_url = image_service.get_image_url(
                tree.kobus[0].thumb_obj_key)

        item = TreeListItem(
            tree_id=tree.id,
            entire_tree_thumb_url=entire_tree_thumb_url,
            stem_thumb_url=stem_thumb_url,
            stem_hole_thumb_url=stem_hole_thumb_url,
            mushroom_thumb_url=mushroom_thumb_url,
            tengusu_thumb_url=tengusu_thumb_url,
            kobu_thumb_url=kobu_thumb_url,
            contributor=contributor,
            location=municipality,
            latitude=tree.latitude,
            longitude=tree.longitude,
            created_at=tree.created_at
        )
        items.append(item)

    return total_count, items
