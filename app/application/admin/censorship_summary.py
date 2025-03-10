import calendar
from datetime import datetime, timedelta

from sqlalchemy import Date, and_, case, cast, func
from sqlalchemy.orm import Session

from app.domain.models.models import CensorshipStatus, Tree
from app.interfaces.schemas.admin import (CensorshipSummaryResponse,
                                          DailyCensorshipStat)


def get_censorship_summary(db: Session, month: str) -> CensorshipSummaryResponse:
    """
    検閲サマリーを取得する

    Args:
        db: DBセッション
        month: 対象月（YYYY-MM形式）

    Returns:
        CensorshipSummaryResponse: 検閲サマリーレスポンス
    """
    # 対象期間を計算
    try:
        year, month_num = map(int, month.split('-'))
        # 月の最初の日
        start_date = datetime(year, month_num, 1)
        # 月の最終日
        _, last_day = calendar.monthrange(year, month_num)
        end_date = datetime(year, month_num, last_day, 23, 59, 59)
    except (ValueError, IndexError):
        # 無効な月形式の場合は現在の月を使用
        now = datetime.now()
        year, month_num = now.year, now.month
        start_date = datetime(year, month_num, 1)
        _, last_day = calendar.monthrange(year, month_num)
        end_date = datetime(year, month_num, last_day, 23, 59, 59)
        month = f"{year}-{month_num:02d}"

    # SQLAlchemyで日付部分を抽出
    date_trunc = cast(Tree.created_at, Date)

    # 一度のクエリで全ての日付の統計を取得
    stats_query = db.query(
        date_trunc.label('date'),
        func.count(Tree.id).label('total_posts'),
        func.sum(case(
            (Tree.censorship_status == CensorshipStatus.APPROVED, 1),
            else_=0
        )).label('approved_count'),
        func.sum(case(
            (Tree.censorship_status == CensorshipStatus.REJECTED, 1),
            else_=0
        )).label('rejected_count'),
        func.sum(case(
            (Tree.censorship_status == CensorshipStatus.ESCALATED, 1),
            else_=0
        )).label('escalated_count'),
        func.sum(case(
            (Tree.censorship_status == CensorshipStatus.UNCENSORED, 1),
            else_=0
        )).label('uncensored_count')
    ).filter(
        and_(
            Tree.created_at >= start_date,
            Tree.created_at <= end_date
        )
    ).group_by(date_trunc).order_by(date_trunc).all()

    # 日付ごとの結果をマッピング
    date_stats_map = {
        stat.date.strftime('%Y-%m-%d'): {
            'total_posts': stat.total_posts,
            'approved_count': stat.approved_count or 0,
            'rejected_count': stat.rejected_count or 0,
            'escalated_count': stat.escalated_count or 0,
            'uncensored_count': stat.uncensored_count or 0
        } for stat in stats_query
    }

    # 各日の統計情報を格納するリスト
    daily_stats = []

    # 対象期間の各日について統計情報を作成
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')

        # その日のデータがあれば使用、なければ0で初期化
        stats = date_stats_map.get(date_str, {
            'total_posts': 0,
            'approved_count': 0,
            'rejected_count': 0,
            'escalated_count': 0,
            'uncensored_count': 0
        })

        # 日別統計情報を追加
        daily_stats.append(
            DailyCensorshipStat(
                date=date_str,
                total_posts=stats['total_posts'],
                approved_count=stats['approved_count'],
                rejected_count=stats['rejected_count'],
                escalated_count=stats['escalated_count'],
                uncensored_count=stats['uncensored_count']
            )
        )

        # 次の日へ
        current_date = current_date + timedelta(days=1)

    # レスポンスを作成して返す
    return CensorshipSummaryResponse(
        month=month,
        days=daily_stats
    )
