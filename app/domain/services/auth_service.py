import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.domain.models.models import User

# .envファイルを読み込む
load_dotenv()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # デフォルト値はローカル開発用
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30日間


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: str) -> str:
        """
        新しいJWTセッショントークンを作成して返す。
        Args:
            user_id: セッションに紐付けるユーザーID
        """
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": user_id,
            "exp": expire
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str | None) -> str | None:
        """
        JWTトークンを検証し、有効な場合はユーザーIDを返す。
        無効な場合はNoneを返す。
        """
        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None

    def get_or_create_user(self, ip_addr: str) -> User:
        """IPアドレスからユーザを取得または作成する"""
        user = self.db.query(User).filter(User.ip_addr == ip_addr).first()
        if user:
            return user

        user = User(ip_addr=ip_addr)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
