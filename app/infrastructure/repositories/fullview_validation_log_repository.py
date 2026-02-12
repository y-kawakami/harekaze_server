from sqlalchemy.orm import Session

from app.domain.models.fullview_validation_log import (
    FullviewValidationLog,
)


class FullviewValidationLogRepository:
    """全景バリデーション NG 判定ログのリポジトリ"""

    db: Session

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        image_obj_key: str,
        is_valid: bool,
        reason: str,
        confidence: float,
        model_id: str,
    ) -> FullviewValidationLog:
        """判定ログを作成する

        Args:
            image_obj_key: S3 画像キー
            is_valid: 判定結果（True=OK, False=NG）
            reason: 判定理由
            confidence: 信頼度（0.0〜1.0）
            model_id: 使用した Bedrock モデル ID

        Returns:
            作成された判定ログ
        """
        log = FullviewValidationLog(
            image_obj_key=image_obj_key,
            is_valid=is_valid,
            reason=reason,
            confidence=confidence,
            model_id=model_id,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log


def get_fullview_validation_log_repository(
    db: Session,
) -> FullviewValidationLogRepository:
    """FullviewValidationLogRepository のインスタンスを取得する"""
    return FullviewValidationLogRepository(db)
