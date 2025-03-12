#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.domain.models.models import Admin
from app.domain.services.auth_service import AuthService
from app.infrastructure.database.database import engine, sessionmaker

# プロジェクトのルートディレクトリをPYTHONPATHに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


# .envファイルを読み込む
load_dotenv()

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_password_hash(password: str) -> str:
    """
    パスワードのハッシュを生成する関数

    Args:
        password: 管理者のパスワード

    Returns:
        str: ハッシュ化されたパスワード
    """
    # DBセッションを取得
    db_session = SessionLocal()

    try:
        # パスワードのハッシュ化
        auth_service = AuthService(db_session)
        hashed_password = auth_service.get_password_hash(password)
        return hashed_password
    finally:
        db_session.close()


def create_admin(username: str, password: str):
    """
    管理者アカウントを作成する関数

    Args:
        username: 管理者のユーザー名
        password: 管理者のパスワード

    Returns:
        bool: 作成に成功したかどうか
    """
    # DBセッションを取得
    db_session = SessionLocal()

    try:
        # 既存の同名管理者をチェック
        existing_admin = db_session.query(Admin).filter(
            Admin.username == username).first()
        if existing_admin:
            print(f"エラー: ユーザー名 '{username}' は既に存在します。")
            return False

        # パスワードのハッシュ化
        auth_service = AuthService(db_session)
        hashed_password = auth_service.get_password_hash(password)

        # 管理者アカウント作成
        admin = Admin(
            username=username,
            hashed_password=hashed_password
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

        print(f"管理者アカウントが作成されました。ID: {admin.id}, ユーザー名: {admin.username}")
        return True

    except Exception as e:
        print(f"エラー: {e}")
        db_session.rollback()
        return False

    finally:
        db_session.close()


def main():
    parser = argparse.ArgumentParser(description="管理者アカウントを作成するツール")
    parser.add_argument("username", help="管理者のユーザー名")
    parser.add_argument("password", help="管理者のパスワード（8文字以上推奨）")
    parser.add_argument("--hash-only", action="store_true",
                        help="DBに登録せず、パスワードハッシュのみを出力する")

    args = parser.parse_args()

    if len(args.password) < 8:
        print("警告: パスワードは8文字以上にすることをお勧めします。")
        confirm = input("続行しますか？ (y/n): ")
        if confirm.lower() != 'y':
            sys.exit(0)

    if args.hash_only:
        # パスワードハッシュのみを生成して表示
        hashed_password = get_password_hash(args.password)
        print(f"パスワードハッシュ: {hashed_password}")
    else:
        # 通常の管理者アカウント作成処理
        success = create_admin(args.username, args.password)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
