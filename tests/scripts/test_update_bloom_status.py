"""update_bloom_status スクリプトのテスト

バッチ更新スクリプトの機能をテストする。
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from app.domain.models.models import EntireTree


class MockTree:
    """Tree モデルのモック"""

    prefecture_code: str

    def __init__(self, prefecture_code: str = "02") -> None:
        self.prefecture_code = prefecture_code


class MockEntireTree:
    """EntireTree モデルのモック"""

    id: int
    latitude: float
    longitude: float
    photo_date: datetime
    bloom_status: str | None
    tree: MockTree | None

    def __init__(
        self,
        id: int,
        latitude: float = 40.8,
        longitude: float = 140.7,
        photo_date: datetime | None = None,
        bloom_status: str | None = None,
        tree: MockTree | None = None,
    ) -> None:
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.photo_date = (
            photo_date if photo_date is not None
            else datetime(2025, 4, 20, tzinfo=timezone.utc)
        )
        self.bloom_status = bloom_status
        self.tree = tree if tree is not None else MockTree()


@pytest.mark.unit
class TestUpdateBloomStatusScript:
    """update_bloom_status スクリプトのテスト"""

    def test_process_batch_calculates_bloom_status(self):
        """バッチ処理で bloom_status が正しく計算されること (Req 3.1)"""
        from scripts.update_bloom_status import process_batch

        mock_records = [
            MockEntireTree(id=1, latitude=40.8, longitude=140.7),
            MockEntireTree(id=2, latitude=35.6, longitude=139.7),
        ]

        mock_session = MagicMock()

        with patch(
            "scripts.update_bloom_status.get_bloom_state_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            mock_service.calculate_bloom_status.side_effect = [
                "full_bloom",
                "blooming",
            ]
            mock_service_getter.return_value = mock_service

            stats = process_batch(
                cast(Sequence[EntireTree], mock_records),
                mock_session,
                dry_run=False,
            )

            assert stats["processed"] == 2
            assert stats["updated"] == 2
            assert stats["skipped"] == 0

    def test_process_batch_dry_run_no_update(self):
        """ドライランモードでは DB 更新が行われないこと (Req 3.3)"""
        from scripts.update_bloom_status import process_batch

        mock_record = MockEntireTree(id=1)
        mock_session = MagicMock()

        with patch(
            "scripts.update_bloom_status.get_bloom_state_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            mock_service.calculate_bloom_status.return_value = "full_bloom"
            mock_service_getter.return_value = mock_service

            stats = process_batch(
                cast(Sequence[EntireTree], [mock_record]),
                mock_session,
                dry_run=True,
            )

            # ドライランでは commit が呼ばれない
            _ = mock_session.commit.assert_not_called()
            assert stats["processed"] == 1

    def test_process_batch_skips_on_none_status(self):
        """bloom_status が None の場合はスキップされること"""
        from scripts.update_bloom_status import process_batch

        mock_record = MockEntireTree(id=1)
        mock_session = MagicMock()

        with patch(
            "scripts.update_bloom_status.get_bloom_state_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            mock_service.calculate_bloom_status.return_value = None
            mock_service_getter.return_value = mock_service

            stats = process_batch(
                cast(Sequence[EntireTree], [mock_record]),
                mock_session,
                dry_run=False,
            )

            assert stats["processed"] == 1
            assert stats["updated"] == 0
            assert stats["skipped"] == 1

    def test_process_batch_handles_errors(self):
        """エラー発生時は処理を継続すること (Req 3.5)"""
        from scripts.update_bloom_status import process_batch

        mock_records = [
            MockEntireTree(id=1),
            MockEntireTree(id=2),
        ]
        mock_session = MagicMock()

        with patch(
            "scripts.update_bloom_status.get_bloom_state_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            # 1件目でエラー、2件目は成功
            mock_service.calculate_bloom_status.side_effect = [
                Exception("Test error"),
                "full_bloom",
            ]
            mock_service_getter.return_value = mock_service

            stats = process_batch(
                cast(Sequence[EntireTree], mock_records),
                mock_session,
                dry_run=False,
            )

            # エラーが発生しても処理を継続
            assert stats["processed"] == 2
            assert stats["errors"] == 1
            assert stats["updated"] == 1


@pytest.mark.unit
class TestProgressDisplay:
    """進捗表示のテスト (Req 3.2)"""

    def test_format_progress_output(self):
        """進捗表示のフォーマットが正しいこと"""
        from scripts.update_bloom_status import format_progress

        result = format_progress(
            processed=100,
            total=1000,
            updated=80,
            skipped=15,
            errors=5,
        )

        assert "100" in result
        assert "1000" in result
        assert "80" in result
        assert "15" in result
        assert "5" in result


@pytest.mark.unit
class TestBatchSize:
    """バッチサイズのテスト (Req 3.4)"""

    def test_query_with_batch_size(self):
        """バッチサイズ指定でクエリが制限されること"""
        from scripts.update_bloom_status import create_batch_query

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        _ = create_batch_query(mock_session, offset=0, batch_size=500)

        _ = mock_query.limit.assert_called_with(500)

    def test_query_with_offset(self):
        """オフセット指定でクエリが正しく設定されること"""
        from scripts.update_bloom_status import create_batch_query

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        _ = create_batch_query(mock_session, offset=1000, batch_size=500)

        _ = mock_query.offset.assert_called_with(1000)
