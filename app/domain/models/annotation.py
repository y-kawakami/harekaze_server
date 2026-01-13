"""アノテーション関連のドメインモデル"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.database import Base

if TYPE_CHECKING:
    from app.domain.models.models import EntireTree


class Annotator(Base):
    """アノテーターアカウント"""
    __tablename__ = "annotators"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc))


class VitalityAnnotation(Base):
    """元気度アノテーション結果"""
    __tablename__ = "vitality_annotations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    entire_tree_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entire_trees.id"), unique=True, nullable=False)
    vitality_value: Mapped[int] = mapped_column(
        Integer, nullable=False)
    annotator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("annotators.id"), nullable=False)
    annotated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_vitality_annotations_entire_tree_id", "entire_tree_id"),
        Index("idx_vitality_annotations_vitality_value", "vitality_value"),
        Index("idx_vitality_annotations_annotator_id", "annotator_id"),
    )

    entire_tree: Mapped["EntireTree"] = relationship(
        "EntireTree", back_populates="vitality_annotation")
    annotator: Mapped["Annotator"] = relationship("Annotator")
