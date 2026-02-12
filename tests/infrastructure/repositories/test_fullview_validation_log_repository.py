"""FullviewValidationLogRepository のユニットテスト

全景バリデーション NG 判定ログのリポジトリのテスト。
Requirements: 運用要件
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.domain.models.fullview_validation_log import (
    FullviewValidationLog,
)
from app.infrastructure.repositories.fullview_validation_log_repository import (  # noqa: E501
    FullviewValidationLogRepository,
    get_fullview_validation_log_repository,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """モック DB セッション"""
    return MagicMock(spec=Session)


@pytest.fixture
def repository(mock_db: MagicMock) -> FullviewValidationLogRepository:
    """テスト用リポジトリ"""
    return FullviewValidationLogRepository(mock_db)


@pytest.mark.unit
class TestFullviewValidationLogRepository:
    """FullviewValidationLogRepository のテスト"""

    def test_init_sets_db(self, mock_db: MagicMock):
        """db セッションが設定される"""
        repo = FullviewValidationLogRepository(mock_db)
        assert repo.db is mock_db

    def test_create_adds_to_session(
        self,
        repository: FullviewValidationLogRepository,
        mock_db: MagicMock,
    ):
        """create で DB セッションに add される"""
        repository.create(
            image_obj_key="validation_ng/20260207/test.jpg",
            is_valid=False,
            reason="枝の先端のみ",
            confidence=0.88,
            model_id="test-model",
        )
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, FullviewValidationLog)

    def test_create_commits(
        self,
        repository: FullviewValidationLogRepository,
        mock_db: MagicMock,
    ):
        """create で commit される"""
        repository.create(
            image_obj_key="validation_ng/20260207/test.jpg",
            is_valid=False,
            reason="枝の先端のみ",
            confidence=0.88,
            model_id="test-model",
        )
        mock_db.commit.assert_called_once()

    def test_create_refreshes(
        self,
        repository: FullviewValidationLogRepository,
        mock_db: MagicMock,
    ):
        """create で refresh される"""
        repository.create(
            image_obj_key="validation_ng/20260207/test.jpg",
            is_valid=False,
            reason="枝の先端のみ",
            confidence=0.88,
            model_id="test-model",
        )
        mock_db.refresh.assert_called_once()

    def test_create_returns_log(
        self,
        repository: FullviewValidationLogRepository,
    ):
        """create が FullviewValidationLog を返す"""
        result = repository.create(
            image_obj_key="validation_ng/20260207/test.jpg",
            is_valid=False,
            reason="枝の先端のみ",
            confidence=0.88,
            model_id="test-model",
        )
        assert isinstance(result, FullviewValidationLog)

    def test_create_sets_fields(
        self,
        repository: FullviewValidationLogRepository,
        mock_db: MagicMock,
    ):
        """create でフィールドが正しく設定される"""
        repository.create(
            image_obj_key="validation_ng/20260207/test.jpg",
            is_valid=False,
            reason="枝の先端のみ",
            confidence=0.88,
            model_id="test-model",
        )
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.image_obj_key == (
            "validation_ng/20260207/test.jpg"
        )
        assert added_obj.is_valid is False
        assert added_obj.reason == "枝の先端のみ"
        assert added_obj.confidence == 0.88
        assert added_obj.model_id == "test-model"

    def test_create_order_add_commit_refresh(
        self,
        repository: FullviewValidationLogRepository,
        mock_db: MagicMock,
    ):
        """add → commit → refresh の順で呼ばれる"""
        manager = MagicMock()
        mock_db.add.side_effect = (
            lambda x: manager.add(x)
        )
        mock_db.commit.side_effect = (
            lambda: manager.commit()
        )
        mock_db.refresh.side_effect = (
            lambda x: manager.refresh(x)
        )

        repository.create(
            image_obj_key="test.jpg",
            is_valid=False,
            reason="test",
            confidence=0.5,
            model_id="model",
        )

        calls = manager.method_calls
        assert calls[0][0] == "add"
        assert calls[1][0] == "commit"
        assert calls[2][0] == "refresh"


@pytest.mark.unit
class TestGetFullviewValidationLogRepository:
    """ファクトリ関数のテスト"""

    def test_returns_repository(self, mock_db: MagicMock):
        """FullviewValidationLogRepository を返す"""
        repo = get_fullview_validation_log_repository(mock_db)
        assert isinstance(repo, FullviewValidationLogRepository)

    def test_sets_db(self, mock_db: MagicMock):
        """db が正しく設定される"""
        repo = get_fullview_validation_log_repository(mock_db)
        assert repo.db is mock_db
