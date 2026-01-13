import re
import sys

import numpy as np


def analyze_process_times(file_path):
    """
    指定されたCSVファイルから処理時間を分析し、様々な統計情報を計算する

    Args:
        file_path: ログファイルのパス

    Returns:
        tuple: (統計情報の辞書, 処理時間のリスト) または (None, None)
    """
    process_times = []
    pattern = r"木の登録処理全体: (\d+\.\d+)ms"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    process_time = float(match.group(1))
                    process_times.append(process_time)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None, None

    if not process_times:
        print("処理時間が見つかりませんでした")
        return None, None

    # 統計情報を計算
    stats = {
        'count': len(process_times),
        'min': min(process_times),
        'max': max(process_times),
        'mean': np.mean(process_times),
        'median': np.median(process_times),
        'p75': np.percentile(process_times, 75),
        'p90': np.percentile(process_times, 90),
        'p95': np.percentile(process_times, 95),
        'p99': np.percentile(process_times, 99),
        'over_5s': sum(1 for t in process_times if t >= 5000),
        'over_10s': sum(1 for t in process_times if t >= 10000)
    }

    return stats, process_times


def count_long_processes(file_path, threshold_ms=5000):
    """
    指定されたCSVファイルから処理時間が閾値以上の行数をカウントする

    Args:
        file_path: ログファイルのパス
        threshold_ms: 閾値（ミリ秒）デフォルトは5000ms（5秒）

    Returns:
        int: 閾値以上の処理時間を持つ行数
    """
    count = 0
    pattern = r"木の登録処理全体: (\d+\.\d+)ms"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    process_time = float(match.group(1))
                    if process_time >= threshold_ms:
                        count += 1
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return -1

    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python count_long_processes.py <ログファイルのパス> [閾値(ミリ秒)]")
        sys.exit(1)

    file_path = sys.argv[1]

    # 詳細な統計情報を計算して表示
    stats, process_times = analyze_process_times(file_path)
    if stats:
        print("処理時間の分析結果:")
        print(f"データ数: {stats['count']}")
        print(f"最小値: {stats['min']:.2f}ms")
        print(f"最大値: {stats['max']:.2f}ms")
        print(f"平均値: {stats['mean']:.2f}ms")
        print(f"中央値(50%タイル): {stats['median']:.2f}ms")
        print(f"75%タイル: {stats['p75']:.2f}ms")
        print(f"90%タイル: {stats['p90']:.2f}ms")
        print(f"95%タイル: {stats['p95']:.2f}ms")
        print(f"99%タイル: {stats['p99']:.2f}ms")
        print(
            f"5秒以上の処理数: {stats['over_5s']} ({stats['over_5s'] / stats['count'] * 100:.2f}%)")
        print(
            f"10秒以上の処理数: {stats['over_10s']} ({stats['over_10s'] / stats['count'] * 100:.2f}%)")

    # 旧機能も維持（特定の閾値以上のカウント）
    if len(sys.argv) > 2:
        threshold_ms = int(float(sys.argv[2]))
        result = count_long_processes(file_path, threshold_ms)
        if result >= 0:
            print(f"\n{threshold_ms}ミリ秒以上の処理時間を持つ行数: {result}")
