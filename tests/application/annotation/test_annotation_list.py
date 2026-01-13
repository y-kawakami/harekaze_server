"""アノテーション一覧取得機能のテスト

TDD: RED フェーズ - まずテストを書く
"""

from datetime import datetime, timezone
from typing import Literal
from unittest.mock import MagicMock, Mock

import pytest

# 遅延インポート用フィクスチャ


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_image_service():
    service = Mock()
    service.get_image_url.return_value = "https://example.com/thumb.jpg"
    return service


@pytest.fixture
def mock_municipality_service():
    service = Mock()
    prefecture = Mock()
    prefecture.name = "東京都"
    service.get_prefecture_by_code.return_value = prefecture
    service.prefectures = [prefecture]
    return service


@pytest.fixture
def sample_tree():
    """サンプルTreeオブジェクト"""
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
    """サンプルEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 100
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.thumb_obj_key = "test/thumb.jpg"
    entire_tree.image_obj_key = "test/image.jpg"
    entire_tree.vitality_annotation = None
    return entire_tree


@pytest.fixture
def sample_annotated_entire_tree(sample_tree):
    """アノテーション済みのEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 101
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.thumb_obj_key = "test/thumb2.jpg"
    entire_tree.image_obj_key = "test/image2.jpg"

    annotation = Mock()
    annotation.vitality_value = 3
    annotation.annotator_id = 1
    annotation.annotated_at = datetime(2024, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.mark.unit
class TestGetAnnotationList:
    """アノテーション一覧取得機能のテスト"""

    def test_get_annotation_list_returns_all_items(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree,
        sample_annotated_entire_tree,
    ):
        """全ての桜画像一覧を取得できる"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        # モックの設定
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 2
        query_mock.all.return_value = [sample_entire_tree, sample_annotated_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        assert result.total == 2
        assert len(result.items) == 2

    def test_get_annotation_list_filter_annotated(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_annotated_entire_tree,
    ):
        """アノテーション済みのみフィルタリングできる"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 1
        query_mock.all.return_value = [sample_annotated_entire_tree]

        filter_params = AnnotationListFilter(status="annotated")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        assert result.total == 1
        assert all(
            item.annotation_status == "annotated" for item in result.items
        )

    def test_get_annotation_list_filter_unannotated(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree,
    ):
        """未アノテーションのみフィルタリングできる"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 1
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(status="unannotated")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        assert result.total == 1
        assert all(
            item.annotation_status == "unannotated" for item in result.items
        )

    def test_get_annotation_list_filter_by_prefecture(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree,
    ):
        """都道府県でフィルタリングできる"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 1
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(
            status="all", prefecture_code="13"
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        assert result.total == 1
        # フィルターが適用されていることを確認
        assert query_mock.filter.called

    def test_get_annotation_list_filter_by_vitality_value(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_annotated_entire_tree,
    ):
        """元気度でフィルタリングできる（入力済み選択時のみ）"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 1
        query_mock.all.return_value = [sample_annotated_entire_tree]

        filter_params = AnnotationListFilter(
            status="annotated", vitality_value=3
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        assert result.total == 1
        assert result.items[0].vitality_value == 3

    def test_get_annotation_list_pagination(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree,
    ):
        """ページネーションが正しく機能する"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 50
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(
            status="all", page=2, per_page=10
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        assert result.total == 50
        assert result.page == 2
        assert result.per_page == 10
        # offset が正しく計算されているか確認
        query_mock.offset.assert_called_with(10)
        query_mock.limit.assert_called_with(10)

    def test_get_annotation_list_item_structure(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree,
    ):
        """一覧アイテムの構造が正しい"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
            get_annotation_list,
        )

        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.outerjoin.return_value = query_mock
        query_mock.options.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.count.return_value = 1
        query_mock.all.return_value = [sample_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
        )

        item = result.items[0]
        assert item.entire_tree_id == 100
        assert item.tree_id == 1
        assert item.thumb_url == "https://example.com/thumb.jpg"
        assert item.prefecture_name == "東京都"
        assert item.location == "渋谷区"
        assert item.annotation_status == "unannotated"
        assert item.vitality_value is None


@pytest.mark.unit
class TestAnnotationStats:
    """統計情報取得機能のテスト"""

    def test_get_annotation_stats(self, mock_db):
        """統計情報を取得できる"""
        from app.application.annotation.annotation_list import (
            get_annotation_stats,
        )

        # scalar_subquery のモック設定
        mock_db.query.return_value.filter.return_value.count.return_value = 100
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 30
        mock_db.query.return_value.outerjoin.return_value.filter.return_value.count.return_value = 70

        # 各元気度別の件数
        scalar_mock = MagicMock()
        scalar_mock.scalar.side_effect = [100, 30, 70, 10, 8, 6, 4, 2, 0]
        mock_db.query.return_value = scalar_mock

        stats = get_annotation_stats(db=mock_db)

        assert stats.total_count >= 0
        assert stats.annotated_count >= 0
        assert stats.unannotated_count >= 0

    def test_get_annotation_stats_vitality_counts(self, mock_db):
        """元気度別の件数を取得できる"""
        from app.application.annotation.annotation_list import (
            get_annotation_stats,
        )

        # モックで返す値を設定
        scalar_mock = MagicMock()
        scalar_mock.scalar.side_effect = [
            100,  # total
            50,   # annotated
            50,   # unannotated
            10,   # vitality 1
            15,   # vitality 2
            12,   # vitality 3
            8,    # vitality 4
            3,    # vitality 5
            2,    # vitality -1 (診断不可)
        ]
        mock_db.query.return_value = scalar_mock

        stats = get_annotation_stats(db=mock_db)

        assert hasattr(stats, 'vitality_1_count')
        assert hasattr(stats, 'vitality_2_count')
        assert hasattr(stats, 'vitality_3_count')
        assert hasattr(stats, 'vitality_4_count')
        assert hasattr(stats, 'vitality_5_count')
        assert hasattr(stats, 'vitality_minus1_count')
