"""アノテーションAPI統合テスト

ログインフロー、一覧取得、アノテーション保存、CSVエクスポートをテストする。
Requirements: 1.1, 1.2, 1.3, 2.1, 3.1, 3.2, 3.3, 3.4, 3.5, 4.4, 9.1
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.domain.models.annotation import Annotator, VitalityAnnotation
from app.domain.models.models import EntireTree, Tree


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def sample_annotator(db: Session) -> Annotator:
    """テスト用アノテーターをDBに作成"""
    annotator = Annotator(
        username="test_annotator",
        hashed_password=pwd_context.hash("test_password123"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(annotator)
    db.commit()
    db.refresh(annotator)
    return annotator


@pytest.fixture
def sample_tree(db: Session) -> Tree:
    """テスト用の桜の木をDBに作成"""
    tree = Tree(
        prefecture_code="13",
        location="東京都渋谷区",
        latitude=35.6580,
        longitude=139.7016,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(tree)
    db.commit()
    db.refresh(tree)
    return tree


@pytest.fixture
def sample_entire_tree(db: Session, sample_tree: Tree) -> EntireTree:
    """テスト用の桜全体画像をDBに作成"""
    entire_tree = EntireTree(
        tree_id=sample_tree.id,
        image_obj_key="2024/04/01/test_image.jpg",
        thumb_obj_key="2024/04/01/test_thumb.jpg",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(entire_tree)
    db.commit()
    db.refresh(entire_tree)
    return entire_tree


@pytest.fixture
def auth_headers(client, sample_annotator: Annotator) -> dict:
    """認証済みヘッダーを取得"""
    response = client.post(
        "/annotation_api/login",
        data={
            "username": "test_annotator",
            "password": "test_password123",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestAnnotationAuthAPI:
    """認証APIのテスト"""

    def test_login_success(self, client, sample_annotator):
        """正常ログイン"""
        response = client.post(
            "/annotation_api/login",
            data={
                "username": "test_annotator",
                "password": "test_password123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, sample_annotator):
        """パスワード間違いで401"""
        response = client.post(
            "/annotation_api/login",
            data={
                "username": "test_annotator",
                "password": "wrong_password",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """存在しないユーザーで401"""
        response = client.post(
            "/annotation_api/login",
            data={
                "username": "nonexistent_user",
                "password": "any_password",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_authenticated(self, client, auth_headers):
        """認証済みでユーザー情報取得"""
        response = client.get(
            "/annotation_api/me",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "test_annotator"

    def test_get_me_unauthenticated(self, client):
        """未認証で401"""
        response = client.get("/annotation_api/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_invalid_token(self, client):
        """無効なトークンで401"""
        response = client.get(
            "/annotation_api/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestAnnotationListAPI:
    """一覧取得APIのテスト"""

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_get_trees_authenticated(
        self,
        mock_municipality_service,
        mock_image_service,
        client,
        auth_headers,
        db,
        sample_entire_tree,
    ):
        """認証済みで一覧取得"""
        # モック設定
        img_service = MagicMock()
        img_service.get_image_url.return_value = \
            "https://example.com/thumb.jpg"
        mock_image_service.return_value = img_service

        muni_service = MagicMock()
        prefecture_mock = MagicMock()
        prefecture_mock.name = "東京都"
        muni_service.get_prefecture_by_code.return_value = prefecture_mock
        mock_municipality_service.return_value = muni_service

        response = client.get(
            "/annotation_api/trees",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "stats" in data
        assert "total" in data

    def test_get_trees_unauthenticated(self, client):
        """未認証で401"""
        response = client.get("/annotation_api/trees")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_get_trees_with_filters(
        self,
        mock_municipality_service,
        mock_image_service,
        client,
        auth_headers,
        db,
        sample_entire_tree,
    ):
        """フィルター付き一覧取得"""
        img_service = MagicMock()
        img_service.get_image_url.return_value = \
            "https://example.com/thumb.jpg"
        mock_image_service.return_value = img_service

        muni_service = MagicMock()
        prefecture_mock = MagicMock()
        prefecture_mock.name = "東京都"
        muni_service.get_prefecture_by_code.return_value = prefecture_mock
        mock_municipality_service.return_value = muni_service

        response = client.get(
            "/annotation_api/trees",
            params={
                "status": "unannotated",
                "prefecture_code": "13",
                "page": 1,
                "per_page": 10,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestAnnotationSaveAPI:
    """アノテーション保存APIのテスト"""

    def test_save_annotation_authenticated(
        self,
        client,
        auth_headers,
        db,
        sample_entire_tree,
    ):
        """認証済みでアノテーション保存"""
        response = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": 3},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["entire_tree_id"] == sample_entire_tree.id
        assert data["vitality_value"] == 3

    def test_save_annotation_update(
        self,
        client,
        auth_headers,
        db,
        sample_entire_tree,
        sample_annotator,
    ):
        """既存アノテーションの更新"""
        # 最初のアノテーション
        response1 = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": 2},
            headers=auth_headers,
        )
        assert response1.status_code == status.HTTP_200_OK

        # 更新
        response2 = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": 5},
            headers=auth_headers,
        )
        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["vitality_value"] == 5

    def test_save_annotation_unauthenticated(self, client, sample_entire_tree):
        """未認証で401"""
        response = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": 3},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_annotation_invalid_value(
        self,
        client,
        auth_headers,
        sample_entire_tree,
    ):
        """無効な元気度値で400"""
        response = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_save_annotation_minus1(
        self,
        client,
        auth_headers,
        db,
        sample_entire_tree,
    ):
        """診断不可（-1）で保存"""
        response = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": -1},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["vitality_value"] == -1

    def test_save_annotation_nonexistent_tree(
        self,
        client,
        auth_headers,
    ):
        """存在しないentire_tree_idで400"""
        response = client.post(
            "/annotation_api/trees/99999/annotation",
            json={"vitality_value": 3},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestPrefecturesAPI:
    """都道府県一覧APIのテスト"""

    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_get_prefectures_authenticated(
        self,
        mock_municipality_service,
        client,
        auth_headers,
    ):
        """認証済みで都道府県一覧取得"""
        mock_service = MagicMock()
        prefecture_mock = MagicMock()
        prefecture_mock.code = "13"
        prefecture_mock.name = "東京都"
        mock_service.prefectures = [prefecture_mock]
        mock_municipality_service.return_value = mock_service

        response = client.get(
            "/annotation_api/prefectures",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "prefectures" in data

    def test_get_prefectures_unauthenticated(self, client):
        """未認証で401"""
        response = client.get("/annotation_api/prefectures")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestCSVExportAPI:
    """CSVエクスポートAPIのテスト"""

    def test_export_csv_authenticated(
        self,
        client,
        auth_headers,
        db,
        sample_entire_tree,
        sample_annotator,
    ):
        """認証済みでCSVエクスポート"""
        # アノテーションを作成
        annotation = VitalityAnnotation(
            entire_tree_id=sample_entire_tree.id,
            vitality_value=3,
            annotator_id=sample_annotator.id,
            annotated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotation)
        db.commit()

        response = client.get(
            "/annotation_api/export/csv",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

        # CSVコンテンツを検証
        content = response.text
        assert "s3_path" in content
        assert "image_filename" in content
        assert "vitality_score" in content

    def test_export_csv_unauthenticated(self, client):
        """未認証で401"""
        response = client.get("/annotation_api/export/csv")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_export_csv_empty(
        self,
        client,
        auth_headers,
        db,
    ):
        """アノテーションがない場合はヘッダーのみ"""
        response = client.get(
            "/annotation_api/export/csv",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        content = response.text
        lines = [line for line in content.split("\n") if line.strip()]
        # BOMとヘッダーのみ
        assert len(lines) == 1

    def test_export_csv_exclude_undiagnosable(
        self,
        client,
        auth_headers,
        db,
        sample_entire_tree,
        sample_annotator,
    ):
        """診断不可を除外してエクスポート"""
        annotation = VitalityAnnotation(
            entire_tree_id=sample_entire_tree.id,
            vitality_value=-1,
            annotator_id=sample_annotator.id,
            annotated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotation)
        db.commit()

        response = client.get(
            "/annotation_api/export/csv",
            params={"include_undiagnosable": False},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        content = response.text
        # -1は除外される
        assert ",-1" not in content


@pytest.mark.integration
class TestAnnotationDetailAPI:
    """詳細取得APIのテスト"""

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_flowering_date_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_get_tree_detail_authenticated(
        self,
        mock_municipality_service,
        mock_flowering_date_service,
        mock_image_service,
        client,
        auth_headers,
        db,
        sample_entire_tree,
    ):
        """認証済みで詳細取得"""
        # モック設定
        img_service = MagicMock()
        img_service.generate_presigned_url.return_value = \
            "https://example.com/image.jpg"
        mock_image_service.return_value = img_service

        flowering_service = MagicMock()
        flowering_service.find_nearest_spot.return_value = None
        mock_flowering_date_service.return_value = flowering_service

        muni_service = MagicMock()
        prefecture_mock = MagicMock()
        prefecture_mock.name = "東京都"
        muni_service.get_prefecture_by_code.return_value = prefecture_mock
        mock_municipality_service.return_value = muni_service

        response = client.get(
            f"/annotation_api/trees/{sample_entire_tree.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["entire_tree_id"] == sample_entire_tree.id

    def test_get_tree_detail_unauthenticated(self, client, sample_entire_tree):
        """未認証で401"""
        response = client.get(f"/annotation_api/trees/{sample_entire_tree.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_flowering_date_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_get_tree_detail_nonexistent(
        self,
        mock_municipality_service,
        mock_flowering_date_service,
        mock_image_service,
        client,
        auth_headers,
    ):
        """存在しないIDで404"""
        mock_image_service.return_value = MagicMock()
        mock_flowering_date_service.return_value = MagicMock()
        mock_municipality_service.return_value = MagicMock()

        response = client.get(
            "/annotation_api/trees/99999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
