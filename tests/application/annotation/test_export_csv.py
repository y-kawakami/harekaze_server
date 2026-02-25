"""CSVエクスポート機能のテスト"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_db():
    return MagicMock()


def _make_entire_tree(
    tree_id: int,
    image_obj_key: str,
    bloom_status: str | None = None,
    vitality_value: int | None = None,
    annotated_at: datetime | None = None,
    is_ready: bool = True,
    prefecture_code: str | None = None,
    photo_date: datetime | None = None,
):
    """テスト用 EntireTree モックを生成"""
    entire_tree = Mock()
    entire_tree.id = tree_id
    entire_tree.tree_id = tree_id
    entire_tree.image_obj_key = image_obj_key
    entire_tree.bloom_status = bloom_status
    entire_tree.photo_date = photo_date or datetime(
        2024, 4, 10, 12, 0, 0, tzinfo=timezone.utc
    )

    tree = Mock()
    tree.prefecture_code = prefecture_code
    entire_tree.tree = tree

    if vitality_value is not None or annotated_at is not None:
        annotation = Mock()
        annotation.vitality_value = vitality_value
        annotation.annotated_at = annotated_at
        annotation.is_ready = is_ready
        entire_tree.vitality_annotation = annotation
    else:
        entire_tree.vitality_annotation = None

    return entire_tree


@pytest.fixture
def sample_entire_trees():
    """サンプルEntireTreeデータ"""
    return [
        _make_entire_tree(
            tree_id=100,
            image_obj_key="2024/04/01/image1.jpg",
            bloom_status="full_bloom",
            vitality_value=3,
            annotated_at=datetime(
                2024, 4, 10, 3, 0, 0, tzinfo=timezone.utc
            ),
        ),
        _make_entire_tree(
            tree_id=101,
            image_obj_key="2024/04/02/image2.jpg",
            bloom_status="30_percent",
            vitality_value=5,
            annotated_at=datetime(
                2024, 4, 11, 6, 30, 0, tzinfo=timezone.utc
            ),
        ),
        _make_entire_tree(
            tree_id=102,
            image_obj_key="2024/04/03/image3.jpg",
            bloom_status=None,
            vitality_value=-1,
            annotated_at=datetime(
                2024, 4, 12, 0, 0, 0, tzinfo=timezone.utc
            ),
        ),
        _make_entire_tree(
            tree_id=103,
            image_obj_key="subdir/image4.jpg",
            bloom_status="before_bloom",
            vitality_value=None,
            annotated_at=None,
        ),
    ]


def _setup_query_mock(mock_db, data):
    """クエリモックのセットアップ"""
    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.outerjoin.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.options.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.all.return_value = data
    return query_mock


@pytest.mark.unit
class TestExportAnnotationCsv:
    """CSVエクスポート機能のテスト"""

    def test_export_csv_generates_content(
        self, mock_db, sample_entire_trees
    ):
        """CSVコンテンツが生成される"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)

        assert result is not None
        assert len(result) > 0

    def test_export_csv_header(
        self, mock_db, sample_entire_trees
    ):
        """CSVヘッダーが正しい"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        header = lines[0].lstrip("\ufeff")
        assert "s3_path" in header
        assert "image_filename" in header
        assert "vitality_score" in header
        assert "bloom_status" in header
        assert "annotated_at" in header

    def test_export_csv_s3_path_format(
        self, mock_db, sample_entire_trees
    ):
        """S3パスが正しいフォーマット"""
        from app.application.annotation.export_csv import (
            S3_BUCKET_NAME,
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        data_line = lines[1]
        expected_prefix = (
            f"s3://{S3_BUCKET_NAME}/sakura_camera/media/trees/"
        )
        assert expected_prefix in data_line

    def test_export_csv_filename_extraction(
        self, mock_db, sample_entire_trees
    ):
        """ファイル名が正しく抽出される"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        assert "image1.jpg" in lines[1]
        assert "image2.jpg" in lines[2]

    def test_export_csv_bloom_status_label(
        self, mock_db, sample_entire_trees
    ):
        """bloom_status が日本語ラベルで出力される"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        # full_bloom -> "8分咲き（満開）"
        assert "8分咲き（満開）" in lines[1]
        # 30_percent -> "3分咲き"
        assert "3分咲き" in lines[2]
        # None -> 空文字（コンマが連続）
        # before_bloom -> "開花前"
        assert "開花前" in lines[4]

    def test_export_csv_bloom_status_null(self, mock_db):
        """bloom_status が NULL の場合は空文字"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        trees = [
            _make_entire_tree(
                tree_id=100,
                image_obj_key="2024/04/01/image1.jpg",
                bloom_status=None,
                vitality_value=3,
                annotated_at=datetime(
                    2024, 4, 10, 3, 0, 0, tzinfo=timezone.utc
                ),
            ),
        ]
        _setup_query_mock(mock_db, trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        # bloom_status 列が空文字であること
        import csv as csv_mod
        import io

        reader = csv_mod.reader(
            io.StringIO(lines[1])
        )
        row = next(reader)
        # row[3] is bloom_status
        assert row[3] == ""

    def test_export_csv_annotated_at_jst(
        self, mock_db
    ):
        """annotated_at がJSTでフォーマットされる"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        trees = [
            _make_entire_tree(
                tree_id=100,
                image_obj_key="2024/04/01/image1.jpg",
                vitality_value=3,
                # UTC 2024-04-10 03:00:00 -> JST 2024-04-10 12:00:00
                annotated_at=datetime(
                    2024, 4, 10, 3, 0, 0, tzinfo=timezone.utc
                ),
            ),
        ]
        _setup_query_mock(mock_db, trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        import csv as csv_mod
        import io

        reader = csv_mod.reader(
            io.StringIO(lines[1])
        )
        row = next(reader)
        # row[4] is annotated_at
        assert row[4] == "2024-04-10 12:00:00"

    def test_export_csv_annotated_at_empty_when_no_annotation(
        self, mock_db
    ):
        """アノテーション未入力時は annotated_at が空文字"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        trees = [
            _make_entire_tree(
                tree_id=100,
                image_obj_key="2024/04/01/image1.jpg",
                vitality_value=None,
                annotated_at=None,
            ),
        ]
        _setup_query_mock(mock_db, trees)

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        import csv as csv_mod
        import io

        reader = csv_mod.reader(
            io.StringIO(lines[1])
        )
        row = next(reader)
        assert row[4] == ""

    def test_export_csv_utf8_with_bom(
        self, mock_db, sample_entire_trees
    ):
        """UTF-8 BOM付きで出力される（Excel対応）"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)

        assert result.startswith("\ufeff")

    def test_export_csv_empty_data(self, mock_db):
        """データがない場合はヘッダーのみ"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, [])

        result = export_annotation_csv(db=mock_db)
        lines = result.split("\n")

        non_empty_lines = [
            line for line in lines if line.strip()
        ]
        assert len(non_empty_lines) == 1

    def test_export_csv_row_count(
        self, mock_db, sample_entire_trees
    ):
        """行数がデータ数+1（ヘッダー）"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        _setup_query_mock(mock_db, sample_entire_trees)

        result = export_annotation_csv(db=mock_db)
        lines = [
            line for line in result.split("\n")
            if line.strip()
        ]

        assert len(lines) == len(sample_entire_trees) + 1

    def test_export_csv_status_filter_applied(
        self, mock_db
    ):
        """status フィルターが適用される"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        query_mock = _setup_query_mock(mock_db, [])

        export_annotation_csv(
            db=mock_db, status="annotated"
        )

        # filter が呼ばれたことを確認
        assert query_mock.filter.called

    def test_export_csv_bloom_status_filter_applied(
        self, mock_db
    ):
        """bloom_status フィルターが適用される"""
        from app.application.annotation.export_csv import (
            export_annotation_csv,
        )

        query_mock = _setup_query_mock(mock_db, [])

        export_annotation_csv(
            db=mock_db,
            bloom_status_filter=["full_bloom"],
        )

        assert query_mock.filter.called
