import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        Numeric, String)
from sqlalchemy.dialects.mysql import GEOMETRY
from sqlalchemy.orm import relationship

from app.infrastructure.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    ip_addr = Column(String(45))  # IPv6アドレスも考慮して45文字
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class Tree(Base):
    __tablename__ = "trees"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'))
    tree_number = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)
    position = Column(GEOMETRY)
    image_obj_key = Column(String(255))
    thumb_obj_key = Column(String(255))
    decorated_image_obj_key = Column(String(255))
    vitality = Column(Float)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))

    user = relationship("User")
    stem = relationship("Stem", back_populates="tree", uselist=False)
    stem_holes = relationship("StemHole", back_populates="tree")
    tengus = relationship("Tengus", back_populates="tree")
    mushrooms = relationship("Mushroom", back_populates="tree")


class Stem(Base):
    __tablename__ = "stems"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'))
    tree_id = Column(String(36), ForeignKey('trees.id'))
    latitude = Column(Float)
    longitude = Column(Float)
    image_obj_key = Column(String(255))
    thumb_obj_key = Column(String(255))
    can_detected = Column(Boolean, default=False)
    circumference = Column(Numeric(10, 2))
    texture = Column(Integer)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))

    user = relationship("User")
    tree = relationship("Tree", back_populates="stem")


class StemHole(Base):
    __tablename__ = "stem_holes"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'))
    tree_id = Column(String(36), ForeignKey('trees.id'))
    latitude = Column(Float)
    longitude = Column(Float)
    image_obj_key = Column(String(255))
    thumb_obj_key = Column(String(255))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))

    user = relationship("User")
    tree = relationship("Tree", back_populates="stem_holes")


class Tengus(Base):
    __tablename__ = "tengus"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'))
    tree_id = Column(String(36), ForeignKey('trees.id'))
    latitude = Column(Float)
    longitude = Column(Float)
    image_obj_key = Column(String(255))
    thumb_obj_key = Column(String(255))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))

    user = relationship("User")
    tree = relationship("Tree", back_populates="tengus")


class Mushroom(Base):
    __tablename__ = "mushrooms"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'))
    tree_id = Column(String(36), ForeignKey('trees.id'))
    latitude = Column(Float)
    longitude = Column(Float)
    image_obj_key = Column(String(255))
    thumb_obj_key = Column(String(255))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))

    user = relationship("User")
    tree = relationship("Tree", back_populates="mushrooms")
