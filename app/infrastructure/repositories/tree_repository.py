from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.domain.models.area_stats import AreaStats
from app.domain.models.models import (CensorshipStatus, EntireTree, Kobu,
                                      Mushroom, PrefectureStats, Stem,
                                      StemHole, Tengus, Tree)
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
        contributor: Optional[str],
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
        vitality: int,
        vitality_real: Optional[float] = None,
        vitality_noleaf: Optional[int] = None,
        vitality_noleaf_real: Optional[float] = None,
        vitality_noleaf_weight: Optional[float] = None,
        vitality_bloom: Optional[int] = None,
        vitality_bloom_real: Optional[float] = None,
        vitality_bloom_weight: Optional[float] = None,
        location: Optional[str] = None,
        prefecture_code: Optional[str] = None,
        municipality_code: Optional[str] = None,
        block: Optional[str] = None,
        photo_date: Optional[datetime] = None,
        vitality_bloom_30: Optional[int] = None,
        vitality_bloom_30_real: Optional[float] = None,
        vitality_bloom_30_weight: Optional[float] = None,
        vitality_bloom_50: Optional[int] = None,
        vitality_bloom_50_real: Optional[float] = None,
        vitality_bloom_50_weight: Optional[float] = None,
        debug_image_obj_key: Optional[str] = None,
        debug_image_obj2_key: Optional[str] = None,
        bloom_status: Optional[str] = None,
        flowering_date: date | None = None,
        bloom_30_date: date | None = None,
        bloom_50_date: date | None = None,
        full_bloom_date: date | None = None,
        full_bloom_end_date: date | None = None,
        version: int = 202601,
    ) -> Tree:
        """
        新しい木を作成する

        Args:
            user_id: ユーザーID
            contributor: 投稿者名
            latitude: 緯度
            longitude: 経度
            image_obj_key: 画像のS3オブジェクトキー
            thumb_obj_key: サムネイル画像のS3オブジェクトキー
            vitality: 元気度
            vitality_real: 元気度の実数値
            location: 場所の名前
            prefecture_code: 都道府県コード
            municipality_code: 市区町村コード
            block: ブロック（A, B, C）
            photo_date: 撮影日時

        Returns:
            作成された木のオブジェクト
        """
        position = f'POINT({longitude} {latitude})'
        tree = Tree(
            user_id=user_id,
            contributor=contributor,
            latitude=latitude,
            longitude=longitude,
            position=func.ST_GeomFromText(position),
            location=location,
            prefecture_code=prefecture_code,
            municipality_code=municipality_code,
            block=block,
            photo_date=photo_date,
            photo_time=photo_date.time() if photo_date else None,
            version=version,
        )
        self.db.add(tree)
        self.db.flush()  # DBに反映してIDを取得

        # 全体写真を作成
        entire_tree = EntireTree(
            user_id=user_id,
            tree_id=tree.id,
            vitality=vitality,
            vitality_real=vitality_real,
            vitality_noleaf=vitality_noleaf,
            vitality_noleaf_real=vitality_noleaf_real,
            vitality_noleaf_weight=vitality_noleaf_weight,
            vitality_bloom=vitality_bloom,
            vitality_bloom_real=vitality_bloom_real,
            vitality_bloom_weight=vitality_bloom_weight,
            vitality_bloom_30=vitality_bloom_30,
            vitality_bloom_30_real=vitality_bloom_30_real,
            vitality_bloom_30_weight=vitality_bloom_30_weight,
            vitality_bloom_50=vitality_bloom_50,
            vitality_bloom_50_real=vitality_bloom_50_real,
            vitality_bloom_50_weight=vitality_bloom_50_weight,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            photo_date=photo_date,
            debug_image_obj_key=debug_image_obj_key,
            debug_image_obj2_key=debug_image_obj2_key,
            bloom_status=bloom_status,
            flowering_date=flowering_date,
            bloom_30_date=bloom_30_date,
            bloom_50_date=bloom_50_date,
            full_bloom_date=full_bloom_date,
            full_bloom_end_date=full_bloom_end_date,
        )
        self.db.add(entire_tree)
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

    def get_tree_with_entire_tree(self, tree_uid: str) -> Optional[Tree]:
        """UIDを使用してツリーを取得する"""
        return self.db.query(Tree).options(joinedload(Tree.entire_tree)).filter(Tree.uid == tree_uid).first()

    def get_tree_with_stem(self, tree_uid: str) -> Optional[Tree]:
        """UIDを使用してツリーを取得する"""
        return self.db.query(Tree).options(joinedload(Tree.stem)).filter(Tree.uid == tree_uid).first()

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
        # 検閲ステータスがAPPROVEDのものだけを対象とするベースクエリを作成
        query = self.db.query(Tree).filter(
            Tree.censorship_status == CensorshipStatus.APPROVED)

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
            # EntireTreeテーブルと結合して元気度条件を適用（検閲ステータスも考慮）
            query = query.join(EntireTree).filter(
                EntireTree.vitality >= vitality_range[0],
                EntireTree.vitality <= vitality_range[1],
                EntireTree.censorship_status == CensorshipStatus.APPROVED
            )

        # age_rangeが指定されている場合のみstemテーブルと結合（検閲ステータスも考慮）
        if age_range:
            query = query.join(Stem).filter(
                Stem.age >= age_range[0],
                Stem.age <= age_range[1],
                Stem.censorship_status == CensorshipStatus.APPROVED
            )

        if has_hole is not None:
            if has_hole:
                query = query.join(StemHole).filter(
                    StemHole.censorship_status == CensorshipStatus.APPROVED)
            else:
                query = query.outerjoin(StemHole).filter(
                    StemHole.id.is_(None) | (StemHole.censorship_status != CensorshipStatus.APPROVED))
        if has_tengusu is not None:
            if has_tengusu:
                query = query.join(Tengus).filter(
                    Tengus.censorship_status == CensorshipStatus.APPROVED)
            else:
                query = query.outerjoin(Tengus).filter(
                    Tengus.id.is_(None) | (Tengus.censorship_status != CensorshipStatus.APPROVED))
        if has_mushroom is not None:
            if has_mushroom:
                query = query.join(Mushroom).filter(
                    Mushroom.censorship_status == CensorshipStatus.APPROVED)
            else:
                query = query.outerjoin(Mushroom).filter(
                    Mushroom.id.is_(None) | (Mushroom.censorship_status != CensorshipStatus.APPROVED))
        if has_kobu is not None:
            if has_kobu:
                query = query.join(Kobu).filter(
                    Kobu.censorship_status == CensorshipStatus.APPROVED)
            else:
                query = query.outerjoin(Kobu).filter(
                    Kobu.id.is_(None) | (Kobu.censorship_status != CensorshipStatus.APPROVED))

        total = query.count()
        trees = query.offset(offset).limit(limit).all()
        return trees, total

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
            EntireTree.vitality,
            func.count(Tree.id).label('count')
        ).join(EntireTree, Tree.id == EntireTree.tree_id)
        if municipality_code:
            vitality_counts = vitality_counts.filter(
                Tree.municipality_code == municipality_code)
        else:
            vitality_counts = vitality_counts.filter(
                Tree.prefecture_code == prefecture_code)
        vitality_counts = vitality_counts.filter(
            EntireTree.censorship_status == CensorshipStatus.APPROVED,
            Tree.censorship_status == CensorshipStatus.APPROVED
        ).group_by(EntireTree.vitality).all()

        vitality_dict = {v: 0 for v in range(1, 6)}
        for vitality, count in vitality_counts:
            vitality_dict[vitality] = count

        # 樹齢ごとの本数を取得
        age_counts = self.db.query(
            case(
                {
                    Stem.age <= 19: '20',
                    Stem.age <= 39: '30',
                    Stem.age <= 59: '40',
                    Stem.age <= 79: '50'
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
        age_counts = age_counts.filter(
            Stem.censorship_status == CensorshipStatus.APPROVED,
            Tree.censorship_status == CensorshipStatus.APPROVED
        ).group_by('age_group').all()

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
        if not municipality_code and not prefecture_code:
            raise ValueError(
                "prefecture_code または municipality_code のいずれかを指定する必要があります")

        # 直接エンティティごとにクエリを実行
        stem_hole_query = self.db.query(StemHole).filter(
            StemHole.censorship_status == CensorshipStatus.APPROVED
        )

        tengus_query = self.db.query(Tengus).filter(
            Tengus.censorship_status == CensorshipStatus.APPROVED
        )

        mushroom_query = self.db.query(Mushroom).filter(
            Mushroom.censorship_status == CensorshipStatus.APPROVED
        )

        kobu_query = self.db.query(Kobu).filter(
            Kobu.censorship_status == CensorshipStatus.APPROVED
        )

        # 地域フィルターを適用
        if municipality_code:
            stem_hole_query = stem_hole_query.join(Tree).filter(
                Tree.municipality_code == municipality_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
            tengus_query = tengus_query.join(Tree).filter(
                Tree.municipality_code == municipality_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
            mushroom_query = mushroom_query.join(Tree).filter(
                Tree.municipality_code == municipality_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
            kobu_query = kobu_query.join(Tree).filter(
                Tree.municipality_code == municipality_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
        elif prefecture_code:
            stem_hole_query = stem_hole_query.join(Tree).filter(
                Tree.prefecture_code == prefecture_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
            tengus_query = tengus_query.join(Tree).filter(
                Tree.prefecture_code == prefecture_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
            mushroom_query = mushroom_query.join(Tree).filter(
                Tree.prefecture_code == prefecture_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)
            kobu_query = kobu_query.join(Tree).filter(
                Tree.prefecture_code == prefecture_code,
                Tree.censorship_status == CensorshipStatus.APPROVED)

        # 各エンティティを取得（最大30件）
        stem_holes = stem_hole_query.order_by(
            StemHole.photo_date.desc()).limit(30).all()
        tengus = tengus_query.order_by(
            Tengus.photo_date.desc()).limit(30).all()
        mushrooms = mushroom_query.order_by(
            Mushroom.photo_date.desc()).limit(30).all()
        kobus = kobu_query.order_by(Kobu.photo_date.desc()).limit(30).all()

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
        logger.info(
            "エリアコードに基づく桜の本数集計開始: "
            + f"area_type={area_type}"
        )

        # area_type に応じたカラムを決定
        group_col = (
            Tree.prefecture_code if area_type == 'prefecture'
            else Tree.municipality_code
        )

        # Step 1: counts サブクエリ（1回のスキャンで count + max(id)）
        counts_query = (
            self.db.query(
                group_col,
                func.count(Tree.id).label('count'),
                func.max(Tree.id).label('latest_tree_id')
            )
            .filter(
                Tree.censorship_status == CensorshipStatus.APPROVED,
                group_col.in_(area_codes)
            )
        )

        # フィルタ条件を counts_query に適用
        if vitality_range:
            counts_query = counts_query.join(EntireTree).filter(
                EntireTree.vitality.between(
                    vitality_range[0], vitality_range[1]),
                EntireTree.censorship_status == CensorshipStatus.APPROVED)
        if age_range:
            counts_query = counts_query.join(Stem).filter(
                Stem.age.between(age_range[0], age_range[1]),
                Stem.censorship_status == CensorshipStatus.APPROVED)
        if has_hole is not None:
            if has_hole:
                counts_query = counts_query.join(StemHole).filter(
                    StemHole.censorship_status
                    == CensorshipStatus.APPROVED)
            else:
                counts_query = counts_query.outerjoin(
                    StemHole
                ).filter(
                    StemHole.id.is_(None)
                    | (StemHole.censorship_status
                       != CensorshipStatus.APPROVED))
        if has_tengusu is not None:
            if has_tengusu:
                counts_query = counts_query.join(Tengus).filter(
                    Tengus.censorship_status
                    == CensorshipStatus.APPROVED)
            else:
                counts_query = counts_query.outerjoin(
                    Tengus
                ).filter(
                    Tengus.id.is_(None)
                    | (Tengus.censorship_status
                       != CensorshipStatus.APPROVED))
        if has_mushroom is not None:
            if has_mushroom:
                counts_query = counts_query.join(Mushroom).filter(
                    Mushroom.censorship_status
                    == CensorshipStatus.APPROVED)
            else:
                counts_query = counts_query.outerjoin(
                    Mushroom
                ).filter(
                    Mushroom.id.is_(None)
                    | (Mushroom.censorship_status
                       != CensorshipStatus.APPROVED))
        if has_kobu is not None:
            if has_kobu:
                counts_query = counts_query.join(Kobu).filter(
                    Kobu.censorship_status
                    == CensorshipStatus.APPROVED)
            else:
                counts_query = counts_query.outerjoin(
                    Kobu
                ).filter(
                    Kobu.id.is_(None)
                    | (Kobu.censorship_status
                       != CensorshipStatus.APPROVED))

        counts = counts_query.group_by(group_col).subquery()

        # Step 2: details サブクエリ（PKルックアップで最新ツリーの詳細取得）
        details = (
            self.db.query(
                Tree.id,
                Tree.contributor.label('latest_contributor'),
                Tree.contributor_censorship_status.label(
                    'latest_contributor_censorship_status'),
                func.max(EntireTree.thumb_obj_key).label(
                    'latest_image_thumb_url')
            )
            .join(EntireTree, Tree.id == EntireTree.tree_id)
            .filter(
                EntireTree.censorship_status == CensorshipStatus.APPROVED
            )
            .group_by(Tree.id)
            .subquery()
        )

        # Step 3: メインクエリ（GROUP BY 不要）
        area_col = (
            counts.c.prefecture_code if area_type == 'prefecture'
            else counts.c.municipality_code
        )
        query = self.db.query(
            area_col,
            counts.c.count,
            details.c.latest_contributor,
            details.c.latest_contributor_censorship_status,
            details.c.latest_image_thumb_url
        ).outerjoin(
            details,
            counts.c.latest_tree_id == details.c.id
        )

        results = query.all()
        logger.debug(f"集計結果: {len(results)}件")

        # 結果をAreaCountItemに変換
        return [
            AreaCountItem(
                prefecture_code=r[0] if area_type == 'prefecture' else None,
                municipality_code=r[0] if area_type == 'municipality' else None,
                location='NotSet',  # locationは呼び出し側で設定
                count=r[1] or 0,
                latitude=0,  # latitudeとlongitudeは呼び出し側で設定
                longitude=0,
                latest_contributor=r[2] if r[3] == CensorshipStatus.APPROVED else None,
                latest_image_thumb_url=r[4],
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

    def find_trees_by_time_range_block(
        self,
        db: Session,
        reference_time: time,
        start_date: datetime,
        blocks: List[str],
        per_block_limit: int,
        censorship_status: int = CensorshipStatus.APPROVED
    ) -> Dict[str, List["Tree"]]:
        """
        指定された時間帯の範囲内で各ブロックごとの樹木を取得する

        Args:
            db (Session): DBセッション
            reference_time (time): 基準時刻
            start_date (datetime): 検索開始日時
            blocks (List[str]): 検索対象のブロック
            per_block_limit (int): ブロックごとの最大取得件数
            censorship_status (int): 検閲ステータス

        Returns:
            Dict[str, Tuple[List["Tree"], int]]: ブロックごとの樹木リストと総数
        """
        # 時間範囲の計算
        # reference_timeから1時間前までを検索範囲とする
        end_time = reference_time
        start_time = (datetime.combine(datetime.today(),
                      end_time) - timedelta(hours=1)).time()

        # 結果を格納する辞書
        results = {}

        # 各ブロックに対して検索を実行
        for block in blocks:
            # サブクエリの条件：指定されたブロックと時刻の条件
            subquery = (
                db.query(Tree)
                .filter(Tree.block == block)
                .filter(Tree.censorship_status == censorship_status)
                .filter(Tree.photo_date >= start_date)
            )

            # 時間範囲の条件
            if start_time < end_time:
                # 日付をまたがない場合: 開始時刻から終了時刻まで
                time_condition = and_(
                    Tree.photo_time >= start_time,
                    Tree.photo_time <= end_time
                )
            else:
                # 日付をまたぐ場合: 開始時刻から翌日の終了時刻まで
                time_condition = or_(
                    Tree.photo_time >= start_time,
                    Tree.photo_time <= end_time
                )

            subquery = subquery.filter(time_condition)

            # 最大件数を制限して取得
            items = subquery.order_by(
                Tree.photo_date.desc()).limit(per_block_limit).all()

            # 結果を保存
            results[block] = items

        return results
