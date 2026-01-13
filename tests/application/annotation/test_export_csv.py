"""CSVエクスポート機能のテスト

TDD: RED フェーズ
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def sample_annotations():
    """サンプルアノテーションデータ"""
    annotations = []

    for i, (vitality_value, image_obj_key) in enumerate([
        (3, "2024/04/01/image1.jpg"),
        (5, "2024/04/02/image2.jpg"),
        (-1, "2024/04/03/image3.jpg"),
        (1, "subdir/image4.jpg"),
    ]):
        annotation = Mock()
        annotation.id = i + 1
        annotation.entire_tree_id = 100 + i
        annotation.vitality_value = vitality_value
        annotation.annotator_id = 1
        annotation.annotated_at = datetime(
            2024, 4, 10, 12, 0, 0, tzinfo=timezone.utc)

        entire_tree = Mock()
        entire_tree.id = 100 + i
        entire_tree.image_obj_key = image_obj_key
        annotation.entire_tree = entire_tree

        annotations.append(annotation)

    return annotations


@pytest.mark.unit
class TestExportAnnotationCsv:
    """CSVエクスポート機能のテスト"""

    def test_export_csv_generates_content(self, mock_db, sample_annotations):
        """CSVコンテンツが生成される"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db)

        assert result is not None
        assert len(result) > 0

    def test_export_csv_header(self, mock_db, sample_annotations):
        """CSVヘッダーが正しい"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        # BOM を除去してヘッダーを確認
        header = lines[0].lstrip("\ufeff")
        assert "s3_path" in header
        assert "image_filename" in header
        assert "vitality_score" in header

    def test_export_csv_s3_path_format(self, mock_db, sample_annotations):
        """S3パスが正しいフォーマット"""
        from app.application.annotation.export_csv import (
            S3_BUCKET_NAME,
            export_annotation_csv,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        # データ行を確認
        data_line = lines[1]  # 最初のデータ行
        expected_prefix = f"s3://{S3_BUCKET_NAME}/sakura_camera/media/trees/"
        assert expected_prefix in data_line

    def test_export_csv_filename_extraction(self, mock_db, sample_annotations):
        """ファイル名が正しく抽出される"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        # ファイル名が抽出されていることを確認
        assert "image1.jpg" in lines[1]
        assert "image2.jpg" in lines[2]

    def test_export_csv_includes_undiagnosable(
        self, mock_db, sample_annotations
    ):
        """診断不可（-1）のデータも含まれる"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db, include_undiagnosable=True)

        # -1 が含まれていることを確認
        has_minus1 = ",-1" in result or ",-1\n" in result or ",-1\r" in result
        assert has_minus1

    def test_export_csv_exclude_undiagnosable(
        self, mock_db, sample_annotations
    ):
        """診断不可（-1）を除外できる"""
        from app.application.annotation.export_csv import export_annotation_csv

        # -1 を除外したデータ
        filtered_annotations = [
            a for a in sample_annotations if a.vitality_value != -1
        ]

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = filtered_annotations

        result = export_annotation_csv(db=mock_db, include_undiagnosable=False)

        # -1 が含まれていないことを確認
        lines = result.split("\n")
        for line in lines[1:]:  # ヘッダー以外
            if line.strip():  # 空行を除く
                assert ",-1" not in line

    def test_export_csv_utf8_with_bom(self, mock_db, sample_annotations):
        """UTF-8 BOM付きで出力される（Excel対応）"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db)

        # BOM が先頭にあることを確認
        assert result.startswith("\ufeff")

    def test_export_csv_empty_data(self, mock_db):
        """データがない場合はヘッダーのみ"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = []

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        # ヘッダー行のみ（空行を除く）
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) == 1

    def test_export_csv_row_count(self, mock_db, sample_annotations):
        """行数がアノテーション数+1（ヘッダー）"""
        from app.application.annotation.export_csv import export_annotation_csv

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.all.return_value = sample_annotations

        result = export_annotation_csv(db=mock_db)
        lines = [line for line in result.split("\n") if line.strip()]

        # ヘッダー + データ行
        assert len(lines) == len(sample_annotations) + 1
