"""新規 Tree 作成時の version 設定テスト"""
import inspect

import pytest

from app.infrastructure.repositories.tree_repository import (
    TreeRepository,
)


@pytest.mark.unit
class TestTreeVersionCreation:
    """新規 Tree 作成時に version=202601 が設定されることを検証"""

    def test_create_tree_accepts_version_parameter(self) -> None:
        """create_tree が version パラメータを受け付けること"""
        sig = inspect.signature(TreeRepository.create_tree)
        assert "version" in sig.parameters

    def test_create_tree_version_default_is_202601(self) -> None:
        """create_tree の version パラメータのデフォルト値が 202601"""
        sig = inspect.signature(TreeRepository.create_tree)
        param = sig.parameters["version"]
        assert param.default == 202601
