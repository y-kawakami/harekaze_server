"""CSVエクスポート機能

アノテーション結果をCSV形式でエクスポートする。
Requirements: 9.1-9.7
"""

import csv
import io
import os

from dotenv import load_dotenv
from sqlalchemy.orm import Session, joinedload

from app.domain.models.annotation import VitalityAnnotation

load_dotenv()

# S3 バケット設定
S3_BUCKET_NAME = os.getenv("S3_CONTENTS_BUCKET", "hrkz-prd-s3-contents")
S3_PREFIX = "sakura_camera/media/trees"


def export_annotation_csv(
    db: Session,
    include_undiagnosable: bool = True,
) -> str:
    """アノテーション結果をCSV形式でエクスポート

    Args:
        db: DBセッション
        include_undiagnosable: 診断不可（-1）を含めるか

    Returns:
        str: CSVコンテンツ（UTF-8 BOM付き）
    """
    # クエリを構築
    query = (
        db.query(VitalityAnnotation)
        .join(VitalityAnnotation.entire_tree)
        .options(joinedload(VitalityAnnotation.entire_tree))
    )

    # 診断不可を除外する場合
    if not include_undiagnosable:
        query = query.filter(VitalityAnnotation.vitality_value != -1)

    annotations = query.all()

    # CSVを生成
    output = io.StringIO()

    # BOM を先頭に追加（Excel対応）
    output.write("\ufeff")

    writer = csv.writer(output)

    # ヘッダー行
    writer.writerow(["s3_path", "image_filename", "vitality_score"])

    # データ行
    for annotation in annotations:
        image_obj_key = annotation.entire_tree.image_obj_key

        # S3パスを構成
        s3_path = f"s3://{S3_BUCKET_NAME}/{S3_PREFIX}/{image_obj_key}"

        # ファイル名を抽出（最後の/以降）
        image_filename = image_obj_key.split("/")[-1]

        # 元気度スコア
        vitality_score = annotation.vitality_value

        writer.writerow([s3_path, image_filename, vitality_score])

    return output.getvalue()
