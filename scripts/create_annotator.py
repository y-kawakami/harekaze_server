#!/usr/bin/env python3
"""アノテーターアカウント作成スクリプト

使用例:
    # アノテーターアカウントを作成
    python scripts/create_annotator.py username password

    # パスワードハッシュのみを生成（DBには登録しない）
    python scripts/create_annotator.py username password --hash-only
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from passlib.context import CryptContext

# プロジェクトのルートディレクトリをPYTHONPATHに追加（importの前に実行する必要がある）
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


# .envファイルを読み込む
load_dotenv()

# パスワードハッシュ用のコンテキスト
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# DB関連の初期化（遅延実行用）
_SessionLocal = None


def _get_session():
    """DBセッションを遅延初期化して取得する"""
    global _SessionLocal
    if _SessionLocal is None:
        from app.infrastructure.database.database import engine, sessionmaker
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()


def get_password_hash(password: str) -> str:
    """パスワードのハッシュを生成する"""
    return pwd_context.hash(password)


def create_annotator(username: str, password: str) -> bool:
    """
    アノテーターアカウントを作成する

    Args:
        username: アノテーターのユーザー名
        password: アノテーターのパスワード

    Returns:
        bool: 作成に成功したかどうか
    """
    from app.domain.models.annotation import Annotator
    db_session = _get_session()

    try:
        # 既存の同名アノテーターをチェック
        existing_annotator = db_session.query(Annotator).filter(
            Annotator.username == username).first()
        if existing_annotator:
            print(f"エラー: ユーザー名 '{username}' は既に存在します。")
            return False

        # パスワードのハッシュ化
        hashed_password = get_password_hash(password)

        # アノテーターアカウント作成
        annotator = Annotator(
            username=username,
            hashed_password=hashed_password
        )
        db_session.add(annotator)
        db_session.commit()
        db_session.refresh(annotator)

        print("アノテーターアカウントが作成されました。")
        print(f"  ID: {annotator.id}")
        print(f"  ユーザー名: {annotator.username}")
        return True

    except Exception as e:
        print(f"エラー: {e}")
        db_session.rollback()
        return False

    finally:
        db_session.close()


def list_annotators() -> None:
    """登録済みのアノテーター一覧を表示する"""
    from app.domain.models.annotation import Annotator
    db_session = _get_session()

    try:
        annotators = db_session.query(Annotator).all()
        if not annotators:
            print("アノテーターが登録されていません。")
            return

        print("登録済みアノテーター一覧:")
        print("-" * 50)
        for annotator in annotators:
            last_login = annotator.last_login.strftime(
                "%Y-%m-%d %H:%M") if annotator.last_login else "未ログイン"
            print(f"  ID: {annotator.id}, ユーザー名: {annotator.username}, "
                  f"最終ログイン: {last_login}")
    finally:
        db_session.close()


def delete_annotator(username: str) -> bool:
    """
    アノテーターアカウントを削除する

    Args:
        username: 削除するアノテーターのユーザー名

    Returns:
        bool: 削除に成功したかどうか
    """
    from app.domain.models.annotation import Annotator
    db_session = _get_session()

    try:
        annotator = db_session.query(Annotator).filter(
            Annotator.username == username).first()
        if not annotator:
            print(f"エラー: ユーザー名 '{username}' は存在しません。")
            return False

        db_session.delete(annotator)
        db_session.commit()
        print(f"アノテーター '{username}' を削除しました。")
        return True

    except Exception as e:
        print(f"エラー: {e}")
        db_session.rollback()
        return False

    finally:
        db_session.close()


def main():
    parser = argparse.ArgumentParser(
        description="アノテーターアカウントを管理するツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # アノテーターを作成
  python scripts/create_annotator.py create username password

  # パスワードハッシュのみを生成
  python scripts/create_annotator.py create username password --hash-only

  # アノテーター一覧を表示
  python scripts/create_annotator.py list

  # アノテーターを削除
  python scripts/create_annotator.py delete username
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # create コマンド
    create_parser = subparsers.add_parser("create", help="アノテーターを作成")
    create_parser.add_argument("username", help="アノテーターのユーザー名")
    create_parser.add_argument("password", help="アノテーターのパスワード（8文字以上推奨）")
    create_parser.add_argument("--hash-only", action="store_true",
                               help="DBに登録せず、パスワードハッシュのみを出力する")

    # list コマンド
    subparsers.add_parser("list", help="アノテーター一覧を表示")

    # delete コマンド
    delete_parser = subparsers.add_parser("delete", help="アノテーターを削除")
    delete_parser.add_argument("username", help="削除するアノテーターのユーザー名")

    args = parser.parse_args()

    # コマンドが指定されていない場合（後方互換性のため、create として扱う）
    if args.command is None:
        # 引数が2つあれば create として扱う
        if len(sys.argv) >= 3 and not sys.argv[1].startswith("-"):
            args.command = "create"
            args.username = sys.argv[1]
            args.password = sys.argv[2]
            args.hash_only = "--hash-only" in sys.argv
        else:
            parser.print_help()
            sys.exit(1)

    if args.command == "create":
        if len(args.password) < 8:
            print("警告: パスワードは8文字以上にすることをお勧めします。")
            confirm = input("続行しますか？ (y/n): ")
            if confirm.lower() != 'y':
                sys.exit(0)

        if args.hash_only:
            hashed_password = get_password_hash(args.password)
            print(f"パスワードハッシュ: {hashed_password}")
        else:
            success = create_annotator(args.username, args.password)
            if not success:
                sys.exit(1)

    elif args.command == "list":
        list_annotators()

    elif args.command == "delete":
        confirm = input(f"アノテーター '{args.username}' を削除しますか？ (y/n): ")
        if confirm.lower() == 'y':
            success = delete_annotator(args.username)
            if not success:
                sys.exit(1)
        else:
            print("削除をキャンセルしました。")


if __name__ == "__main__":
    main()
