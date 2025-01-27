from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.models import Mushroom, Stem, StemHole, Tengus, Tree


class TreeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_tree(self, user_id: str, contributor: str, latitude: float, longitude: float,
                    image_obj_key: str, thumb_obj_key: str,
                    vitality: float) -> Tree:
        tree = Tree(
            user_id=user_id,
            contributor=contributor,
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
                         thumb_obj_key: str) -> bool:
        """幹の穴の写真を登録する"""
        tree = self.db.query(Tree).filter(Tree.id == tree_id).first()
        if not tree:
            return False

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
        return True

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
                        thumb_obj_key: str) -> bool:
        """キノコの写真を登録する"""
        tree = self.db.query(Tree).filter(Tree.id == tree_id).first()
        if not tree:
            return False

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
        return True

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
        last_number = last_tree.tree_number
        return f"{last_number + 1:05d}"

    def count_trees(
        self,
        prefecture: str | None,
        city: str | None,
        vitality_range: tuple[int | None, int | None] | None,
        age_range: tuple[int | None, int | None] | None,
        has_hole: bool | None,
        has_tengusu: bool | None,
        has_mushroom: bool | None
    ) -> int:
        """条件に合致する桜の本数を取得する"""
        query = self.db.query(Tree)

        # 位置による絞り込み
        if prefecture or city:
            # TODO: 逆ジオコーディングAPIを使用して緯度経度の範囲を取得
            pass

        # 元気度による絞り込み
        if vitality_range:
            if vitality_range[0] is not None:
                query = query.filter(Tree.vitality >= vitality_range[0])
            if vitality_range[1] is not None:
                query = query.filter(Tree.vitality <= vitality_range[1])

        # 樹齢による絞り込み（幹周りから推定）
        if age_range:
            # TODO: 幹周りから樹齢を推定する計算式を実装
            if age_range[0] is not None:
                pass  # TODO: 最小樹齢の条件を適用
            if age_range[1] is not None:
                pass  # TODO: 最大樹齢の条件を適用

        # 状態による絞り込み
        if has_hole is not None:
            subquery = self.db.query(StemHole.tree_id).distinct()
            if has_hole:
                query = query.filter(Tree.id.in_(subquery))
            else:
                query = query.filter(~Tree.id.in_(subquery))

        if has_tengusu is not None:
            subquery = self.db.query(Tengus.tree_id).distinct()
            if has_tengusu:
                query = query.filter(Tree.id.in_(subquery))
            else:
                query = query.filter(~Tree.id.in_(subquery))

        if has_mushroom is not None:
            subquery = self.db.query(Mushroom.tree_id).distinct()
            if has_mushroom:
                query = query.filter(Tree.id.in_(subquery))
            else:
                query = query.filter(~Tree.id.in_(subquery))

        return query.count()

    def get_tree_stats(
        self,
        prefecture: str | None,
        city: str | None,
        vitality_range: tuple[int | None, int | None] | None,
        age_range: tuple[int | None, int | None] | None,
        has_hole: bool | None,
        has_tengusu: bool | None,
        has_mushroom: bool | None
    ) -> dict:
        """条件に合致する桜の統計情報を取得する"""
        # ベースとなるクエリを作成（count_treesと同じ条件）
        query = self.db.query(Tree)

        # 位置による絞り込み
        if prefecture or city:
            # TODO: 逆ジオコーディングAPIを使用して緯度経度の範囲を取得
            pass

        # 元気度による絞り込み
        if vitality_range:
            if vitality_range[0] is not None:
                query = query.filter(Tree.vitality >= vitality_range[0])
            if vitality_range[1] is not None:
                query = query.filter(Tree.vitality <= vitality_range[1])

        # 樹齢による絞り込み（幹周りから推定）
        if age_range:
            # TODO: 幹周りから樹齢を推定する計算式を実装
            if age_range[0] is not None:
                pass  # TODO: 最小樹齢の条件を適用
            if age_range[1] is not None:
                pass  # TODO: 最大樹齢の条件を適用

        # 状態による絞り込み
        if has_hole is not None:
            subquery = self.db.query(StemHole.tree_id).distinct()
            if has_hole:
                query = query.filter(Tree.id.in_(subquery))
            else:
                query = query.filter(~Tree.id.in_(subquery))

        if has_tengusu is not None:
            subquery = self.db.query(Tengus.tree_id).distinct()
            if has_tengusu:
                query = query.filter(Tree.id.in_(subquery))
            else:
                query = query.filter(~Tree.id.in_(subquery))

        if has_mushroom is not None:
            subquery = self.db.query(Mushroom.tree_id).distinct()
            if has_mushroom:
                query = query.filter(Tree.id.in_(subquery))
            else:
                query = query.filter(~Tree.id.in_(subquery))

        # 元気度の分布を取得
        vitality_stats = {
            f"vitality_{i}": query.filter(
                Tree.vitality >= i,
                Tree.vitality < i + 1
            ).count()
            for i in range(1, 6)
        }

        # 樹齢の分布を取得
        # TODO: 幹周りから樹齢を推定する計算式を実装
        age_stats = {
            "age_0_20": 0,
            "age_30_39": 0,
            "age_40_49": 0,
            "age_50_59": 0,
            "age_60_plus": 0
        }

        return {**vitality_stats, **age_stats}

    def get_flowering_info(
        self,
        latitude: float,
        longitude: float
    ) -> dict:
        """開花情報を取得する"""
        # TODO: 外部APIを使用して住所を取得
        address = "東京都千代田区"

        # TODO: 気象データAPIを使用して開花予想日を計算
        flowering_date = "2024-03-20"
        full_bloom_date = "2024-03-27"

        return {
            "address": address,
            "flowering_date": flowering_date,
            "full_bloom_date": full_bloom_date
        }
