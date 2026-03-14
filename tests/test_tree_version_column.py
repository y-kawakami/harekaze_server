"""Tree モデルの version カラム追加のユニットテスト"""
import pytest
from sqlalchemy import Integer

from app.domain.models.models import Tree


@pytest.mark.unit
class TestTreeVersionColumn:
    """Tree に version カラムが存在し、正しく設定されていることを検証"""

    def test_has_version_attribute(self) -> None:
        """Tree モデルに version 属性が存在すること"""
        assert hasattr(Tree, "version")

    def test_version_column_type_is_integer(self) -> None:
        """version カラムが INTEGER 型であること"""
        table = Tree.__table__
        col = table.columns["version"]
        assert isinstance(col.type, Integer), (
            "version should be Integer"
        )

    def test_version_column_not_nullable(self) -> None:
        """version カラムが NOT NULL であること"""
        table = Tree.__table__
        col = table.columns["version"]
        assert col.nullable is False, (
            "version should not be nullable"
        )

    def test_version_column_has_default_202501(self) -> None:
        """version カラムの Python デフォルトが 202501 であること"""
        table = Tree.__table__
        col = table.columns["version"]
        assert col.default is not None
        assert col.default.arg == 202501

    def test_version_column_has_server_default_202501(self) -> None:
        """version カラムの server_default が 202501 であること"""
        table = Tree.__table__
        col = table.columns["version"]
        assert col.server_default is not None
        assert col.server_default.arg == "202501"

    def test_version_column_is_indexed(self) -> None:
        """version カラムにインデックスが設定されていること"""
        table = Tree.__table__
        col = table.columns["version"]
        assert col.index is True, (
            "version should be indexed"
        )
