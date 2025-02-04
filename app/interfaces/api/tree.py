import uuid
from datetime import datetime, timezone

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Path,
                     Query, UploadFile)
from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.database.database import get_db
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.api.auth import get_current_user
from app.interfaces.schemas.tree import (AreaCountResponse, AreaStatsResponse,
                                         MushroomInfo, StemHoleInfo, StemInfo,
                                         TengusuInfo, TreeDecoratedResponse,
                                         TreeDetailResponse, TreeResponse,
                                         TreeSearchResponse, TreeSearchResult)

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
    logger.info(f"新しい木の登録を開始: ユーザーID={current_user.id}, 位置={
                latitude},{longitude}")

    # 画像を解析
    image_data = await image.read()
    logger.debug("画像解析を開始")
    vitality, tree_detected = image_service.analyze_tree_vitality(image_data)
    if not tree_detected:
        logger.warning(f"木が検出できません: ユーザーID={current_user.id}")
        raise HTTPException(status_code=400, detail="木が検出できません")

    # サムネイル作成
    logger.debug("サムネイル作成を開始")
    thumb_data = image_service.create_thumbnail(image_data)

    # UIDを生成
    tree_uid = str(uuid.uuid4())
    logger.debug(f"生成されたツリーUID: {tree_uid}")

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree_uid}/entire_{random_suffix}.jpg"
    thumb_key = f"{tree_uid}/entire_thumb_{random_suffix}.jpg"

    try:
        if not (image_service.upload_image(image_data, image_key) and
                image_service.upload_image(thumb_data, thumb_key)):
            logger.error(f"画像アップロード失敗: ツリーUID={tree_uid}")
            raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")
        logger.debug(f"画像アップロード成功: image_key={image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # DBに登録
    try:
        repository = TreeRepository(db)
        tree = repository.create_tree(
            user_id=current_user.id,
            uid=tree_uid,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            vitality=vitality,
            position=f'POINT({longitude} {latitude})',
            location="東京都多摩市",  # TODO: 逆ジオコーディングAPIから取得
            prefecture_code="13",  # TODO: 逆ジオコーディングAPIから取得
            municipality_code="132241"  # TODO: 逆ジオコーディングAPIから取得
        )
        logger.info(f"木の登録が完了: ツリーUID={tree_uid}, 元気度={vitality}")
    except Exception as e:
        logger.exception(f"DB登録中にエラー発生: {str(e)}")
        raise HTTPException(status_code=500, detail="データベースへの登録に失敗しました")

    return TreeResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        prefecture_code=tree.prefecture_code,
        municipality_code=tree.municipality_code,
        vitality=tree.vitality,
        created_at=tree.created_at
    )


@router.post("/tree/{tree_id}/decorated", response_model=TreeDecoratedResponse)
async def update_tree_decorated_image(
    tree_id: str = Path(
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
    ogp_image: UploadFile = File(
        ...,
        description="OGP用の画像"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。
    """
    repository = TreeRepository(db)
    tree = repository.get_tree(tree_id)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    # 装飾画像をアップロード
    image_data = await image.read()
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/decorated_{random_suffix}.jpg"
    if not image_service.upload_image(image_data, image_key):
        raise HTTPException(status_code=500, detail="画像のアップロードに失敗しました")

    # OGP画像をアップロード
    ogp_image_data = await ogp_image.read()
    ogp_image_key = f"trees/{tree.id}/ogp_{random_suffix}.jpg"
    if not image_service.upload_image(ogp_image_data, ogp_image_key):
        raise HTTPException(status_code=500, detail="OGP画像のアップロードに失敗しました")

    # DBを更新
    tree.decorated_image_obj_key = image_key
    tree.ogp_image_obj_key = ogp_image_key
    tree.contributor = contributor
    repository.update_tree(tree)

    return TreeDecoratedResponse(
        decorated_image_url=image_service.get_image_url(image_key),
        ogp_image_url=image_service.get_image_url(ogp_image_key)
    )


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
            vitality=tree.vitality,
            image_thumb_url=image_service.get_image_url(tree.thumb_obj_key),
            latitude=tree.latitude,
            longitude=tree.longitude,
            location=tree.location,
            prefecture_code=tree.prefecture_code or None,
            municipality_code=tree.municipality_code or None,
            created_at=tree.created_at,
            age=tree.stem.age if tree.stem else None
        ) for tree in trees]
    )


@router.get("/tree/area_count", response_model=AreaCountResponse)
async def get_area_count(
    area_type: str = Query(
        ...,
        description="集計レベル（'prefecture'または'municipality'）"
    ),
    latitude: float = Query(
        ...,
        description="検索の中心となる緯度"
    ),
    longitude: float = Query(
        ...,
        description="検索の中心となる経度"
    ),
    radius: float = Query(
        ...,
        description="検索範囲（メートル）"
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
    エリア（都道府県または市区町村）ごとの桜の本数を取得する。
    area_typeで'prefecture'または'municipality'を指定し、
    指定された範囲内の桜を集計する。
    """
    logger.info(f"エリアごとの桜の本数取得開始: area_type={area_type}, lat={
                latitude}, lon={longitude}, radius={radius}m")

    try:
        # area_typeのバリデーション
        if area_type not in ['prefecture', 'municipality']:
            logger.error(f"不正なarea_type: {area_type}")
            raise HTTPException(
                status_code=400,
                detail="area_typeは'prefecture'または'municipality'を指定してください"
            )

        # パラメータのログ出力
        logger.debug(f"検索条件: vitality_min={vitality_min}, vitality_max={vitality_max}, "
                     f"age_min={age_min}, age_max={age_max}, "
                     f"has_hole={has_hole}, has_tengusu={has_tengusu}, has_mushroom={has_mushroom}")

        repository = TreeRepository(db)

        # レンジパラメータの構築
        vitality_range = None
        if vitality_min is not None or vitality_max is not None:
            vitality_range = (
                vitality_min or 1,
                vitality_max or 5
            )
            logger.debug(f"元気度範囲を設定: {vitality_range}")

        age_range = None
        if age_min is not None or age_max is not None:
            age_range = (
                age_min or 0,
                age_max or 1000
            )
            logger.debug(f"樹齢範囲を設定: {age_range}")

        # エリアごとの集計を取得
        area_counts = repository.get_area_counts(
            area_type=area_type,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            vitality_range=vitality_range,
            age_range=age_range,
            has_hole=has_hole,
            has_tengusu=has_tengusu,
            has_mushroom=has_mushroom
        )

        if not area_counts:
            logger.info("指定された条件に一致する桜は見つかりませんでした")
            return AreaCountResponse(total=0, areas=[])

        # 合計を計算
        total = sum(area.count for area in area_counts)
        logger.info(f"集計完了: 合計{total}件のデータを取得")

        return AreaCountResponse(total=total, areas=area_counts)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"エリアごとの桜の本数取得中に予期せぬエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail="内部サーバーエラーが発生しました")


@router.get("/tree/area_stats", response_model=AreaStatsResponse)
async def get_area_stats(
    prefecture_code: str | None = Query(
        None,
        description="都道府県コード（JIS X 0401に準拠）"
    ),
    municipality_code: str | None = Query(
        None,
        description="市区町村コード（JIS X 0402に準拠）"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    指定された地域（都道府県または市区町村）の統計情報を取得する。(データサマリー向け)
    都道府県コードまたは市区町村コードのいずれかは必須。
    """
    if municipality_code:
        # 市区町村の統計情報を取得
        repository = TreeRepository(db)
        stats = repository.get_municipality_stats(municipality_code)
        if not stats:
            raise HTTPException(
                status_code=404,
                detail="指定された市区町村の統計情報が見つかりません"
            )
    elif prefecture_code:
        # 都道府県の統計情報を取得
        repository = TreeRepository(db)
        stats = repository.get_prefecture_stats(prefecture_code)
        if not stats:
            raise HTTPException(
                status_code=404,
                detail="指定された都道府県の統計情報が見つかりません"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="都道府県コードまたは市区町村コードのいずれかを指定してください"
        )

    return AreaStatsResponse(
        total_trees=stats.total_trees,
        location=stats.location,
        # 元気度の分布
        vitality1_count=stats.vitality1_count,
        vitality2_count=stats.vitality2_count,
        vitality3_count=stats.vitality3_count,
        vitality4_count=stats.vitality4_count,
        vitality5_count=stats.vitality5_count,
        # 樹齢の分布
        age20_count=stats.age20_count,
        age30_count=stats.age30_count,
        age40_count=stats.age40_count,
        age50_count=stats.age50_count,
        age60_count=stats.age60_count,
        # 問題の分布
        hole_count=stats.hole_count,
        tengusu_count=stats.tengus_count,
        mushroom_count=stats.mushroom_count,
        # 位置情報
        latitude=stats.latitude,
        longitude=stats.longitude,
    )


@router.get("/tree/{tree_id}", response_model=TreeDetailResponse)
async def get_tree_detail(
    tree_id: str = Path(
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
    tree = repository.get_tree(tree_id)
    if not tree:
        raise HTTPException(status_code=404, detail="指定された木が見つかりません")

    response = TreeDetailResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        contributor=tree.contributor,
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        vitality=tree.vitality,
        prefecture_code=tree.prefecture_code or None,
        municipality_code=tree.municipality_code or None,
        image_url=image_service.get_image_url(str(tree.image_obj_key)),
        image_thumb_url=image_service.get_image_url(str(tree.thumb_obj_key)),
        decorated_image_url=image_service.get_image_url(
            tree.decorated_image_obj_key) if tree.decorated_image_obj_key else None,
        ogp_image_url=image_service.get_image_url(
            tree.ogp_image_obj_key) if tree.ogp_image_obj_key else None,
        stem=None,
        stem_hole=None,
        tengusu=None,
        mushroom=None,
        created_at=tree.created_at,
    )

    if tree.stem:
        response.stem = StemInfo(
            image_url=image_service.get_image_url(
                str(tree.stem.image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.stem.thumb_obj_key)),
            texture=tree.stem.texture,
            can_detected=tree.stem.can_detected,
            circumference=tree.stem.circumference,
            age=tree.stem.age,
            created_at=tree.stem.created_at,
        )

    if tree.stem_holes:
        response.stem_hole = StemHoleInfo(
            image_url=image_service.get_image_url(
                str(tree.stem_holes[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.stem_holes[0].thumb_obj_key)),
            created_at=tree.stem_holes[0].created_at,
        )

    if tree.tengus:
        response.tengusu = TengusuInfo(
            image_url=image_service.get_image_url(
                str(tree.tengus[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.tengus[0].thumb_obj_key)),
            created_at=tree.tengus[0].created_at,
        )

    if tree.mushrooms:
        response.mushroom = MushroomInfo(
            image_url=image_service.get_image_url(
                str(tree.mushrooms[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.mushrooms[0].thumb_obj_key)),
            created_at=tree.mushrooms[0].created_at,
        )

    return response


@router.post("/tree/{tree_id}/stem", response_model=StemInfo)
async def create_stem(
    tree_id: str = Path(
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
    tree = repository.get_tree(tree_id)
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
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=400, detail={
            "error": 100,
            "reason": "tree_id が存在しません"
        })

    return StemInfo(
        texture=texture,
        can_detected=can_detected,
        circumference=circumference,
        age=age,
        image_url=image_service.get_image_url(image_key),
        image_thumb_url=image_service.get_image_url(thumb_key),
        created_at=datetime.now(timezone.utc)
    )


@router.post("/tree/{tree_id}/hole", response_model=StemHoleInfo)
async def create_stem_hole(
    tree_id: str = Path(
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
    tree = repository.get_tree(tree_id)
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

    return StemHoleInfo(
        image_url=image_service.get_image_url(image_key),
        image_thumb_url=image_service.get_image_url(thumb_key),
        created_at=datetime.now(timezone.utc)
    )


@router.post("/tree/{tree_id}/tengusu", response_model=TengusuInfo)
async def create_tengusu(
    tree_id: str = Path(
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
    tree = repository.get_tree(tree_id)
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

    return TengusuInfo(
        image_url=image_service.get_image_url(image_key),
        image_thumb_url=image_service.get_image_url(thumb_key),
        created_at=datetime.now(timezone.utc)
    )


@router.post("/tree/{tree_id}/mushroom", response_model=MushroomInfo)
async def create_mushroom(
    tree_id: str = Path(
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
    tree = repository.get_tree(tree_id)
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

    return MushroomInfo(
        image_url=image_service.get_image_url(image_key),
        image_thumb_url=image_service.get_image_url(thumb_key),
        created_at=datetime.now(timezone.utc)
    )
