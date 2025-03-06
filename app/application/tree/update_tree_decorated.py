import uuid
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import (ImageUploadError, NgWordError,
                                        TreeNotFoundError)
from app.domain.constants.ngwords import is_ng_word
from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import TreeDecoratedResponse


async def update_tree_decorated_image(
    db: Session,
    current_user: User,
    tree_id: str,
    contributor: Optional[str],
    image_data: bytes,
    ogp_image_data: bytes,
    image_service: ImageService,
) -> TreeDecoratedResponse:
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        tree_id (str): 装飾する木のUID
        contributor (str): 投稿者の名前
        image_data (bytes): 装飾済みの写真データ
        ogp_image_data (bytes): OGP用の画像データ
        image_service (ImageService): 画像サービス

    Returns:
        TreeDecoratedResponse: 装飾された木の情報

    Raises:
        TreeNotFoundError: 指定された木が見つからない場合
        ImageUploadError: 画像のアップロードに失敗した場合
    """

    if contributor is not None and is_ng_word(contributor):
        raise NgWordError(contributor)

    logger.info(f"木の装飾画像の更新を開始: tree_id={tree_id}")

    # 木の取得
    repository = TreeRepository(db)
    tree = repository.get_tree_with_entire_tree(tree_id)
    if not tree:
        logger.warning(f"木が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)
    entire_tree = tree.entire_tree
    if not entire_tree:
        logger.warning(f"木全体の画像が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree.uid}/decorated_{random_suffix}.jpg"
    ogp_image_key = f"{tree.uid}/ogp_{random_suffix}.jpg"

    try:
        # 装飾画像をアップロード
        if not await image_service.upload_image(image_data, image_key):
            logger.error(f"装飾画像のアップロード失敗: tree_id={tree_id}")
            raise ImageUploadError(tree_uid=tree_id)

        # OGP画像をアップロード
        if not await image_service.upload_image(ogp_image_data, ogp_image_key):
            logger.error(f"OGP画像のアップロード失敗: tree_id={tree_id}")
            raise ImageUploadError(tree_uid=tree_id)

        logger.debug(
            f"画像アップロード成功: image_key={image_key}, ogp_image_key={ogp_image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_uid=tree_id) from e

    # DBを更新
    entire_tree.decorated_image_obj_key = image_key
    entire_tree.ogp_image_obj_key = ogp_image_key
    if contributor:
        tree.contributor = contributor
    repository.update_tree(tree)
    logger.info(f"木の装飾画像の更新が完了: tree_id={tree_id}")

    return TreeDecoratedResponse(
        decorated_image_url=image_service.get_image_url(image_key),
        ogp_image_url=image_service.get_image_url(ogp_image_key)
    )
