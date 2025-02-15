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
            error_response["details"] = exc.details

        return JSONResponse(
            status_code=exc.status,
            content=error_response
        )
