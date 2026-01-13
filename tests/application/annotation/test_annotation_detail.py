"""アノテーション詳細取得機能のテスト

TDD: RED フェーズ
"""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_image_service():
    service = Mock()
    service.get_presigned_url.return_value = (
        "https://example.com/signed/image.jpg?signature=xxx"
    )
    return service


@pytest.fixture
def mock_municipality_service():
    service = Mock()
    prefecture = Mock()
    prefecture.name = "東京都"
    service.get_prefecture_by_code.return_value = prefecture
    return service


@pytest.fixture
def mock_flowering_date_service():
    service = Mock()
    spot = Mock()
    spot.flowering_date = date(2024, 3, 25)
    spot.full_bloom_date = date(2024, 4, 1)
    spot.full_bloom_end_date = date(2024, 4, 7)
    service.find_nearest_spot.return_value = spot
    return service


@pytest.fixture
def sample_tree():
    tree = Mock()
    tree.id = 1
    tree.prefecture_code = "13"
    tree.location = "渋谷区"
    tree.latitude = 35.6762
    tree.longitude = 139.6503
    tree.photo_date = datetime(2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    return tree


@pytest.fixture
def sample_entire_tree(sample_tree):
    entire_tree = Mock()
    entire_tree.id = 100
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.image_obj_key = "test/image.jpg"
    entire_tree.thumb_obj_key = "test/thumb.jpg"
    entire_tree.photo_date = datetime(
        2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    entire_tree.vitality_annotation = None
    return entire_tree


@pytest.fixture
def sample_annotated_entire_tree(sample_tree):
    entire_tree = Mock()
    entire_tree.id = 101
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.image_obj_key = "test/image2.jpg"
    entire_tree.thumb_obj_key = "test/thumb2.jpg"
    entire_tree.photo_date = datetime(
        2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)

    annotation = Mock()
    annotation.vitality_value = 3
    annotation.annotator_id = 1
    annotation.annotated_at = datetime(
        2024, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.mark.unit
class TestGetAnnotationDetail:
    """アノテーション詳細取得機能のテスト"""

    def test_get_annotation_detail_basic(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree,
    ):
        """詳細情報を取得できる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_entire_tree
        query_mock.count.return_value = 10
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [
            Mock(id=98),
            Mock(id=99),
            sample_entire_tree,
            Mock(id=101),
            Mock(id=102),
        ]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=100,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.entire_tree_id == 100
        assert result.tree_id == 1

    def test_get_annotation_detail_with_image_url(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree,
    ):
        """署名付きURLが含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=100,
            filter_params=filter_params,
        )

        assert result is not None
        assert "signed" in result.image_url
        mock_image_service.get_presigned_url.assert_called_once()

    def test_get_annotation_detail_with_photo_info(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree,
    ):
        """撮影情報が含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=100,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.prefecture_name == "東京都"
        assert result.location == "渋谷区"
        assert result.photo_date is not None

    def test_get_annotation_detail_with_flowering_info(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree,
    ):
        """開花予想日情報が含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=100,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.flowering_date == "2024-03-25"
        assert result.full_bloom_start_date == "2024-04-01"
        assert result.full_bloom_end_date == "2024-04-07"
        mock_flowering_date_service.find_nearest_spot.assert_called_once()

    def test_get_annotation_detail_with_existing_annotation(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_annotated_entire_tree,
    ):
        """既存アノテーション値が含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_annotated_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_annotated_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=101,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.current_vitality_value == 3

    def test_get_annotation_detail_not_found(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
    ):
        """存在しないIDの場合はNoneを返す"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=999,
            filter_params=filter_params,
        )

        assert result is None

    def test_get_annotation_detail_navigation(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree,
    ):
        """前後ナビゲーション用のIDが含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = sample_entire_tree
        query_mock.count.return_value = 5
        query_mock.order_by.return_value = query_mock

        # ID リスト（current が 100）
        mock_items = [
            Mock(id=98),
            Mock(id=99),
            sample_entire_tree,  # id=100
            Mock(id=101),
            Mock(id=102),
        ]
        query_mock.all.return_value = mock_items

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=100,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.current_index >= 0
        assert result.total_count == 5
        assert result.prev_id == 99
        assert result.next_id == 101

    def test_get_annotation_detail_first_item_no_prev(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
    ):
        """最初の項目の場合、prev_idはNone"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        first_item = Mock()
        first_item.id = 100
        first_item.tree_id = 1
        first_item.tree = Mock()
        first_item.tree.id = 1
        first_item.tree.prefecture_code = "13"
        first_item.tree.location = "渋谷区"
        first_item.tree.latitude = 35.6762
        first_item.tree.longitude = 139.6503
        first_item.tree.photo_date = datetime(2024, 4, 1, tzinfo=timezone.utc)
        first_item.image_obj_key = "test/image.jpg"
        first_item.photo_date = datetime(2024, 4, 1, tzinfo=timezone.utc)
        first_item.vitality_annotation = None

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = first_item
        query_mock.count.return_value = 3
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [
            first_item,
            Mock(id=101),
            Mock(id=102),
        ]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=100,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.prev_id is None
        assert result.next_id == 101

    def test_get_annotation_detail_last_item_no_next(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
    ):
        """最後の項目の場合、next_idはNone"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        last_item = Mock()
        last_item.id = 102
        last_item.tree_id = 1
        last_item.tree = Mock()
        last_item.tree.id = 1
        last_item.tree.prefecture_code = "13"
        last_item.tree.location = "渋谷区"
        last_item.tree.latitude = 35.6762
        last_item.tree.longitude = 139.6503
        last_item.tree.photo_date = datetime(2024, 4, 1, tzinfo=timezone.utc)
        last_item.image_obj_key = "test/image.jpg"
        last_item.photo_date = datetime(2024, 4, 1, tzinfo=timezone.utc)
        last_item.vitality_annotation = None

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = last_item
        query_mock.count.return_value = 3
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [
            Mock(id=100),
            Mock(id=101),
            last_item,
        ]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=102,
            filter_params=filter_params,
        )

        assert result is not None
        assert result.prev_id == 101
        assert result.next_id is None
