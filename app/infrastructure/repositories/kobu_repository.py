from datetime import datetime
from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import Kobu


class KobuRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_kobus_by_tree_id(self, tree_id: int) -> List[Kobu]:
        """
        木に紐づくこぶ状の枝の情報を取得する

        Args:
            tree_id (int): 木のID

        Returns:
            List[Kobu]: こぶ状の枝の情報のリスト
        """
        return self.db.query(Kobu).filter(Kobu.tree_id == tree_id).all()

    def get_kobu_by_id(self, kobu_id: int) -> Optional[Kobu]:
        """
        こぶ状の枝の情報をIDで取得する

        Args:
            kobu_id (int): こぶ状の枝のID

        Returns:
            Optional[Kobu]: こぶ状の枝の情報。存在しない場合はNone
        """
        return self.db.query(Kobu).filter(Kobu.id == kobu_id).first()

    def create_kobu(
        self,
        tree_id: int,
        user_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
        photo_date: Optional[datetime] = None
    ) -> Kobu:
        """
        こぶ状の枝の情報を保存する

        Args:
            tree_id (int): 木のID
            user_id (int): ユーザーID
            latitude (float): 緯度
            longitude (float): 経度
            image_obj_key (str): 画像のオブジェクトキー
            thumb_obj_key (str): サムネイル画像のオブジェクトキー
            photo_date (Optional[datetime]): 撮影日時

        Returns:
            Kobu: 作成されたこぶ状の枝の情報
        """
        kobu = Kobu(
            tree_id=tree_id,
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            photo_date=photo_date
        )
        self.db.add(kobu)
        self.db.commit()
        self.db.refresh(kobu)
        return kobu

    def delete_kobu(self, kobu_id: int) -> bool:
        """
        こぶ状の枝の情報を削除する

        Args:
            kobu_id (int): こぶ状の枝のID

        Returns:
            bool: 削除に成功したかどうか
        """
        try:
            kobu = self.get_kobu_by_id(kobu_id)
            if not kobu:
                logger.warning(f"削除対象のこぶ状の枝が見つかりません: kobu_id={kobu_id}")
                return False

            self.db.delete(kobu)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"こぶ状の枝の削除中にエラー発生: {str(e)}")
            self.db.rollback()
            return False
