from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.models import Mushroom, Stem, StemHole, Tengus, Tree


class TreeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_tree(self, user_id: str, latitude: float, longitude: float,
                    image_obj_key: str, thumb_obj_key: str,
                    vitality: float) -> Tree:
        tree = Tree(
            user_id=user_id,
            tree_number=self._generate_tree_number(),
            latitude=latitude,
            longitude=longitude,
            position=func.ST_GeomFromText(
                f'POINT({longitude} {latitude})'),
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            vitality=vitality
        )
        self.db.add(tree)
        self.db.commit()
        self.db.refresh(tree)
        return tree

    def update_tree_decorated_image(self, tree_id: str,
                                    decorated_image_obj_key: str) -> bool:
        tree = self.db.query(Tree).filter(Tree.id == tree_id).first()
        if not tree:
            return False
        tree.decorated_image_obj_key = decorated_image_obj_key
        self.db.commit()
        return True

    def create_stem(self, user_id: str, tree_id: str, latitude: float,
                    longitude: float, image_obj_key: str, thumb_obj_key: str,
                    can_detected: bool, circumference: Optional[float],
                    texture: int) -> Stem:
        stem = Stem(
            user_id=user_id,
            tree_id=tree_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            can_detected=can_detected,
            circumference=circumference,
            texture=texture
        )
        self.db.add(stem)
        self.db.commit()
        self.db.refresh(stem)
        return stem

    def create_stem_hole(self, user_id: str, tree_id: str, latitude: float,
                         longitude: float, image_obj_key: str,
                         thumb_obj_key: str) -> StemHole:
        stem_hole = StemHole(
            user_id=user_id,
            tree_id=tree_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key
        )
        self.db.add(stem_hole)
        self.db.commit()
        self.db.refresh(stem_hole)
        return stem_hole

    def create_tengus(self, user_id: str, tree_id: str, latitude: float,
                      longitude: float, image_obj_key: str,
                      thumb_obj_key: str) -> Tengus:
        tengus = Tengus(
            user_id=user_id,
            tree_id=tree_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key
        )
        self.db.add(tengus)
        self.db.commit()
        self.db.refresh(tengus)
        return tengus

    def create_mushroom(self, user_id: str, tree_id: str, latitude: float,
                        longitude: float, image_obj_key: str,
                        thumb_obj_key: str) -> Mushroom:
        mushroom = Mushroom(
            user_id=user_id,
            tree_id=tree_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key
        )
        self.db.add(mushroom)
        self.db.commit()
        self.db.refresh(mushroom)
        return mushroom

    def get_tree(self, tree_id: str) -> Optional[Tree]:
        return self.db.query(Tree).filter(Tree.id == tree_id).first()

    def search_trees(self, latitude: float, longitude: float, radius: float,
                     vitality_range: Optional[tuple[int, int]] = None,
                     age_range: Optional[tuple[int, int]] = None,
                     has_hole: Optional[bool] = None,
                     has_tengusu: Optional[bool] = None,
                     has_mushroom: Optional[bool] = None,
                     offset: int = 0, limit: int = 20) -> tuple[List[Tree], int]:
        query = self.db.query(Tree).filter(
            func.ST_Distance_Sphere(
                Tree.position,
                func.ST_GeomFromText(f'POINT({longitude} {latitude})')
            ) <= radius
        )

        if vitality_range:
            query = query.filter(
                Tree.vitality >= vitality_range[0],
                Tree.vitality <= vitality_range[1]
            )

        if has_hole is not None:
            subq = self.db.query(StemHole.tree_id).distinct()
            if has_hole:
                query = query.filter(Tree.id.in_(subq))
            else:
                query = query.filter(~Tree.id.in_(subq))

        if has_tengusu is not None:
            subq = self.db.query(Tengus.tree_id).distinct()
            if has_tengusu:
                query = query.filter(Tree.id.in_(subq))
            else:
                query = query.filter(~Tree.id.in_(subq))

        if has_mushroom is not None:
            subq = self.db.query(Mushroom.tree_id).distinct()
            if has_mushroom:
                query = query.filter(Tree.id.in_(subq))
            else:
                query = query.filter(~Tree.id.in_(subq))

        total = query.count()
        trees = query.offset(offset).limit(limit).all()
        return trees, total

    def _generate_tree_number(self) -> str:
        """次の tree_number を生成する"""
        last_tree = self.db.query(Tree).order_by(
            Tree.created_at.desc()).first()
        if not last_tree:
            return "00001"
        last_number = int(last_tree.tree_number)
        return f"{last_number + 1:05d}"
