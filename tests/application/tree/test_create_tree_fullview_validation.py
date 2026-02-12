"""create_tree パイプラインの全景バリデーション統合テスト

Rekognition ラベル検出後、元気度解析前に全景バリデーションを実行する。
NG 判定時は画像を S3 に保存し判定結果を DB に記録した後に
FullviewValidationError を送出する。
OK 判定時は後続の元気度解析・DB 登録を通常通り実行する。

Requirements: 3.1, 3.2, 3.3
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.exceptions import FullviewValidationError
from app.application.tree.create_tree import create_tree
from app.domain.services.fullview_validation_service import (
    FullviewValidationResult,
)


def _make_mock_user() -> MagicMock:
    """テスト用モックユーザー"""
    user = MagicMock()
    user.id = 1
    return user


def _make_mock_address() -> MagicMock:
    """テスト用モックアドレス"""
    address = MagicMock()
    address.country = "日本"
    address.detail = "東京都千代田区"
    address.prefecture_code = "13"
    address.municipality_code = "13101"
    address.block = "千代田1-1"
    return address


def _make_mock_services():
    """テスト用モックサービス群を生成する"""
    db = MagicMock()
    current_user = _make_mock_user()

    image_service = MagicMock()
    image_service.bytes_to_pil.return_value = MagicMock(
        format="JPEG"
    )
    image_service.pil_to_bytes.return_value = b"jpeg-data"
    image_service.upload_image = AsyncMock(return_value=True)
    image_service.create_thumbnail.return_value = b"thumb-data"
    image_service.get_contents_bucket_name.return_value = "bucket"
    image_service.get_full_object_key.return_value = "full-key"

    geocoding_service = MagicMock()
    geocoding_service.get_address.return_value = (
        _make_mock_address()
    )

    label_detector = MagicMock()
    label_detector.detect = AsyncMock(
        return_value={"Tree": [MagicMock()]}
    )

    flowering_date_service = MagicMock()
    spot = MagicMock()
    spot.estimate_vitality.return_value = (0.5, 0.5)
    flowering_date_service.find_nearest_spot.return_value = spot

    ai_service = MagicMock()
    bloom_result = MagicMock()
    bloom_result.vitality = 3
    bloom_result.vitality_real = 3.0
    noleaf_result = MagicMock()
    noleaf_result.vitality = 3
    noleaf_result.vitality_real = 3.0
    ai_service.analyze_tree_vitality_bloom = AsyncMock(
        return_value=bloom_result
    )
    ai_service.analyze_tree_vitality_noleaf = AsyncMock(
        return_value=noleaf_result
    )

    fullview_service = MagicMock()
    fullview_service.validate = AsyncMock()
    fullview_service.model_id = "test-model-id"

    fv_log_repo = MagicMock()
    fv_log_repo.create.return_value = MagicMock()

    return {
        "db": db,
        "current_user": current_user,
        "image_service": image_service,
        "geocoding_service": geocoding_service,
        "label_detector": label_detector,
        "flowering_date_service": flowering_date_service,
        "ai_service": ai_service,
        "fullview_validation_service": fullview_service,
        "fullview_validation_log_repository": fv_log_repo,
    }


@pytest.mark.unit
class TestCreateTreeFullviewValidationNG:
    """NG 判定時のパイプライン動作テスト"""

    @pytest.mark.asyncio
    async def test_ng_raises_fullview_validation_error(self):
        """NG 判定時に FullviewValidationError を送出する
        (Requirements 3.2)"""
        mocks = _make_mock_services()
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=False,
                reason="枝の先端部分のみ",
                confidence=0.88,
            )
        )

        with pytest.raises(FullviewValidationError) as exc_info:
            await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        assert exc_info.value.error_code == 114
        assert exc_info.value.status == 400

    @pytest.mark.asyncio
    async def test_ng_error_contains_reason_and_confidence(self):
        """NG エラーレスポンスに理由と信頼度を含む
        (Requirements 3.3)"""
        mocks = _make_mock_services()
        reason = "枝の先端部分のみが写っています"
        confidence = 0.88
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=False,
                reason=reason,
                confidence=confidence,
            )
        )

        with pytest.raises(FullviewValidationError) as exc_info:
            await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        assert exc_info.value.reason == reason
        assert exc_info.value.details is not None
        assert exc_info.value.details["confidence"] == confidence

    @pytest.mark.asyncio
    async def test_ng_skips_ai_analysis(self):
        """NG 判定時は元気度解析を実行しない
        (Requirements 3.2)"""
        mocks = _make_mock_services()
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=False,
                reason="寄りすぎ",
                confidence=0.90,
            )
        )

        with pytest.raises(FullviewValidationError):
            await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        mocks["ai_service"].analyze_tree_vitality_bloom \
            .assert_not_called()
        mocks["ai_service"].analyze_tree_vitality_noleaf \
            .assert_not_called()

    @pytest.mark.asyncio
    async def test_ng_uploads_image_to_s3(self):
        """NG 判定時に画像を S3 に保存する"""
        mocks = _make_mock_services()
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=False,
                reason="はみ出し",
                confidence=0.85,
            )
        )

        with pytest.raises(FullviewValidationError):
            await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        # upload_image が NG 画像保存で呼ばれる
        mocks["image_service"].upload_image.assert_called()
        call_args = (
            mocks["image_service"].upload_image.call_args
        )
        obj_key = call_args[0][1]
        assert obj_key.startswith("validation_ng/")

    @pytest.mark.asyncio
    async def test_ng_saves_log_to_db(self):
        """NG 判定時に判定結果を DB に記録する"""
        mocks = _make_mock_services()
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=False,
                reason="はみ出し",
                confidence=0.85,
            )
        )

        with pytest.raises(FullviewValidationError):
            await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        fv_log_repo = mocks["fullview_validation_log_repository"]
        fv_log_repo.create.assert_called_once()
        call_kwargs = fv_log_repo.create.call_args[1]
        assert call_kwargs["is_valid"] is False
        assert call_kwargs["reason"] == "はみ出し"
        assert call_kwargs["confidence"] == 0.85
        assert call_kwargs["model_id"] == "test-model-id"
        assert call_kwargs["image_obj_key"].startswith(
            "validation_ng/"
        )


@pytest.mark.unit
class TestCreateTreeFullviewValidationOK:
    """OK 判定時のパイプライン動作テスト"""

    @pytest.mark.asyncio
    async def test_ok_continues_pipeline(self):
        """OK 判定時は後続の元気度解析を実行する
        (Requirements 3.1)"""
        mocks = _make_mock_services()
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=True,
                reason="桜の木全体が適切に収まっています。",
                confidence=0.95,
            )
        )

        # create_tree が正常終了するためには
        # DB 登録のモックも必要
        mock_tree = MagicMock()
        mock_tree.uid = "test-uid"
        mock_tree.id = 1
        mock_tree.latitude = 35.0
        mock_tree.longitude = 139.0
        mock_tree.location = "東京都千代田区"
        mock_tree.prefecture_code = "13"
        mock_tree.municipality_code = "13101"
        mock_tree.photo_date = datetime.now(timezone.utc)
        mock_tree.entire_tree = None

        with patch(
            "app.application.tree.create_tree.TreeRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.create_tree.return_value = mock_tree
            mock_repo_class.return_value = mock_repo

            result = await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        # 元気度解析が実行された
        mocks["ai_service"].analyze_tree_vitality_bloom \
            .assert_called_once()
        mocks["ai_service"].analyze_tree_vitality_noleaf \
            .assert_called_once()

        # TreeResponse が返却された
        assert result is not None
        assert result.id == "test-uid"

    @pytest.mark.asyncio
    async def test_ok_does_not_save_ng_log(self):
        """OK 判定時は NG ログを保存しない"""
        mocks = _make_mock_services()
        mocks["fullview_validation_service"].validate.return_value = (
            FullviewValidationResult(
                is_valid=True,
                reason="適切",
                confidence=0.95,
            )
        )

        mock_tree = MagicMock()
        mock_tree.uid = "test-uid"
        mock_tree.id = 1
        mock_tree.latitude = 35.0
        mock_tree.longitude = 139.0
        mock_tree.location = "東京都千代田区"
        mock_tree.prefecture_code = "13"
        mock_tree.municipality_code = "13101"
        mock_tree.photo_date = datetime.now(timezone.utc)
        mock_tree.entire_tree = None

        with patch(
            "app.application.tree.create_tree.TreeRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.create_tree.return_value = mock_tree
            mock_repo_class.return_value = mock_repo

            _ = await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        # NG ログは保存されない
        fv_log_repo = mocks["fullview_validation_log_repository"]
        fv_log_repo.create.assert_not_called()


@pytest.mark.unit
class TestCreateTreeFullviewValidationExecution:
    """全景バリデーション実行タイミングのテスト"""

    @pytest.mark.asyncio
    async def test_validation_called_after_label_detection(self):
        """Rekognition ラベル検出後に全景バリデーションが実行される
        (Requirements 3.1)"""
        mocks = _make_mock_services()
        call_order: list[str] = []

        async def track_detect(
            *args: object, **kwargs: object
        ) -> dict[str, list[MagicMock]]:
            call_order.append("label_detect")
            return {"Tree": [MagicMock()]}

        async def track_validate(
            *args: object, **kwargs: object
        ) -> FullviewValidationResult:
            call_order.append("fullview_validate")
            return FullviewValidationResult(
                is_valid=False,
                reason="NG",
                confidence=0.9,
            )

        mocks["label_detector"].detect = AsyncMock(
            side_effect=track_detect
        )
        mocks["fullview_validation_service"].validate = AsyncMock(
            side_effect=track_validate
        )

        with pytest.raises(FullviewValidationError):
            await create_tree(
                db=mocks["db"],
                current_user=mocks["current_user"],
                latitude=35.0,
                longitude=139.0,
                image_data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                contributor=None,
                image_service=mocks["image_service"],
                geocoding_service=mocks["geocoding_service"],
                label_detector=mocks["label_detector"],
                flowering_date_service=(
                    mocks["flowering_date_service"]
                ),
                ai_service=mocks["ai_service"],
                fullview_validation_service=(
                    mocks["fullview_validation_service"]
                ),
                fullview_validation_log_repository=(
                    mocks["fullview_validation_log_repository"]
                ),
            )

        assert call_order == ["label_detect", "fullview_validate"]
