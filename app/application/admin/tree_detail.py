from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.application.admin.common import create_tree_censor_item
from app.domain.models.models import Tree
from app.domain.services.image_service import ImageService
from app.interfaces.schemas.admin import TreeCensorDetailResponse


def get_tree_detail(db: Session, tree_id: int, image_service: ImageService) -> Optional[TreeCensorDetailResponse]:
    """
    投稿詳細を取得する

    Args:
        db: DBセッション
        tree_id: 投稿ID
        image_service: 画像サービス

    Returns:
        Optional[TreeCensorDetailResponse]: 投稿詳細情報（存在しない場合はNone）
    """
    # 投稿を取得
    tree = db.query(Tree).filter(Tree.id == tree_id).options(
        joinedload(Tree.entire_tree),
        joinedload(Tree.stem),
        joinedload(Tree.stem_holes),
        joinedload(Tree.tengus),
        joinedload(Tree.mushrooms),
        joinedload(Tree.kobus)
    ).first()

    if not tree:
        return None

    # TreeCensorItemを作成
    tree_item = create_tree_censor_item(tree, image_service)

    # TreeCensorDetailResponseに変換
    detail_response = TreeCensorDetailResponse(
        **tree_item.model_dump(),
        censorship_ng_reason=tree.censorship_ng_reason
    )

    return detail_response
