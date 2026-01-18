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
        role="annotator",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(annotator)
    db.commit()
    db.refresh(annotator)
    return annotator


@pytest.fixture
def admin_annotator(db: Session) -> Annotator:
    """テスト用adminアノテーターをDBに作成"""
    annotator = Annotator(
        username="admin_annotator",
        hashed_password=pwd_context.hash("admin_password123"),
        role="admin",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(annotator)
    db.commit()
    db.refresh(annotator)
    return annotator


@pytest.fixture
def admin_auth_headers(client, admin_annotator: Annotator) -> dict:
    """admin認証済みヘッダーを取得"""
    response = client.post(
        "/annotation_api/login",
        data={
            "username": "admin_annotator",
            "password": "admin_password123",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_user(db: Session):
    """テスト用ユーザーをDBに作成"""
    from app.domain.models.models import User
    user = User(
        ip_addr="127.0.0.1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_tree(db: Session, sample_user) -> Tree:
    """テスト用の桜の木をDBに作成"""
    tree = Tree(
        user_id=sample_user.id,
        prefecture_code="13",
        location="東京都渋谷区",
        latitude=35.6580,
        longitude=139.7016,
        position="POINT(139.7016 35.6580)",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(tree)
    db.commit()
    db.refresh(tree)
    return tree


@pytest.fixture
def sample_entire_tree(db: Session, sample_tree: Tree, sample_user) -> EntireTree:
    """テスト用の桜全体画像をDBに作成"""
    entire_tree = EntireTree(
        tree_id=sample_tree.id,
        user_id=sample_user.id,
        latitude=35.6580,
        longitude=139.7016,
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
        assert data["role"] == "annotator"

    def test_get_me_returns_admin_role(self, client, admin_auth_headers):
        """adminロールの場合、roleがadminで返される"""
        response = client.get(
            "/annotation_api/me",
            headers=admin_auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin_annotator"
        assert data["role"] == "admin"

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
        """無効な元気度値で422（Pydanticバリデーションエラー）"""
        response = client.post(
            f"/annotation_api/trees/{sample_entire_tree.id}/annotation",
            json={"vitality_value": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

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
class TestRequireAdminDependency:
    """require_admin 依存関数のテスト"""

    def test_require_admin_allows_admin_role(
        self,
        client,
        admin_auth_headers,
        db,
        sample_entire_tree,
    ):
        """adminロールでis_ready変更APIにアクセスできる"""
        # is_ready更新エンドポイント（admin専用）にアクセス
        response = client.patch(
            f"/annotation_api/trees/{sample_entire_tree.id}/is_ready",
            json={"is_ready": True},
            headers=admin_auth_headers,
        )

        # adminなのでアクセス許可される（200または404）
        assert response.status_code in [
            status.HTTP_200_OK, status.HTTP_404_NOT_FOUND
        ]

    def test_require_admin_denies_annotator_role(
        self,
        client,
        auth_headers,
        db,
        sample_entire_tree,
    ):
        """annotatorロールでis_ready変更APIへのアクセスは403"""
        response = client.patch(
            f"/annotation_api/trees/{sample_entire_tree.id}/is_ready",
            json={"is_ready": True},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_require_admin_denies_unauthenticated(
        self,
        client,
        sample_entire_tree,
    ):
        """未認証でis_ready変更APIへのアクセスは401"""
        response = client.patch(
            f"/annotation_api/trees/{sample_entire_tree.id}/is_ready",
            json={"is_ready": True},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


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
        admin_auth_headers,
        db,
        sample_entire_tree,
    ):
        """認証済みで詳細取得（adminロールで全画像にアクセス可能）"""
        # モック設定
        img_service = MagicMock()
        img_service.get_image_url.return_value = \
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
            headers=admin_auth_headers,
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


@pytest.mark.integration
class TestIsReadyIntegrationFlow:
    """is_ready 機能の統合テスト

    認証 → 一覧取得 → is_ready 更新のフローをテストする。
    Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.4
    """

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_auth_list_update_is_ready_flow(
        self,
        mock_municipality_service,
        mock_image_service,
        client,
        db,
        sample_entire_tree,
    ):
        """認証 → 一覧取得 → is_ready更新の完全フロー（admin）"""
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

        # Step 1: adminアノテーターを作成
        admin = Annotator(
            username="flow_test_admin",
            hashed_password=pwd_context.hash("admin_pass"),
            role="admin",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

        # Step 2: 認証
        login_response = client.post(
            "/annotation_api/login",
            data={"username": "flow_test_admin", "password": "admin_pass"},
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: 一覧取得（初期状態: VitalityAnnotationが無い画像）
        list_response = client.get("/annotation_api/trees", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        data = list_response.json()
        # 統計情報が含まれていることを確認
        assert "stats" in data
        assert "total_count" in data["stats"]

        # Step 4: is_ready を True に更新
        update_response = client.patch(
            f"/annotation_api/trees/{sample_entire_tree.id}/is_ready",
            json={"is_ready": True},
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["is_ready"] is True

        # Step 5: 一覧取得で is_ready 状態が反映されていることを確認
        list_response2 = client.get("/annotation_api/trees", headers=headers)
        assert list_response2.status_code == status.HTTP_200_OK
        items = list_response2.json()["items"]
        target_item = next(
            (i for i in items if i["entire_tree_id"] == sample_entire_tree.id),
            None
        )
        assert target_item is not None
        assert target_item["is_ready"] is True

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_flowering_date_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_annotator_cannot_access_not_ready_detail(
        self,
        mock_municipality_service,
        mock_flowering_date_service,
        mock_image_service,
        client,
        db,
        sample_entire_tree,
    ):
        """annotatorロールが is_ready=FALSE の画像詳細にアクセスすると403"""
        # モック設定
        mock_image_service.return_value = MagicMock()
        mock_flowering_date_service.return_value = MagicMock()
        mock_municipality_service.return_value = MagicMock()

        # annotatorアノテーターを作成
        annotator = Annotator(
            username="access_test_annotator",
            hashed_password=pwd_context.hash("annotator_pass"),
            role="annotator",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotator)
        db.commit()

        # 認証
        login_response = client.post(
            "/annotation_api/login",
            data={
                "username": "access_test_annotator",
                "password": "annotator_pass"
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # is_ready=FALSE の画像詳細にアクセス → 403
        response = client.get(
            f"/annotation_api/trees/{sample_entire_tree.id}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_flowering_date_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_annotator_can_access_ready_detail(
        self,
        mock_municipality_service,
        mock_flowering_date_service,
        mock_image_service,
        client,
        db,
        sample_entire_tree,
    ):
        """annotatorロールが is_ready=TRUE の画像詳細にアクセスできる"""
        # モック設定
        img_service = MagicMock()
        img_service.get_image_url.return_value = \
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

        # まずadminを作成してis_readyを設定するため
        admin = Annotator(
            username="ready_test_admin",
            hashed_password=pwd_context.hash("admin_pass"),
            role="admin",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        # VitalityAnnotation を is_ready=TRUE で作成（有効なannotator_idを使用）
        annotation = VitalityAnnotation(
            entire_tree_id=sample_entire_tree.id,
            vitality_value=None,
            is_ready=True,
            annotator_id=admin.id,
            annotated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotation)
        db.commit()

        # annotatorを作成
        annotator = Annotator(
            username="ready_access_annotator",
            hashed_password=pwd_context.hash("annotator_pass"),
            role="annotator",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotator)
        db.commit()

        # 認証
        login_response = client.post(
            "/annotation_api/login",
            data={
                "username": "ready_access_annotator",
                "password": "annotator_pass"
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # is_ready=TRUE の画像詳細にアクセス → 200
        response = client.get(
            f"/annotation_api/trees/{sample_entire_tree.id}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_ready"] is True

    def test_batch_update_is_ready_multiple_records(
        self,
        client,
        db,
        sample_user,
        sample_tree,
    ):
        """バッチ更新で複数レコードを一括更新"""
        # 複数のEntireTreeを作成
        entire_trees = []
        for i in range(3):
            et = EntireTree(
                tree_id=sample_tree.id,
                user_id=sample_user.id,
                latitude=35.6580 + i * 0.001,
                longitude=139.7016 + i * 0.001,
                image_obj_key=f"2024/04/01/test_image_{i}.jpg",
                thumb_obj_key=f"2024/04/01/test_thumb_{i}.jpg",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(et)
            entire_trees.append(et)
        db.commit()
        for et in entire_trees:
            db.refresh(et)

        # adminアノテーターを作成
        admin = Annotator(
            username="batch_test_admin",
            hashed_password=pwd_context.hash("admin_pass"),
            role="admin",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

        # 認証
        login_response = client.post(
            "/annotation_api/login",
            data={"username": "batch_test_admin", "password": "admin_pass"},
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # バッチ更新
        entire_tree_ids = [et.id for et in entire_trees]
        response = client.patch(
            "/annotation_api/trees/is_ready/batch",
            json={"entire_tree_ids": entire_tree_ids, "is_ready": True},
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3
        assert set(data["updated_ids"]) == set(entire_tree_ids)

    def test_batch_update_is_ready_denied_for_annotator(
        self,
        client,
        db,
        sample_entire_tree,
    ):
        """annotatorロールでバッチ更新は403"""
        # annotatorを作成
        annotator = Annotator(
            username="batch_denied_annotator",
            hashed_password=pwd_context.hash("annotator_pass"),
            role="annotator",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotator)
        db.commit()

        # 認証
        login_response = client.post(
            "/annotation_api/login",
            data={
                "username": "batch_denied_annotator",
                "password": "annotator_pass"
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # バッチ更新を試行 → 403
        response = client.patch(
            "/annotation_api/trees/is_ready/batch",
            json={
                "entire_tree_ids": [sample_entire_tree.id],
                "is_ready": True
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_annotator_only_sees_ready_items_in_list(
        self,
        mock_municipality_service,
        mock_image_service,
        client,
        db,
        sample_user,
        sample_tree,
    ):
        """annotatorロールは一覧で is_ready=TRUE の画像のみ表示"""
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

        # is_ready=TRUE と FALSE の画像を作成
        et_ready = EntireTree(
            tree_id=sample_tree.id,
            user_id=sample_user.id,
            latitude=35.6580,
            longitude=139.7016,
            image_obj_key="2024/04/01/ready_image.jpg",
            thumb_obj_key="2024/04/01/ready_thumb.jpg",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        et_not_ready = EntireTree(
            tree_id=sample_tree.id,
            user_id=sample_user.id,
            latitude=35.6590,
            longitude=139.7026,
            image_obj_key="2024/04/01/not_ready_image.jpg",
            thumb_obj_key="2024/04/01/not_ready_thumb.jpg",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(et_ready)
        db.add(et_not_ready)
        db.commit()
        db.refresh(et_ready)
        db.refresh(et_not_ready)

        # adminを作成してis_readyを設定
        admin = Annotator(
            username="list_test_admin",
            hashed_password=pwd_context.hash("admin_pass"),
            role="admin",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

        admin_login = client.post(
            "/annotation_api/login",
            data={"username": "list_test_admin", "password": "admin_pass"},
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # et_ready を is_ready=TRUE に設定
        client.patch(
            f"/annotation_api/trees/{et_ready.id}/is_ready",
            json={"is_ready": True},
            headers=admin_headers,
        )

        # annotatorを作成
        annotator = Annotator(
            username="list_test_annotator",
            hashed_password=pwd_context.hash("annotator_pass"),
            role="annotator",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annotator)
        db.commit()

        annotator_login = client.post(
            "/annotation_api/login",
            data={
                "username": "list_test_annotator",
                "password": "annotator_pass"
            },
        )
        annotator_token = annotator_login.json()["access_token"]
        annotator_headers = {
            "Authorization": f"Bearer {annotator_token}"
        }

        # annotatorで一覧取得
        response = client.get(
            "/annotation_api/trees",
            headers=annotator_headers
        )
        assert response.status_code == status.HTTP_200_OK
        items = response.json()["items"]

        # is_ready=TRUEの画像のみ含まれる
        item_ids = [item["entire_tree_id"] for item in items]
        assert et_ready.id in item_ids
        assert et_not_ready.id not in item_ids

    @patch("app.interfaces.api.annotation.get_image_service")
    @patch("app.interfaces.api.annotation.get_municipality_service")
    def test_admin_can_filter_by_is_ready(
        self,
        mock_municipality_service,
        mock_image_service,
        client,
        db,
        sample_user,
        sample_tree,
    ):
        """adminロールは is_ready フィルターで絞り込み可能"""
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

        # 画像を作成
        et1 = EntireTree(
            tree_id=sample_tree.id,
            user_id=sample_user.id,
            latitude=35.6580,
            longitude=139.7016,
            image_obj_key="2024/04/01/filter_test1.jpg",
            thumb_obj_key="2024/04/01/filter_test1_thumb.jpg",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        et2 = EntireTree(
            tree_id=sample_tree.id,
            user_id=sample_user.id,
            latitude=35.6590,
            longitude=139.7026,
            image_obj_key="2024/04/01/filter_test2.jpg",
            thumb_obj_key="2024/04/01/filter_test2_thumb.jpg",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(et1)
        db.add(et2)
        db.commit()
        db.refresh(et1)
        db.refresh(et2)

        # adminを作成
        admin = Annotator(
            username="filter_test_admin",
            hashed_password=pwd_context.hash("admin_pass"),
            role="admin",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

        login_response = client.post(
            "/annotation_api/login",
            data={"username": "filter_test_admin", "password": "admin_pass"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # et1を is_ready=TRUE に設定
        resp1 = client.patch(
            f"/annotation_api/trees/{et1.id}/is_ready",
            json={"is_ready": True},
            headers=headers,
        )
        assert resp1.status_code == status.HTTP_200_OK

        # et2を is_ready=FALSE に設定（明示的にレコードを作成）
        resp2 = client.patch(
            f"/annotation_api/trees/{et2.id}/is_ready",
            json={"is_ready": False},
            headers=headers,
        )
        assert resp2.status_code == status.HTTP_200_OK

        # is_ready=TRUE でフィルター
        response_ready = client.get(
            "/annotation_api/trees",
            params={"is_ready": True},
            headers=headers,
        )
        assert response_ready.status_code == status.HTTP_200_OK
        ready_items = response_ready.json()["items"]
        ready_ids = [i["entire_tree_id"] for i in ready_items]
        assert et1.id in ready_ids
        assert et2.id not in ready_ids

        # is_ready=FALSE でフィルター
        response_not_ready = client.get(
            "/annotation_api/trees",
            params={"is_ready": False},
            headers=headers,
        )
        assert response_not_ready.status_code == status.HTTP_200_OK
        not_ready_ids = [
            i["entire_tree_id"] for i in response_not_ready.json()["items"]
        ]
        assert et1.id not in not_ready_ids
        assert et2.id in not_ready_ids
