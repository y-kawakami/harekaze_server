import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.domain.models.models import User

# .envファイルを読み込む
load_dotenv()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # デフォルト値はローカル開発用
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1週間


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_access_token(self, user_id: str) -> str:
        """JWTトークンを生成する"""
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": user_id,
            "exp": expire
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        """トークンを検証し、ユーザIDを返す"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: Optional[str] = payload.get("sub")
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
