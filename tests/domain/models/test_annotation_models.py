"""アノテーション関連モデルのテスト"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.domain.models.annotation import Annotator, VitalityAnnotation
from app.domain.models.models import EntireTree, Tree, User


class TestAnnotatorModel:
    """Annotatorモデルのテスト"""

    def test_create_annotator(self, db: Session):
        """アノテーターを作成できる"""
        annotator = Annotator(
            username="test_annotator",
            hashed_password="hashed_password_here"
        )
        db.add(annotator)
        db.commit()
        db.refresh(annotator)

        assert annotator.id is not None
        assert annotator.username == "test_annotator"
        assert annotator.hashed_password == "hashed_password_here"
        assert annotator.last_login is None
        assert annotator.created_at is not None
        assert annotator.updated_at is not None

    def test_annotator_username_unique(self, db: Session):
        """ユーザー名はユニークである"""
        annotator1 = Annotator(
            username="unique_user",
            hashed_password="password1"
        )
        db.add(annotator1)
        db.commit()

        annotator2 = Annotator(
            username="unique_user",
            hashed_password="password2"
        )
        db.add(annotator2)
        with pytest.raises(Exception):
            db.commit()

    def test_annotator_update_last_login(self, db: Session):
        """最終ログイン日時を更新できる"""
        annotator = Annotator(
            username="login_test",
            hashed_password="password"
        )
        db.add(annotator)
        db.commit()

        now = datetime.now(timezone.utc)
        annotator.last_login = now
        db.commit()
        db.refresh(annotator)

        assert annotator.last_login is not None

    def test_annotator_default_role_is_annotator(self, db: Session):
        """デフォルトのroleは'annotator'である"""
        annotator = Annotator(
            username="default_role_test",
            hashed_password="password"
        )
        db.add(annotator)
        db.commit()
        db.refresh(annotator)

        assert annotator.role == "annotator"

    def test_annotator_role_can_be_admin(self, db: Session):
        """roleを'admin'に設定できる"""
        annotator = Annotator(
            username="admin_test",
            hashed_password="password",
            role="admin"
        )
        db.add(annotator)
        db.commit()
        db.refresh(annotator)

        assert annotator.role == "admin"

    def test_annotator_role_can_be_annotator(self, db: Session):
        """roleを'annotator'に明示的に設定できる"""
        annotator = Annotator(
            username="annotator_role_test",
            hashed_password="password",
            role="annotator"
        )
        db.add(annotator)
        db.commit()
        db.refresh(annotator)

        assert annotator.role == "annotator"


class TestVitalityAnnotationModel:
    """VitalityAnnotationモデルのテスト"""

    @pytest.fixture
    def setup_data(self, db: Session):
        """テスト用のUser, Tree, EntireTree, Annotatorを作成"""
        user = User(ip_addr="127.0.0.1")
        db.add(user)
        db.commit()
        db.refresh(user)

        tree = Tree(
            user_id=user.id,
            latitude=35.6762,
            longitude=139.6503,
            position="POINT(139.6503 35.6762)"
        )
        db.add(tree)
        db.commit()
        db.refresh(tree)

        entire_tree = EntireTree(
            user_id=user.id,
            tree_id=tree.id,
            latitude=35.6762,
            longitude=139.6503,
            image_obj_key="test/image.jpg",
            thumb_obj_key="test/thumb.jpg"
        )
        db.add(entire_tree)
        db.commit()
        db.refresh(entire_tree)

        annotator = Annotator(
            username="annotator1",
            hashed_password="password"
        )
        db.add(annotator)
        db.commit()
        db.refresh(annotator)

        return {
            "user": user,
            "tree": tree,
            "entire_tree": entire_tree,
            "annotator": annotator
        }

    def test_create_vitality_annotation(self, db: Session, setup_data):
        """元気度アノテーションを作成できる"""
        annotation = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=3,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc)
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.id is not None
        assert annotation.entire_tree_id == setup_data["entire_tree"].id
        assert annotation.vitality_value == 3
        assert annotation.annotator_id == setup_data["annotator"].id
        assert annotation.annotated_at is not None
        assert annotation.created_at is not None
        assert annotation.updated_at is not None

    def test_vitality_annotation_valid_values(self, db: Session, setup_data):
        """元気度値は1-5および-1を許容する"""
        valid_values = [1, 2, 3, 4, 5, -1]

        for i, value in enumerate(valid_values):
            # 各値ごとに新しいentire_treeを作成
            entire_tree = EntireTree(
                user_id=setup_data["user"].id,
                tree_id=setup_data["tree"].id,
                latitude=35.6762,
                longitude=139.6503,
                image_obj_key=f"test/image_{i}.jpg",
                thumb_obj_key=f"test/thumb_{i}.jpg"
            )
            db.add(entire_tree)
            db.commit()
            db.refresh(entire_tree)

            annotation = VitalityAnnotation(
                entire_tree_id=entire_tree.id,
                vitality_value=value,
                annotator_id=setup_data["annotator"].id,
                annotated_at=datetime.now(timezone.utc)
            )
            db.add(annotation)
            db.commit()
            db.refresh(annotation)

            assert annotation.vitality_value == value

    def test_vitality_annotation_entire_tree_unique(self, db: Session, setup_data):
        """entire_tree_idはユニークである（1画像1アノテーション）"""
        annotation1 = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=3,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc)
        )
        db.add(annotation1)
        db.commit()

        annotation2 = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=4,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc)
        )
        db.add(annotation2)
        with pytest.raises(Exception):
            db.commit()

    def test_vitality_annotation_relationship_to_entire_tree(
        self, db: Session, setup_data
    ):
        """EntireTreeとのリレーションシップが機能する"""
        annotation = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=3,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc)
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.entire_tree is not None
        assert annotation.entire_tree.id == setup_data["entire_tree"].id

    def test_vitality_annotation_relationship_to_annotator(
        self, db: Session, setup_data
    ):
        """Annotatorとのリレーションシップが機能する"""
        annotation = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=3,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc)
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.annotator is not None
        assert annotation.annotator.id == setup_data["annotator"].id

    def test_vitality_annotation_default_is_ready_false(
        self, db: Session, setup_data
    ):
        """is_readyのデフォルト値はFalseである"""
        annotation = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=3,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc)
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.is_ready is False

    def test_vitality_annotation_is_ready_can_be_true(
        self, db: Session, setup_data
    ):
        """is_readyをTrueに設定できる"""
        annotation = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=3,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc),
            is_ready=True
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.is_ready is True

    def test_vitality_annotation_vitality_value_nullable(
        self, db: Session, setup_data
    ):
        """vitality_valueはNULL許容である（is_readyのみ設定時）"""
        annotation = VitalityAnnotation(
            entire_tree_id=setup_data["entire_tree"].id,
            vitality_value=None,
            annotator_id=setup_data["annotator"].id,
            annotated_at=datetime.now(timezone.utc),
            is_ready=True
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.vitality_value is None
        assert annotation.is_ready is True
