import asyncio

from fastapi import APIRouter

router = APIRouter()


@router.get("/ping", status_code=200)
async def ping():
    """
    ヘルスチェック用のエンドポイント
    """
    return {}


@router.get("/async_sleep/{wait_time}")
async def async_wait_for(wait_time: int):
    await asyncio.sleep(wait_time)
    return {"Wait time(sec)": wait_time}
