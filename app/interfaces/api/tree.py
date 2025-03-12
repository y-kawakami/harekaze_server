from datetime import datetime, time, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile
from sqlalchemy.orm import Session

from app.application.common.constants import APPROVED_DEBUG
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
from app.application.tree.get_total_count import \
    get_total_count as get_total_count_app
from app.application.tree.get_tree_detail import \
    get_tree_detail as get_tree_detail_app
from app.application.tree.search_trees import search_trees as search_trees_app
from app.application.tree.search_trees_by_time_block import \
    search_trees_by_time_block as search_trees_by_time_block_app
from app.application.tree.update_stem_og import update_stem_og_app
from app.application.tree.update_tree_decorated import \
    update_tree_decorated_image as update_tree_decorated_app
from app.domain.models.models import User
from app.domain.services.flowering_date_service import (
    FloweringDateService, get_flowering_date_service)
from app.domain.services.image_service import ImageService, get_image_service
from app.domain.services.lambda_service import (LambdaService,
                                                get_lambda_service)
from app.domain.services.municipality_service import (MunicipalityService,
                                                      get_municipality_service)
from app.infrastructure.database.database import get_db
from app.infrastructure.geocoding.geocoding_service import GeocodingService
from app.infrastructure.images.label_detector import (LabelDetector,
                                                      get_label_detector)
from app.interfaces.api.auth import get_current_user
from app.interfaces.schemas.tree import (AreaCountResponse, AreaStatsResponse,
                                         KobuInfo, MushroomInfo, StemHoleInfo,
                                         StemInfo, StemOgInfo, TengusuInfo,
                                         TimeRangeTreesResponse,
                                         TreeDecoratedResponse,
                                         TreeDetailResponse, TreeResponse,
                                         TreeSearchResponse,
                                         TreeTotalCountResponse)

router = APIRouter()


def get_geocoding_service_dependency(
    municipality_service: MunicipalityService = Depends(
        get_municipality_service, use_cache=True)
):
    return GeocodingService(municipality_service)


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
    contributor: str | None = Form(
        None,
        description="投稿者のニックネーム（任意）"
    ),
    date: str | None = Form(
        None,
        description="撮影日時（ISO8601形式、例: 2024-04-01T12:34:56Z）（省略時は現在時刻）"
    ),
    is_approved_debug: bool = Form(
        True,
        description="デバッグ用: 投稿を承認済みとしてマークする"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    geocoding_service: GeocodingService = Depends(
        get_geocoding_service_dependency, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    flowering_date_service: FloweringDateService = Depends(
        get_flowering_date_service, use_cache=True),
    lambda_service: LambdaService = Depends(get_lambda_service, use_cache=True)
):
    """
    桜の木全体の写真を登録する。
    """
    image_data = await image.read()
    return await create_tree_app(
        db=db,
        current_user=current_user,
        latitude=latitude,
        longitude=longitude,
        image_data=image_data,
        contributor=contributor,
        image_service=image_service,
        geocoding_service=geocoding_service,
        label_detector=label_detector,
        lambda_service=lambda_service,
        flowering_date_service=flowering_date_service,
        photo_date=date,
        is_approved_debug=APPROVED_DEBUG
    )


@router.post("/tree/{tree_id}/decorated", response_model=TreeDecoratedResponse)
async def update_tree_decorated_image(
    tree_id: str = Path(
        ...,
        description="装飾する木のUID"
    ),
    contributor: str | None = Form(
        None,
        description="投稿者の名前（任意）"
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
    image_service: ImageService = Depends(get_image_service, use_cache=True)
):
    """
    桜の木全体の写真に、診断結果（元気度）に基づき情報を付与して装飾した写真を送信する。
    """
    image_data = await image.read()
    ogp_image_data = await ogp_image.read()

    return await update_tree_decorated_app(
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
    latitude: float | None = Query(None, description="検索の中心となる緯度"),
    longitude: float | None = Query(None, description="検索の中心となる経度"),
    radius: float | None = Query(None, description="検索範囲（メートル）"),
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
    has_kobu: bool | None = Query(None, description="コブ状の枝の有無"),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service, use_cache=True)
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
        has_kobu=has_kobu,
        image_service=image_service
    )


@router.get("/tree/total_count", response_model=TreeTotalCountResponse)
async def get_total_count(
    approved: bool | None = Query(None, description="検閲後の投稿のみを対象とするか"),
    db: Session = Depends(get_db)
):
    """
    承認済みの桜の木の総数を取得する。
    """
    total_count = get_total_count_app(db=db, approved=approved)
    return TreeTotalCountResponse(total_count=total_count)


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
    has_kobu: bool | None = Query(
        None,
        description="コブ状の枝の有無"
    ),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    municipality_service: MunicipalityService = Depends(
        get_municipality_service, use_cache=True)
):
    """
    エリア（都道府県または市区町村）ごとの桜の本数を取得する。
    area_typeで'prefecture'または'municipality'を指定し、
    指定された範囲内の桜を集計する。
    """
    return get_area_count_app(
        db=db,
        image_service=image_service,
        municipality_service=municipality_service,
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
        has_mushroom=has_mushroom,
        has_kobu=has_kobu
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
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    municipality_service: MunicipalityService = Depends(
        get_municipality_service, use_cache=True)
):
    """
    指定された地域（都道府県または市区町村）の統計情報を取得する。(データサマリー向け)
    都道府県コードまたは市区町村コードのいずれかは必須。
    """
    return get_area_stats_app(
        db=db,
        prefecture_code=prefecture_code,
        municipality_code=municipality_code,
        image_service=image_service,
        municipality_service=municipality_service
    )


@router.get("/tree/time_block", response_model=TimeRangeTreesResponse)
async def search_trees_by_time_block(
    per_block_limit: int = Query(
        10,
        description="ブロックごとの最大取得件数",
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    municipality_service: MunicipalityService = Depends(
        get_municipality_service, use_cache=True)
):
    """
    直近1ヶ月の投稿から、現在時刻と同じ時間帯（過去1時間内）の投稿をブロックごとに取得する。

    各ブロックにおける最大取得件数を指定できる。

    ブロックの定義：
    - ブロックA: 北海道・東北・関東
    - ブロックB: 中部・近畿
    - ブロックC: 中国・四国・九州・沖縄

    Args:
        per_block_limit (int): ブロックごとの最大取得件数

    Returns:
        TimeRangeTreesResponse: 時間帯別ブロック別の投稿一覧
    """
    # 現在時刻を取得. すぐに反映されるように +1分
    now = datetime.now(timezone.utc) + timedelta(minutes=1)
    reference_time = time(now.hour, now.minute)

    # アプリケーションロジックを呼び出す
    return search_trees_by_time_block_app(
        db=db,
        image_service=image_service,
        municipality_service=municipality_service,
        reference_time=reference_time,
        per_block_limit=per_block_limit
    )


@router.get("/tree/{tree_id}", response_model=TreeDetailResponse)
async def get_tree_detail(
    tree_id: str = Path(
        ...,
        description="取得したい桜の木のUID"
    ),
    is_debug_hrkz_wdobqcztdarm: Optional[bool] = Query(
        None,
        description="デバッグ用: デバッグ情報を含めるか"
    ),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service, use_cache=True)
):
    """
    各木の詳細情報を取得する。
    """
    return get_tree_detail_app(
        db=db,
        tree_id=tree_id,
        image_service=image_service,
        is_debug=is_debug_hrkz_wdobqcztdarm or False
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
    date: str | None = Form(
        None,
        description="撮影日時（ISO8601形式、例: 2024-04-01T12:34:56Z）（省略時は現在時刻）"
    ),
    is_can_required: bool = Form(
        False,
        description="缶を検出する場合は true"
    ),
    is_approved_debug: bool = Form(
        True,
        description="デバッグ用: 投稿を承認済みとしてマークする"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    lambda_service: LambdaService = Depends(get_lambda_service, use_cache=True)
):
    """
    幹の写真を登録する。
    """
    image_data = await image.read()
    return await create_stem_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service,
        label_detector=label_detector,
        lambda_service=lambda_service,
        photo_date=date,
        is_can_rquired=is_can_required,
        is_approved_debug=APPROVED_DEBUG
    )


@router.post("/tree/{tree_id}/stem/og", response_model=StemOgInfo)
async def update_stem_og(
    tree_id: str = Path(
        ...,
        description="木のUID"
    ),
    ogp_image: UploadFile = File(
        ...,
        description="OGP用の画像"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True)
):
    """
    幹の写真に、OG画像を送信する。
    """
    ogp_image_data = await ogp_image.read()

    return await update_stem_og_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        ogp_image_data=ogp_image_data,
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
    date: str | None = Form(
        None,
        description="撮影日時（ISO8601形式、例: 2024-04-01T12:34:56Z）（省略時は現在時刻）"
    ),
    is_approved_debug: bool = Form(
        True,
        description="デバッグ用: 投稿を承認済みとしてマークする"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
):
    """
    幹の穴の写真を登録する。
    """
    image_data = await image.read()
    return await create_stem_hole_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service,
        label_detector=label_detector,
        photo_date=date,
        is_approved_debug=APPROVED_DEBUG
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
    date: str | None = Form(
        None,
        description="撮影日時（ISO8601形式、例: 2024-04-01T12:34:56Z）（省略時は現在時刻）"
    ),
    is_approved_debug: bool = Form(
        True,
        description="デバッグ用: 投稿を承認済みとしてマークする"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
):
    """
    テングス病の写真を登録する。
    """
    image_data = await image.read()
    return await create_tengusu_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service,
        label_detector=label_detector,
        photo_date=date,
        is_approved_debug=APPROVED_DEBUG
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
    date: str | None = Form(
        None,
        description="撮影日時（ISO8601形式、例: 2024-04-01T12:34:56Z）（省略時は現在時刻）"
    ),
    is_approved_debug: bool = Form(
        True,
        description="デバッグ用: 投稿を承認済みとしてマークする"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),

):
    """
    キノコの写真を登録する。
    """
    image_data = await image.read()
    return await create_mushroom_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service,
        label_detector=label_detector,
        photo_date=date,
        is_approved_debug=APPROVED_DEBUG
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
    date: str | None = Form(
        None,
        description="撮影日時（ISO8601形式、例: 2024-04-01T12:34:56Z）（省略時は現在時刻）"
    ),
    is_approved_debug: bool = Form(
        True,
        description="デバッグ用: 投稿を承認済みとしてマークする"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
):
    """
    こぶ状の枝の写真を登録する。
    """
    image_data = await image.read()
    return await create_kobu_app(
        db=db,
        current_user=current_user,
        tree_id=tree_id,
        image_data=image_data,
        latitude=latitude,
        longitude=longitude,
        image_service=image_service,
        label_detector=label_detector,
        photo_date=date,
        is_approved_debug=APPROVED_DEBUG
    )
