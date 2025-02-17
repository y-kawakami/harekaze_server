from dataclasses import dataclass
from typing import Any


@dataclass
class ApplicationError(Exception):
    """アプリケーション層の基底例外クラス"""
    reason: str
    error_code: int = 100
    status: int = 400
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.reason


class InvalidParamError(ApplicationError):
    """パラメータが不正な場合の例外"""

    def __init__(self, reason: str, param_name: str | None = None):
        super().__init__(
            reason=reason,
            error_code=105,
            status=400,
            details={"param": param_name} if param_name else None
        )


class TreeNotFoundError(ApplicationError):
    """指定された木が見つからない場合の例外"""

    def __init__(self, tree_id: str):
        super().__init__(
            reason="指定された木が見つかりません",
            error_code=104,
            status=400,
            details={"tree_id": tree_id}
        )


class TreeNotDetectedError(ApplicationError):
    """木が検出できない場合の例外"""

    def __init__(self):
        super().__init__(
            reason="木が検出できません",
            error_code=101,
            status=400
        )


class LocationNotFoundError(ApplicationError):
    """指定された場所が見つからない場合の例外"""

    def __init__(self, latitude: float, longitude: float):
        super().__init__(
            reason="指定された場所が見つかりません",
            error_code=106,
            status=400,
            details={"latitude": latitude, "longitude": longitude}
        )


class LocationNotInJapanError(ApplicationError):
    """指定された場所が日本国内に存在しない場合の例外"""

    def __init__(self, latitude: float, longitude: float):
        super().__init__(
            reason="指定された場所が日本国内に存在しません",
            error_code=107,
            status=400,
            details={"latitude": latitude, "longitude": longitude}
        )


class NgWordError(ApplicationError):
    """不適切な単語が含まれている場合の例外"""

    def __init__(self, ng_word: str):
        super().__init__(
            reason="不適切な単語が含まれています",
            error_code=108,
            status=400,
            details={"ng_word": ng_word}
        )


class MunicipalityNotFoundError(ApplicationError):
    """指定された市区町村が見つからない場合の例外"""

    def __init__(self, municipality_code: str):
        super().__init__(
            reason="指定された市区町村が見つかりません",
            error_code=109,
            status=400,
            details={"municipality_code": municipality_code}
        )


class PrefectureNotFoundError(ApplicationError):
    """指定された都道府県が見つからない場合の例外"""

    def __init__(self, prefecture_code: str):
        super().__init__(
            reason="指定された都道府県が見つかりません",
            error_code=110,
            status=400,
            details={"prefecture_code": prefecture_code}
        )


class ImageUploadError(ApplicationError):
    """画像アップロードに失敗した場合の例外"""

    def __init__(self, tree_uid: str | None = None):
        super().__init__(
            reason="画像のアップロードに失敗しました",
            error_code=102,
            status=500,
            details={"tree_uid": tree_uid} if tree_uid else None
        )


class DatabaseError(ApplicationError):
    """データベース操作に失敗した場合の例外"""

    def __init__(self, message: str):
        super().__init__(
            reason="データベースへの登録に失敗しました",
            error_code=103,
            status=500,
            details={"message": message}
        )
