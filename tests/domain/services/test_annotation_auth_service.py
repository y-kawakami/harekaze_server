"""AnnotationAuthService のユニットテスト

DB 接続を必要としない純粋なユニットテスト。
モジュールトップレベルでの SQLAlchemy モデルインポートを回避することで、
conftest.py の DB セットアップに依存しない。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from passlib.context import CryptContext

# Note: AnnotationAuthService と Annotator は fixture 内で遅延インポートする


@pytest.fixture
def pwd_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def service(mock_db):
    # 遅延インポートでDB接続を回避
    from app.domain.services.annotation_auth_service import (
        AnnotationAuthService,
    )

    return AnnotationAuthService(mock_db)


@pytest.fixture
def sample_annotator(pwd_context):
    """テスト用アノテーターを作成"""
    # 遅延インポートでDB接続を回避
    from app.domain.models.annotation import Annotator

    return Annotator(
        id=1,
        username="test_annotator",
        hashed_password=pwd_context.hash("correct_password"),
        last_login=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.unit
class TestAnnotationAuthServiceAuthenticate:
    """認証機能のテスト"""

    def test_authenticate_annotator_success(
        self, service, mock_db, sample_annotator
    ):
        """正しいユーザー名とパスワードで認証成功"""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_annotator
        )

        result = service.authenticate_annotator(
            "test_annotator", "correct_password"
        )

        assert result is not None
        assert result.id == 1
        assert result.username == "test_annotator"

    def test_authenticate_annotator_wrong_password(
        self, service, mock_db, sample_annotator
    ):
        """パスワードが間違っている場合は認証失敗"""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_annotator
        )

        result = service.authenticate_annotator(
            "test_annotator", "wrong_password"
        )

        assert result is None

    def test_authenticate_annotator_user_not_found(self, service, mock_db):
        """存在しないユーザーの場合は認証失敗"""
        query = mock_db.query.return_value.filter.return_value
        query.first.return_value = None

        result = service.authenticate_annotator(
            "nonexistent_user", "any_password"
        )

        assert result is None

    def test_authenticate_annotator_updates_last_login(
        self, service, mock_db, sample_annotator
    ):
        """認証成功時に最終ログイン日時が更新される"""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_annotator
        )
        original_last_login = sample_annotator.last_login

        result = service.authenticate_annotator(
            "test_annotator", "correct_password"
        )

        assert result is not None
        assert result.last_login is not None
        assert result.last_login != original_last_login
        mock_db.commit.assert_called_once()


@pytest.mark.unit
class TestAnnotationAuthServiceToken:
    """トークン機能のテスト"""

    def test_create_annotator_token(self, service):
        """アノテーター用JWTトークンが生成される"""
        token = service.create_annotator_token(123)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_annotator_token_valid(self, service):
        """有効なトークンからアノテーターIDを取得できる"""
        token = service.create_annotator_token(456)

        annotator_id = service.verify_annotator_token(token)

        assert annotator_id == 456

    def test_verify_annotator_token_invalid(self, service):
        """無効なトークンはNoneを返す"""
        result = service.verify_annotator_token("invalid.token.here")

        assert result is None

    def test_verify_annotator_token_none(self, service):
        """Noneトークンは None を返す"""
        result = service.verify_annotator_token(None)

        assert result is None

    def test_verify_annotator_token_empty_string(self, service):
        """空文字トークンは None を返す"""
        result = service.verify_annotator_token("")

        assert result is None

    @patch("app.domain.services.annotation_auth_service.jwt.decode")
    def test_verify_annotator_token_expired(self, mock_decode, service):
        """期限切れトークンは None を返す"""
        from jose import JWTError

        mock_decode.side_effect = JWTError("Token has expired")

        result = service.verify_annotator_token("expired.token.here")

        assert result is None

    def test_verify_annotator_token_wrong_type(self, service):
        """is_annotator フラグがないトークンは無効"""
        # AdminサービスのトークンはAnnotatorでは使えない
        from jose import jwt
        from app.domain.services.annotation_auth_service import (
            SECRET_KEY,
            ALGORITHM,
        )

        # is_annotatorフラグなしのトークン
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "123", "exp": expires}, SECRET_KEY, algorithm=ALGORITHM
        )

        result = service.verify_annotator_token(token)

        assert result is None


@pytest.mark.unit
class TestAnnotationAuthServiceGetAnnotator:
    """アノテーター取得機能のテスト"""

    def test_get_annotator_by_id_found(
        self, service, mock_db, sample_annotator
    ):
        """IDでアノテーターを取得できる"""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_annotator
        )

        result = service.get_annotator_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.username == "test_annotator"

    def test_get_annotator_by_id_not_found(self, service, mock_db):
        """存在しないIDの場合はNoneを返す"""
        query = mock_db.query.return_value.filter.return_value
        query.first.return_value = None

        result = service.get_annotator_by_id(999)

        assert result is None
