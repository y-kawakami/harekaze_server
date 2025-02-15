from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile
from sqlalchemy.orm import Session

from app.application.tree.create_kobu import create_kobu as create_kobu_app
from app.application.tree.create_mushroom import \
    create_mushroom as create_mushroom_app
from app.application.tree.create_stem import create_stem as create_stem_app
from app.application.tree.create_stem_hole import \
    create_stem_hole as create_stem_hole_app
from app.application.tree.create_tengusu import \
    create_tengusu as create_tengusu_app
from app.application.tree.create_tree import create_tree as create_tree_app
from app.application.tree.get_area_count import \
    get_area_count as get_area_count_app
from app.application.tree.get_area_stats import \
    get_area_stats as get_area_stats_app
from app.application.tree.get_tree_detail import \
    get_tree_detail as get_tree_detail_app
from app.application.tree.search_trees import search_trees as search_trees_app
from app.application.tree.update_tree_decorated import \
    update_tree_decorated_image as update_tree_decorated_app
from app.domain.models.models import User
from app.domain.services.image_service import ImageService, get_image_service
from app.infrastructure.database.database import get_db
from app.interfaces.api.auth import get_current_user
from app.interfaces.schemas.tree import (AreaCountResponse, AreaStatsResponse,
                                         KobuInfo, MushroomInfo, StemHoleInfo,
                                         StemInfo, TengusuInfo,
                                         TreeDecoratedResponse,
                                         TreeDetailResponse, TreeResponse,
                                         TreeSearchResponse)

router = APIRouter()


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
    nickname: str = Form(
        ...,
        description="投稿者のニックネーム"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """
    桜の木全体の写真を登録する。
    """
    image_data = await image.read()
    return create_tree_app(
        db=db,
        current_user=current_user,
        latitude=latitude,
        longitude=longitude,
        image_data=image_data,
        nickname=nickname,
        image_service=image_service
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
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。
    """
    image_data = await image.read()
    ogp_image_data = await ogp_image.read()

    return update_tree_decorated_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        contributor=contributor,
        image_data=image_data,
        ogp_image_data=ogp_image_data,
        image_service=image_service
    )


@router.get("/tree/search", response_model=TreeSearchResponse)
async def search_trees(
    latitude: float = Query(..., description="検索の中心となる緯度"),
    longitude: float = Query(..., description="検索の中心となる経度"),
    radius: float = Query(..., description="検索範囲（メートル）"),
    # TODO: フィルター条件を追加
    municipality_code: str | None = Query(
        None, description="市区町村コード（JIS X 0402に準拠）"),
    page: int = Query(1, description="ページ番号", ge=1),
    per_page: int = Query(10, description="1ページあたりの件数", ge=1, le=100),
    vitality_min: int | None = Query(
        None, description="元気度の最小値（1-5）", ge=1, le=5),
    vitality_max: int | None = Query(
        None, description="元気度の最大値（1-5）", ge=1, le=5),
    age_min: int | None = Query(
        None, description="年齢の最小値（0-100）", ge=0, le=100),
    age_max: int | None = Query(
        None, description="元気度の最大値（0-1000）", ge=0, le=1000),
    has_hole: bool | None = Query(None, description="幹の穴の有無"),
    has_tengusu: bool | None = Query(None, description="テングス病の有無"),
    has_mushroom: bool | None = Query(None, description="キノコの有無"),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service)
):
    """
    全ユーザから投稿された桜の情報の検索を行う。
    """
    return search_trees_app(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        municipality_code=municipality_code,
        page=page,
        per_page=per_page,
        vitality_min=vitality_min,
        vitality_max=vitality_max,
        age_min=age_min,
        age_max=age_max,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom,
        image_service=image_service
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
    db: Session = Depends(get_db)
):
    """
    エリア（都道府県または市区町村）ごとの桜の本数を取得する。
    area_typeで'prefecture'または'municipality'を指定し、
    指定された範囲内の桜を集計する。
    """
    return get_area_count_app(
        db=db,
        area_type=area_type,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        vitality_min=vitality_min,
        vitality_max=vitality_max,
        age_min=age_min,
        age_max=age_max,
        has_hole=has_hole,
        has_tengusu=has_tengusu,
        has_mushroom=has_mushroom
    )


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
):
    """
    指定された地域（都道府県または市区町村）の統計情報を取得する。(データサマリー向け)
    都道府県コードまたは市区町村コードのいずれかは必須。
    """
    return get_area_stats_app(
        db=db,
        prefecture_code=prefecture_code,
        municipality_code=municipality_code
    )


@router.get("/tree/{tree_id}", response_model=TreeDetailResponse)
async def get_tree_detail(
    tree_id: str = Path(
        ...,
        description="取得したい桜の木のUID"
    ),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service)
):
    """
    各木の詳細情報を取得する。
    """
    return get_tree_detail_app(
        db=db,
        tree_id=tree_id,
        image_service=image_service
    )


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
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """幹の写真を登録する"""
    image_data = await image.read()
    return create_stem_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service
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
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """
    幹の穴の写真を登録する。
    """
    image_data = await image.read()
    return create_stem_hole_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service
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
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """
    テングス病の写真を登録する。
    """
    image_data = await image.read()
    return create_tengusu_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service
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
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """
    キノコの写真を登録する。
    """
    image_data = await image.read()
    return create_mushroom_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service
    )


@router.post("/tree/{tree_id}/kobu", response_model=KobuInfo)
async def create_kobu(
    tree_id: str = Path(
        ...,
        description="こぶ状の枝の写真を登録する木のUID"
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
        description="こぶ状の枝の写真"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service)
):
    """
    こぶ状の枝の写真を登録する。
    """
    image_data = await image.read()
    return create_kobu_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service
    )
