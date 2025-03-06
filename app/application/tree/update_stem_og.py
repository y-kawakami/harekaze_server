import uuid

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import ImageUploadError, TreeNotFoundError
from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.stem_repository import StemRepository
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import StemOgInfo


async def update_stem_og_app(
    db: Session,
    current_user: User,
    tree_id: str,
    ogp_image_data: bytes,
    image_service: ImageService,
) -> StemOgInfo:
    """
    幹の写真に、OGを送信する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        tree_id (str): 装飾する木のUID
        contributor (str): 投稿者の名前
        ogp_image_data (bytes): OGP用の画像データ
        image_service (ImageService): 画像サービス

    Returns:
        TreeDecoratedResponse: 装飾された木の情報

    Raises:
        TreeNotFoundError: 指定された木が見つからない場合
        ImageUploadError: 画像のアップロードに失敗した場合
    """

    logger.info(f"幹のOG画像の更新を開始: tree_id={tree_id}")

    # 木の取得
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_id)
    if not tree:
        logger.warning(f"木が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)

    stem_repo = StemRepository(db)
    stem = stem_repo.get_stem_by_tree_id(tree.id)
    if not stem:
        logger.warning(f"幹が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    ogp_image_key = f"{tree.uid}/stem_ogp_{random_suffix}.jpg"

    try:
        # OGP画像をアップロード
        if not await image_service.upload_image(ogp_image_data, ogp_image_key):
            logger.error(f"OGP画像のアップロード失敗: tree_id={tree_id}")
            raise ImageUploadError(tree_uid=tree_id)

        logger.debug(
            f"画像アップロード成功: ogp_image_key={ogp_image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_uid=tree_id) from e

    # DBを更新
    stem.ogp_image_obj_key = ogp_image_key
    stem_repo.update_stem(stem)
    logger.info(f"木の装飾画像の更新が完了: tree_id={tree_id}")

    return StemOgInfo(
        ogp_image_url=image_service.get_image_url(ogp_image_key)
    )
