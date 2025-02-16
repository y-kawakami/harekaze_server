from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService
from app.infrastructure.geocoding.geocoding_service import GeocodingService
from main import app


@pytest.fixture
def client():
    """FastAPIのテストクライアント"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """モック化されたデータベースセッション"""
    return Mock(spec=Session)


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
