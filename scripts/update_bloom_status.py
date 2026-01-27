#!/usr/bin/env python3
"""EntireTree の bloom_status 一括更新スクリプト

既存の EntireTree レコードに対して開花状態を計算し、bloom_status カラムを更新する。
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import cast

from loguru import logger
from sqlalchemy.orm import Query, Session, joinedload

# プロジェクトのルートディレクトリをPYTHONPATHに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.domain.models.models import EntireTree  # noqa: E402
from app.domain.services.bloom_state_service import (  # noqa: E402
    get_bloom_state_service,
)
from app.infrastructure.database.database import SessionLocal  # noqa: E402


@dataclass
class Args:
    """コマンドライン引数の型定義"""

    dry_run: bool
    batch_size: int


def format_progress(
    processed: int,
    total: int,
    updated: int,
    skipped: int,
    errors: int,
) -> str:
    """進捗表示をフォーマット (Req 3.2)

    Args:
        processed: 処理済み件数
        total: 総件数
        updated: 更新件数
        skipped: スキップ件数
        errors: エラー件数

    Returns:
        フォーマットされた進捗文字列
    """
    percentage = (processed / total * 100) if total > 0 else 0
    return (
        f"進捗: {processed}/{total} ({percentage:.1f}%) | "
        f"更新: {updated} | スキップ: {skipped} | エラー: {errors}"
    )


def create_batch_query(
    session: Session,
    offset: int,
    batch_size: int,
) -> Query[EntireTree]:
    """バッチクエリを作成 (Req 3.4)

    Args:
        session: データベースセッション
        offset: オフセット
        batch_size: バッチサイズ

    Returns:
        クエリオブジェクト
    """
    return (
        session.query(EntireTree)
        .options(joinedload(EntireTree.tree))
        .offset(offset)
        .limit(batch_size)
    )


def process_batch(
    records: Sequence[EntireTree],
    session: Session,
    dry_run: bool,
) -> dict[str, int]:
    """バッチ単位でレコードを処理 (Req 3.1, 3.5)

    Args:
        records: 処理対象のレコードリスト
        session: データベースセッション
        dry_run: ドライランモードかどうか

    Returns:
        処理統計（processed, updated, skipped, errors）
    """
    bloom_service = get_bloom_state_service()
    stats = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}

    for record in records:
        stats["processed"] += 1

        try:
            # 都道府県コードを Tree から取得
            prefecture_code = None
            if record.tree:
                prefecture_code = record.tree.prefecture_code

            # 撮影日を date 型に変換（photo_date は datetime 型）
            photo_date_only = record.photo_date.date()

            # bloom_status を計算
            bloom_status = bloom_service.calculate_bloom_status(
                photo_date=photo_date_only,
                latitude=record.latitude,
                longitude=record.longitude,
                prefecture_code=prefecture_code,
            )

            if bloom_status is None:
                stats["skipped"] += 1
                continue

            # 更新
            if not dry_run:
                record.bloom_status = bloom_status
            stats["updated"] += 1

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"ID {record.id} の処理中にエラー: {e}")

    # バッチ単位でコミット（ドライラン時はスキップ）
    if not dry_run and stats["updated"] > 0:
        session.commit()

    return stats


def get_total_count(session: Session) -> int:
    """総レコード数を取得

    Args:
        session: データベースセッション

    Returns:
        総レコード数
    """
    return session.query(EntireTree).count()


def parse_args() -> Args:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="EntireTree の bloom_status を一括更新するツール"
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際の更新を行わず、計算結果のみ表示する (Req 3.3)",
    )
    _ = parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="バッチサイズ（デフォルト: 1000）(Req 3.4)",
    )
    namespace = parser.parse_args()
    return Args(
        dry_run=cast(bool, namespace.dry_run),
        batch_size=cast(int, namespace.batch_size),
    )


def main() -> None:
    """メイン処理"""
    args = parse_args()

    if args.dry_run:
        print("=== ドライランモード（実際の更新は行われません）===")

    # セッション作成
    session = SessionLocal()

    try:
        # 総件数取得
        total_count = get_total_count(session)
        print(f"総レコード数: {total_count}")

        if total_count == 0:
            print("更新対象のレコードがありません。")
            return

        # 統計初期化
        total_stats = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}
        offset = 0

        # バッチ処理
        while offset < total_count:
            # バッチクエリ実行
            query = create_batch_query(session, offset, args.batch_size)
            records = query.all()

            if not records:
                break

            # バッチ処理
            batch_stats = process_batch(records, session, args.dry_run)

            # 統計を集計
            for key in total_stats:
                total_stats[key] += batch_stats[key]

            # 進捗表示 (Req 3.2)
            print(
                format_progress(
                    processed=total_stats["processed"],
                    total=total_count,
                    updated=total_stats["updated"],
                    skipped=total_stats["skipped"],
                    errors=total_stats["errors"],
                )
            )

            offset += args.batch_size

        # 最終結果
        print("\n=== 処理完了 ===")
        print(f"処理済み: {total_stats['processed']}")
        print(f"更新: {total_stats['updated']}")
        print(f"スキップ: {total_stats['skipped']}")
        print(f"エラー: {total_stats['errors']}")

        if args.dry_run:
            print("\n※ドライランモードのため、データベースは更新されていません。")

    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {e}")
        session.rollback()
        sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
