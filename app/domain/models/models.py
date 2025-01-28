import uuid
from datetime import datetime, timezone
from typing import List, Optional

from geoalchemy2.types import Geometry
from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, Numeric,
                        String)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    ip_addr: Mapped[str] = mapped_column(String(45))  # IPv6アドレスも考慮して45文字
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))


class Tree(Base):
    __tablename__ = "trees"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    contributor: Mapped[Optional[str]] = mapped_column(String(100))
    vitality: Mapped[Optional[int]] = mapped_column(Integer)
    vitality_real: Mapped[Optional[float]] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    position: Mapped[str] = mapped_column(Geometry('POINT'))
    location: Mapped[Optional[str]] = mapped_column(String(100))  # 自治体名
    prefecture_code: Mapped[Optional[str]] = mapped_column(
        String(2), index=True)  # 都道府県コード（JIS X 0401）
    municipality_code: Mapped[Optional[str]] = mapped_column(
        String(8), index=True)  # 自治体コード（JIS X 0402）
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    decorated_image_obj_key: Mapped[Optional[str]] = mapped_column(
        String(255))
    ogp_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)

    # リレーションシップ
    stem: Mapped[Optional["Stem"]] = relationship(
        "Stem", uselist=False, back_populates="tree")
    stem_holes: Mapped[List["StemHole"]] = relationship(
        "StemHole", back_populates="tree")
    tengus: Mapped[List["Tengus"]] = relationship(
        "Tengus", back_populates="tree")
    mushrooms: Mapped[List["Mushroom"]] = relationship(
        "Mushroom", back_populates="tree")


class Stem(Base):
    __tablename__ = "stems"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id'))
    tree_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('trees.id'))
    can_detected: Mapped[bool] = mapped_column(
        Boolean, default=False)
    circumference: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    texture_real: Mapped[Optional[float]] = mapped_column(Float)
    texture: Mapped[Optional[int]] = mapped_column(Integer)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="stem")


class StemHole(Base):
    __tablename__ = "stem_holes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id'), nullable=False)
    tree_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('trees.id'), nullable=False)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="stem_holes")


class Tengus(Base):
    __tablename__ = "tengus"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id'), nullable=False)
    tree_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('trees.id'), nullable=False)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="tengus")


class Mushroom(Base):
    __tablename__ = "mushrooms"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id'), nullable=False)
    tree_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('trees.id'), nullable=False)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="mushrooms")
