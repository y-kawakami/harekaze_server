"""is_ready フラグ更新機能のテスト

TDD: RED フェーズ - まずテストを書く
Requirements: 4.1, 4.3, 4.4
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def sample_entire_tree():
    """サンプルEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 100
    entire_tree.tree_id = 1
    return entire_tree


@pytest.fixture
def sample_entire_tree_2():
    """サンプルEntireTreeオブジェクト（2つ目）"""
    entire_tree = Mock()
    entire_tree.id = 101
    entire_tree.tree_id = 2
    return entire_tree


@pytest.fixture
def sample_entire_tree_3():
    """サンプルEntireTreeオブジェクト（3つ目）"""
    entire_tree = Mock()
    entire_tree.id = 102
    entire_tree.tree_id = 3
    return entire_tree


@pytest.fixture
def sample_vitality_annotation():
    """サンプルVitalityAnnotationオブジェクト"""
    annotation = Mock()
    annotation.id = 1
    annotation.entire_tree_id = 100
    annotation.vitality_value = 3
    annotation.is_ready = False
    annotation.annotator_id = 1
    annotation.annotated_at = datetime(2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    annotation.updated_at = datetime(2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    return annotation


@pytest.mark.unit
class TestUpdateIsReady:
    """is_ready フラグ更新機能のテスト"""

    def test_update_is_ready_existing_annotation(
        self, mock_db, sample_entire_tree, sample_vitality_annotation
    ):
        """既存のアノテーションの is_ready を更新できる"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyRequest,
            update_is_ready,
        )

        # EntireTree が存在することをモック
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.side_effect = [
            sample_entire_tree,  # EntireTree の存在確認
            sample_vitality_annotation,  # VitalityAnnotation の検索
        ]

        request = UpdateIsReadyRequest(
            entire_tree_id=100,
            is_ready=True,
        )

        result = update_is_ready(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result is not None
        assert result.entire_tree_id == 100
        assert result.is_ready is True
        assert result.updated_at is not None

    def test_update_is_ready_new_annotation(
        self, mock_db, sample_entire_tree
    ):
        """アノテーションがない場合は新規作成される"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyRequest,
            update_is_ready,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.side_effect = [
            sample_entire_tree,  # EntireTree の存在確認
            None,  # VitalityAnnotation がない
        ]

        request = UpdateIsReadyRequest(
            entire_tree_id=100,
            is_ready=True,
        )

        result = update_is_ready(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result is not None
        assert result.entire_tree_id == 100
        assert result.is_ready is True
        mock_db.add.assert_called_once()

    def test_update_is_ready_nonexistent_entire_tree(self, mock_db):
        """存在しないEntireTreeはエラーを発生させる"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyRequest,
            update_is_ready,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None  # EntireTree が存在しない

        request = UpdateIsReadyRequest(
            entire_tree_id=999,
            is_ready=True,
        )

        with pytest.raises(ValueError, match="not found"):
            update_is_ready(
                db=mock_db,
                annotator_id=1,
                request=request,
            )


@pytest.mark.unit
class TestUpdateIsReadyBatch:
    """is_ready バッチ更新機能のテスト"""

    def test_update_is_ready_batch_multiple_items(
        self,
        mock_db,
        sample_entire_tree,
        sample_entire_tree_2,
        sample_entire_tree_3,
    ):
        """複数の画像の is_ready を一括更新できる"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyBatchRequest,
            update_is_ready_batch,
        )

        # EntireTree の存在確認用モック
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [
            sample_entire_tree,
            sample_entire_tree_2,
            sample_entire_tree_3,
        ]
        query_mock.first.return_value = None  # VitalityAnnotation がない

        request = UpdateIsReadyBatchRequest(
            entire_tree_ids=[100, 101, 102],
            is_ready=True,
        )

        result = update_is_ready_batch(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result is not None
        assert result.updated_count == 3
        assert len(result.updated_ids) == 3
        assert 100 in result.updated_ids
        assert 101 in result.updated_ids
        assert 102 in result.updated_ids

    def test_update_is_ready_batch_partial_update(
        self,
        mock_db,
        sample_entire_tree,
        sample_entire_tree_2,
    ):
        """一部のEntireTreeが存在しない場合は存在するもののみ更新"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyBatchRequest,
            update_is_ready_batch,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        # 3つのIDを渡すが2つのみ存在
        query_mock.all.return_value = [
            sample_entire_tree,
            sample_entire_tree_2,
        ]
        query_mock.first.return_value = None

        request = UpdateIsReadyBatchRequest(
            entire_tree_ids=[100, 101, 999],  # 999は存在しない
            is_ready=True,
        )

        result = update_is_ready_batch(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result.updated_count == 2
        assert len(result.updated_ids) == 2
        assert 999 not in result.updated_ids

    def test_update_is_ready_batch_empty_list(self, mock_db):
        """空のリストは0件更新を返す"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyBatchRequest,
            update_is_ready_batch,
        )

        request = UpdateIsReadyBatchRequest(
            entire_tree_ids=[],
            is_ready=True,
        )

        result = update_is_ready_batch(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result.updated_count == 0
        assert result.updated_ids == []

    def test_update_is_ready_batch_all_nonexistent(self, mock_db):
        """すべてのIDが存在しない場合は0件更新を返す"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyBatchRequest,
            update_is_ready_batch,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []  # 存在するEntireTreeなし

        request = UpdateIsReadyBatchRequest(
            entire_tree_ids=[997, 998, 999],
            is_ready=True,
        )

        result = update_is_ready_batch(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result.updated_count == 0
        assert result.updated_ids == []

    def test_update_is_ready_batch_set_false(
        self,
        mock_db,
        sample_entire_tree,
        sample_entire_tree_2,
    ):
        """is_ready を FALSE に設定できる"""
        from app.application.annotation.update_is_ready import (
            UpdateIsReadyBatchRequest,
            update_is_ready_batch,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [
            sample_entire_tree,
            sample_entire_tree_2,
        ]
        query_mock.first.return_value = None

        request = UpdateIsReadyBatchRequest(
            entire_tree_ids=[100, 101],
            is_ready=False,
        )

        result = update_is_ready_batch(
            db=mock_db,
            annotator_id=1,
            request=request,
        )

        assert result is not None
        assert result.updated_count == 2
