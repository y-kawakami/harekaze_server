"""アノテーター認証サービス

アノテーターの認証・JWT トークン発行・検証を行うサービス。
既存 AuthService のパターンを踏襲。
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.domain.models.annotation import Annotator

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30日間


class AnnotationAuthService:
    """アノテーター認証サービス"""

    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """パスワードを検証する"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def authenticate_annotator(
        self, username: str, password: str
    ) -> Annotator | None:
        """アノテーター認証を行う

        Args:
            username: アノテーターのユーザー名
            password: アノテーターのパスワード

        Returns:
            Annotator | None: 認証成功時は Annotator オブジェクト、失敗時は None
        """
        annotator = (
            self.db.query(Annotator)
            .filter(Annotator.username == username)
            .first()
        )
        if not annotator:
            return None

        if not self.verify_password(password, annotator.hashed_password):
            return None

        # 最終ログイン日時を更新
        annotator.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(annotator)

        return annotator

    def create_annotator_token(self, annotator_id: int) -> str:
        """アノテーター用の JWT トークンを作成する

        Args:
            annotator_id: アノテーター ID

        Returns:
            str: JWT トークン
        """
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "sub": str(annotator_id),
            "exp": expire,
            "is_annotator": True,
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_annotator_token(self, token: str | None) -> int | None:
        """アノテーター用の JWT トークンを検証する

        Args:
            token: JWT トークン

        Returns:
            int | None: アノテーター ID または None
        """
        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            annotator_id = payload.get("sub")
            is_annotator = payload.get("is_annotator", False)

            if not annotator_id or not is_annotator:
                return None

            return int(annotator_id)
        except (JWTError, ValueError):
            return None

    def get_annotator_by_id(self, annotator_id: int) -> Annotator | None:
        """ID からアノテーターを取得する

        Args:
            annotator_id: アノテーター ID

        Returns:
            Annotator | None: アノテーターオブジェクトまたは None
        """
        return (
            self.db.query(Annotator)
            .filter(Annotator.id == annotator_id)
            .first()
        )
