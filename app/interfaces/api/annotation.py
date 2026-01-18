"""アノテーションAPIエンドポイント

GET /annotation_api/trees: 一覧取得・フィルタリング
GET /annotation_api/trees/{entire_tree_id}: 詳細取得
POST /annotation_api/trees/{entire_tree_id}/annotation: アノテーション保存
GET /annotation_api/prefectures: 都道府県一覧
GET /annotation_api/export/csv: CSVエクスポート

Requirements: 2-6, 9
"""

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.annotation.annotation_detail import (
    AnnotationListFilter as DetailFilter,
    get_annotation_detail,
)
from app.application.annotation.annotation_list import (
    AnnotationListFilter,
    get_annotation_list,
)
from app.application.annotation.export_csv import export_annotation_csv
from app.application.annotation.save_annotation import (
    SaveAnnotationRequest,
    save_annotation,
)
from app.application.annotation.update_is_ready import (
    UpdateIsReadyBatchRequest as UpdateIsReadyBatchUseCaseRequest,
    UpdateIsReadyRequest as UpdateIsReadyUseCaseRequest,
    update_is_ready,
    update_is_ready_batch,
)
from app.domain.models.annotation import Annotator
from app.domain.services.flowering_date_service import (
    get_flowering_date_service,
)
from app.domain.services.image_service import get_image_service
from app.domain.services.municipality_service import (
    get_municipality_service,
)
from app.infrastructure.database.database import get_db
from app.interfaces.api.annotation_auth import get_current_annotator, require_admin
from app.interfaces.schemas.annotation import (
    AnnotationDetailResponse,
    AnnotationListItemResponse,
    AnnotationListResponse,
    AnnotationRequest,
    AnnotationStatsResponse,
    PrefectureListResponse,
    PrefectureResponse,
    SaveAnnotationResponse,
    UpdateIsReadyBatchRequest,
    UpdateIsReadyBatchResponse,
    UpdateIsReadyRequest,
    UpdateIsReadyResponse,
)

router = APIRouter(
    prefix="",
    tags=["annotation"]
)


@router.get("/trees", response_model=AnnotationListResponse)
async def get_trees(
    status_filter: Literal["all", "annotated", "unannotated"] = Query(
        "all", alias="status", description="アノテーション状態フィルター"),
    prefecture_code: Optional[str] = Query(
        None, description="都道府県コード"),
    vitality_value: Optional[int] = Query(
        None, description="元気度（1-5または-1）"),
    photo_date_from: Optional[date] = Query(
        None, description="撮影日開始（YYYY-MM-DD）"),
    photo_date_to: Optional[date] = Query(
        None, description="撮影日終了（YYYY-MM-DD）"),
    is_ready_filter: Optional[bool] = Query(
        None, alias="is_ready", description="準備完了フィルター（adminのみ有効）"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    current_annotator: Annotator = Depends(get_current_annotator),
    db: Session = Depends(get_db),
) -> AnnotationListResponse:
    """
    桜画像一覧を取得する

    フィルター条件:
    - status: all（全て）/ annotated（入力済み）/ unannotated（未入力）
    - prefecture_code: 都道府県コード
    - vitality_value: 元気度（入力済み選択時のみ有効）
    - photo_date_from: 撮影日開始（YYYY-MM-DD）
    - photo_date_to: 撮影日終了（YYYY-MM-DD）
    - is_ready: 準備完了フィルター（adminのみ有効）
    """
    image_service = get_image_service()
    municipality_service = get_municipality_service()

    filter_params = AnnotationListFilter(
        status=status_filter,
        prefecture_code=prefecture_code,
        vitality_value=vitality_value,
        photo_date_from=photo_date_from,
        photo_date_to=photo_date_to,
        is_ready_filter=is_ready_filter,
        page=page,
        per_page=per_page,
    )

    result = get_annotation_list(
        db=db,
        image_service=image_service,
        municipality_service=municipality_service,
        filter_params=filter_params,
        annotator_role=current_annotator.role,
    )

    return AnnotationListResponse(
        items=[
            AnnotationListItemResponse(
                entire_tree_id=item.entire_tree_id,
                tree_id=item.tree_id,
                thumb_url=item.thumb_url,
                prefecture_name=item.prefecture_name,
                location=item.location,
                annotation_status=item.annotation_status,
                vitality_value=item.vitality_value,
                is_ready=item.is_ready,
            )
            for item in result.items
        ],
        stats=AnnotationStatsResponse(
            total_count=result.stats.total_count,
            annotated_count=result.stats.annotated_count,
            unannotated_count=result.stats.unannotated_count,
            vitality_1_count=result.stats.vitality_1_count,
            vitality_2_count=result.stats.vitality_2_count,
            vitality_3_count=result.stats.vitality_3_count,
            vitality_4_count=result.stats.vitality_4_count,
            vitality_5_count=result.stats.vitality_5_count,
            vitality_minus1_count=result.stats.vitality_minus1_count,
            ready_count=result.stats.ready_count,
            not_ready_count=result.stats.not_ready_count,
        ),
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


@router.get("/trees/{entire_tree_id}", response_model=AnnotationDetailResponse)
async def get_tree_detail(
    entire_tree_id: int,
    status_filter: Literal["all", "annotated", "unannotated"] = Query(
        "all", alias="status", description="アノテーション状態フィルター"),
    prefecture_code: Optional[str] = Query(
        None, description="都道府県コード"),
    vitality_value: Optional[int] = Query(
        None, description="元気度（1-5または-1）"),
    photo_date_from: Optional[date] = Query(
        None, description="撮影日開始（YYYY-MM-DD）"),
    photo_date_to: Optional[date] = Query(
        None, description="撮影日終了（YYYY-MM-DD）"),
    is_ready_filter: Optional[bool] = Query(
        None, alias="is_ready",
        description="準備完了フィルター（adminのみ有効、ナビゲーション用）"),
    current_annotator: Annotator = Depends(get_current_annotator),
    db: Session = Depends(get_db),
) -> AnnotationDetailResponse:
    """
    桜画像の詳細情報を取得する

    ナビゲーション用のフィルター条件を保持し、前後のIDを計算する。
    annotator ロールが is_ready=FALSE の画像にアクセスした場合は 403 を返す。
    """
    image_service = get_image_service()
    flowering_date_service = get_flowering_date_service()
    municipality_service = get_municipality_service()

    filter_params = DetailFilter(
        status=status_filter,
        prefecture_code=prefecture_code,
        vitality_value=vitality_value,
        photo_date_from=photo_date_from,
        photo_date_to=photo_date_to,
        is_ready_filter=is_ready_filter,
        annotator_role=current_annotator.role,
    )

    try:
        result = get_annotation_detail(
            db=db,
            image_service=image_service,
            flowering_date_service=flowering_date_service,
            municipality_service=municipality_service,
            entire_tree_id=entire_tree_id,
            filter_params=filter_params,
            annotator_role=current_annotator.role,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された画像が見つかりません",
        )

    return AnnotationDetailResponse(
        entire_tree_id=result.entire_tree_id,
        tree_id=result.tree_id,
        image_url=result.image_url,
        photo_date=result.photo_date,
        prefecture_name=result.prefecture_name,
        location=result.location,
        flowering_date=result.flowering_date,
        full_bloom_start_date=result.full_bloom_start_date,
        full_bloom_end_date=result.full_bloom_end_date,
        current_vitality_value=result.current_vitality_value,
        current_index=result.current_index,
        total_count=result.total_count,
        prev_id=result.prev_id,
        next_id=result.next_id,
        is_ready=result.is_ready,
    )


@router.post(
    "/trees/{entire_tree_id}/annotation",
    response_model=SaveAnnotationResponse
)
async def post_annotation(
    entire_tree_id: int,
    request: AnnotationRequest,
    current_annotator: Annotator = Depends(get_current_annotator),
    db: Session = Depends(get_db),
) -> SaveAnnotationResponse:
    """
    アノテーション結果を保存する

    既存のアノテーションがある場合は上書きする（UPSERT）。
    """
    try:
        save_request = SaveAnnotationRequest(
            entire_tree_id=entire_tree_id,
            vitality_value=request.vitality_value,
        )

        result = save_annotation(
            db=db,
            annotator_id=current_annotator.id,
            request=save_request,
        )

        return SaveAnnotationResponse(
            entire_tree_id=result.entire_tree_id,
            vitality_value=result.vitality_value,
            annotated_at=result.annotated_at,
            annotator_id=result.annotator_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/prefectures", response_model=PrefectureListResponse)
async def get_prefectures(
    _: Annotator = Depends(get_current_annotator),
) -> PrefectureListResponse:
    """
    都道府県一覧を取得する
    """
    municipality_service = get_municipality_service()

    return PrefectureListResponse(
        prefectures=[
            PrefectureResponse(
                code=p.code,
                name=p.name,
            )
            for p in municipality_service.prefectures
        ]
    )


@router.get("/export/csv")
async def export_csv(
    include_undiagnosable: bool = Query(
        True, description="診断不可（-1）を含めるか"),
    _: Annotator = Depends(get_current_annotator),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    アノテーション結果をCSV形式でエクスポートする

    CSVカラム:
    - s3_path: S3パス（s3://bucket/prefix/key形式）
    - image_filename: 画像ファイル名
    - vitality_score: 元気度スコア（1-5または-1）
    """
    csv_content = export_annotation_csv(
        db=db,
        include_undiagnosable=include_undiagnosable,
    )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=annotations.csv",
        },
    )


@router.patch(
    "/trees/{entire_tree_id}/is_ready",
    response_model=UpdateIsReadyResponse
)
async def update_tree_is_ready(
    entire_tree_id: int,
    request: UpdateIsReadyRequest,
    current_annotator: Annotator = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UpdateIsReadyResponse:
    """
    画像の is_ready フラグを更新する（管理者専用）

    管理者がアノテーション対象画像を選別するためのエンドポイント。
    """
    try:
        use_case_request = UpdateIsReadyUseCaseRequest(
            entire_tree_id=entire_tree_id,
            is_ready=request.is_ready,
        )

        result = update_is_ready(
            db=db,
            annotator_id=current_annotator.id,
            request=use_case_request,
        )

        return UpdateIsReadyResponse(
            entire_tree_id=result.entire_tree_id,
            is_ready=result.is_ready,
            updated_at=result.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/trees/is_ready/batch",
    response_model=UpdateIsReadyBatchResponse
)
async def update_trees_is_ready_batch(
    request: UpdateIsReadyBatchRequest,
    current_annotator: Annotator = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UpdateIsReadyBatchResponse:
    """
    複数画像の is_ready フラグを一括更新する（管理者専用）

    管理者が複数のアノテーション対象画像を一括で選別するためのエンドポイント。
    存在しないIDはスキップされる。
    """
    use_case_request = UpdateIsReadyBatchUseCaseRequest(
        entire_tree_ids=request.entire_tree_ids,
        is_ready=request.is_ready,
    )

    result = update_is_ready_batch(
        db=db,
        annotator_id=current_annotator.id,
        request=use_case_request,
    )

    return UpdateIsReadyBatchResponse(
        updated_count=result.updated_count,
        updated_ids=result.updated_ids,
    )
