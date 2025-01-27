import uuid

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Path,
                     Query, UploadFile)
from sqlalchemy.orm import Session

from app.domain.services.auth_service import AuthService
from app.domain.services.image_service import ImageService
from app.infrastructure.database.database import get_db
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import (TreeCountResponse, TreeDetailResponse,
                                         TreeResponse, TreeSearchRequest,
                                         TreeSearchResponse, TreeStatsResponse)

router = APIRouter()
image_service = ImageService()  # 本番環境では環境変数から取得


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
    contributor: str = Form(
        ...,
        description="投稿者の名前"
    ),
    latitude: float = Form(
        ...,
        description="撮影場所の緯度"
    ),
    longitude: float = Form(
        ...,
        description="撮影場所の経度"
    ),
    image: UploadFile = File(
        ...,
        description="桜の木全体の写真（推奨サイズ: 1080x1920）"
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    桜の木全体の写真を登録する。
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
        vitality=vitality,
        position=f'POINT({longitude} {latitude})'
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
    tree_id: str = Path(
        ...,
        description="POST /api/tree/entire で返された tree id"
    ),
    image: UploadFile = File(
        ...,
        description="診断結果と情報を付与した装飾済みの写真"
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。
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
    request: TreeSearchRequest = Depends(),
    db: Session = Depends(get_db)
):
    """
    全ユーザから投稿された桜の情報の検索を行う。
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
    tree_id: str = Path(
        ...,
        description="取得したい桜の木のID"
    ),
    db: Session = Depends(get_db)
):
    """
    各木の詳細情報を取得する。
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


@router.post("/tree/{tree_id}/hole")
async def create_stem_hole(
    tree_id: str = Path(
        ...,
        description="POST /api/tree/entire で返された tree id"
    ),
    latitude: float = Form(
        ...,
        description="撮影場所の緯度"
    ),
    longitude: float = Form(
        ...,
        description="撮影場所の経度"
    ),
    image: UploadFile = File(
        ...,
        description="幹の穴の写真"
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    幹の穴の写真を登録する。
    """
    # 画像をアップロード
    image_data = await image.read()

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    image_key = f"holes/{uuid.uuid4()}.jpg"
    thumb_key = f"thumbnails/holes/{uuid.uuid4()}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    repository = TreeRepository(db)
    if not repository.create_stem_hole(
        user_id=current_user_id,
        tree_id=tree_id,
        latitude=latitude,
        longitude=longitude,
        image_obj_key=image_key,
        thumb_obj_key=thumb_key
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "code": 100,
                "message": "指定された木が見つかりません"
            }
        )

    return {"status": "success"}


@router.post("/tree/{tree_id}/tengusu")
async def create_tengusu(
    tree_id: str = Path(
        ...,
        description="POST /api/tree/entire で返された tree id"
    ),
    latitude: float = Form(
        ...,
        description="撮影場所の緯度"
    ),
    longitude: float = Form(
        ...,
        description="撮影場所の経度"
    ),
    image: UploadFile = File(
        ...,
        description="テングス病の写真"
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    テングス病の写真を登録する。
    """
    # 画像をアップロード
    image_data = await image.read()

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    image_key = f"tengusu/{uuid.uuid4()}.jpg"
    thumb_key = f"thumbnails/tengusu/{uuid.uuid4()}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    repository = TreeRepository(db)
    if not repository.create_tengus(
        user_id=current_user_id,
        tree_id=tree_id,
        latitude=latitude,
        longitude=longitude,
        image_obj_key=image_key,
        thumb_obj_key=thumb_key
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "code": 100,
                "message": "指定された木が見つかりません"
            }
        )

    return {"status": "success"}


@router.post("/tree/{tree_id}/mushroom")
async def create_mushroom(
    tree_id: str = Path(
        ...,
        description="POST /api/tree/entire で返された tree id"
    ),
    latitude: float = Form(
        ...,
        description="撮影場所の緯度"
    ),
    longitude: float = Form(
        ...,
        description="撮影場所の経度"
    ),
    image: UploadFile = File(
        ...,
        description="キノコの写真"
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    キノコの写真を登録する。
    """
    # 画像をアップロード
    image_data = await image.read()

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    image_key = f"mushrooms/{uuid.uuid4()}.jpg"
    thumb_key = f"thumbnails/mushrooms/{uuid.uuid4()}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    repository = TreeRepository(db)
    if not repository.create_mushroom(
        user_id=current_user_id,
        tree_id=tree_id,
        latitude=latitude,
        longitude=longitude,
        image_obj_key=image_key,
        thumb_obj_key=thumb_key
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "code": 100,
                "message": "指定された木が見つかりません"
            }
        )

    return {"status": "success"}


@router.get("/tree/count", response_model=TreeCountResponse)
async def get_tree_count(
    prefecture: str | None = Query(
        None,
        description="都道府県名（都道府県名もしくは市区町村名のいずれかは必須）"
    ),
    city: str | None = Query(
        None,
        description="市区町村名（都道府県名もしくは市区町村名のいずれかは必須）"
    ),
    vitality_min: int | None = Query(
        None,
        description="元気度の最小値（1-5）",
        ge=1,
        le=5
    ),
    vitality_max: int | None = Query(
        None,
        description="元気度の最大値（1-5）",
        ge=1,
        le=5
    ),
    age_min: int | None = Query(
        None,
        description="樹齢の最小値（年）",
        ge=0
    ),
    age_max: int | None = Query(
        None,
        description="樹齢の最大値（年）",
        ge=0
    ),
    has_hole: bool | None = Query(
        None,
        description="幹の穴の有無"
    ),
    has_tengusu: bool | None = Query(
        None,
        description="テングス病の有無"
    ),
    has_mushroom: bool | None = Query(
        None,
        description="キノコの有無"
    ),
    db: Session = Depends(get_db)
):
    """
    ユーザから投稿された桜の本数を取得する。
    """
    if not prefecture and not city:
        raise HTTPException(
            status_code=400,
            detail="都道府県名もしくは市区町村名のいずれかを指定してください"
        )

    repository = TreeRepository(db)
    count = repository.count_trees(
        prefecture=prefecture,
        city=city,
        vitality_range=(
            vitality_min, vitality_max) if vitality_min or vitality_max else None,
        age_range=(age_min, age_max) if age_min or age_max else None,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom
    )

    return {"count": count}


@router.get("/tree/stats", response_model=TreeStatsResponse)
async def get_tree_stats(
    prefecture: str | None = Query(
        None,
        description="都道府県名（都道府県名もしくは市区町村名のいずれかは必須）"
    ),
    city: str | None = Query(
        None,
        description="市区町村名（都道府県名もしくは市区町村名のいずれかは必須）"
    ),
    vitality_min: int | None = Query(
        None,
        description="元気度の最小値（1-5）",
        ge=1,
        le=5
    ),
    vitality_max: int | None = Query(
        None,
        description="元気度の最大値（1-5）",
        ge=1,
        le=5
    ),
    age_min: int | None = Query(
        None,
        description="樹齢の最小値（年）",
        ge=0
    ),
    age_max: int | None = Query(
        None,
        description="樹齢の最大値（年）",
        ge=0
    ),
    has_hole: bool | None = Query(
        None,
        description="幹の穴の有無"
    ),
    has_tengusu: bool | None = Query(
        None,
        description="テングス病の有無"
    ),
    has_mushroom: bool | None = Query(
        None,
        description="キノコの有無"
    ),
    db: Session = Depends(get_db)
):
    """
    ユーザから投稿された桜の集計情報を取得する。
    """
    if not prefecture and not city:
        raise HTTPException(
            status_code=400,
            detail="都道府県名もしくは市区町村名のいずれかを指定してください"
        )

    repository = TreeRepository(db)
    stats = repository.get_tree_stats(
        prefecture=prefecture,
        city=city,
        vitality_range=(
            vitality_min, vitality_max) if vitality_min or vitality_max else None,
        age_range=(age_min, age_max) if age_min or age_max else None,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom
    )

    return {
        "vitality_distribution": {
            "1": stats["vitality_1"],
            "2": stats["vitality_2"],
            "3": stats["vitality_3"],
            "4": stats["vitality_4"],
            "5": stats["vitality_5"]
        },
        "age_distribution": {
            "0-20": stats["age_0_20"],
            "30-39": stats["age_30_39"],
            "40-49": stats["age_40_49"],
            "50-59": stats["age_50_59"],
            "60+": stats["age_60_plus"]
        }
    }
