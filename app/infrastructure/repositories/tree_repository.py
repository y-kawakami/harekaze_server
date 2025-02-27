from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.domain.models.area_stats import AreaStats
from app.domain.models.models import (CensorshipStatus, Kobu, Mushroom,
                                      PrefectureStats, Stem, StemHole, Tengus,
                                      Tree)
from app.interfaces.schemas.tree import AreaCountItem


@dataclass
class TreeRelatedEntities:
    """木に関連するエンティティのデータクラス"""
    stem_holes: List[StemHole] = field(default_factory=list)
    tengus: List[Tengus] = field(default_factory=list)
    mushrooms: List[Mushroom] = field(default_factory=list)
    kobus: List[Kobu] = field(default_factory=list)

    stem_hole_count: int = 0
    tengus_count: int = 0
    mushroom_count: int = 0
    kobu_count: int = 0

    def __post_init__(self):
        """各リストを最大30件に制限"""
        self.stem_hole_count = len(self.stem_holes)
        self.stem_holes = self.stem_holes[:30]
        self.tengus_count = len(self.tengus)
        self.tengus = self.tengus[:30]
        self.mushroom_count = len(self.mushrooms)
        self.mushrooms = self.mushrooms[:30]
        self.kobu_count = len(self.kobus)
        self.kobus = self.kobus[:30]


class TreeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_tree(
        self,
        user_id: int,
        uid: str,
        contributor: Optional[str],
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
            contributor=contributor,
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
        has_kobu: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[Tree], int]:
        query = self.db.query(Tree)

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

        # age_rangeが指定されている場合のみstemテーブルと結合
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

        if has_kobu is not None:
            subq = self.db.query(Kobu.tree_id).distinct()
            if has_kobu:
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

    def get_area_stats(
        self,
        prefecture_code: Optional[str] = None,
        municipality_code: Optional[str] = None
    ) -> Optional[AreaStats]:
        """地域（都道府県または市区町村）の統計情報を取得する

        Args:
            prefecture_code (Optional[str]): 都道府県コード
            municipality_code (Optional[str]): 市区町村コード
            ※いずれか一方を指定する必要があります

        Returns:
            Optional[AreaStats]: 地域の統計情報
        """
        if not municipality_code and not prefecture_code:
            logger.error("都道府県コードと市区町村コードの両方が指定されていません")
            return None

        if municipality_code and prefecture_code:
            logger.error("都道府県コードと市区町村コードの両方が指定されています")
            return None

        # 基本となるクエリを作成
        base_query = self.db.query(Tree)
        if municipality_code:
            base_query = base_query.filter(
                Tree.municipality_code == municipality_code)
        else:
            base_query = base_query.filter(
                Tree.prefecture_code == prefecture_code)

        # 総本数を取得
        total_trees = base_query.count()
        if total_trees == 0:
            return None

        # 元気度ごとの本数を取得
        vitality_counts = self.db.query(
            Tree.vitality,
            func.count(Tree.id).label('count')
        )
        if municipality_code:
            vitality_counts = vitality_counts.filter(
                Tree.municipality_code == municipality_code)
        else:
            vitality_counts = vitality_counts.filter(
                Tree.prefecture_code == prefecture_code)
        vitality_counts = vitality_counts.group_by(Tree.vitality).all()

        vitality_dict = {v: 0 for v in range(1, 6)}
        for vitality, count in vitality_counts:
            vitality_dict[vitality] = count

        # 樹齢ごとの本数を取得
        age_counts = self.db.query(
            case(
                {
                    Stem.age <= 30: '20',
                    Stem.age <= 40: '30',
                    Stem.age <= 50: '40',
                    Stem.age <= 60: '50'
                },
                else_='60'
            ).label('age_group'),
            func.count(Tree.id).label('count')
        ).join(Tree)
        if municipality_code:
            age_counts = age_counts.filter(
                Tree.municipality_code == municipality_code)
        else:
            age_counts = age_counts.filter(
                Tree.prefecture_code == prefecture_code)
        age_counts = age_counts.group_by('age_group').all()

        age_dict = {'20': 0, '30': 0, '40': 0, '50': 0, '60': 0}
        for age_group, count in age_counts:
            age_dict[age_group] = count

        # 問題のある木の数を取得
        base_problem_query = self.db.query(Tree)
        if municipality_code:
            base_problem_query = base_problem_query.filter(
                Tree.municipality_code == municipality_code)
        else:
            base_problem_query = base_problem_query.filter(
                Tree.prefecture_code == prefecture_code)

        hole_count = base_problem_query.join(StemHole).distinct().count()
        tengusu_count = base_problem_query.join(Tengus).distinct().count()
        mushroom_count = base_problem_query.join(Mushroom).distinct().count()
        kobu_count = base_problem_query.join(Kobu).distinct().count()

        # AreaStatsオブジェクトを作成して返す
        return AreaStats(
            total_trees=total_trees,
            vitality1_count=vitality_dict[1],
            vitality2_count=vitality_dict[2],
            vitality3_count=vitality_dict[3],
            vitality4_count=vitality_dict[4],
            vitality5_count=vitality_dict[5],
            age20_count=age_dict['20'],
            age30_count=age_dict['30'],
            age40_count=age_dict['40'],
            age50_count=age_dict['50'],
            age60_count=age_dict['60'],
            hole_count=hole_count,
            tengus_count=tengusu_count,
            mushroom_count=mushroom_count,
            kobu_count=kobu_count,
        )

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
        has_mushroom: Optional[bool] = None,
        has_kobu: Optional[bool] = None
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
            if has_kobu is not None:
                logger.debug(f"こぶフィルタを適用: has_kobu={has_kobu}")
                if has_kobu:
                    query = query.join(Kobu)
                else:
                    query = query.outerjoin(Kobu).filter(Kobu.id.is_(None))

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
                    location='NotSet',  # locationは集計時には不要
                    count=r[3] or 0,  # countは4番目のカラム
                    latitude=r[1] or 0,  # latitudeは2番目のカラム
                    longitude=r[2] or 0,  # longitudeは3番目のカラム
                    latest_contributor=None,
                    latest_image_thumb_url=None,
                )
                for r in results
            ]
            logger.debug("レスポンスの整形完了")
            return area_counts

        except Exception as e:
            logger.exception(f"エリアごとの桜の本数取得中にエラー発生: {str(e)}")
            raise

    def list_tree_related_entities_in_region(
        self,
        prefecture_code: str | None = None,
        municipality_code: str | None = None,
    ) -> TreeRelatedEntities:
        """指定された地域の木に関連するエンティティを取得する

        Args:
            prefecture_code (str | None): 都道府県コード
            municipality_code (str | None): 市区町村コード

        Returns:
            TreeRelatedEntities: 各エンティティのリストを含むデータクラス
                - stem_holes: 幹の穴のリスト（最大30件）
                - tengus: テングス病のリスト（最大30件）
                - mushrooms: キノコのリスト（最大30件）
                - kobus: こぶのリスト（最大30件）

        Raises:
            ValueError: prefecture_codeとmunicipality_codeの両方がNoneの場合
        """
        # 基本となるツリーのクエリを作成
        tree_query = self.db.query(Tree.id)

        if municipality_code:
            tree_query = tree_query.filter(
                Tree.municipality_code == municipality_code)
        elif prefecture_code:
            tree_query = tree_query.filter(
                Tree.prefecture_code == prefecture_code)
        else:
            raise ValueError(
                "prefecture_code または municipality_code のいずれかを指定する必要があります")

        # 対象の木のIDを取得
        tree_ids = [tree_id for (tree_id,) in tree_query.all()]

        if not tree_ids:
            return TreeRelatedEntities()

        # 各エンティティを取得（最大30件）
        stem_holes = self.db.query(StemHole).filter(
            StemHole.tree_id.in_(tree_ids)
        ).limit(30).all()

        tengus = self.db.query(Tengus).filter(
            Tengus.tree_id.in_(tree_ids)
        ).limit(30).all()

        mushrooms = self.db.query(Mushroom).filter(
            Mushroom.tree_id.in_(tree_ids)
        ).limit(30).all()

        kobus = self.db.query(Kobu).filter(
            Kobu.tree_id.in_(tree_ids)
        ).limit(30).all()

        return TreeRelatedEntities(
            stem_holes=stem_holes,
            tengus=tengus,
            mushrooms=mushrooms,
            kobus=kobus
        )

    def get_area_counts_by_codes(
        self,
        area_type: str,
        area_codes: List[str],
        vitality_range: Optional[Tuple[int, int]] = None,
        age_range: Optional[Tuple[int, int]] = None,
        has_hole: Optional[bool] = None,
        has_tengusu: Optional[bool] = None,
        has_mushroom: Optional[bool] = None,
        has_kobu: Optional[bool] = None
    ) -> List[AreaCountItem]:
        """エリアコードのリストに基づいて桜の本数を集計する

        Args:
            area_type (str): 集計レベル（'prefecture'または'municipality'）
            area_codes (List[str]): 都道府県コードまたは市区町村コードのリスト
            vitality_range (Optional[Tuple[int, int]]): 元気度の範囲
            age_range (Optional[Tuple[int, int]]): 樹齢の範囲
            has_hole (Optional[bool]): 幹の穴の有無
            has_tengusu (Optional[bool]): テングス病の有無
            has_mushroom (Optional[bool]): キノコの有無
            has_kobu (Optional[bool]): こぶの有無

        Returns:
            List[AreaCountItem]: エリアごとの集計結果
        """
        logger.info(f"エリアコードに基づく桜の本数集計開始: area_type={area_type}")

        # サブクエリで最新の木を取得
        latest_tree_subq = self.db.query(
            Tree.prefecture_code if area_type == 'prefecture' else Tree.municipality_code,
            Tree.contributor.label('latest_contributor'),
            Tree.thumb_obj_key.label('latest_image_thumb_url'),
            func.row_number().over(
                partition_by=Tree.prefecture_code if area_type == 'prefecture' else Tree.municipality_code,
                order_by=Tree.created_at.desc()
            ).label('rn')
        ).filter(
            Tree.prefecture_code.in_(area_codes) if area_type == 'prefecture'
            else Tree.municipality_code.in_(area_codes)
        ).subquery()

        # メインクエリの作成
        if area_type == 'prefecture':
            query = self.db.query(
                Tree.prefecture_code,
                func.avg(Tree.latitude).label('latitude'),
                func.avg(Tree.longitude).label('longitude'),
                func.count(Tree.id).label('count'),
                func.max(latest_tree_subq.c.latest_contributor).label(
                    'latest_contributor'),
                func.max(latest_tree_subq.c.latest_image_thumb_url).label(
                    'latest_image_thumb_url')
            ).outerjoin(
                latest_tree_subq,
                (Tree.prefecture_code == latest_tree_subq.c.prefecture_code) &
                (latest_tree_subq.c.rn == 1)
            ).filter(Tree.prefecture_code.in_(area_codes))
        else:  # municipality
            query = self.db.query(
                Tree.municipality_code,
                func.avg(Tree.latitude).label('latitude'),
                func.avg(Tree.longitude).label('longitude'),
                func.count(Tree.id).label('count'),
                func.max(latest_tree_subq.c.latest_contributor).label(
                    'latest_contributor'),
                func.max(latest_tree_subq.c.latest_image_thumb_url).label(
                    'latest_image_thumb_url')
            ).outerjoin(
                latest_tree_subq,
                (Tree.municipality_code == latest_tree_subq.c.municipality_code) &
                (latest_tree_subq.c.rn == 1)
            ).filter(Tree.municipality_code.in_(area_codes))

        # フィルタ条件を適用
        if vitality_range:
            query = query.filter(
                Tree.vitality.between(vitality_range[0], vitality_range[1]))
        if age_range:
            query = query.join(Stem).filter(
                Stem.age.between(age_range[0], age_range[1]))
        if has_hole is not None:
            if has_hole:
                query = query.join(StemHole)
            else:
                query = query.outerjoin(StemHole).filter(StemHole.id.is_(None))
        if has_tengusu is not None:
            if has_tengusu:
                query = query.join(Tengus)
            else:
                query = query.outerjoin(Tengus).filter(Tengus.id.is_(None))
        if has_mushroom is not None:
            if has_mushroom:
                query = query.join(Mushroom)
            else:
                query = query.outerjoin(Mushroom).filter(Mushroom.id.is_(None))
        if has_kobu is not None:
            if has_kobu:
                query = query.join(Kobu)
            else:
                query = query.outerjoin(Kobu).filter(Kobu.id.is_(None))

        # グループ化
        if area_type == 'prefecture':
            query = query.group_by(Tree.prefecture_code)
        else:  # municipality
            query = query.group_by(Tree.municipality_code)

        results = query.all()
        logger.debug(f"集計結果: {len(results)}件")

        # 結果をAreaCountItemに変換
        return [
            AreaCountItem(
                prefecture_code=r[0] if area_type == 'prefecture' else None,
                municipality_code=r[0] if area_type == 'municipality' else None,
                location='NotSet',  # locationは呼び出し側で設定
                count=r[3] or 0,
                latitude=r[1] or 0,
                longitude=r[2] or 0,
                latest_contributor=r[4],
                latest_image_thumb_url=r[5],
            )
            for r in results
        ]

    def count_trees_by_status(self, status: Optional[CensorshipStatus] = None) -> int:
        """
        指定された検閲ステータスの木の総数を取得する

        Args:
            status (Optional[CensorshipStatus]): 検閲ステータス。Noneの場合は全ての木を対象とする。

        Returns:
            int: 指定された検閲ステータスの木の総数
        """
        query = self.db.query(Tree)
        if status is not None:
            query = query.filter(Tree.censorship_status == status)
        return query.count()
