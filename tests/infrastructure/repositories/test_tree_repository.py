"""TreeRepository のユニットテスト

create_tree() の bloom_30/bloom_50 パラメータ拡張を検証する。
Requirements: 5.1, 5.2, 5.3, 5.4
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain.models.models import EntireTree
from app.infrastructure.repositories.tree_repository import (
    TreeRepository,
)

_PATCH_TARGET = (
    "app.infrastructure.repositories"
    + ".tree_repository.func"
)


@pytest.fixture
def mock_db() -> MagicMock:
    """モック DB セッション"""
    db = MagicMock(spec=Session)
    db.flush = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture
def repository(mock_db: MagicMock) -> TreeRepository:
    """テスト用リポジトリ"""
    return TreeRepository(mock_db)


def _call_create_tree(
    repo: TreeRepository,
    vitality_bloom_30: int | None = None,
    vitality_bloom_30_real: float | None = None,
    vitality_bloom_30_weight: float | None = None,
    vitality_bloom_50: int | None = None,
    vitality_bloom_50_real: float | None = None,
    vitality_bloom_50_weight: float | None = None,
) -> None:
    """create_tree を基本パラメータ + 指定パラメータで呼ぶ"""
    with patch(_PATCH_TARGET):
        _ = repo.create_tree(
            user_id=1,
            contributor="test_user",
            latitude=35.0,
            longitude=139.0,
            image_obj_key="images/test.jpg",
            thumb_obj_key="thumbs/test.jpg",
            vitality=3,
            vitality_bloom_30=vitality_bloom_30,
            vitality_bloom_30_real=vitality_bloom_30_real,
            vitality_bloom_30_weight=vitality_bloom_30_weight,
            vitality_bloom_50=vitality_bloom_50,
            vitality_bloom_50_real=vitality_bloom_50_real,
            vitality_bloom_50_weight=vitality_bloom_50_weight,
        )


def _get_entire_tree(mock_db: MagicMock) -> EntireTree:
    """add の2番目の呼び出しから EntireTree を取得"""
    call = mock_db.add.call_args_list[1]  # pyright: ignore[reportAny]
    result: EntireTree = call[0][0]  # pyright: ignore[reportAny]
    return result


@pytest.mark.unit
class TestCreateTreeBloom30Bloom50:
    """create_tree の bloom_30/bloom_50 パラメータのテスト"""

    def test_bloom_30_fields_set_on_entire_tree(
        self,
        repository: TreeRepository,
        mock_db: MagicMock,
    ):
        """bloom_30 パラメータが EntireTree に設定される"""
        _call_create_tree(
            repository,
            vitality_bloom_30=2,
            vitality_bloom_30_real=2.3,
            vitality_bloom_30_weight=0.6,
        )
        entire_tree = _get_entire_tree(mock_db)
        assert entire_tree.vitality_bloom_30 == 2
        assert entire_tree.vitality_bloom_30_real == 2.3
        assert entire_tree.vitality_bloom_30_weight == 0.6

    def test_bloom_50_fields_set_on_entire_tree(
        self,
        repository: TreeRepository,
        mock_db: MagicMock,
    ):
        """bloom_50 パラメータが EntireTree に設定される"""
        _call_create_tree(
            repository,
            vitality_bloom_50=4,
            vitality_bloom_50_real=3.8,
            vitality_bloom_50_weight=0.4,
        )
        entire_tree = _get_entire_tree(mock_db)
        assert entire_tree.vitality_bloom_50 == 4
        assert entire_tree.vitality_bloom_50_real == 3.8
        assert entire_tree.vitality_bloom_50_weight == 0.4

    def test_all_bloom_30_50_fields_set(
        self,
        repository: TreeRepository,
        mock_db: MagicMock,
    ):
        """bloom_30 と bloom_50 の全フィールドが同時に設定される"""
        _call_create_tree(
            repository,
            vitality_bloom_30=2,
            vitality_bloom_30_real=2.1,
            vitality_bloom_30_weight=0.7,
            vitality_bloom_50=3,
            vitality_bloom_50_real=3.2,
            vitality_bloom_50_weight=0.3,
        )
        entire_tree = _get_entire_tree(mock_db)
        assert entire_tree.vitality_bloom_30 == 2
        assert entire_tree.vitality_bloom_30_real == 2.1
        assert entire_tree.vitality_bloom_30_weight == 0.7
        assert entire_tree.vitality_bloom_50 == 3
        assert entire_tree.vitality_bloom_50_real == 3.2
        assert entire_tree.vitality_bloom_50_weight == 0.3

    def test_bloom_30_50_default_none(
        self,
        repository: TreeRepository,
        mock_db: MagicMock,
    ):
        """bloom_30/bloom_50 省略時は None"""
        _call_create_tree(repository)
        entire_tree = _get_entire_tree(mock_db)
        assert entire_tree.vitality_bloom_30 is None
        assert entire_tree.vitality_bloom_30_real is None
        assert entire_tree.vitality_bloom_30_weight is None
        assert entire_tree.vitality_bloom_50 is None
        assert entire_tree.vitality_bloom_50_real is None
        assert entire_tree.vitality_bloom_50_weight is None

    def test_bloom_weight_zero_for_unused_model(
        self,
        repository: TreeRepository,
        mock_db: MagicMock,
    ):
        """未使用モデルの weight を 0.0 で保存できる"""
        _call_create_tree(
            repository,
            vitality_bloom_30_weight=0.0,
            vitality_bloom_50_weight=0.0,
        )
        entire_tree = _get_entire_tree(mock_db)
        assert entire_tree.vitality_bloom_30_weight == 0.0
        assert entire_tree.vitality_bloom_50_weight == 0.0
