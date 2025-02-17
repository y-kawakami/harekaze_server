import os
from typing import Generator
from unittest.mock import Mock

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService
from app.infrastructure.database.database import Base, get_db
from app.infrastructure.geocoding.geocoding_service import GeocodingService
from main import app


def get_test_db_url() -> str:
    """テスト用DBのURLを取得"""
    load_dotenv()
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "root")
    host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("TEST_DB_NAME", "harekaze_test_db")
    return f"mysql://{user}:{password}@{host}/{db_name}"


# テスト用DBエンジンの作成
test_engine = create_engine(get_test_db_url())
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    テストセッション開始時にテーブルを作成
    テストセッション終了時にテーブルを削除
    """
    # 既存のテーブルをクリーンアップ
    Base.metadata.drop_all(bind=test_engine)
    # テーブルを作成
    Base.metadata.create_all(bind=test_engine)
    yield
    # テーブルを削除
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    各テストケースで使用するDBセッション
    テストケース終了時にロールバック
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # 全テーブルの内容をクリア
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session):
    """
    テスト用のFastAPIクライアント
    DBセッションを依存性注入
    """
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_current_user():
    """モック化されたユーザー"""
    return User(
        id=1,
        email="test@example.com",
        hashed_password="dummy_hashed_password"
    )


@pytest.fixture
def mock_image_service():
    """モック化されたImageService"""
    return Mock(spec=ImageService)


@pytest.fixture
def mock_municipality_service():
    """モック化されたMunicipalityService"""
    return Mock(spec=MunicipalityService)


@pytest.fixture
def mock_geocoding_service(mock_municipality_service):
    """モック化されたGeocodingService"""
    service = Mock(spec=GeocodingService)
    service.municipality_service = mock_municipality_service
    return service


@pytest.fixture
def test_image_data():
    """テスト用の画像データ"""
    return b"dummy_image_data"
