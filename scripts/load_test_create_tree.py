"""create_tree API 負荷テストスクリプト

Usage:
    python scripts/load_test_create_tree.py --interval 5 --count 10
    python scripts/load_test_create_tree.py --interval 3  # 無限ループ (Ctrl+C で停止)
"""

import argparse
import random
import time
from collections import Counter
from pathlib import Path

import requests

# 主要都市の緯度経度（確実に住所解決できる地点）
LOCATIONS = [
    (35.6812, 139.7671),  # 東京駅
    (34.7024, 135.4959),  # 大阪駅
    (35.1709, 136.8815),  # 名古屋駅
    (43.0687, 141.3508),  # 札幌駅
    (33.5902, 130.4017),  # 博多駅
    (34.3853, 132.4553),  # 広島駅
    (38.2601, 140.8822),  # 仙台駅
    (36.5783, 139.8486),  # 宇都宮駅
    (35.0116, 135.7681),  # 京都駅
    (34.6638, 133.9179),  # 岡山駅
    (33.2490, 131.6088),  # 大分駅
    (35.9078, 139.6232),  # さいたま新都心駅
    (35.4437, 139.6380),  # 横浜駅
    (32.7503, 129.8779),  # 長崎駅
    (31.5838, 130.5417),  # 鹿児島中央駅
]

TEST_IMAGES_DIR = Path(__file__).parent / "test_images"


def get_random_image() -> Path:
    images = list(TEST_IMAGES_DIR.glob("*"))
    images = [p for p in images if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}]
    if not images:
        raise FileNotFoundError(f"No image files found in {TEST_IMAGES_DIR}")
    return random.choice(images)


def send_request(
    session: requests.Session, base_url: str
) -> tuple[int, float]:
    """リクエストを送信し、(ステータスコード, レスポンスタイム) を返す。"""
    url = f"{base_url}/api/tree/entire"
    image_path = get_random_image()

    base_lat, base_lng = random.choice(LOCATIONS)
    # 駅周辺 ±0.01度（約1km）の範囲でばらつかせる
    lat = base_lat + random.uniform(-0.01, 0.01)
    lng = base_lng + random.uniform(-0.01, 0.01)

    with open(image_path, "rb") as f:
        files = {"image": (image_path.name, f, "image/jpeg")}
        data = {
            "latitude": str(lat),
            "longitude": str(lng),
            "contributor": "load_test_user",
            "is_approved_debug": "true",
        }

        start = time.time()
        resp = session.post(url, files=files, data=data)
        elapsed = time.time() - start

    # レスポンス概要
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:200]

    print(
        f"[{resp.status_code}] {elapsed:.2f}s "
        f"lat={lat:.4f} lng={lng:.4f} "
        f"image={image_path.name} "
        f"response={body}"
    )

    return resp.status_code, elapsed


def print_summary(
    status_counts: Counter[int], times: list[float]
) -> None:
    """集計結果を表示する。"""
    total = len(times)
    if total == 0:
        print("\nNo requests sent.")
        return

    times_sorted = sorted(times)
    avg = sum(times) / total
    p50 = times_sorted[int(total * 0.5)]
    p95 = times_sorted[min(int(total * 0.95), total - 1)]
    p99 = times_sorted[min(int(total * 0.99), total - 1)]

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Total requests : {total}")
    print(f"Status codes   : ", end="")
    print(
        ", ".join(
            f"{code}={cnt}" for code, cnt in sorted(status_counts.items())
        )
    )
    print(f"Min            : {times_sorted[0]:.2f}s")
    print(f"Max            : {times_sorted[-1]:.2f}s")
    print(f"Avg            : {avg:.2f}s")
    print(f"Median (p50)   : {p50:.2f}s")
    print(f"p95            : {p95:.2f}s")
    print(f"p99            : {p99:.2f}s")
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="create_tree API 負荷テスト")
    parser.add_argument("--interval", type=float, default=5, help="リクエスト間隔（秒）")
    parser.add_argument("--count", type=int, default=None, help="リクエスト回数（省略時は無限）")
    parser.add_argument(
        "--base-url",
        default="https://dev.kb6rvv06ctr2.com/sakura_camera",
        help="ベースURL",
    )
    args = parser.parse_args()

    session = requests.Session()
    status_counts: Counter[int] = Counter()
    times: list[float] = []
    i = 0

    print(f"Target: {args.base_url}/api/tree/entire")
    print(f"Interval: {args.interval}s, Count: {args.count or 'infinite'}")
    print("---")

    try:
        while args.count is None or i < args.count:
            status, elapsed = send_request(session, args.base_url)
            status_counts[status] += 1
            times.append(elapsed)
            i += 1
            if args.count is None or i < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\nStopped after {i} requests.")

    print_summary(status_counts, times)


if __name__ == "__main__":
    main()
