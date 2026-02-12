import uuid
from datetime import datetime, timezone
from typing import ClassVar

from sqlalchemy import (Boolean, DateTime, Double, Index, Integer,
                        String, Text)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class FullviewValidationLog(Base):  # pyright: ignore[reportAny]
    """全景バリデーション NG ログ"""
    __tablename__: ClassVar[str] = "fullview_validation_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True,
        default=lambda: str(uuid.uuid4()))
    image_obj_key: Mapped[str] = mapped_column(
        String(255), comment="S3 画像キー")
    is_valid: Mapped[bool] = mapped_column(
        Boolean, index=True,
        comment="判定結果（True=OK, False=NG）")
    reason: Mapped[str] = mapped_column(
        Text, comment="判定理由")
    confidence: Mapped[float] = mapped_column(
        Double, comment="信頼度（0.0〜1.0）")
    model_id: Mapped[str] = mapped_column(
        String(255), comment="使用した Bedrock モデル ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc))

    __table_args__: ClassVar[tuple[Index, ...]] = (
        Index("idx_fvlog_is_valid", "is_valid"),
        Index("idx_fvlog_created_at", "created_at"),
    )
