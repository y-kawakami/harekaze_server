import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import User

# .envファイルを読み込む
load_dotenv()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # デフォルト値はローカル開発用
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30日間

# loguruの設定
logger.add(
    "logs/app.log",  # ログファイルのパス
    rotation="500 MB",  # ログローテーション
    retention="10 days",  # ログの保持期間
    level="INFO",  # ログレベル
    # ログフォーマット
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    serialize=True  # JSON形式で出力
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, uid: str) -> str:
        """
        新しいJWTセッショントークンを作成して返す。
        UUIDを使用することで、連番による推測を防ぐ。
        暗号化は行わず、署名のみでトークンの改ざんを防ぐ。

        Args:
            uid: セッションに紐付けるユーザーのUID
        Returns:
            str: JWTトークン（ヘッダー.ペイロード.署名）
        """
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": uid,  # UUIDをそのまま使用
            "exp": expire
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str | None) -> str | None:
        """
        JWTトークンを検証し、有効な場合はユーザーのUIDを返す。
        トークンの検証のみを行い、ユーザーの取得は呼び出し側で行う。

        Args:
            token: JWTトークン
        Returns:
            str | None: ユーザーのUID（UUID）またはNone
        """
        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_uid = payload.get("sub")
            if user_uid is None:
                return None
            return user_uid
        except JWTError:
            return None

    def get_or_create_user(self, uid: str, ip_addr: str) -> User:
        """
        IPアドレスからユーザを取得または作成する。
        新規作成時はUUIDが自動的に生成される。

        Args:
            ip_addr: ユーザーのIPアドレス
        Returns:
            User: 取得または作成されたユーザーオブジェクト
        """
        user = self.db.query(User).filter(User.uid == uid).first()
        if user:
            return user

        user = User(uid=uid, ip_addr=ip_addr)  # UIDは自動生成される
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
