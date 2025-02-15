from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.models import (Kobu, MunicipalityStats, Mushroom,
                                      PrefectureStats, Stem, StemHole, Tengus,
                                      Tree)
from app.interfaces.schemas.tree import AreaCountItem


class TreeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_tree(
        self,
        user_id: int,
        uid: str,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
        vitality: float,
        position: str,
        location: str,
        prefecture_code: str,
        municipality_code: str
    ) -> Tree:
        tree = Tree(
            user_id=user_id,
            uid=uid,
            latitude=latitude,
            longitude=longitude,
            position=func.ST_GeomFromText(position),
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            vitality=vitality,
            location=location,
            prefecture_code=prefecture_code,
            municipality_code=municipality_code
        )
        self.db.add(tree)
        self.db.commit()
        self.db.refresh(tree)
        return tree

    def update_tree(self, tree: Tree) -> bool:
        self.db.commit()
        return True

    def create_stem(
        self,
        db: Session,
        tree_id: int,
        user_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
        texture: int,
        can_detected: bool,
        circumference: Optional[float],
        age: int,
    ) -> Stem:
        """幹の情報を保存する"""
        stem = Stem(
            tree_id=tree_id,
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            texture=texture,
            can_detected=can_detected,
            circumference=circumference,
            age=age,
        )
        db.add(stem)
        db.commit()
        db.refresh(stem)
        return stem

    def create_stem_hole(
        self,
        user_id: int,
        tree_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str
    ) -> bool:
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

    def create_tengus(
        self,
        user_id: int,
        tree_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str
    ) -> Tengus:
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

    def create_mushroom(
        self,
        user_id: int,
        tree_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str
    ) -> bool:
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

    def create_kobu(
        self,
        user_id: int,
        tree_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str
    ) -> bool:
        """こぶ状の枝の写真を登録する"""
        tree = self.db.query(Tree).filter(Tree.id == tree_id).first()
        if not tree:
            return False

        kobu = Kobu(
            user_id=user_id,
            tree_id=tree_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key
        )
        self.db.add(kobu)
        self.db.commit()
        return True

    def get_tree(self, tree_uid: str) -> Optional[Tree]:
        """UIDを使用してツリーを取得する"""
        return self.db.query(Tree).filter(Tree.uid == tree_uid).first()

    def get_tree_by_id(self, tree_id: int) -> Optional[Tree]:
        """内部IDを使用してツリーを取得する（内部処理用）"""
        return self.db.query(Tree).filter(Tree.id == tree_id).first()

    def search_trees(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: Optional[float] = None,
        municipality_code: Optional[str] = None,
        vitality_range: Optional[tuple[int, int]] = None,
        age_range: Optional[tuple[int, int]] = None,
        has_hole: Optional[bool] = None,
        has_tengusu: Optional[bool] = None,
        has_mushroom: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[Tree], int]:
        query = self.db.query(Tree).outerjoin(Stem)

        # 市区町村コードまたは位置による検索
        if municipality_code is not None:
            query = query.filter(Tree.municipality_code == municipality_code)
        elif latitude is not None and longitude is not None and radius is not None:
            query = query.filter(
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
        if age_range:
            query = query.join(Stem).filter(
                Stem.age >= age_range[0],
                Stem.age <= age_range[1]
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

    def get_prefecture_stats(self, prefecture_code: str) -> PrefectureStats | None:
        """都道府県の統計情報を取得する"""
        return self.db.query(PrefectureStats).filter(
            PrefectureStats.prefecture_code == prefecture_code
        ).first()

    def get_municipality_stats(self, municipality_code: str) -> MunicipalityStats | None:
        """市区町村の統計情報を取得する"""
        return self.db.query(MunicipalityStats).filter(
            MunicipalityStats.municipality_code == municipality_code
        ).first()

    def get_area_counts(
        self,
        area_type: str,
        latitude: float,
        longitude: float,
        radius: float,
        vitality_range: Optional[Tuple[int, int]] = None,
        age_range: Optional[Tuple[int, int]] = None,
        has_hole: Optional[bool] = None,
        has_tengusu: Optional[bool] = None,
        has_mushroom: Optional[bool] = None
    ) -> List[AreaCountItem]:
        """エリアごとの桜の本数を取得する"""
        logger.info(f"エリアごとの桜の本数を取得開始: area_type={area_type}, lat={
                    latitude}, lon={longitude}, radius={radius}m")
        try:
            # area_typeに応じてSELECT句を変更
            if area_type == 'prefecture':
                query = self.db.query(
                    Tree.prefecture_code,
                    func.avg(Tree.latitude).label('latitude'),
                    func.avg(Tree.longitude).label('longitude'),
                    func.count(Tree.id).label('count')
                )
            else:  # municipality
                query = self.db.query(
                    Tree.municipality_code,
                    func.avg(Tree.latitude).label('latitude'),
                    func.avg(Tree.longitude).label('longitude'),
                    func.count(Tree.id).label('count')
                )

            query = query.filter(
                func.ST_Distance_Sphere(
                    Tree.position,
                    func.ST_GeomFromText(f'POINT({longitude} {latitude})')
                ) <= radius
            )

            # フィルタ条件を適用
            if vitality_range:
                logger.debug(f"元気度フィルタを適用: min={vitality_range[0]}, max={
                             vitality_range[1]}")
                query = query.filter(
                    Tree.vitality.between(vitality_range[0], vitality_range[1]))
            if age_range:
                logger.debug(f"樹齢フィルタを適用: min={
                             age_range[0]}, max={age_range[1]}")
                query = query.join(Stem).filter(
                    Stem.age.between(age_range[0], age_range[1]))
            if has_hole is not None:
                logger.debug(f"幹の穴フィルタを適用: has_hole={has_hole}")
                if has_hole:
                    query = query.join(StemHole)
                else:
                    query = query.outerjoin(StemHole).filter(
                        StemHole.id.is_(None))
            if has_tengusu is not None:
                logger.debug(f"テングス病フィルタを適用: has_tengusu={has_tengusu}")
                if has_tengusu:
                    query = query.join(Tengus)
                else:
                    query = query.outerjoin(Tengus).filter(Tengus.id.is_(None))
            if has_mushroom is not None:
                logger.debug(f"キノコフィルタを適用: has_mushroom={has_mushroom}")
                if has_mushroom:
                    query = query.join(Mushroom)
                else:
                    query = query.outerjoin(Mushroom).filter(
                        Mushroom.id.is_(None))

            # グループ化
            if area_type == 'prefecture':
                logger.debug("都道府県単位でグループ化")
                query = query.group_by(Tree.prefecture_code)
            else:  # municipality
                logger.debug("市区町村単位でグループ化")
                query = query.group_by(Tree.municipality_code)

            logger.debug("クエリ実行開始")
            results = query.all()
            logger.info(f"クエリ実行完了: {len(results)}件の結果を取得")

            area_counts = [
                AreaCountItem(
                    prefecture_code=r[0] if area_type == 'prefecture' else None,
                    municipality_code=r[0] if area_type == 'municipality' else None,
                    location='TODO: 東京都',  # locationは集計時には不要
                    count=r[3] or 0,  # countは4番目のカラム
                    latitude=r[1] or 0,  # latitudeは2番目のカラム
                    longitude=r[2] or 0,  # longitudeは3番目のカラム
                    latest_nickname=None,
                    latest_image_thumb_url=None,
                )
                for r in results
            ]
            logger.debug("レスポンスの整形完了")
            return area_counts

        except Exception as e:
            logger.exception(f"エリアごとの桜の本数取得中にエラー発生: {str(e)}")
            raise
