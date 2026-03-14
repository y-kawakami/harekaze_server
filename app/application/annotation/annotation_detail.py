"""アノテーション詳細取得機能

単一画像の詳細情報取得、撮影情報・開花予想日の取得を行う。
Requirements: 4.1, 5.1-5.7, 3.4
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.domain.models.annotation import VitalityAnnotation
from app.domain.models.flowering_date_spot import FloweringDateSpot
from app.domain.models.models import EntireTree, Tree
from app.domain.services.flowering_date_service import FloweringDateService
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService


@dataclass
class AnnotationListFilter:
    """一覧フィルター条件（ナビゲーション用）"""

    status: Literal["all", "annotated", "unannotated"] = "all"
    prefecture_code: str | None = None
    vitality_value: int | None = None
    photo_date_from: date | None = None
    photo_date_to: date | None = None
    is_ready_filter: bool | None = None
    bloom_status_filter: list[str] | None = None  # 開花状態フィルター（複数指定可）
    versions_filter: list[int] | None = None  # 年度バージョンフィルター
    model_vitality_filter: int | None = None  # Admin限定: 推論モデルvitalityフィルター
    annotator_role: str = "annotator"


@dataclass
class DiagnosticsData:
    """診断値データ"""

    vitality: int | None = None
    vitality_noleaf: int | None = None
    vitality_noleaf_weight: float | None = None
    vitality_bloom: int | None = None
    vitality_bloom_weight: float | None = None
    vitality_bloom_30: int | None = None
    vitality_bloom_30_weight: float | None = None
    vitality_bloom_50: int | None = None
    vitality_bloom_50_weight: float | None = None


@dataclass
class DebugImagesData:
    """デバッグ画像URLデータ"""

    noleaf_url: str | None = None
    bloom_url: str | None = None


@dataclass
class AnnotationDetailResponse:
    """詳細レスポンス"""

    entire_tree_id: int
    tree_id: int
    image_url: str
    photo_date: datetime | None
    prefecture_name: str
    location: str
    nearest_spot_location: str | None
    flowering_date: str | None
    full_bloom_start_date: str | None
    full_bloom_end_date: str | None
    current_vitality_value: int | None
    current_index: int
    total_count: int
    prev_id: int | None
    next_id: int | None
    is_ready: bool = False
    bloom_status: str | None = None
    bloom_30_date: str | None = None
    bloom_50_date: str | None = None
    diagnostics: DiagnosticsData | None = None
    debug_images: DebugImagesData | None = None


def get_annotation_detail(
    db: Session,
    image_service: ImageService,
    flowering_date_service: FloweringDateService,
    municipality_service: MunicipalityService,
    entire_tree_id: int,
    filter_params: AnnotationListFilter,
    annotator_role: str = "annotator",
) -> AnnotationDetailResponse | None:
    """アノテーション詳細を取得

    Args:
        db: DBセッション
        image_service: 画像サービス
        flowering_date_service: 開花日サービス
        municipality_service: 自治体サービス
        entire_tree_id: 対象のEntireTree ID
        filter_params: フィルター条件（ナビゲーション計算用）
        annotator_role: アノテーターのロール（'admin' or 'annotator'）

    Returns:
        AnnotationDetailResponse | None: 詳細データまたはNone

    Raises:
        PermissionError: annotatorロールがis_ready=FALSEの画像にアクセスした場合
    """
    # 対象のEntireTreeを取得
    entire_tree = (
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
        .filter(EntireTree.id == entire_tree_id)
        .first()
    )

    if not entire_tree:
        return None

    # is_ready 状態を取得
    is_ready = False
    if entire_tree.vitality_annotation:
        is_ready = entire_tree.vitality_annotation.is_ready

    # 権限チェック: annotator ロールは is_ready=FALSE の画像にアクセスできない
    if annotator_role == "annotator":
        if not entire_tree.vitality_annotation or not is_ready:
            raise PermissionError(
                f"Image {entire_tree_id} is not ready for annotation"
            )

    # 画像URLを生成（CloudFront経由）
    image_url = image_service.get_image_url(entire_tree.image_obj_key)

    # 撮影情報を取得
    photo_date = entire_tree.photo_date
    prefecture_name = ""
    location = ""
    latitude = 0.0
    longitude = 0.0

    if entire_tree.tree:
        if entire_tree.tree.prefecture_code:
            prefecture = municipality_service.get_prefecture_by_code(
                entire_tree.tree.prefecture_code
            )
            if prefecture:
                prefecture_name = prefecture.name
        location = entire_tree.tree.location or ""
        latitude = entire_tree.tree.latitude or 0.0
        longitude = entire_tree.tree.longitude or 0.0

    # 開花予想日情報を取得
    flowering_date: str | None = None
    full_bloom_start_date: str | None = None
    full_bloom_end_date: str | None = None
    nearest_spot: FloweringDateSpot | None = None

    if latitude and longitude:
        spot = flowering_date_service.find_nearest_spot(latitude, longitude)
        if spot and photo_date:
            # 撮影日の年に合わせて日付を調整
            target_year = photo_date.year
            flowering_date = spot.flowering_date.replace(
                year=target_year).isoformat()
            full_bloom_start_date = spot.full_bloom_date.replace(
                year=target_year).isoformat()
            full_bloom_end_date = spot.full_bloom_end_date.replace(
                year=target_year).isoformat()
            nearest_spot = spot

    # 既存アノテーション値を取得
    current_vitality_value: int | None = None
    if entire_tree.vitality_annotation:
        current_vitality_value = entire_tree.vitality_annotation.vitality_value

    # ナビゲーション情報を計算
    current_index, total_count, prev_id, next_id = _calculate_navigation(
        db, entire_tree_id, filter_params
    )

    # 開花状態はDBに保存された値を使用
    bloom_status = entire_tree.bloom_status

    # 開花段階日（全ロール共通）
    bloom_30_date: str | None = None
    bloom_50_date: str | None = None
    if entire_tree.bloom_30_date:
        bloom_30_date = entire_tree.bloom_30_date.isoformat()
    if entire_tree.bloom_50_date:
        bloom_50_date = entire_tree.bloom_50_date.isoformat()

    # Admin限定: 診断値・デバッグ画像
    diagnostics: DiagnosticsData | None = None
    debug_images: DebugImagesData | None = None
    if annotator_role == "admin":
        diagnostics = DiagnosticsData(
            vitality=entire_tree.vitality,
            vitality_noleaf=entire_tree.vitality_noleaf,
            vitality_noleaf_weight=entire_tree.vitality_noleaf_weight,
            vitality_bloom=entire_tree.vitality_bloom,
            vitality_bloom_weight=entire_tree.vitality_bloom_weight,
            vitality_bloom_30=entire_tree.vitality_bloom_30,
            vitality_bloom_30_weight=entire_tree.vitality_bloom_30_weight,
            vitality_bloom_50=entire_tree.vitality_bloom_50,
            vitality_bloom_50_weight=entire_tree.vitality_bloom_50_weight,
        )
        noleaf_url: str | None = None
        bloom_url: str | None = None
        if entire_tree.debug_image_obj_key:
            noleaf_url = image_service.get_image_url(
                entire_tree.debug_image_obj_key
            )
        if entire_tree.debug_image_obj2_key:
            bloom_url = image_service.get_image_url(
                entire_tree.debug_image_obj2_key
            )
        debug_images = DebugImagesData(
            noleaf_url=noleaf_url,
            bloom_url=bloom_url,
        )

    return AnnotationDetailResponse(
        entire_tree_id=entire_tree.id,
        tree_id=entire_tree.tree_id,
        image_url=image_url,
        photo_date=photo_date,
        prefecture_name=prefecture_name,
        location=location,
        nearest_spot_location=nearest_spot.address if nearest_spot else None,
        flowering_date=flowering_date,
        full_bloom_start_date=full_bloom_start_date,
        full_bloom_end_date=full_bloom_end_date,
        current_vitality_value=current_vitality_value,
        current_index=current_index,
        total_count=total_count,
        prev_id=prev_id,
        next_id=next_id,
        is_ready=is_ready,
        bloom_status=bloom_status,
        bloom_30_date=bloom_30_date,
        bloom_50_date=bloom_50_date,
        diagnostics=diagnostics,
        debug_images=debug_images,
    )


def _calculate_navigation(
    db: Session,
    current_id: int,
    filter_params: AnnotationListFilter,
) -> tuple[int, int, int | None, int | None]:
    """ナビゲーション情報を計算

    Args:
        db: DBセッション
        current_id: 現在のEntireTree ID
        filter_params: フィルター条件

    Returns:
        tuple: (current_index, total_count, prev_id, next_id)
    """
    # フィルター条件に基づくクエリを構築
    query = (
        db.query(EntireTree)
        .join(Tree, EntireTree.tree_id == Tree.id)
        .outerjoin(
            VitalityAnnotation,
            EntireTree.id == VitalityAnnotation.entire_tree_id,
        )
    )

    # is_ready フィルター（権限に応じた処理）
    if filter_params.annotator_role == "annotator":
        # annotator ロールは自動的に is_ready=TRUE でフィルター
        query = query.filter(VitalityAnnotation.is_ready == True)  # noqa: E712
    elif filter_params.annotator_role == "admin":
        # admin ロールは is_ready フィルターパラメータを使用可能
        if filter_params.is_ready_filter is True:
            query = query.filter(
                VitalityAnnotation.is_ready == True  # noqa: E712
            )
        elif filter_params.is_ready_filter is False:
            query = query.filter(
                or_(
                    VitalityAnnotation.id.is_(None),
                    VitalityAnnotation.is_ready == False,  # noqa: E712
                )
            )

    # ステータスフィルター
    if filter_params.status == "annotated":
        query = query.filter(
            VitalityAnnotation.id.isnot(None),
            VitalityAnnotation.vitality_value.isnot(None),
        )
    elif filter_params.status == "unannotated":
        query = query.filter(
            or_(
                VitalityAnnotation.id.is_(None),
                VitalityAnnotation.vitality_value.is_(None),
            )
        )

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

    # 開花状態フィルター
    if filter_params.bloom_status_filter:
        query = query.filter(
            EntireTree.bloom_status.in_(filter_params.bloom_status_filter)
        )

    # 年度バージョンフィルター
    if filter_params.versions_filter:
        query = query.filter(
            Tree.version.in_(filter_params.versions_filter)
        )

    # Admin限定: 推論モデルvitalityフィルター
    if (
        filter_params.annotator_role == "admin"
        and filter_params.model_vitality_filter is not None
    ):
        query = query.filter(
            EntireTree.vitality == filter_params.model_vitality_filter
        )

    # 総件数
    total_count = query.count()

    # ID リストを取得（ソート順を維持）
    id_list = query.order_by(EntireTree.id.desc()).all()

    # 現在位置と前後IDを計算
    current_index = -1
    prev_id: int | None = None
    next_id: int | None = None

    for i, item in enumerate(id_list):
        if item.id == current_id:
            current_index = i
            if i > 0:
                prev_id = id_list[i - 1].id
            if i < len(id_list) - 1:
                next_id = id_list[i + 1].id
            break

    return current_index, total_count, prev_id, next_id
