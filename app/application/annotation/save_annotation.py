"""アノテーション保存機能

元気度アノテーション結果の保存を行う。
Requirements: 4.2-4.6
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain.models.annotation import VitalityAnnotation
from app.domain.models.models import EntireTree


# 有効な元気度値
VALID_VITALITY_VALUES = {1, 2, 3, 4, 5, -1}


@dataclass
class SaveAnnotationRequest:
    """アノテーション保存リクエスト"""

    entire_tree_id: int
    vitality_value: int


@dataclass
class SaveAnnotationResponse:
    """アノテーション保存レスポンス"""

    entire_tree_id: int
    vitality_value: int
    annotated_at: datetime
    annotator_id: int


def save_annotation(
    db: Session,
    annotator_id: int,
    request: SaveAnnotationRequest,
) -> SaveAnnotationResponse:
    """アノテーション結果を保存

    UPSERT: 既存レコードがあれば更新、なければ挿入。

    Args:
        db: DBセッション
        annotator_id: アノテーターID
        request: 保存リクエスト

    Returns:
        SaveAnnotationResponse: 保存結果

    Raises:
        ValueError: entire_tree_id が存在しない場合
        ValueError: vitality_value が無効な場合
    """
    # バリデーション: 元気度値
    if request.vitality_value not in VALID_VITALITY_VALUES:
        raise ValueError(
            f"vitality_value must be one of {VALID_VITALITY_VALUES}, "
            f"got {request.vitality_value}"
        )

    # バリデーション: entire_tree_id の存在確認
    entire_tree = db.get(EntireTree, request.entire_tree_id)
    if not entire_tree:
        raise ValueError(
            f"entire_tree_id {request.entire_tree_id} does not exist"
        )

    # 既存アノテーションを検索
    existing_annotation = (
        db.query(VitalityAnnotation)
        .filter(VitalityAnnotation.entire_tree_id == request.entire_tree_id)
        .first()
    )

    annotated_at = datetime.now(timezone.utc)

    if existing_annotation:
        # 更新
        existing_annotation.vitality_value = request.vitality_value
        existing_annotation.annotator_id = annotator_id
        existing_annotation.annotated_at = annotated_at
        db.commit()
        db.refresh(existing_annotation)

        return SaveAnnotationResponse(
            entire_tree_id=existing_annotation.entire_tree_id,
            vitality_value=existing_annotation.vitality_value,
            annotated_at=existing_annotation.annotated_at,
            annotator_id=existing_annotation.annotator_id,
        )
    else:
        # 新規作成
        new_annotation = VitalityAnnotation(
            entire_tree_id=request.entire_tree_id,
            vitality_value=request.vitality_value,
            annotator_id=annotator_id,
            annotated_at=annotated_at,
        )
        db.add(new_annotation)
        db.commit()
        db.refresh(new_annotation)

        return SaveAnnotationResponse(
            entire_tree_id=new_annotation.entire_tree_id,
            vitality_value=new_annotation.vitality_value,
            annotated_at=new_annotation.annotated_at,
            annotator_id=new_annotation.annotator_id,
        )
