import html

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.exceptions import ApplicationError


def register_error_handlers(app: FastAPI) -> None:
    """
    FastAPIアプリケーションにエラーハンドラを登録する。

    Args:
        app (FastAPI): FastAPIアプリケーションインスタンス
    """
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError
    ) -> JSONResponse:
        """
        アプリケーション層の例外をHTTPレスポンスに変換する。

        Args:
            request (Request): リクエストオブジェクト
            exc (ApplicationError): アプリケーション層の例外

        Returns:
            JSONResponse: エラーレスポンス
        """
        error_response = {
            "code": exc.error_code,
            "reason": exc.reason,
        }
        if exc.details:
            # HTML特殊文字をエスケープ
            if isinstance(exc.details, str):
                error_response["details"] = html.escape(exc.details)
            elif isinstance(exc.details, dict):
                # 辞書の場合は再帰的にエスケープ
                error_response["details"] = {k: html.escape(v) if isinstance(v, str) else v
                                             for k, v in exc.details.items()}
            else:
                error_response["details"] = exc.details

        return JSONResponse(
            status_code=exc.status,
            content=error_response
        )
