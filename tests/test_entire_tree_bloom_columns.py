"""EntireTree モデルの bloom_30/bloom_50 カラム追加のユニットテスト"""
import pytest

from app.domain.models.models import EntireTree


@pytest.mark.unit
class TestEntireTreeBloomColumns:
    """EntireTree に 3分咲き・5分咲き用の6カラムが存在することを検証"""

    def test_has_vitality_bloom_30(self) -> None:
        assert hasattr(EntireTree, "vitality_bloom_30")

    def test_has_vitality_bloom_30_real(self) -> None:
        assert hasattr(EntireTree, "vitality_bloom_30_real")

    def test_has_vitality_bloom_30_weight(self) -> None:
        assert hasattr(EntireTree, "vitality_bloom_30_weight")

    def test_has_vitality_bloom_50(self) -> None:
        assert hasattr(EntireTree, "vitality_bloom_50")

    def test_has_vitality_bloom_50_real(self) -> None:
        assert hasattr(EntireTree, "vitality_bloom_50_real")

    def test_has_vitality_bloom_50_weight(self) -> None:
        assert hasattr(EntireTree, "vitality_bloom_50_weight")

    def test_columns_are_nullable(self) -> None:
        """全カラムが NULL 許可であること"""
        table = EntireTree.__table__
        new_columns = [
            "vitality_bloom_30",
            "vitality_bloom_30_real",
            "vitality_bloom_30_weight",
            "vitality_bloom_50",
            "vitality_bloom_50_real",
            "vitality_bloom_50_weight",
        ]
        for col_name in new_columns:
            col = table.columns[col_name]
            assert col.nullable is True, (
                f"{col_name} should be nullable"
            )

    def test_column_types(self) -> None:
        """カラム型が正しいこと（Integer / Double）"""
        from sqlalchemy import Double, Integer
        table = EntireTree.__table__

        int_cols = ["vitality_bloom_30", "vitality_bloom_50"]
        double_cols = [
            "vitality_bloom_30_real",
            "vitality_bloom_30_weight",
            "vitality_bloom_50_real",
            "vitality_bloom_50_weight",
        ]

        for col_name in int_cols:
            col = table.columns[col_name]
            assert isinstance(col.type, Integer), (
                f"{col_name} should be Integer"
            )

        for col_name in double_cols:
            col = table.columns[col_name]
            assert isinstance(col.type, Double), (
                f"{col_name} should be Double"
            )

    def test_columns_have_no_server_default(self) -> None:
        """新カラムにサーバーデフォルトが設定されていないこと"""
        table = EntireTree.__table__
        new_columns = [
            "vitality_bloom_30",
            "vitality_bloom_30_real",
            "vitality_bloom_30_weight",
            "vitality_bloom_50",
            "vitality_bloom_50_real",
            "vitality_bloom_50_weight",
        ]
        for col_name in new_columns:
            col = table.columns[col_name]
            assert col.default is None, (
                f"{col_name} should have no default"
            )
            assert col.server_default is None, (
                f"{col_name} should have no server_default"
            )
