from datetime import datetime
from typing import List, Optional

from fastapi import (APIRouter, Body, Depends, HTTPException, Path, Query,
                     status)
from sqlalchemy.orm import Session

from app.application.admin.tree_detail import get_tree_detail
from app.application.admin.tree_list import get_tree_list
from app.application.admin.update_censorship import update_censorship
from app.domain.models.models import Admin
from app.infrastructure.database.database import get_db
from app.interfaces.api.admin_auth import get_current_admin
from app.interfaces.schemas.admin import (CensorshipUpdateRequest,
                                          TreeCensorDetailResponse,
                                          TreeCensorListResponse)

router = APIRouter(
    prefix="",
    tags=["admin"]
)


@router.get("/trees", response_model=TreeCensorListResponse)
async def list_trees(
    begin_date: Optional[datetime] = Query(None, description="検索開始日時"),
    end_date: Optional[datetime] = Query(None, description="検索終了日時"),
    tree_censorship_status: List[int] = Query(
        None, description="全体の検閲ステータスリスト"),
    detail_censorship_status: List[int] = Query(
        None, description="詳細の検閲ステータスリスト"),
    page: int = Query(1, description="ページ番号", ge=1),
    per_page: int = Query(20, description="1ページあたりの件数", ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    投稿一覧を取得する（管理者用）
    """
    # 投稿一覧を取得
    total_count, items = get_tree_list(
        db=db,
        begin_date=begin_date,
        end_date=end_date,
        tree_censorship_status=tree_censorship_status,
        detail_censorship_status=detail_censorship_status,
        page=page,
        per_page=per_page
    )

    return {
        "total": total_count,
        "items": items
    }


@router.get("/trees/{tree_id}", response_model=TreeCensorDetailResponse)
async def get_tree_detail_api(
    tree_id: int = Path(..., description="投稿ID"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    投稿詳細を取得する（管理者用）
    """
    # 投稿詳細を取得
    tree_detail = get_tree_detail(db=db, tree_id=tree_id)

    if not tree_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された投稿が見つかりません"
        )

    return tree_detail


@router.put("/trees/{tree_id}", response_model=TreeCensorDetailResponse)
async def update_tree_censorship(
    tree_id: int = Path(..., description="投稿ID"),
    update_data: CensorshipUpdateRequest = Body(..., description="更新データ"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    投稿の検閲状態を更新する（管理者用）
    """
    # 検閲状態を更新
    updated_tree = update_censorship(
        db=db, tree_id=tree_id, update_data=update_data)

    if not updated_tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された投稿が見つかりません"
        )

    return updated_tree
