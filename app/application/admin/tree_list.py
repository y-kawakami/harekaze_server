from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.application.admin.common import create_tree_censor_item
from app.domain.models.models import (EntireTree, Kobu, Mushroom, Stem,
                                      StemHole, Tengus, Tree)
from app.interfaces.schemas.admin import TreeCensorItem


def get_tree_list(
    db: Session,
    begin_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tree_censorship_status: Optional[List[int]] = None,
    detail_censorship_status: Optional[List[int]] = None,
    page: int = 1,
    per_page: int = 20
) -> Tuple[int, List[TreeCensorItem]]:
    """
    投稿一覧を取得する

    Args:
        db: DBセッション
        begin_date: 検索開始日時
        end_date: 検索終了日時
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
    query = query.order_by(Tree.created_at.desc()).offset(
        offset).limit(per_page)

    trees = query.all()

    # レスポンスデータの作成
    items = []
    for tree in trees:
        item = create_tree_censor_item(tree)
        items.append(item)

    return total_count, items
