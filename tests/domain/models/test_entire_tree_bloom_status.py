"""EntireTree モデルの bloom_status カラムテスト

EntireTree に bloom_status カラムが追加されていることをテストする。
Requirements: 2.1, 2.2
"""

import pytest
from sqlalchemy.orm import Session

from app.domain.models.models import EntireTree, Tree, User


class TestEntireTreeBloomStatus:
    """EntireTree の bloom_status カラムテスト (Req 2.1, 2.2)"""

    @pytest.fixture
    def setup_data(self, db: Session):
        """テスト用の User, Tree を作成"""
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

        return {"user": user, "tree": tree}

    def test_bloom_status_default_is_none(self, db: Session, setup_data):
        """bloom_status のデフォルト値は None であること (Req 2.1)"""
        entire_tree = EntireTree(
            user_id=setup_data["user"].id,
            tree_id=setup_data["tree"].id,
            latitude=35.6762,
            longitude=139.6503,
            image_obj_key="test/image.jpg",
            thumb_obj_key="test/thumb.jpg"
        )
        db.add(entire_tree)
        db.commit()
        db.refresh(entire_tree)

        assert entire_tree.bloom_status is None

    def test_bloom_status_can_be_set_to_valid_values(self, db: Session, setup_data):
        """bloom_status に有効な値を設定できること (Req 2.2)"""
        valid_statuses = [
            "before_bloom",
            "blooming",
            "30_percent",
            "50_percent",
            "full_bloom",
            "falling",
            "with_leaves",
            "leaves_only",
        ]

        for i, status in enumerate(valid_statuses):
            entire_tree = EntireTree(
                user_id=setup_data["user"].id,
                tree_id=setup_data["tree"].id,
                latitude=35.6762,
                longitude=139.6503,
                image_obj_key=f"test/image_{i}.jpg",
                thumb_obj_key=f"test/thumb_{i}.jpg",
                bloom_status=status,
            )
            db.add(entire_tree)
            db.commit()
            db.refresh(entire_tree)

            assert entire_tree.bloom_status == status

    def test_bloom_status_can_be_updated(self, db: Session, setup_data):
        """bloom_status を更新できること"""
        entire_tree = EntireTree(
            user_id=setup_data["user"].id,
            tree_id=setup_data["tree"].id,
            latitude=35.6762,
            longitude=139.6503,
            image_obj_key="test/update_image.jpg",
            thumb_obj_key="test/update_thumb.jpg",
            bloom_status="before_bloom",
        )
        db.add(entire_tree)
        db.commit()

        # 値を更新
        entire_tree.bloom_status = "full_bloom"
        db.commit()
        db.refresh(entire_tree)

        assert entire_tree.bloom_status == "full_bloom"

    def test_bloom_status_can_be_set_to_none(self, db: Session, setup_data):
        """bloom_status を None に設定できること"""
        entire_tree = EntireTree(
            user_id=setup_data["user"].id,
            tree_id=setup_data["tree"].id,
            latitude=35.6762,
            longitude=139.6503,
            image_obj_key="test/none_image.jpg",
            thumb_obj_key="test/none_thumb.jpg",
            bloom_status="full_bloom",
        )
        db.add(entire_tree)
        db.commit()

        # None に更新
        entire_tree.bloom_status = None
        db.commit()
        db.refresh(entire_tree)

        assert entire_tree.bloom_status is None

    def test_bloom_status_max_length(self, db: Session, setup_data):
        """bloom_status は最大20文字を格納できること"""
        # 最長のステータス値は "with_leaves" で 11文字
        # VARCHAR(20) なので 20 文字まで OK
        long_value = "a" * 20
        entire_tree = EntireTree(
            user_id=setup_data["user"].id,
            tree_id=setup_data["tree"].id,
            latitude=35.6762,
            longitude=139.6503,
            image_obj_key="test/length_image.jpg",
            thumb_obj_key="test/length_thumb.jpg",
            bloom_status=long_value,
        )
        db.add(entire_tree)
        db.commit()
        db.refresh(entire_tree)

        assert entire_tree.bloom_status is not None
        assert len(entire_tree.bloom_status) == 20
