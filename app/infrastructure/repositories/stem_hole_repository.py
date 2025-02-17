from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import StemHole


class StemHoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_stem_holes_by_tree_id(self, tree_id: int) -> List[StemHole]:
        """
        木に紐づく幹の穴の情報を取得する

        Args:
            tree_id (int): 木のID

        Returns:
            List[StemHole]: 幹の穴の情報のリスト
        """
        return self.db.query(StemHole).filter(StemHole.tree_id == tree_id).all()

    def get_stem_hole_by_id(self, stem_hole_id: int) -> Optional[StemHole]:
        """
        幹の穴の情報をIDで取得する

        Args:
            stem_hole_id (int): 幹の穴のID

        Returns:
            Optional[StemHole]: 幹の穴の情報。存在しない場合はNone
        """
        return self.db.query(StemHole).filter(StemHole.id == stem_hole_id).first()

    def create_stem_hole(
        self,
        tree_id: int,
        user_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
    ) -> StemHole:
        """
        幹の穴の情報を保存する

        Args:
            tree_id (int): 木のID
            user_id (int): ユーザーID
            latitude (float): 緯度
            longitude (float): 経度
            image_obj_key (str): 画像のオブジェクトキー
            thumb_obj_key (str): サムネイル画像のオブジェクトキー

        Returns:
            StemHole: 作成された幹の穴の情報
        """
        stem_hole = StemHole(
            tree_id=tree_id,
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
        )
        self.db.add(stem_hole)
        self.db.commit()
        self.db.refresh(stem_hole)
        return stem_hole

    def delete_stem_hole(self, stem_hole_id: int) -> bool:
        """
        幹の穴の情報を削除する

        Args:
            stem_hole_id (int): 幹の穴のID

        Returns:
            bool: 削除に成功したかどうか
        """
        try:
            stem_hole = self.get_stem_hole_by_id(stem_hole_id)
            if not stem_hole:
                logger.warning(
                    f"削除対象の幹の穴が見つかりません: stem_hole_id={stem_hole_id}")
                return False

            self.db.delete(stem_hole)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"幹の穴の削除中にエラー発生: {str(e)}")
            self.db.rollback()
            return False
