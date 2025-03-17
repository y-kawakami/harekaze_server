from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.application.admin.common import create_tree_censor_item
from app.domain.models.models import CensorshipStatus, Tree
from app.domain.services.image_service import ImageService
from app.domain.services.municipality_service import MunicipalityService
from app.interfaces.schemas.admin import (CensorshipUpdateRequest,
                                          TreeCensorDetailResponse)


def update_censorship(
    db: Session,
    tree_id: int,
    update_data: CensorshipUpdateRequest,
    image_service: ImageService,
    municipality_service: MunicipalityService
) -> Optional[TreeCensorDetailResponse]:
    """
    検閲状態を更新する

    Args:
        db: DBセッション
        tree_id: 投稿ID
        update_data: 更新データ
        image_service: 画像サービス
        municipality_service: 自治体サービス

    Returns:
        Optional[TreeCensorDetailResponse]: 更新後の投稿詳細情報（存在しない場合はNone）
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

    # 投稿全体の検閲ステータスを更新
    if update_data.tree_censorship_status is not None:
        tree.censorship_status = update_data.tree_censorship_status

        # NG理由を更新
        if update_data.tree_censorship_status == CensorshipStatus.APPROVED:
            tree.censorship_ng_reason = None
        else:
            if update_data.censorship_ng_reason is not None:
                tree.censorship_ng_reason = update_data.censorship_ng_reason

    # 投稿者名の検閲ステータスを更新
    if update_data.contributor_censorship_status is not None:
        tree.contributor_censorship_status = update_data.contributor_censorship_status

    # 桜全体画像の検閲ステータスを更新
    if update_data.entire_tree_censorship_status is not None and tree.entire_tree:
        tree.entire_tree.censorship_status = update_data.entire_tree_censorship_status

    # 幹の検閲ステータスを更新
    if update_data.stem_censorship_status is not None and tree.stem:
        tree.stem.censorship_status = update_data.stem_censorship_status

    # 幹の穴の検閲ステータスを更新
    if update_data.stem_hole_censorship_status is not None and tree.stem_holes and len(tree.stem_holes) > 0:
        for stem_hole in tree.stem_holes:
            stem_hole.censorship_status = update_data.stem_hole_censorship_status

    # キノコの検閲ステータスを更新
    if update_data.mushroom_censorship_status is not None and tree.mushrooms and len(tree.mushrooms) > 0:
        for mushroom in tree.mushrooms:
            mushroom.censorship_status = update_data.mushroom_censorship_status

    # テングス病の検閲ステータスを更新
    if update_data.tengusu_censorship_status is not None and tree.tengus and len(tree.tengus) > 0:
        for tengusu in tree.tengus:
            tengusu.censorship_status = update_data.tengusu_censorship_status

    # こぶの検閲ステータスを更新
    if update_data.kobu_censorship_status is not None and tree.kobus and len(tree.kobus) > 0:
        for kobu in tree.kobus:
            kobu.censorship_status = update_data.kobu_censorship_status

    # 変更をコミット
    db.commit()
    db.refresh(tree)

    # 更新後の投稿詳細情報を作成
    tree_item = create_tree_censor_item(
        tree, image_service, municipality_service)
    detail_response = TreeCensorDetailResponse(
        **tree_item.model_dump(),
    )

    return detail_response
