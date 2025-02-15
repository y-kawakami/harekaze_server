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
