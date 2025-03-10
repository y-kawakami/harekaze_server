import uuid
from datetime import datetime, time, timezone
from enum import IntEnum
from typing import List, Optional

from geoalchemy2.types import Geometry
from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Index, Integer,
                        Numeric, String, Time)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.database import Base


class CensorshipStatus(IntEnum):
    """検閲ステータス"""
    UNCENSORED = 0  # 未検閲
    APPROVED = 1    # 検閲OK
    REJECTED = 2    # 検閲NG
    ESCALATED = 3   # エスカレーション


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
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    position: Mapped[str] = mapped_column(Geometry('POINT'))
    location: Mapped[Optional[str]] = mapped_column(String(100))  # 自治体名
    prefecture_code: Mapped[Optional[str]] = mapped_column(
        String(2), index=True)  # 都道府県コード（JIS X 0401）
    municipality_code: Mapped[Optional[str]] = mapped_column(
        String(8), index=True)  # 自治体コード（JIS X 0402）
    block: Mapped[Optional[str]] = mapped_column(
        String(1), index=True)  # ブロック（A, B, C）
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    photo_time: Mapped[time] = mapped_column(
        # 撮影時間（時刻検索用）
        Time, default=lambda: datetime.now(timezone.utc).time(), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now)

    # find_trees_by_time_range_blockメソッド用の複合インデックス
    __table_args__ = (
        # ブロック、検閲ステータス、撮影日付、撮影時間の複合インデックス
        # これはfind_trees_by_time_range_blockの主要な検索条件をカバー
        Index('idx_tree_block_status_date_time', 'block',
              'censorship_status', 'photo_date', 'photo_time'),
        # get_area_counts_by_codes用の複合インデックス
        # 都道府県コードと検閲ステータスの複合インデックス
        Index('idx_tree_prefecture_status',
              'prefecture_code', 'censorship_status'),
        # 市区町村コードと検閲ステータスの複合インデックス
        Index('idx_tree_municipality_status',
              'municipality_code', 'censorship_status'),
    )

    # リレーションシップ
    entire_tree: Mapped[Optional["EntireTree"]] = relationship(
        "EntireTree", uselist=False, back_populates="tree")
    stem: Mapped[Optional["Stem"]] = relationship(
        "Stem", uselist=False, back_populates="tree")
    stem_holes: Mapped[List["StemHole"]] = relationship(
        "StemHole", back_populates="tree")
    tengus: Mapped[List["Tengus"]] = relationship(
        "Tengus", back_populates="tree")
    mushrooms: Mapped[List["Mushroom"]] = relationship(
        "Mushroom", back_populates="tree")
    kobus: Mapped[List["Kobu"]] = relationship(
        "Kobu", back_populates="tree")


class EntireTree(Base):
    __tablename__ = "entire_trees"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id'))
    tree_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('trees.id'))
    vitality: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    vitality_real: Mapped[Optional[float]] = mapped_column(Float)
    vitality_noleaf: Mapped[Optional[int]] = mapped_column(Integer)
    vitality_noleaf_real: Mapped[Optional[float]] = mapped_column(Float)
    vitality_noleaf_weight: Mapped[Optional[float]] = mapped_column(Float)
    vitality_bloom: Mapped[Optional[int]] = mapped_column(Integer)
    vitality_bloom_real: Mapped[Optional[float]] = mapped_column(Float)
    vitality_bloom_weight: Mapped[Optional[float]] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    debug_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    debug_image_obj2_key: Mapped[Optional[str]] = mapped_column(String(255))
    decorated_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    ogp_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="entire_tree")


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
    can_width_mm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    circumference: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    texture: Mapped[Optional[int]] = mapped_column(Integer)
    texture_real: Mapped[Optional[float]] = mapped_column(Float)
    age: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    age_texture: Mapped[Optional[int]] = mapped_column(Integer)
    age_circumference: Mapped[Optional[int]] = mapped_column(Integer)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    image_obj_key: Mapped[str] = mapped_column(String(255))
    thumb_obj_key: Mapped[str] = mapped_column(String(255))
    debug_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    ogp_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    debug_image_obj_key: Mapped[Optional[str]] = mapped_column(String(255))
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="mushrooms")


class Kobu(Base):
    __tablename__ = "kobus"

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
    censorship_status: Mapped[int] = mapped_column(
        Integer, default=CensorshipStatus.UNCENSORED, index=True)  # 検閲ステータス
    photo_date: Mapped[datetime] = mapped_column(
        # 撮影日時
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),
                                                 onupdate=datetime.now(
                                                     timezone.utc),
                                                 nullable=False)

    user: Mapped["User"] = relationship("User")
    tree: Mapped["Tree"] = relationship("Tree", back_populates="kobus")


class PrefectureStats(Base):
    __tablename__ = "prefecture_stats"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    prefecture_code: Mapped[str] = mapped_column(String(2), unique=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    position: Mapped[str] = mapped_column(Geometry('POINT'))
    location: Mapped[str] = mapped_column(String(100))
    total_trees: Mapped[int] = mapped_column(Integer)
    vitality1_count: Mapped[int] = mapped_column(Integer)
    vitality2_count: Mapped[int] = mapped_column(Integer)
    vitality3_count: Mapped[int] = mapped_column(Integer)
    vitality4_count: Mapped[int] = mapped_column(Integer)
    vitality5_count: Mapped[int] = mapped_column(Integer)
    age20_count: Mapped[int] = mapped_column(Integer)
    age30_count: Mapped[int] = mapped_column(Integer)
    age40_count: Mapped[int] = mapped_column(Integer)
    age50_count: Mapped[int] = mapped_column(Integer)
    age60_count: Mapped[int] = mapped_column(Integer)
    hole_count: Mapped[int] = mapped_column(Integer)
    tengus_count: Mapped[int] = mapped_column(Integer)
    mushroom_count: Mapped[int] = mapped_column(Integer)
    kobu_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))


class MunicipalityStats(Base):
    __tablename__ = "municipality_stats"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    municipality_code: Mapped[Optional[str]] = mapped_column(
        String(8), index=True)  # 自治体コード（JIS X 0402）
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    position: Mapped[str] = mapped_column(Geometry('POINT'))
    location: Mapped[str] = mapped_column(String(100))  # 自治体名
    total_trees: Mapped[int] = mapped_column(Integer)
    vitality1_count: Mapped[int] = mapped_column(Integer)
    vitality2_count: Mapped[int] = mapped_column(Integer)
    vitality3_count: Mapped[int] = mapped_column(Integer)
    vitality4_count: Mapped[int] = mapped_column(Integer)
    vitality5_count: Mapped[int] = mapped_column(Integer)
    age20_count: Mapped[int] = mapped_column(Integer)
    age30_count: Mapped[int] = mapped_column(Integer)
    age40_count: Mapped[int] = mapped_column(Integer)
    age50_count: Mapped[int] = mapped_column(Integer)
    age60_count: Mapped[int] = mapped_column(Integer)
    hole_count: Mapped[int] = mapped_column(Integer)
    tengus_count: Mapped[int] = mapped_column(Integer)
    mushroom_count: Mapped[int] = mapped_column(Integer)
    kobu_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))


class Admin(Base):
    """管理者アカウント"""
    __tablename__ = "admins"

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
