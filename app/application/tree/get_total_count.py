from sqlalchemy.orm import Session

# from app.domain.models.models import CensorshipStatus
from app.infrastructure.repositories.tree_repository import TreeRepository


def get_total_count(db: Session) -> int:
    """
    承認済みの木の総数を取得する

    Args:
        db (Session): データベースセッション

    Returns:
        int: 承認済みの木の総数
    """
    tree_repository = TreeRepository(db)
    # return tree_repository.count_trees_by_status(CensorshipStatus.APPROVED)
    # TODO: 検閲済みの木の総数を取得する
    return tree_repository.count_trees_by_status()
