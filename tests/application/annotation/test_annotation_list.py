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
