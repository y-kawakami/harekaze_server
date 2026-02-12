"""FullviewValidationLog モデルのユニットテスト

全景バリデーション NG 判定ログの DB モデルのテスト。
Requirements: 運用要件
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import Boolean, DateTime, Double, Integer, String, Text

from app.domain.models.fullview_validation_log import (
    FullviewValidationLog,
)


@pytest.mark.unit
class TestFullviewValidationLogModel:
    """FullviewValidationLog モデルのテスト"""

    def test_tablename(self):
        """テーブル名が fullview_validation_logs"""
        assert FullviewValidationLog.__tablename__ == (
            "fullview_validation_logs"
        )

    def test_has_id_column(self):
        """id カラムが存在する"""
        col = FullviewValidationLog.__table__.columns["id"]
        assert isinstance(col.type, Integer)
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_has_uid_column(self):
        """uid カラムが存在し unique"""
        col = FullviewValidationLog.__table__.columns["uid"]
        assert isinstance(col.type, String)
        assert col.type.length == 36
        assert col.unique is True

    def test_has_image_obj_key_column(self):
        """image_obj_key カラムが存在する"""
        col = FullviewValidationLog.__table__.columns["image_obj_key"]
        assert isinstance(col.type, String)
        assert col.type.length == 255

    def test_has_is_valid_column(self):
        """is_valid カラムが Boolean で存在する"""
        col = FullviewValidationLog.__table__.columns["is_valid"]
        assert isinstance(col.type, Boolean)

    def test_has_reason_column(self):
        """reason カラムが Text で存在する"""
        col = FullviewValidationLog.__table__.columns["reason"]
        assert isinstance(col.type, Text)

    def test_has_confidence_column(self):
        """confidence カラムが Double で存在する"""
        col = FullviewValidationLog.__table__.columns["confidence"]
        assert isinstance(col.type, Double)

    def test_has_model_id_column(self):
        """model_id カラムが存在する"""
        col = FullviewValidationLog.__table__.columns["model_id"]
        assert isinstance(col.type, String)
        assert col.type.length == 255

    def test_has_created_at_column(self):
        """created_at カラムが DateTime で存在する"""
        col = FullviewValidationLog.__table__.columns["created_at"]
        assert isinstance(col.type, DateTime)

    def test_has_index_on_is_valid(self):
        """is_valid にインデックスがある"""
        indexes = FullviewValidationLog.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "idx_fvlog_is_valid" in index_names

    def test_has_index_on_created_at(self):
        """created_at にインデックスがある"""
        indexes = FullviewValidationLog.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "idx_fvlog_created_at" in index_names

    def test_uid_default_is_uuid(self):
        """uid のデフォルトが UUID を生成する"""
        col = FullviewValidationLog.__table__.columns["uid"]
        assert col.default is not None
        generated = col.default.arg(None)
        # UUID フォーマットの検証
        uuid.UUID(generated)  # 不正な場合 ValueError

    def test_created_at_default_is_utc(self):
        """created_at のデフォルトが UTC datetime を返す"""
        col = FullviewValidationLog.__table__.columns["created_at"]
        assert col.default is not None
        generated = col.default.arg(None)
        assert isinstance(generated, datetime)
        assert generated.tzinfo == timezone.utc

    def test_inherits_base(self):
        """SQLAlchemy Base を継承している"""
        from app.infrastructure.database.database import Base
        assert issubclass(FullviewValidationLog, Base)
