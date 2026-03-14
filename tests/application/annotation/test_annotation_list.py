"""アノテーション一覧取得機能のテスト

TDD: RED フェーズ - まずテストを書く
"""

from datetime import datetime, timezone
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
    annotation.annotated_at = datetime(
        2024, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
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
        query_mock.all.return_value = [
            sample_entire_tree, sample_annotated_entire_tree]

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

        # 各クエリの scalar 結果をモック（bloom_status_counts用の追加分を含む）
        scalar_mock = MagicMock()
        # scalar() は全てのクエリで呼ばれる
        # bloom_status_counts 追加により呼び出し回数が増加
        scalar_mock.scalar.return_value = 100
        mock_db.query.return_value = scalar_mock

        stats = get_annotation_stats(db=mock_db, annotator_role="admin")

        # 統計情報が取得できていることを確認
        assert stats.total_count == 100
        # 基本的なフィールドが存在することを確認
        assert hasattr(stats, 'annotated_count')
        assert hasattr(stats, 'unannotated_count')
        assert hasattr(stats, 'bloom_status_counts')

    def test_get_annotation_stats_vitality_counts(self, mock_db):
        """元気度別の件数を取得できる"""
        from app.application.annotation.annotation_list import (
            get_annotation_stats,
        )

        # モックで返す値を設定
        scalar_mock = MagicMock()
        scalar_mock.scalar.return_value = 10  # 全ての scalar に対して同じ値を返す
        mock_db.query.return_value = scalar_mock

        stats = get_annotation_stats(db=mock_db, annotator_role="admin")

        assert hasattr(stats, 'vitality_1_count')
        assert hasattr(stats, 'vitality_2_count')
        assert hasattr(stats, 'vitality_3_count')
        assert hasattr(stats, 'vitality_4_count')
        assert hasattr(stats, 'vitality_5_count')
        assert hasattr(stats, 'vitality_minus1_count')
        assert hasattr(stats, 'ready_count')
        assert hasattr(stats, 'not_ready_count')
        assert hasattr(stats, 'bloom_status_counts')


@pytest.fixture
def sample_ready_entire_tree(sample_tree):
    """is_ready=TRUEのEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 102
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.thumb_obj_key = "test/thumb_ready.jpg"
    entire_tree.image_obj_key = "test/image_ready.jpg"

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
    entire_tree.id = 103
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.thumb_obj_key = "test/thumb_not_ready.jpg"
    entire_tree.image_obj_key = "test/image_not_ready.jpg"

    annotation = Mock()
    annotation.vitality_value = 2
    annotation.is_ready = False
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.mark.unit
class TestGetAnnotationListWithRole:
    """権限ベースフィルタリング機能のテスト"""

    def test_annotator_role_auto_filters_is_ready_true(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_ready_entire_tree,
    ):
        """annotatorロールは自動的にis_ready=TRUEでフィルタリングされる"""
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
        query_mock.all.return_value = [sample_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="annotator",  # annotator ロール
        )

        assert result.total == 1
        assert len(result.items) == 1
        # is_ready=TRUE のみが返される
        assert result.items[0].is_ready is True

    def test_admin_role_can_see_all_items(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_ready_entire_tree,
        sample_not_ready_entire_tree,
    ):
        """adminロールは全ての画像を取得できる"""
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
        query_mock.count.return_value = 2
        query_mock.all.return_value = [
            sample_ready_entire_tree,
            sample_not_ready_entire_tree,
        ]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",  # admin ロール
        )

        assert result.total == 2
        assert len(result.items) == 2

    def test_admin_role_can_filter_by_is_ready(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_not_ready_entire_tree,
    ):
        """adminロールはis_readyフィルターパラメータを使用できる"""
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
        query_mock.all.return_value = [sample_not_ready_entire_tree]

        filter_params = AnnotationListFilter(
            status="all",
            is_ready_filter=False,  # is_ready=FALSE でフィルター
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 1
        # is_ready フィルターが適用されていることを確認
        assert query_mock.filter.called

    def test_annotation_list_item_has_is_ready_field(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_ready_entire_tree,
    ):
        """一覧アイテムにis_readyフィールドが含まれる"""
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
        query_mock.all.return_value = [sample_ready_entire_tree]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        item = result.items[0]
        assert hasattr(item, 'is_ready')
        assert item.is_ready is True


@pytest.fixture
def sample_entire_tree_with_bloom_status(sample_tree):
    """bloom_status付きのEntireTreeオブジェクト"""
    entire_tree = Mock()
    entire_tree.id = 104
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.thumb_obj_key = "test/thumb_bloom.jpg"
    entire_tree.image_obj_key = "test/image_bloom.jpg"
    entire_tree.bloom_status = "full_bloom"

    annotation = Mock()
    annotation.vitality_value = 4
    annotation.is_ready = True
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.mark.unit
class TestGetAnnotationListWithBloomStatus:
    """bloom_statusフィルタリング機能のテスト"""

    def test_filter_by_single_bloom_status(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_bloom_status,
    ):
        """単一のbloom_statusでフィルタリングできる"""
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
        query_mock.all.return_value = [sample_entire_tree_with_bloom_status]

        filter_params = AnnotationListFilter(
            status="all",
            bloom_status_filter=["full_bloom"],
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 1
        # フィルターが適用されていることを確認
        assert query_mock.filter.called

    def test_filter_by_multiple_bloom_status(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_bloom_status,
    ):
        """複数のbloom_statusでフィルタリングできる"""
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
        query_mock.all.return_value = [sample_entire_tree_with_bloom_status]

        filter_params = AnnotationListFilter(
            status="all",
            bloom_status_filter=["full_bloom", "falling"],
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 1

    def test_list_item_has_bloom_status_field(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_bloom_status,
    ):
        """一覧アイテムにbloom_statusフィールドが含まれる"""
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
        query_mock.all.return_value = [sample_entire_tree_with_bloom_status]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        item = result.items[0]
        assert hasattr(item, 'bloom_status')
        assert item.bloom_status == "full_bloom"


@pytest.mark.unit
class TestAnnotationStatsWithIsReady:
    """is_ready統計情報機能のテスト"""

    def test_stats_include_ready_count(self, mock_db):
        """統計情報にready_countが含まれる"""
        from app.application.annotation.annotation_list import (
            get_annotation_stats,
        )

        scalar_mock = MagicMock()
        # 通常の統計 + ready_count, not_ready_count
        scalar_mock.scalar.side_effect = [
            100,  # total
            50,   # annotated
            10, 15, 12, 8, 3, 2,  # vitality counts
            30,   # ready_count
            20,   # not_ready_count
        ]
        mock_db.query.return_value = scalar_mock

        stats = get_annotation_stats(db=mock_db, annotator_role="admin")

        assert hasattr(stats, 'ready_count')
        assert hasattr(stats, 'not_ready_count')

    def test_annotator_stats_only_count_ready_items(self, mock_db):
        """annotatorロールの統計はis_ready=TRUEのみを対象"""
        from app.application.annotation.annotation_list import (
            get_annotation_stats,
        )

        # annotator の場合、filter().count() が呼ばれる
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock

        # count() の戻り値をチェーン
        filter_mock.count.return_value = 30  # base_query.count()
        filter_mock.filter.return_value.count.return_value = 25  # annotated count

        # scalar の戻り値
        scalar_mock = MagicMock()
        scalar_mock.scalar.side_effect = [
            5, 8, 6, 4, 1, 1,  # vitality counts
            30,   # ready_count
            0,    # not_ready_count
        ]
        filter_mock.filter.return_value = filter_mock
        query_mock.scalar = scalar_mock.scalar

        stats = get_annotation_stats(db=mock_db, annotator_role="annotator")

        # annotatorの場合、統計はis_ready=TRUEのもののみを対象
        assert stats.total_count == 30


@pytest.mark.unit
class TestAnnotationStatsWithBloomStatus:
    """bloom_status統計情報機能のテスト (タスク 4.2)"""

    def test_stats_include_bloom_status_counts(self, mock_db):
        """統計情報にbloom_status別件数が含まれる"""
        from app.application.annotation.annotation_list import (
            get_annotation_stats,
        )

        scalar_mock = MagicMock()
        # 通常の統計 + ready_count, not_ready_count
        scalar_mock.scalar.side_effect = [
            100,  # total
            50,   # annotated
            10, 15, 12, 8, 3, 2,  # vitality counts
            30,   # ready_count
            20,   # not_ready_count
        ]
        mock_db.query.return_value = scalar_mock

        stats = get_annotation_stats(db=mock_db, annotator_role="admin")

        # bloom_status_counts が含まれていることを確認
        assert hasattr(stats, 'bloom_status_counts')


@pytest.fixture
def sample_entire_tree_with_version(sample_tree):
    """version付きのEntireTreeオブジェクト"""
    sample_tree.version = 202501
    entire_tree = Mock()
    entire_tree.id = 105
    entire_tree.tree_id = sample_tree.id
    entire_tree.tree = sample_tree
    entire_tree.thumb_obj_key = "test/thumb_v.jpg"
    entire_tree.image_obj_key = "test/image_v.jpg"
    entire_tree.bloom_status = None
    entire_tree.vitality = None

    annotation = Mock()
    annotation.vitality_value = 3
    annotation.is_ready = True
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.fixture
def sample_entire_tree_version_2026(sample_tree):
    """version=202601のEntireTreeオブジェクト"""
    tree_2026 = Mock()
    tree_2026.id = 2
    tree_2026.prefecture_code = "13"
    tree_2026.location = "新宿区"
    tree_2026.version = 202601
    entire_tree = Mock()
    entire_tree.id = 106
    entire_tree.tree_id = tree_2026.id
    entire_tree.tree = tree_2026
    entire_tree.thumb_obj_key = "test/thumb_v2.jpg"
    entire_tree.image_obj_key = "test/image_v2.jpg"
    entire_tree.bloom_status = None
    entire_tree.vitality = 3

    annotation = Mock()
    annotation.vitality_value = 4
    annotation.is_ready = True
    annotation.annotator_id = 1
    entire_tree.vitality_annotation = annotation
    return entire_tree


@pytest.mark.unit
class TestGetAnnotationListWithVersion:
    """年度バージョンフィルタ機能のテスト (タスク 2.1, 2.2)"""

    def test_list_item_has_version_field(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_version,
    ):
        """一覧アイテムにversionフィールドが含まれる"""
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
        query_mock.all.return_value = [sample_entire_tree_with_version]

        filter_params = AnnotationListFilter(status="all")

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        item = result.items[0]
        assert hasattr(item, 'version')
        assert item.version == 202501

    def test_filter_accepts_versions_parameter(self):
        """AnnotationListFilterにversions_filterフィールドがある"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
        )

        f = AnnotationListFilter(
            status="all",
            versions_filter=[202501],
        )
        assert f.versions_filter == [202501]

    def test_filter_versions_default_is_none(self):
        """versions_filterのデフォルトはNone"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
        )

        f = AnnotationListFilter(status="all")
        assert f.versions_filter is None

    def test_filter_by_versions_applies_filter(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_version,
    ):
        """versionsフィルタが適用される"""
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
        query_mock.all.return_value = [sample_entire_tree_with_version]

        filter_params = AnnotationListFilter(
            status="all",
            versions_filter=[202501],
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 1
        assert query_mock.filter.called


@pytest.mark.unit
class TestGetAnnotationListWithModelVitality:
    """Admin限定model_vitalityフィルタのテスト (タスク 2.3)"""

    def test_filter_accepts_model_vitality_parameter(self):
        """AnnotationListFilterにmodel_vitality_filterフィールドがある"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
        )

        f = AnnotationListFilter(
            status="all",
            model_vitality_filter=3,
        )
        assert f.model_vitality_filter == 3

    def test_model_vitality_filter_default_is_none(self):
        """model_vitality_filterのデフォルトはNone"""
        from app.application.annotation.annotation_list import (
            AnnotationListFilter,
        )

        f = AnnotationListFilter(status="all")
        assert f.model_vitality_filter is None

    def test_admin_model_vitality_filter_applies(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_version_2026,
    ):
        """Admin権限でmodel_vitalityフィルタが適用される"""
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
        query_mock.all.return_value = [sample_entire_tree_version_2026]

        filter_params = AnnotationListFilter(
            status="all",
            model_vitality_filter=3,
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 1
        assert query_mock.filter.called

    def test_non_admin_model_vitality_filter_ignored(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_version_2026,
    ):
        """非Admin権限ではmodel_vitalityフィルタが無視される"""
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
        query_mock.all.return_value = [sample_entire_tree_version_2026]

        filter_params = AnnotationListFilter(
            status="all",
            model_vitality_filter=3,
        )

        # annotatorロールで呼び出し - フィルタは無視されるべき
        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="annotator",
        )

        assert result.total == 1


@pytest.mark.unit
class TestVersionsParameterParsing:
    """Task 5.1: versionsパラメータのパース処理テスト"""

    def test_parse_single_version(self):
        """単一バージョン文字列のパース"""
        versions = "202501"
        result = [
            int(v.strip())
            for v in versions.split(",") if v.strip()
        ]
        assert result == [202501]

    def test_parse_multiple_versions(self):
        """複数バージョン文字列のパース"""
        versions = "202501,202601"
        result = [
            int(v.strip())
            for v in versions.split(",") if v.strip()
        ]
        assert result == [202501, 202601]

    def test_parse_versions_with_spaces(self):
        """スペース付きバージョン文字列のパース"""
        versions = " 202501 , 202601 "
        result = [
            int(v.strip())
            for v in versions.split(",") if v.strip()
        ]
        assert result == [202501, 202601]

    def test_parse_versions_with_trailing_comma(self):
        """末尾カンマ付きバージョン文字列のパース"""
        versions = "202501,"
        result = [
            int(v.strip())
            for v in versions.split(",") if v.strip()
        ]
        assert result == [202501]

    def test_parse_invalid_version_raises_error(self):
        """不正な値（非整数）はValueErrorを発生"""
        versions = "abc"
        with pytest.raises(ValueError):
            [
                int(v.strip())
                for v in versions.split(",") if v.strip()
            ]

    def test_none_versions_no_filter(self):
        """versions=NoneのときフィルタなしでNone"""
        versions = None
        versions_filter = None
        if versions:
            versions_filter = [
                int(v.strip())
                for v in versions.split(",") if v.strip()
            ]
        assert versions_filter is None

    def test_filter_by_both_versions(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_version,
        sample_entire_tree_version_2026,
    ):
        """両方のバージョンでフィルタすると両方返却される"""
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
        query_mock.count.return_value = 2
        query_mock.all.return_value = [
            sample_entire_tree_with_version,
            sample_entire_tree_version_2026,
        ]

        filter_params = AnnotationListFilter(
            status="all",
            versions_filter=[202501, 202601],
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 2
        assert len(result.items) == 2
        versions_in_result = {item.version for item in result.items}
        assert versions_in_result == {202501, 202601}

    def test_no_versions_filter_returns_all(
        self,
        mock_db,
        mock_image_service,
        mock_municipality_service,
        sample_entire_tree_with_version,
        sample_entire_tree_version_2026,
    ):
        """versions未指定時は全件表示"""
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
        query_mock.count.return_value = 2
        query_mock.all.return_value = [
            sample_entire_tree_with_version,
            sample_entire_tree_version_2026,
        ]

        filter_params = AnnotationListFilter(
            status="all",
            versions_filter=None,
        )

        result = get_annotation_list(
            db=mock_db,
            image_service=mock_image_service,
            municipality_service=mock_municipality_service,
            filter_params=filter_params,
            annotator_role="admin",
        )

        assert result.total == 2
        assert len(result.items) == 2


@pytest.mark.unit
class TestAnnotationSchemasSerialization:
    """Task 5.2: スキーマのシリアライズテスト"""

    def test_diagnostics_response_serialization(self):
        """DiagnosticsResponseのシリアライズ"""
        from app.interfaces.schemas.annotation import (
            DiagnosticsResponse,
        )

        diag = DiagnosticsResponse(
            vitality=3,
            vitality_noleaf=4,
            vitality_noleaf_weight=0.8,
            vitality_bloom=2,
            vitality_bloom_weight=0.6,
            vitality_bloom_30=3,
            vitality_bloom_30_weight=0.5,
            vitality_bloom_50=4,
            vitality_bloom_50_weight=0.7,
        )
        data = diag.model_dump()
        assert data["vitality"] == 3
        assert data["vitality_noleaf"] == 4
        assert data["vitality_noleaf_weight"] == 0.8
        assert data["vitality_bloom"] == 2
        assert data["vitality_bloom_weight"] == 0.6
        assert data["vitality_bloom_30"] == 3
        assert data["vitality_bloom_30_weight"] == 0.5
        assert data["vitality_bloom_50"] == 4
        assert data["vitality_bloom_50_weight"] == 0.7

    def test_diagnostics_response_all_none(self):
        """DiagnosticsResponseの全フィールドnull"""
        from app.interfaces.schemas.annotation import (
            DiagnosticsResponse,
        )

        diag = DiagnosticsResponse()
        data = diag.model_dump()
        assert all(v is None for v in data.values())

    def test_debug_images_response_serialization(self):
        """DebugImagesResponseのシリアライズ"""
        from app.interfaces.schemas.annotation import (
            DebugImagesResponse,
        )

        debug = DebugImagesResponse(
            noleaf_url="https://example.com/noleaf.jpg",
            bloom_url="https://example.com/bloom.jpg",
        )
        data = debug.model_dump()
        assert data["noleaf_url"] == "https://example.com/noleaf.jpg"
        assert data["bloom_url"] == "https://example.com/bloom.jpg"

    def test_debug_images_response_all_none(self):
        """DebugImagesResponseの全フィールドnull"""
        from app.interfaces.schemas.annotation import (
            DebugImagesResponse,
        )

        debug = DebugImagesResponse()
        data = debug.model_dump()
        assert data["noleaf_url"] is None
        assert data["bloom_url"] is None

    def test_annotation_list_item_has_version(self):
        """AnnotationListItemResponseにversionフィールドがある"""
        from app.interfaces.schemas.annotation import (
            AnnotationListItemResponse,
        )

        item = AnnotationListItemResponse(
            entire_tree_id=1,
            tree_id=1,
            thumb_url="https://example.com/thumb.jpg",
            prefecture_name="東京都",
            location="渋谷区",
            annotation_status="unannotated",
            vitality_value=None,
            is_ready=False,
            bloom_status=None,
            version=202601,
        )
        data = item.model_dump()
        assert data["version"] == 202601

    def test_detail_response_with_diagnostics_and_debug(self):
        """AnnotationDetailResponseにdiagnosticsとdebug_images"""
        from app.interfaces.schemas.annotation import (
            AnnotationDetailResponse,
            DebugImagesResponse,
            DiagnosticsResponse,
        )

        detail = AnnotationDetailResponse(
            entire_tree_id=1,
            tree_id=1,
            image_url="https://example.com/image.jpg",
            photo_date=None,
            prefecture_name="東京都",
            location="渋谷区",
            nearest_spot_location=None,
            flowering_date=None,
            full_bloom_start_date=None,
            full_bloom_end_date=None,
            current_vitality_value=None,
            current_index=0,
            total_count=1,
            prev_id=None,
            next_id=None,
            is_ready=True,
            bloom_status=None,
            bloom_30_date="2024-03-30",
            bloom_50_date="2024-04-02",
            diagnostics=DiagnosticsResponse(vitality=3),
            debug_images=DebugImagesResponse(
                noleaf_url="https://example.com/noleaf.jpg",
            ),
        )
        data = detail.model_dump()
        assert data["bloom_30_date"] == "2024-03-30"
        assert data["bloom_50_date"] == "2024-04-02"
        assert data["diagnostics"]["vitality"] == 3
        assert (
            data["debug_images"]["noleaf_url"]
            == "https://example.com/noleaf.jpg"
        )

    def test_detail_response_without_admin_fields(self):
        """非Admin時はdiagnosticsとdebug_imagesがnull"""
        from app.interfaces.schemas.annotation import (
            AnnotationDetailResponse,
        )

        detail = AnnotationDetailResponse(
            entire_tree_id=1,
            tree_id=1,
            image_url="https://example.com/image.jpg",
            photo_date=None,
            prefecture_name="東京都",
            location="渋谷区",
            nearest_spot_location=None,
            flowering_date=None,
            full_bloom_start_date=None,
            full_bloom_end_date=None,
            current_vitality_value=None,
            current_index=0,
            total_count=1,
            prev_id=None,
            next_id=None,
            is_ready=True,
            bloom_status=None,
            bloom_30_date=None,
            bloom_50_date=None,
            diagnostics=None,
            debug_images=None,
        )
        data = detail.model_dump()
        assert data["diagnostics"] is None
        assert data["debug_images"] is None
