from app.domain.models.models import Tree
from app.interfaces.schemas.admin import ImageCensorInfo, TreeCensorItem


def create_tree_censor_item(tree: Tree) -> TreeCensorItem:
    """
    TreeオブジェクトからTreeCensorItemを作成する

    Args:
        tree: Treeオブジェクト

    Returns:
        TreeCensorItem: 検閲対象の投稿情報
    """
    # 桜全体画像の情報
    entire_tree_info = None
    if tree.entire_tree:
        entire_tree_info = ImageCensorInfo(
            image_thumb_url=tree.entire_tree.thumb_obj_key,
            censorship_status=tree.entire_tree.censorship_status
        )

    # 幹の画像情報
    stem_info = None
    if tree.stem:
        stem_info = ImageCensorInfo(
            image_thumb_url=tree.stem.thumb_obj_key,
            censorship_status=tree.stem.censorship_status
        )

    # 幹の穴の画像情報
    stem_hole_info = None
    if tree.stem_holes and len(tree.stem_holes) > 0:
        stem_hole = tree.stem_holes[0]  # 最初の1つだけ使用
        stem_hole_info = ImageCensorInfo(
            image_thumb_url=stem_hole.thumb_obj_key,
            censorship_status=stem_hole.censorship_status
        )

    # テングス病の画像情報
    tengusu_info = None
    if tree.tengus and len(tree.tengus) > 0:
        tengusu = tree.tengus[0]  # 最初の1つだけ使用
        tengusu_info = ImageCensorInfo(
            image_thumb_url=tengusu.thumb_obj_key,
            censorship_status=tengusu.censorship_status
        )

    # キノコの画像情報
    mushroom_info = None
    if tree.mushrooms and len(tree.mushrooms) > 0:
        mushroom = tree.mushrooms[0]  # 最初の1つだけ使用
        mushroom_info = ImageCensorInfo(
            image_thumb_url=mushroom.thumb_obj_key,
            censorship_status=mushroom.censorship_status
        )

    # こぶの画像情報
    kobu_info = None
    if tree.kobus and len(tree.kobus) > 0:
        kobu = tree.kobus[0]  # 最初の1つだけ使用
        kobu_info = ImageCensorInfo(
            image_thumb_url=kobu.thumb_obj_key,
            censorship_status=kobu.censorship_status
        )

    # 投稿情報の作成
    return TreeCensorItem(
        tree_id=tree.id,
        entire_tree=entire_tree_info,
        stem=stem_info,
        stem_hole=stem_hole_info,
        mushroom=mushroom_info,
        tengusu=tengusu_info,
        kobu=kobu_info,
        contributor=tree.contributor,
        contributor_censorship_status=tree.contributor_censorship_status,
        location=tree.location,
        censorship_status=tree.censorship_status,
        created_at=tree.created_at
    )
