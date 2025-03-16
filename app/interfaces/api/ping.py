import asyncio

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/ping", status_code=200)
async def ping(request: Request):
    """
    ヘルスチェック用のエンドポイント
    リクエストのaccess_log属性をFalseに設定してログ出力を抑制します
    """
    # ログ抑制設定
    request.state.access_log = False
    return {}


@router.get("/async_sleep/{wait_time}")
async def async_wait_for(wait_time: int):
    await asyncio.sleep(wait_time)
    return {"Wait time(sec)": wait_time}
