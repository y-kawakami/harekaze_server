import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
# from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import Admin, User

# .envファイルを読み込む
load_dotenv()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # デフォルト値はローカル開発用
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30日間

# loguruの設定
# logger.add(
#     "logs/app.log",  # ログファイルのパス
#     rotation="500 MB",  # ログローテーション
#     retention="10 days",  # ログの保持期間
#     level="INFO",  # ログレベル
#     # ログフォーマット
#     format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
#     serialize=True  # JSON形式で出力
# )


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

    def verify_password(self, plain_password, hashed_password):
        """
        パスワードの検証を行う

        Args:
            plain_password: 平文のパスワード
            hashed_password: ハッシュ化されたパスワード
        Returns:
            bool: パスワードが一致すればTrue
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        """
        パスワードをハッシュ化する

        Args:
            password: 平文のパスワード
        Returns:
            str: ハッシュ化されたパスワード
        """
        return self.pwd_context.hash(password)

    def authenticate_admin(self, username: str, password: str) -> Admin | None:
        """
        管理者認証を行う

        Args:
            username: 管理者のユーザー名
            password: 管理者のパスワード
        Returns:
            Admin | None: 認証成功時はAdminオブジェクト、失敗時はNone
        """
        admin = self.db.query(Admin).filter(Admin.username == username).first()
        if not admin:
            return None
        if not self.verify_password(password, admin.hashed_password):
            return None

        # 最終ログイン日時を更新
        admin.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(admin)

        return admin

    def create_admin_token(self, admin_id: int) -> str:
        """
        管理者用のJWTトークンを作成する

        Args:
            admin_id: 管理者ID
        Returns:
            str: JWTトークン
        """
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": str(admin_id),
            "exp": expire,
            "is_admin": True
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_admin_token(self, token: str | None) -> int | None:
        """
        管理者用のJWTトークンを検証する

        Args:
            token: JWTトークン
        Returns:
            int | None: 管理者IDまたはNone
        """
        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            admin_id = payload.get("sub")
            is_admin = payload.get("is_admin", False)

            if not admin_id or not is_admin:
                return None

            return int(admin_id)
        except (JWTError, ValueError):
            return None

    def get_admin_by_id(self, admin_id: int) -> Admin | None:
        """
        IDから管理者を取得する

        Args:
            admin_id: 管理者ID
        Returns:
            Admin | None: 管理者オブジェクトまたはNone
        """
        return self.db.query(Admin).filter(Admin.id == admin_id).first()
