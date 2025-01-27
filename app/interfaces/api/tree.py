import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.domain.services.auth_service import AuthService
from app.domain.services.image_service import ImageService
from app.infrastructure.database.database import get_db
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import (TreeDetailResponse, TreeResponse,
                                         TreeSearchRequest, TreeSearchResponse)

router = APIRouter()
image_service = ImageService("your-bucket-name")  # 本番環境では環境変数から取得


def get_current_user_id(
    token: str = Depends(lambda: None),  # TODO: 実際のトークン取得処理
    db: Session = Depends(get_db)
) -> str:
    auth_service = AuthService(db)
    user_id = auth_service.verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="認証が必要です")
    return user_id


@router.post("/tree/entire", response_model=TreeResponse)
async def create_tree(
    contributor: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    桜の木全体の写真を登録する。

    Args:
        contributor: 投稿者名
        latitude: 緯度
        longitude: 経度
        image: 桜の木全体の写真（1080x1920）

    Returns:
        TreeResponse: 登録された桜の情報
            - tree_id: 登録した桜に付与されるID
            - tree_number: 表示用の番号（例: #23493）
            - vitality: 元気度（1-5の整数値）
            - location: 撮影場所
            - created_at: 撮影日時（ISO8601形式）

    Raises:
        HTTPException(400): 木が映っていない場合
        HTTPException(500): 画像のアップロードに失敗した場合
    """
    # 画像を解析
    image_data = await image.read()
    vitality, tree_detected = image_service.analyze_tree_vitality(image_data)
    if not tree_detected:
        raise HTTPException(status_code=400, detail="木が検出できません")

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    image_key = f"trees/{uuid.uuid4()}.jpg"
    thumb_key = f"thumbnails/trees/{uuid.uuid4()}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    repository = TreeRepository(db)
    tree = repository.create_tree(
        user_id=current_user_id,
        contributor=contributor,
        latitude=latitude,
        longitude=longitude,
        image_obj_key=image_key,
        thumb_obj_key=thumb_key,
        vitality=vitality
    )

    return TreeResponse(
        id=tree.id,
        tree_number=tree.tree_number,
        contributor=tree.contributor,
        latitude=tree.latitude,
        longitude=tree.longitude,
        vitality=round(tree.vitality),
        location="TODO: 逆ジオコーディング",  # TODO: 実装
        created_at=tree.created_at
    )


@router.post("/tree/{tree_id}/decorated")
async def update_tree_decorated_image(
    tree_id: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。

    Args:
        tree_id: POST /api/tree/entire で返された tree id
        image: 情報を付与した写真

    Raises:
        HTTPException(404): 指定された木が見つからない場合
        HTTPException(500): 画像のアップロードに失敗した場合
    """
    # 画像をアップロード
    image_data = await image.read()
    image_key = f"decorated/{uuid.uuid4()}.jpg"
    if not image_service.upload_image(image_data, image_key):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBを更新
    repository = TreeRepository(db)
    if not repository.update_tree_decorated_image(tree_id, image_key):
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    return {"status": "success"}


@router.get("/tree/search", response_model=TreeSearchResponse)
async def search_trees(
    request: TreeSearchRequest,
    db: Session = Depends(get_db)
):
    """
    全ユーザから投稿された桜の情報の検索を行う。

    Args:
        request: 検索条件
            - latitude: 中心点の緯度
            - longitude: 中心点の経度
            - radius: 検索半径（メートル）
            - filter: フィルタ条件
                - vitality_range: 元気度の範囲（1-5）
                - age_range: 樹齢の範囲
                - has_hole: 幹の穴の有無
                - has_tengusu: テングス病の有無
                - has_mushroom: キノコの有無
            - page: ページ番号
            - per_page: 1ページあたりの件数

    Returns:
        TreeSearchResponse:
            - total: 総ヒット件数
            - trees: 検索結果の桜の情報のリスト
    """
    repository = TreeRepository(db)
    vitality_range = None
    if request.filter and (request.filter.vitality_min is not None or
                           request.filter.vitality_max is not None):
        vitality_range = (
            request.filter.vitality_min or 1,
            request.filter.vitality_max or 5
        )

    trees, total = repository.search_trees(
        latitude=request.latitude,
        longitude=request.longitude,
        radius=request.radius,
        vitality_range=vitality_range,
        has_hole=request.filter.has_hole if request.filter else None,
        has_tengusu=request.filter.has_tengusu if request.filter else None,
        has_mushroom=request.filter.has_mushroom if request.filter else None,
        offset=(request.page - 1) * request.per_page,
        limit=request.per_page
    )

    return TreeSearchResponse(
        total=total,
        trees=[{
            "id": tree.id,
            "tree_number": tree.tree_number,
            "contributor": tree.contributor,
            "thumb_url": image_service.get_image_url(tree.thumb_obj_key)
        } for tree in trees]
    )


@router.get("/tree/{tree_id}", response_model=TreeDetailResponse)
async def get_tree_detail(
    tree_id: str,
    db: Session = Depends(get_db)
):
    """
    各木の詳細情報を取得する。

    Args:
        tree_id: POST /api/tree/entire で返された tree id

    Returns:
        TreeDetailResponse: 桜の詳細情報
            - 基本情報（ID、番号、位置情報など）
            - 幹の情報（存在する場合）
            - 各種写真のURL

    Raises:
        HTTPException(404): 指定された木が見つからない場合
    """
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_id)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    response = TreeDetailResponse(
        id=tree.id,
        tree_number=tree.tree_number,
        contributor=tree.contributor,
        latitude=tree.latitude,
        longitude=tree.longitude,
        vitality=round(tree.vitality),
        location="TODO: 逆ジオコーディング",  # TODO: 実装
        created_at=tree.created_at,
        image_url=image_service.get_image_url(tree.image_obj_key)
    )

    if tree.stem:
        response.stem = {
            "texture": tree.stem.texture,
            "can_detected": tree.stem.can_detected,
            "circumference": tree.stem.circumference,
            "age": 45  # TODO: 実装
        }

    if tree.stem_holes:
        response.stem_hole_image_url = image_service.get_image_url(
            tree.stem_holes[0].image_obj_key)

    if tree.tengus:
        response.tengusu_image_url = image_service.get_image_url(
            tree.tengus[0].image_obj_key)

    if tree.mushrooms:
        response.mushroom_image_url = image_service.get_image_url(
            tree.mushrooms[0].image_obj_key)

    return response
