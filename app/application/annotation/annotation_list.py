"""アノテーション一覧取得機能

桜画像一覧の取得・フィルタリング・統計情報取得を行う。
Requirements: 2.1-2.5, 3.1-3.6, 3.1, 3.2, 3.3, 7.1, 7.2
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.domain.models.annotation import VitalityAnnotation
from app.domain.models.models import EntireTree, Tree
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService


@dataclass
class AnnotationListFilter:
    """一覧フィルター条件"""

    status: Literal["all", "annotated", "unannotated"] = "all"
    prefecture_code: str | None = None
    vitality_value: int | None = None
    photo_date_from: date | None = None
    photo_date_to: date | None = None
    is_ready_filter: bool | None = None  # adminのみ使用可能
    page: int = 1
    per_page: int = 20


@dataclass
class AnnotationListItem:
    """一覧アイテム"""

    entire_tree_id: int
    tree_id: int
    thumb_url: str
    prefecture_name: str
    location: str
    annotation_status: Literal["annotated", "unannotated"]
    vitality_value: int | None
    is_ready: bool


@dataclass
class AnnotationStats:
    """統計情報"""

    total_count: int
    annotated_count: int
    unannotated_count: int
    vitality_1_count: int
    vitality_2_count: int
    vitality_3_count: int
    vitality_4_count: int
    vitality_5_count: int
    vitality_minus1_count: int
    ready_count: int = 0
    not_ready_count: int = 0


@dataclass
class AnnotationListResponse:
    """一覧レスポンス"""

    items: list[AnnotationListItem]
    stats: AnnotationStats
    total: int
    page: int
    per_page: int


def get_annotation_list(
    db: Session,
    image_service: ImageService,
    municipality_service: MunicipalityService,
    filter_params: AnnotationListFilter,
    annotator_role: str = "annotator",
) -> AnnotationListResponse:
    """フィルタリング付きアノテーション一覧を取得

    Args:
        db: DBセッション
        image_service: 画像サービス
        municipality_service: 自治体サービス
        filter_params: フィルター条件
        annotator_role: アノテーターのロール（'admin' or 'annotator'）

    Returns:
        AnnotationListResponse: 一覧データと統計情報
    """
    # 基本クエリ: EntireTree を基点に Tree と VitalityAnnotation を JOIN
    query = (
        db.query(EntireTree)
        .join(Tree, EntireTree.tree_id == Tree.id)
        .outerjoin(
            VitalityAnnotation,
            EntireTree.id == VitalityAnnotation.entire_tree_id,
        )
        .options(
            joinedload(EntireTree.tree),
            joinedload(EntireTree.vitality_annotation),
        )
    )

    # is_ready フィルター（権限に応じた処理）
    if annotator_role == "annotator":
        # annotator ロールは自動的に is_ready=TRUE でフィルター
        query = query.filter(VitalityAnnotation.is_ready == True)  # noqa: E712
    elif annotator_role == "admin":
        # admin ロールは is_ready フィルターパラメータを使用可能
        if filter_params.is_ready_filter is not None:
            query = query.filter(
                VitalityAnnotation.is_ready == filter_params.is_ready_filter
            )

    # ステータスフィルター
    if filter_params.status == "annotated":
        query = query.filter(VitalityAnnotation.id.isnot(None))
    elif filter_params.status == "unannotated":
        query = query.filter(VitalityAnnotation.id.is_(None))

    # 都道府県フィルター
    if filter_params.prefecture_code:
        query = query.filter(
            Tree.prefecture_code == filter_params.prefecture_code
        )

    # 元気度フィルター（入力済み選択時のみ有効）
    if (
        filter_params.status == "annotated"
        and filter_params.vitality_value is not None
    ):
        query = query.filter(
            VitalityAnnotation.vitality_value == filter_params.vitality_value
        )

    # 撮影日範囲フィルター
    if filter_params.photo_date_from:
        query = query.filter(
            EntireTree.photo_date >= datetime.combine(
                filter_params.photo_date_from, datetime.min.time()
            )
        )
    if filter_params.photo_date_to:
        query = query.filter(
            EntireTree.photo_date <= datetime.combine(
                filter_params.photo_date_to, datetime.max.time()
            )
        )

    # 総件数を取得（ページネーション前）
    total_count = query.count()

    # ページネーション
    offset = (filter_params.page - 1) * filter_params.per_page
    query = (
        query.order_by(EntireTree.id.desc())
        .offset(offset)
        .limit(filter_params.per_page)
    )

    entire_trees = query.all()

    # レスポンスデータの作成
    items: list[AnnotationListItem] = []
    for entire_tree in entire_trees:
        # 都道府県名を取得
        prefecture_name = ""
        if entire_tree.tree and entire_tree.tree.prefecture_code:
            prefecture = municipality_service.get_prefecture_by_code(
                entire_tree.tree.prefecture_code
            )
            if prefecture:
                prefecture_name = prefecture.name

        # 撮影場所を取得
        location = ""
        if entire_tree.tree and entire_tree.tree.location:
            location = entire_tree.tree.location

        # アノテーション状態と元気度、is_ready を取得
        annotation_status: Literal["annotated", "unannotated"] = "unannotated"
        vitality_value: int | None = None
        is_ready: bool = False
        if entire_tree.vitality_annotation:
            annotation_status = "annotated"
            vitality_value = entire_tree.vitality_annotation.vitality_value
            is_ready = entire_tree.vitality_annotation.is_ready

        # サムネイルURLを生成
        thumb_url = image_service.get_image_url(entire_tree.thumb_obj_key)

        items.append(
            AnnotationListItem(
                entire_tree_id=entire_tree.id,
                tree_id=entire_tree.tree_id,
                thumb_url=thumb_url,
                prefecture_name=prefecture_name,
                location=location,
                annotation_status=annotation_status,
                vitality_value=vitality_value,
                is_ready=is_ready,
            )
        )

    # 統計情報を取得
    stats = get_annotation_stats(db, annotator_role)

    return AnnotationListResponse(
        items=items,
        stats=stats,
        total=total_count,
        page=filter_params.page,
        per_page=filter_params.per_page,
    )


def get_annotation_stats(
    db: Session, annotator_role: str = "annotator"
) -> AnnotationStats:
    """統計情報を取得

    Args:
        db: DBセッション
        annotator_role: アノテーターのロール（'admin' or 'annotator'）

    Returns:
        AnnotationStats: 統計情報
    """
    # annotator ロールの場合は is_ready=TRUE のみを対象とした統計
    is_ready_filter = annotator_role == "annotator"

    if is_ready_filter:
        # is_ready=TRUE のレコードのみを対象
        base_query = db.query(VitalityAnnotation).filter(
            VitalityAnnotation.is_ready == True  # noqa: E712
        )
        # 全件数は is_ready=TRUE のアノテーション済み件数
        total_count = base_query.count()
        annotated_count = (
            base_query.filter(
                VitalityAnnotation.vitality_value.isnot(None)
            ).count()
        )
    else:
        # admin は全件対象
        total_count = db.query(func.count(EntireTree.id)).scalar() or 0
        annotated_count = (
            db.query(func.count(VitalityAnnotation.id)).scalar() or 0
        )

    # 未入力件数
    unannotated_count = total_count - annotated_count

    # 元気度別件数
    vitality_counts = {}
    for value in [1, 2, 3, 4, 5, -1]:
        vitality_query = db.query(func.count(VitalityAnnotation.id)).filter(
            VitalityAnnotation.vitality_value == value
        )
        if is_ready_filter:
            vitality_query = vitality_query.filter(
                VitalityAnnotation.is_ready == True  # noqa: E712
            )
        count = vitality_query.scalar() or 0
        vitality_counts[value] = count

    # is_ready 統計（admin のみ意味がある）
    ready_count = (
        db.query(func.count(VitalityAnnotation.id))
        .filter(VitalityAnnotation.is_ready == True)  # noqa: E712
        .scalar()
        or 0
    )
    not_ready_count = (
        db.query(func.count(VitalityAnnotation.id))
        .filter(VitalityAnnotation.is_ready == False)  # noqa: E712
        .scalar()
        or 0
    )

    return AnnotationStats(
        total_count=total_count,
        annotated_count=annotated_count,
        unannotated_count=unannotated_count,
        vitality_1_count=vitality_counts[1],
        vitality_2_count=vitality_counts[2],
        vitality_3_count=vitality_counts[3],
        vitality_4_count=vitality_counts[4],
        vitality_5_count=vitality_counts[5],
        vitality_minus1_count=vitality_counts[-1],
        ready_count=ready_count,
        not_ready_count=not_ready_count,
    )
