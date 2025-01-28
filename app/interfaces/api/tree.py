import uuid

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Path,
                     Query, UploadFile)
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.database.database import get_db
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.api.auth import get_current_user
from app.interfaces.schemas.stem import StemResponse as StemResponseSchema
from app.interfaces.schemas.tree import (TreeCountResponse, TreeDetailResponse,
                                         TreeResponse, TreeSearchResponse,
                                         TreeSearchResult, TreeStatsResponse)

router = APIRouter()
image_service = ImageService()  # 本番環境では環境変数から取得


@router.post("/tree/entire", response_model=TreeResponse)
async def create_tree(
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
    current_user: User = Depends(get_current_user)
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

    # UIDを生成
    tree_uid = str(uuid.uuid4())

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree_uid}/entire_{random_suffix}.jpg"
    thumb_key = f"trees/{tree_uid}/entire_thumb_{random_suffix}.jpg"

    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    repository = TreeRepository(db)
    tree = repository.create_tree(
        user_id=current_user.id,  # 認証済みユーザーのIDを使用
        uid=tree_uid,
        latitude=latitude,
        longitude=longitude,
        image_obj_key=image_key,
        thumb_obj_key=thumb_key,
        vitality=vitality,
        position=f'POINT({longitude} {latitude})',
        municipality="TODO",  # TODO: 逆ジオコーディングAPIから取得
        prefecture_code="13",  # TODO: 逆ジオコーディングAPIから取得
        municipality_code="13101"  # TODO: 逆ジオコーディングAPIから取得
    )

    return TreeResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        latitude=tree.latitude,
        longitude=tree.longitude,
        vitality=round(tree.vitality),
        location="TODO: 逆ジオコーディング",  # TODO: 実装
        created_at=tree.created_at
    )


@router.post("/tree/{tree_uid}/decorated")
async def update_tree_decorated_image(
    tree_uid: str = Path(
        ...,
        description="装飾する木のUID"
    ),
    contributor: str = Form(
        ...,
        description="投稿者の名前"
    ),
    image: UploadFile = File(
        ...,
        description="診断結果と情報を付与した装飾済みの写真"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。
    """
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_uid)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    # 画像をアップロード
    image_data = await image.read()
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/decorated_{random_suffix}.jpg"
    if not image_service.upload_image(image_data, image_key):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBを更新
    tree.decorated_image_obj_key = image_key
    tree.contributor = contributor
    repository.update_tree(tree)

    return {"status": "success"}


@router.get("/tree/search", response_model=TreeSearchResponse)
async def search_trees(
    latitude: float = Query(..., description="検索の中心となる緯度"),
    longitude: float = Query(..., description="検索の中心となる経度"),
    radius: float = Query(..., description="検索範囲（メートル）"),
    page: int = Query(1, description="ページ番号", ge=1),
    per_page: int = Query(10, description="1ページあたりの件数", ge=1, le=100),
    vitality_min: int | None = Query(
        None, description="元気度の最小値（1-5）", ge=1, le=5),
    vitality_max: int | None = Query(
        None, description="元気度の最大値（1-5）", ge=1, le=5),
    has_hole: bool | None = Query(None, description="幹の穴の有無"),
    has_tengusu: bool | None = Query(None, description="テングス病の有無"),
    has_mushroom: bool | None = Query(None, description="キノコの有無"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    全ユーザから投稿された桜の情報の検索を行う。
    """
    repository = TreeRepository(db)
    vitality_range = None
    if vitality_min is not None or vitality_max is not None:
        vitality_range = (
            vitality_min or 1,
            vitality_max or 5
        )

    trees, total = repository.search_trees(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        vitality_range=vitality_range,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom,
        offset=(page - 1) * per_page,
        limit=per_page
    )

    return TreeSearchResponse(
        total=total,
        trees=[TreeSearchResult(
            id=tree.uid,
            tree_number=f"#{tree.id}",
            contributor=tree.contributor,
            thumb_url=image_service.get_image_url(tree.thumb_obj_key),
            municipality=tree.municipality or None,
            prefecture_code=tree.prefecture_code or None,
            municipality_code=tree.municipality_code or None
        ) for tree in trees]
    )


@router.get("/tree/{tree_uid}", response_model=TreeDetailResponse)
async def get_tree_detail(
    tree_uid: str = Path(
        ...,
        description="取得したい桜の木のUID"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    各木の詳細情報を取得する。
    """
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_uid)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    response = TreeDetailResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        contributor=tree.contributor,
        latitude=tree.latitude,
        longitude=tree.longitude,
        vitality=round(tree.vitality),
        location="TODO: 逆ジオコーディング",  # TODO: 実装
        created_at=tree.created_at,
        image_url=image_service.get_image_url(str(tree.image_obj_key)),
        municipality=tree.municipality or None,
        prefecture_code=tree.prefecture_code or None,
        municipality_code=tree.municipality_code or None,
        stem=None,
        stem_hole_image_url=None,
        tengusu_image_url=None,
        mushroom_image_url=None
    )

    if tree.stem:
        response.stem = StemResponseSchema(
            texture=tree.stem.texture,
            can_detected=tree.stem.can_detected,
            circumference=tree.stem.circumference,
            age=45  # TODO: 実装
        )

    if tree.stem_holes:
        response.stem_hole_image_url = image_service.get_image_url(
            tree.stem_holes[0].image_obj_key)

    if tree.tengus:
        response.tengusu_image_url = image_service.get_image_url(
            str(tree.tengus[0].image_obj_key))

    if tree.mushrooms:
        response.mushroom_image_url = image_service.get_image_url(
            str(tree.mushrooms[0].image_obj_key))

    return response


@router.post("/{tree_uid}/stem", response_model=StemResponseSchema)
async def create_stem(
    tree_uid: str = Path(
        ...,
        description="幹の写真を登録する木のUID"
    ),
    image: UploadFile = File(
        ...,
        description="幹の写真"
    ),
    latitude: float = Form(
        ...,
        description="撮影場所の緯度"
    ),
    longitude: float = Form(
        ...,
        description="撮影場所の経度"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """幹の写真を登録する"""
    # 木の取得
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_uid)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    # 画像データを読み込む
    image_data = await image.read()

    # 画像を解析
    texture, can_detected, circumference, age = image_service.analyze_stem_image(
        image_data)

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/stem_{random_suffix}.jpg"
    thumb_key = f"trees/{tree.id}/stem_thumb_{random_suffix}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに保存
    try:
        repository.create_stem(
            db=db,
            tree_id=tree.id,  # 内部IDを使用
            user_id=current_user.id,  # 認証済みユーザーのIDを使用
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            texture=texture,
            can_detected=can_detected,
            circumference=circumference,
            age=age,
        )
    except Exception:
        raise HTTPException(status_code=400, detail={
            "error": 100,
            "reason": "tree_id が存在しません"
        })

    return StemResponseSchema(
        texture=texture,
        can_detected=can_detected,
        circumference=circumference,
        age=age,
    )


@router.post("/tree/{tree_uid}/hole")
async def create_stem_hole(
    tree_uid: str = Path(
        ...,
        description="幹の穴の写真を登録する木のUID"
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
    current_user: User = Depends(get_current_user)
):
    """
    幹の穴の写真を登録する。
    """
    # 木の取得
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_uid)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    # 画像をアップロード
    image_data = await image.read()

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/hole_{random_suffix}.jpg"
    thumb_key = f"trees/{tree.id}/hole_thumb_{random_suffix}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    if not repository.create_stem_hole(
        user_id=current_user.id,  # 認証済みユーザーのIDを使用
        tree_id=tree.id,  # 内部IDを使用
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


@router.post("/tree/{tree_uid}/tengusu")
async def create_tengusu(
    tree_uid: str = Path(
        ...,
        description="テングス病の写真を登録する木のUID"
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
    current_user: User = Depends(get_current_user)
):
    """
    テングス病の写真を登録する。
    """
    # 木の取得
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_uid)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    # 画像をアップロード
    image_data = await image.read()

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/tengusu_{random_suffix}.jpg"
    thumb_key = f"trees/{tree.id}/tengusu_thumb_{random_suffix}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    if not repository.create_tengus(
        user_id=current_user.id,  # 認証済みユーザーのIDを使用
        tree_id=tree.id,  # 内部IDを使用
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


@router.post("/tree/{tree_uid}/mushroom")
async def create_mushroom(
    tree_uid: str = Path(
        ...,
        description="キノコの写真を登録する木のUID"
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
    current_user: User = Depends(get_current_user)
):
    """
    キノコの写真を登録する。
    """
    # 木の取得
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_uid)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    # 画像をアップロード
    image_data = await image.read()

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/mushroom_{random_suffix}.jpg"
    thumb_key = f"trees/{tree.id}/mushroom_thumb_{random_suffix}.jpg"
    if not (image_service.upload_image(image_data, image_key) and
            image_service.upload_image(thumb_data, thumb_key)):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    if not repository.create_mushroom(
        user_id=current_user.id,  # 認証済みユーザーのIDを使用
        tree_id=tree.id,  # 内部IDを使用
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
