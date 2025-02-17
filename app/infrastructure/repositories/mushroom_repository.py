from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import Mushroom


class MushroomRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_mushrooms_by_tree_id(self, tree_id: int) -> List[Mushroom]:
        """
        木に紐づくキノコの情報を取得する

        Args:
            tree_id (int): 木のID

        Returns:
            List[Mushroom]: キノコの情報のリスト
        """
        return self.db.query(Mushroom).filter(Mushroom.tree_id == tree_id).all()

    def get_mushroom_by_id(self, mushroom_id: int) -> Optional[Mushroom]:
        """
        キノコの情報をIDで取得する

        Args:
            mushroom_id (int): キノコのID

        Returns:
            Optional[Mushroom]: キノコの情報。存在しない場合はNone
        """
        return self.db.query(Mushroom).filter(Mushroom.id == mushroom_id).first()

    def create_mushroom(
        self,
        tree_id: int,
        user_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
    ) -> Mushroom:
        """
        キノコの情報を保存する

        Args:
            tree_id (int): 木のID
            user_id (int): ユーザーID
            latitude (float): 緯度
            longitude (float): 経度
            image_obj_key (str): 画像のオブジェクトキー
            thumb_obj_key (str): サムネイル画像のオブジェクトキー

        Returns:
            Mushroom: 作成されたキノコの情報
        """
        mushroom = Mushroom(
            tree_id=tree_id,
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
        )
        self.db.add(mushroom)
        self.db.commit()
        self.db.refresh(mushroom)
        return mushroom

    def delete_mushroom(self, mushroom_id: int) -> bool:
        """
        キノコの情報を削除する

        Args:
            mushroom_id (int): キノコのID

        Returns:
            bool: 削除に成功したかどうか
        """
        try:
            mushroom = self.get_mushroom_by_id(mushroom_id)
            if not mushroom:
                logger.warning(f"削除対象のキノコが見つかりません: mushroom_id={mushroom_id}")
                return False

            self.db.delete(mushroom)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"キノコの削除中にエラー発生: {str(e)}")
            self.db.rollback()
            return False
