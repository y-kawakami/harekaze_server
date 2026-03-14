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
    service.get_image_url.return_value = (
        "https://example.com/sakura_camera/media/trees/image.jpg"
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
    entire_tree.bloom_30_date = None
    entire_tree.bloom_50_date = None
    entire_tree.bloom_status = None
    entire_tree.debug_image_obj_key = None
    entire_tree.debug_image_obj2_key = None
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
    entire_tree.bloom_30_date = None
    entire_tree.bloom_50_date = None
    entire_tree.bloom_status = None
    entire_tree.debug_image_obj_key = None
    entire_tree.debug_image_obj2_key = None

    annotation = Mock()
    annotation.vitality_value = 3
    annotation.is_ready = True
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
            annotator_role="admin",  # admin ロールで全画像にアクセス
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
        """画像URLが含まれる"""
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
            annotator_role="admin",
        )

        assert result is not None
        assert "sakura_camera" in result.image_url
        mock_image_service.get_image_url.assert_called_once()

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
            annotator_role="admin",
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
            annotator_role="admin",
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
            annotator_role="admin",
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
        first_item.bloom_30_date = None
        first_item.bloom_50_date = None
        first_item.bloom_status = None
        first_item.debug_image_obj_key = None
        first_item.debug_image_obj2_key = None

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
            annotator_role="admin",
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
        last_item.bloom_30_date = None
        last_item.bloom_50_date = None
        last_item.bloom_status = None
        last_item.debug_image_obj_key = None
        last_item.debug_image_obj2_key = None

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
            annotator_role="admin",
        )

        assert result is not None
        assert result.prev_id == 101
        assert result.next_id is None


@pytest.fixture
def sample_ready_entire_tree(sample_tree):
    """is_ready=TRUEのEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 200
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.image_obj_key = "test/image_ready.jpg"
    entire_tree.thumb_obj_key = "test/thumb_ready.jpg"
    entire_tree.photo_date = datetime(2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    entire_tree.bloom_30_date = None
    entire_tree.bloom_50_date = None
    entire_tree.bloom_status = None
    entire_tree.debug_image_obj_key = None
    entire_tree.debug_image_obj2_key = None

    annotation = Mock()
    annotation.vitality_value = 4
    annotation.is_ready = True
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.fixture
def sample_not_ready_entire_tree(sample_tree):
    """is_ready=FALSEのEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 201
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.image_obj_key = "test/image_not_ready.jpg"
    entire_tree.thumb_obj_key = "test/thumb_not_ready.jpg"
    entire_tree.photo_date = datetime(2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    entire_tree.bloom_30_date = None
    entire_tree.bloom_50_date = None
    entire_tree.bloom_status = None
    entire_tree.debug_image_obj_key = None
    entire_tree.debug_image_obj2_key = None

    annotation = Mock()
    annotation.vitality_value = 2
    annotation.is_ready = False
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.mark.unit
class TestGetAnnotationDetailWithRole:
    """権限ベースアクセス制御のテスト"""

    def test_admin_can_access_not_ready_image(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_not_ready_entire_tree,
    ):
        """adminロールはis_ready=FALSEの画像にアクセスできる"""
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
        query_mock.first.return_value = sample_not_ready_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_not_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=201,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.entire_tree_id == 201
        assert result.is_ready is False

    def test_admin_can_access_ready_image(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_ready_entire_tree,
    ):
        """adminロールはis_ready=TRUEの画像にアクセスできる"""
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
        query_mock.first.return_value = sample_ready_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=200,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.entire_tree_id == 200
        assert result.is_ready is True

    def test_annotator_can_access_ready_image(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_ready_entire_tree,
    ):
        """annotatorロールはis_ready=TRUEの画像にアクセスできる"""
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
        query_mock.first.return_value = sample_ready_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=200,
            filter_params=filter_params,
            annotator_role="annotator",
        )

        assert result is not None
        assert result.entire_tree_id == 200

    def test_annotator_cannot_access_not_ready_image(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_not_ready_entire_tree,
    ):
        """annotatorロールはis_ready=FALSEの画像にアクセスできない（PermissionError）"""
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
        query_mock.first.return_value = sample_not_ready_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_not_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        with pytest.raises(PermissionError, match="not ready"):
            get_annotation_detail(
                db=mock_db,
                image_service=mock_image_service,
                flowering_date_service=mock_flowering_date_service,
                municipality_service=mock_municipality_service,
                entire_tree_id=201,
                filter_params=filter_params,
                annotator_role="annotator",
            )

    def test_annotator_cannot_access_no_annotation_image(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree,
    ):
        """annotatorロールはアノテーションがない画像にアクセスできない"""
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
        query_mock.first.return_value = sample_entire_tree  # vitality_annotation = None
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        with pytest.raises(PermissionError, match="not ready"):
            get_annotation_detail(
                db=mock_db,
                image_service=mock_image_service,
                flowering_date_service=mock_flowering_date_service,
                municipality_service=mock_municipality_service,
                entire_tree_id=100,
                filter_params=filter_params,
                annotator_role="annotator",
            )

    def test_detail_response_has_is_ready_field(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_ready_entire_tree,
    ):
        """詳細レスポンスにis_readyフィールドが含まれる"""
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
        query_mock.first.return_value = sample_ready_entire_tree
        query_mock.count.return_value = 1
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [sample_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=200,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert hasattr(result, 'is_ready')
        assert result.is_ready is True


@pytest.fixture
def sample_entire_tree_with_bloom_dates(sample_tree):
    """bloom_30_date/bloom_50_dateを持つEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 300
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.image_obj_key = "test/image_bloom.jpg"
    entire_tree.photo_date = datetime(
        2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    entire_tree.bloom_30_date = date(2024, 3, 30)
    entire_tree.bloom_50_date = date(2024, 4, 2)
    entire_tree.bloom_status = "blooming"
    entire_tree.vitality = 3
    entire_tree.vitality_noleaf = 4
    entire_tree.vitality_noleaf_weight = 0.8
    entire_tree.vitality_bloom = 2
    entire_tree.vitality_bloom_weight = 0.6
    entire_tree.vitality_bloom_30 = 3
    entire_tree.vitality_bloom_30_weight = 0.5
    entire_tree.vitality_bloom_50 = 4
    entire_tree.vitality_bloom_50_weight = 0.7
    entire_tree.debug_image_obj_key = "debug/noleaf_abc.jpg"
    entire_tree.debug_image_obj2_key = "debug/bloom_abc.jpg"

    annotation = Mock()
    annotation.vitality_value = 3
    annotation.is_ready = True
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.fixture
def sample_entire_tree_no_bloom_dates(sample_tree):
    """bloom日がnullのEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 301
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.image_obj_key = "test/image_nobloom.jpg"
    entire_tree.photo_date = datetime(
        2024, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    entire_tree.bloom_30_date = None
    entire_tree.bloom_50_date = None
    entire_tree.bloom_status = None
    entire_tree.vitality = None
    entire_tree.vitality_noleaf = None
    entire_tree.vitality_noleaf_weight = None
    entire_tree.vitality_bloom = None
    entire_tree.vitality_bloom_weight = None
    entire_tree.vitality_bloom_30 = None
    entire_tree.vitality_bloom_30_weight = None
    entire_tree.vitality_bloom_50 = None
    entire_tree.vitality_bloom_50_weight = None
    entire_tree.debug_image_obj_key = None
    entire_tree.debug_image_obj2_key = None

    annotation = Mock()
    annotation.vitality_value = None
    annotation.is_ready = True
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


def _setup_detail_query(mock_db, entire_tree):
    """詳細取得用のクエリモックセットアップヘルパー"""
    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = query_mock
    query_mock.outerjoin.return_value = query_mock
    query_mock.options.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = entire_tree
    query_mock.count.return_value = 1
    query_mock.order_by.return_value = query_mock
    query_mock.all.return_value = [entire_tree]


@pytest.mark.unit
class TestAnnotationDetailBloomDates:
    """Task 3.1: 開花段階日のレスポンス追加テスト"""

    def test_bloom_dates_included_in_response(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_with_bloom_dates,
    ):
        """bloom_30_dateとbloom_50_dateがレスポンスに含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_with_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=300,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.bloom_30_date == "2024-03-30"
        assert result.bloom_50_date == "2024-04-02"

    def test_bloom_dates_null_when_not_recorded(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_no_bloom_dates,
    ):
        """bloom日が未記録の場合はnullを返す"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_no_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=301,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.bloom_30_date is None
        assert result.bloom_50_date is None

    def test_bloom_dates_visible_to_annotator(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_with_bloom_dates,
    ):
        """annotatorロールでもbloom日は表示される"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_with_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=300,
            filter_params=filter_params,
            annotator_role="annotator",
        )

        assert result is not None
        assert result.bloom_30_date == "2024-03-30"
        assert result.bloom_50_date == "2024-04-02"


@pytest.mark.unit
class TestAnnotationDetailDiagnostics:
    """Task 3.2: Admin限定の診断値表示テスト"""

    def test_admin_sees_diagnostics(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_with_bloom_dates,
    ):
        """Adminロール時に診断値が含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_with_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=300,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.diagnostics is not None
        assert result.diagnostics.vitality == 3
        assert result.diagnostics.vitality_noleaf == 4
        assert result.diagnostics.vitality_noleaf_weight == 0.8
        assert result.diagnostics.vitality_bloom == 2
        assert result.diagnostics.vitality_bloom_weight == 0.6
        assert result.diagnostics.vitality_bloom_30 == 3
        assert result.diagnostics.vitality_bloom_30_weight == 0.5
        assert result.diagnostics.vitality_bloom_50 == 4
        assert result.diagnostics.vitality_bloom_50_weight == 0.7

    def test_annotator_does_not_see_diagnostics(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_with_bloom_dates,
    ):
        """非Adminロール時に診断値はnull"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_with_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=300,
            filter_params=filter_params,
            annotator_role="annotator",
        )

        assert result is not None
        assert result.diagnostics is None


@pytest.mark.unit
class TestAnnotationDetailDebugImages:
    """Task 3.3: Admin限定のデバッグ画像URL表示テスト"""

    def test_admin_sees_debug_images(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_with_bloom_dates,
    ):
        """Adminロール時にデバッグ画像URLが含まれる"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_with_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=300,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.debug_images is not None
        assert result.debug_images.noleaf_url is not None
        assert result.debug_images.bloom_url is not None

    def test_annotator_does_not_see_debug_images(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_with_bloom_dates,
    ):
        """非Adminロール時にデバッグ画像はnull"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_with_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=300,
            filter_params=filter_params,
            annotator_role="annotator",
        )

        assert result is not None
        assert result.debug_images is None

    def test_admin_debug_images_null_when_keys_missing(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        mock_flowering_date_service,
        sample_entire_tree_no_bloom_dates,
    ):
        """デバッグ画像キーがnullの場合はURLもnull"""
        from app.application.annotation.annotation_detail import (
            AnnotationListFilter,
            get_annotation_detail,
        )

        _setup_detail_query(
            mock_db, sample_entire_tree_no_bloom_dates)

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_detail(
            db=mock_db,
            image_service=mock_image_service,
            flowering_date_service=mock_flowering_date_service,
            municipality_service=mock_municipality_service,
            entire_tree_id=301,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result is not None
        assert result.debug_images is not None
        assert result.debug_images.noleaf_url is None
        assert result.debug_images.bloom_url is None
