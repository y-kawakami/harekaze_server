from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import Stem


class StemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_stem_by_tree_id(self, tree_id: int) -> Optional[Stem]:
        """
        木に紐づく幹の情報を取得する

        Args:
            tree_id (int): 木のID

        Returns:
            Optional[Stem]: 幹の情報。存在しない場合はNone
        """
        return self.db.query(Stem).filter(Stem.tree_id == tree_id).first()

    def get_stem_by_id(self, stem_id: int) -> Optional[Stem]:
        """
        幹の情報をIDで取得する

        Args:
            stem_id (int): 幹のID

        Returns:
            Optional[Stem]: 幹の情報。存在しない場合はNone
        """
        return self.db.query(Stem).filter(Stem.id == stem_id).first()

    def create_stem(
        self,
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
        photo_date: Optional[datetime] = None
    ) -> Stem:
        """
        幹の情報を保存する

        Args:
            tree_id (int): 木のID
            user_id (int): ユーザーID
            latitude (float): 緯度
            longitude (float): 経度
            image_obj_key (str): 画像のオブジェクトキー
            thumb_obj_key (str): サムネイル画像のオブジェクトキー
            texture (int): 幹の模様スコア
            can_detected (bool): 缶が検出されたかどうか
            circumference (Optional[float]): 幹周（cm）
            age (int): 推定樹齢
            photo_date (Optional[datetime]): 撮影日時

        Returns:
            Stem: 作成された幹の情報
        """
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
            photo_date=photo_date
        )
        self.db.add(stem)
        self.db.commit()
        self.db.refresh(stem)
        return stem

    def delete_stem(self, stem_id: int) -> bool:
        """
        幹の情報を削除する

        Args:
            stem_id (int): 幹のID

        Returns:
            bool: 削除に成功したかどうか
        """
        try:
            stem = self.get_stem_by_id(stem_id)
            if not stem:
                logger.warning(f"削除対象の幹が見つかりません: stem_id={stem_id}")
                return False

            self.db.delete(stem)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"幹の削除中にエラー発生: {str(e)}")
            self.db.rollback()
            return False

    def delete_stem_for_tree(self, tree_id: int) -> bool:
        """
        特定の木に紐づく幹の情報を削除する

        Args:
            tree_id (int): 木のID

        Returns:
            bool: 削除に成功したかどうか
        """
        try:
            stem = self.get_stem_by_tree_id(tree_id)
            if not stem:
                # 対象の幹がない場合は成功扱い
                return True

            self.db.delete(stem)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(
                f"木に紐づく幹の削除中にエラー発生: tree_id={tree_id}, error={str(e)}")
            self.db.rollback()
            return False
