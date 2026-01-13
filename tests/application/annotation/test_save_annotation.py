"""アノテーション保存機能のテスト

TDD: RED フェーズ
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def sample_entire_tree():
    entire_tree = Mock()
    entire_tree.id = 100
    entire_tree.tree_id = 1
    return entire_tree


@pytest.fixture
def sample_existing_annotation():
    annotation = Mock()
    annotation.id = 1
    annotation.entire_tree_id = 100
    annotation.vitality_value = 3
    annotation.annotator_id = 1
    annotation.annotated_at = datetime(2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    return annotation


@pytest.mark.unit
class TestSaveAnnotation:
    """アノテーション保存機能のテスト"""

    def test_save_annotation_new(self, mock_db, sample_entire_tree):
        """新規アノテーションを保存できる"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        # entire_tree が存在することをモック
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None  # 既存アノテーションなし

        # entire_tree の存在確認用
        mock_db.get.return_value = sample_entire_tree

        request = SaveAnnotationRequest(
            entire_tree_id=100,
            vitality_value=3,
        )

        result = save_annotation(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result is not None
        assert result.entire_tree_id == 100
        assert result.vitality_value == 3
        assert result.annotator_id == 1
        assert result.annotated_at is not None

    def test_save_annotation_update(
        self, mock_db, sample_entire_tree, sample_existing_annotation
    ):
        """既存アノテーションを更新できる（UPSERT）"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_existing_annotation

        mock_db.get.return_value = sample_entire_tree

        request = SaveAnnotationRequest(
            entire_tree_id=100,
            vitality_value=5,  # 更新
        )

        result = save_annotation(
            db=mock_db,
            annotator_id=2,  # 別のアノテーター
            request=request,
        )

        assert result is not None
        assert result.vitality_value == 5
        assert result.annotator_id == 2

    def test_save_annotation_valid_values(self, mock_db, sample_entire_tree):
        """有効な元気度値（1-5, -1）で保存できる"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        valid_values = [1, 2, 3, 4, 5, -1]

        for value in valid_values:
            query_mock = MagicMock()
            mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.first.return_value = None

            mock_db.get.return_value = sample_entire_tree

            request = SaveAnnotationRequest(
                entire_tree_id=100,
                vitality_value=value,
            )

            result = save_annotation(
                db=mock_db,
                annotator_id=1,
                request=request,
            )

            assert result is not None
            assert result.vitality_value == value

    def test_save_annotation_invalid_value_raises_error(
        self, mock_db, sample_entire_tree
    ):
        """無効な元気度値はエラーを発生させる"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        invalid_values = [0, 6, 10, -2, -10]

        for value in invalid_values:
            query_mock = MagicMock()
            mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.first.return_value = None

            mock_db.get.return_value = sample_entire_tree

            request = SaveAnnotationRequest(
                entire_tree_id=100,
                vitality_value=value,
            )

            with pytest.raises(ValueError, match="vitality_value"):
                save_annotation(
                    db=mock_db,
                    annotator_id=1,
                    request=request,
                )

    def test_save_annotation_nonexistent_entire_tree(self, mock_db):
        """存在しないentire_tree_idはエラーを発生させる"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        mock_db.get.return_value = None  # entire_tree が存在しない

        request = SaveAnnotationRequest(
            entire_tree_id=999,
            vitality_value=3,
        )

        with pytest.raises(ValueError, match="entire_tree_id"):
            save_annotation(
                db=mock_db,
                annotator_id=1,
                request=request,
            )

    def test_save_annotation_records_timestamp(self, mock_db, sample_entire_tree):
        """アノテーション日時が記録される"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None

        mock_db.get.return_value = sample_entire_tree

        before = datetime.now(timezone.utc)

        request = SaveAnnotationRequest(
            entire_tree_id=100,
            vitality_value=3,
        )

        result = save_annotation(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        after = datetime.now(timezone.utc)

        assert result is not None
        assert before <= result.annotated_at <= after

    def test_save_annotation_commits_to_db(self, mock_db, sample_entire_tree):
        """DBにコミットされる"""
        from app.application.annotation.save_annotation import (
            SaveAnnotationRequest,
            save_annotation,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None

        mock_db.get.return_value = sample_entire_tree

        request = SaveAnnotationRequest(
            entire_tree_id=100,
            vitality_value=3,
        )

        save_annotation(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        mock_db.commit.assert_called()
