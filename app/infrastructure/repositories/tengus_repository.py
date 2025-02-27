from datetime import datetime
from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import Tengus


class TengusRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_tengus_by_tree_id(self, tree_id: int) -> List[Tengus]:
        """
        木に紐づくテングス病の情報を取得する

        Args:
            tree_id (int): 木のID

        Returns:
            List[Tengus]: テングス病の情報のリスト
        """
        return self.db.query(Tengus).filter(Tengus.tree_id == tree_id).all()

    def get_tengus_by_id(self, tengus_id: int) -> Optional[Tengus]:
        """
        テングス病の情報をIDで取得する

        Args:
            tengus_id (int): テングス病のID

        Returns:
            Optional[Tengus]: テングス病の情報。存在しない場合はNone
        """
        return self.db.query(Tengus).filter(Tengus.id == tengus_id).first()

    def create_tengus(
        self,
        tree_id: int,
        user_id: int,
        latitude: float,
        longitude: float,
        image_obj_key: str,
        thumb_obj_key: str,
        photo_date: Optional[datetime] = None
    ) -> Tengus:
        """
        テングス病の情報を保存する

        Args:
            tree_id (int): 木のID
            user_id (int): ユーザーID
            latitude (float): 緯度
            longitude (float): 経度
            image_obj_key (str): 画像のオブジェクトキー
            thumb_obj_key (str): サムネイル画像のオブジェクトキー
            photo_date (Optional[datetime]): 撮影日時

        Returns:
            Tengus: 作成されたテングス病の情報
        """
        tengus = Tengus(
            tree_id=tree_id,
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_obj_key,
            thumb_obj_key=thumb_obj_key,
            photo_date=photo_date
        )
        self.db.add(tengus)
        self.db.commit()
        self.db.refresh(tengus)
        return tengus

    def delete_tengus(self, tengus_id: int) -> bool:
        """
        テングス病の情報を削除する

        Args:
            tengus_id (int): テングス病のID

        Returns:
            bool: 削除に成功したかどうか
        """
        try:
            tengus = self.get_tengus_by_id(tengus_id)
            if not tengus:
                logger.warning(f"削除対象のテングス病が見つかりません: tengus_id={tengus_id}")
                return False

            self.db.delete(tengus)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"テングス病の削除中にエラー発生: {str(e)}")
            self.db.rollback()
            return False
