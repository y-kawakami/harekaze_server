"""CSVエクスポート機能

アノテーション結果をCSV形式でエクスポートする。
Requirements: 9.1-9.7
"""

import csv
import io
import os
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.domain.models.annotation import VitalityAnnotation
from app.domain.models.models import EntireTree, Tree
from app.domain.services.bloom_state_service import BLOOM_STATUS_LABELS

load_dotenv()

# S3 バケット設定
S3_BUCKET_NAME = os.getenv(
    "S3_CONTENTS_BUCKET", "hrkz-prd-s3-contents"
)
S3_PREFIX = "sakura_camera/media/trees"

# JST タイムゾーン
JST = timezone(timedelta(hours=9))


def export_annotation_csv(
    db: Session,
    status: Literal["all", "annotated", "unannotated"] = "all",
    prefecture_code: str | None = None,
    vitality_value: int | None = None,
    photo_date_from: date | None = None,
    photo_date_to: date | None = None,
    is_ready_filter: bool | None = None,
    bloom_status_filter: list[str] | None = None,
    annotator_role: str = "annotator",
) -> str:
    """アノテーション結果をCSV形式でエクスポート

    Args:
        db: DBセッション
        status: アノテーション状態フィルター
        prefecture_code: 都道府県コード
        vitality_value: 元気度フィルター
        photo_date_from: 撮影日開始
        photo_date_to: 撮影日終了
        is_ready_filter: 準備完了フィルター
        bloom_status_filter: 開花状態フィルター
        annotator_role: アノテーターのロール

    Returns:
        str: CSVコンテンツ（UTF-8 BOM付き）
    """
    # EntireTree を基点にクエリを構築
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
        query = query.filter(
            VitalityAnnotation.is_ready == True  # noqa: E712
        )
    elif annotator_role == "admin":
        if is_ready_filter is True:
            query = query.filter(
                VitalityAnnotation.is_ready == True  # noqa: E712
            )
        elif is_ready_filter is False:
            query = query.filter(
                or_(
                    VitalityAnnotation.id.is_(None),
                    VitalityAnnotation.is_ready == False,  # noqa: E712
                )
            )

    # ステータスフィルター
    if status == "annotated":
        query = query.filter(
            VitalityAnnotation.id.isnot(None),
            VitalityAnnotation.vitality_value.isnot(None),
        )
    elif status == "unannotated":
        query = query.filter(
            or_(
                VitalityAnnotation.id.is_(None),
                VitalityAnnotation.vitality_value.is_(None),
            )
        )

    # 都道府県フィルター
    if prefecture_code:
        query = query.filter(
            Tree.prefecture_code == prefecture_code
        )

    # 元気度フィルター
    if (
        status == "annotated"
        and vitality_value is not None
    ):
        query = query.filter(
            VitalityAnnotation.vitality_value == vitality_value
        )

    # 撮影日範囲フィルター
    if photo_date_from:
        query = query.filter(
            EntireTree.photo_date >= datetime.combine(
                photo_date_from, datetime.min.time()
            )
        )
    if photo_date_to:
        query = query.filter(
            EntireTree.photo_date <= datetime.combine(
                photo_date_to, datetime.max.time()
            )
        )

    # 開花状態フィルター
    if bloom_status_filter:
        query = query.filter(
            EntireTree.bloom_status.in_(bloom_status_filter)
        )

    entire_trees = query.order_by(EntireTree.id.desc()).all()

    # CSVを生成
    output = io.StringIO()

    # BOM を先頭に追加（Excel対応）
    output.write("\ufeff")

    writer = csv.writer(output)

    # ヘッダー行
    writer.writerow([
        "s3_path",
        "image_filename",
        "vitality_score",
        "bloom_status",
        "annotated_at",
    ])

    # データ行
    for entire_tree in entire_trees:
        image_obj_key = entire_tree.image_obj_key

        # S3パスを構成
        s3_path = (
            f"s3://{S3_BUCKET_NAME}/{S3_PREFIX}/{image_obj_key}"
        )

        # ファイル名を抽出（最後の/以降）
        image_filename = image_obj_key.split("/")[-1]

        # 元気度スコア
        annotation = entire_tree.vitality_annotation
        vitality_score = ""
        annotated_at_str = ""
        if annotation and annotation.vitality_value is not None:
            vitality_score = str(annotation.vitality_value)
        if annotation and annotation.annotated_at:
            # UTC→JST に変換してフォーマット
            dt = annotation.annotated_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            jst_dt = dt.astimezone(JST)
            annotated_at_str = jst_dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # 開花状態の日本語ラベル
        bloom_label = ""
        if entire_tree.bloom_status:
            bloom_label = BLOOM_STATUS_LABELS.get(
                entire_tree.bloom_status, ""
            )

        writer.writerow([
            s3_path,
            image_filename,
            vitality_score,
            bloom_label,
            annotated_at_str,
        ])

    return output.getvalue()
