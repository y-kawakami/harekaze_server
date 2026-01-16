"""is_ready フラグ更新ユースケース

単一画像の is_ready フラグを更新する。
Requirements: 4.1, 4.3, 4.4
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain.models.annotation import VitalityAnnotation
from app.domain.models.models import EntireTree


@dataclass
class UpdateIsReadyRequest:
    """is_ready更新リクエスト"""
    entire_tree_id: int
    is_ready: bool


@dataclass
class UpdateIsReadyResponse:
    """is_ready更新レスポンス"""
    entire_tree_id: int
    is_ready: bool
    updated_at: datetime


def update_is_ready(
    db: Session,
    annotator_id: int,
    request: UpdateIsReadyRequest,
) -> UpdateIsReadyResponse:
    """is_ready フラグを更新する

    VitalityAnnotation レコードが存在しない場合は新規作成する。

    Args:
        db: DBセッション
        annotator_id: 実行者のアノテーターID
        request: 更新リクエスト

    Returns:
        UpdateIsReadyResponse: 更新結果

    Raises:
        ValueError: 対象の EntireTree が存在しない場合
    """
    # EntireTree の存在確認
    entire_tree = db.query(EntireTree).filter(
        EntireTree.id == request.entire_tree_id
    ).first()

    if not entire_tree:
        raise ValueError(
            f"EntireTree with id {request.entire_tree_id} not found"
        )

    # 既存の VitalityAnnotation を検索
    annotation = db.query(VitalityAnnotation).filter(
        VitalityAnnotation.entire_tree_id == request.entire_tree_id
    ).first()

    now = datetime.now(timezone.utc)

    if annotation:
        # 既存レコードを更新
        annotation.is_ready = request.is_ready
        annotation.updated_at = now
    else:
        # 新規作成（vitality_value=NULL）
        annotation = VitalityAnnotation(
            entire_tree_id=request.entire_tree_id,
            vitality_value=None,
            is_ready=request.is_ready,
            annotator_id=annotator_id,
            annotated_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(annotation)

    db.commit()
    db.refresh(annotation)

    return UpdateIsReadyResponse(
        entire_tree_id=annotation.entire_tree_id,
        is_ready=annotation.is_ready,
        updated_at=annotation.updated_at,
    )


@dataclass
class UpdateIsReadyBatchRequest:
    """is_readyバッチ更新リクエスト"""
    entire_tree_ids: list[int]
    is_ready: bool


@dataclass
class UpdateIsReadyBatchResponse:
    """is_readyバッチ更新レスポンス"""
    updated_count: int
    updated_ids: list[int]


def update_is_ready_batch(
    db: Session,
    annotator_id: int,
    request: UpdateIsReadyBatchRequest,
) -> UpdateIsReadyBatchResponse:
    """複数画像の is_ready フラグを一括更新する

    指定されたIDのうち、存在するEntireTreeのみ更新する。
    存在しないIDはスキップされる。

    Args:
        db: DBセッション
        annotator_id: 実行者のアノテーターID
        request: バッチ更新リクエスト

    Returns:
        UpdateIsReadyBatchResponse: 更新結果
    """
    if not request.entire_tree_ids:
        return UpdateIsReadyBatchResponse(
            updated_count=0,
            updated_ids=[],
        )

    # 存在するEntireTreeのIDリストを取得
    existing_trees = db.query(EntireTree).filter(
        EntireTree.id.in_(request.entire_tree_ids)
    ).all()

    if not existing_trees:
        return UpdateIsReadyBatchResponse(
            updated_count=0,
            updated_ids=[],
        )

    existing_ids = [tree.id for tree in existing_trees]
    now = datetime.now(timezone.utc)
    updated_ids = []

    for entire_tree_id in existing_ids:
        # 既存のVitalityAnnotationを検索
        annotation = db.query(VitalityAnnotation).filter(
            VitalityAnnotation.entire_tree_id == entire_tree_id
        ).first()

        if annotation:
            # 既存レコードを更新
            annotation.is_ready = request.is_ready
            annotation.updated_at = now
        else:
            # 新規作成（vitality_value=NULL）
            annotation = VitalityAnnotation(
                entire_tree_id=entire_tree_id,
                vitality_value=None,
                is_ready=request.is_ready,
                annotator_id=annotator_id,
                annotated_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(annotation)

        updated_ids.append(entire_tree_id)

    db.commit()

    return UpdateIsReadyBatchResponse(
        updated_count=len(updated_ids),
        updated_ids=updated_ids,
    )
