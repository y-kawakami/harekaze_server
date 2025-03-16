"""
画像の特定領域にぼかしを適用するユーティリティモジュール
"""
from typing import List, Union

import cv2
import numpy as np
from PIL import Image

from app.domain.models.bounding_box import BoundingBox


def calculate_iou(box1: List[Union[int, float]], box2: List[Union[int, float]]) -> float:
    """
    2つのバウンディングボックス間のIoU（Intersection over Union）を計算します

    Args:
        box1: 1つ目のバウンディングボックス [x1, y1, x2, y2]
        box2: 2つ目のバウンディングボックス [x1, y1, x2, y2]

    Returns:
        IoUの値（0.0～1.0）
    """
    # ボックスの座標を取得
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # 共通部分の座標を計算
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    # 共通部分の幅と高さを計算
    w_i = max(0, x2_i - x1_i)
    h_i = max(0, y2_i - y1_i)

    # 共通部分の面積を計算
    area_i = w_i * h_i

    # 各ボックスの面積を計算
    area_1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area_2 = (x2_2 - x1_2) * (y2_2 - y1_2)

    # 和集合の面積を計算
    area_u = area_1 + area_2 - area_i

    # IoUを計算（0で割ることを防ぐ）
    return area_i / area_u if area_u > 0 else 0.0


def has_overlap(box1: List[Union[int, float]], box2: List[Union[int, float]], threshold: float = 0.1) -> bool:
    """
    2つのバウンディングボックスが重なっているかをチェック

    Args:
        box1: 1つ目のバウンディングボックス [x1, y1, x2, y2]
        box2: 2つ目のバウンディングボックス [x1, y1, x2, y2]
        threshold: 重なりと判定するためのIOU閾値

    Returns:
        重なりがあればTrue、なければFalse
    """
    iou = calculate_iou(box1, box2)
    return iou > threshold


def apply_blur_to_bbox(
        image: Image.Image,
        bboxes: List[BoundingBox],
        padding_ratio: float = 0.1,
        blur_strength: float = 3.0
) -> Image.Image:
    bbox_coords = []
    for bbox in bboxes:
        img_width, img_height = image.size
        x1, y1, x2, y2 = bbox.to_corners(img_width, img_height)
        bbox_coords.append([x1, y1, x2, y2])
    return apply_blur_to_regions(image, bbox_coords, padding_ratio=padding_ratio, blur_strength=blur_strength)


def apply_blur_to_bbox_except(
        image: Image.Image,
        bboxes: List[BoundingBox],
        except_bboxes: List[BoundingBox],
        padding_ratio: float = 0.1,
        blur_strength: float = 3.0
) -> Image.Image:
    """
    except_bboxesと重ならないbboxesのみにぼかしをかけます

    Args:
        image: 元の画像（PIL形式）
        bboxes: ぼかしを適用する可能性のあるバウンディングボックスのリスト
        except_bboxes: ぼかしを適用しない（除外する）バウンディングボックスのリスト
        padding_ratio: ぼかし領域のパディング率（デフォルト: 0.1）
        blur_strength: ぼかしの強度（デフォルト: 1.0）

    Returns:
        ぼかしを適用した画像（PIL形式）
    """
    img_width, img_height = image.size

    # 除外するバウンディングボックスの座標を取得
    except_coords = []
    for bbox in except_bboxes:
        x1, y1, x2, y2 = bbox.to_corners(img_width, img_height)
        except_coords.append([x1, y1, x2, y2])

    # 除外対象と重ならないバウンディングボックスのみを選択
    filtered_bboxes = []
    for bbox in bboxes:
        x1, y1, x2, y2 = bbox.to_corners(img_width, img_height)
        bbox_coord = [x1, y1, x2, y2]

        # 除外対象と重なっているかチェック
        overlaps_with_except = False
        for except_coord in except_coords:
            if has_overlap(bbox_coord, except_coord):
                overlaps_with_except = True
                break

        # 重なっていなければリストに追加
        if not overlaps_with_except:
            filtered_bboxes.append(bbox)

    # 選択されたバウンディングボックスにぼかしを適用
    return apply_blur_to_bbox(image, filtered_bboxes, padding_ratio, blur_strength)


def apply_blur_to_regions_original(
    image: Image.Image,
    regions: List[List[int]],
    padding_ratio: float = 0.1,
    blur_strength: float = 1.0
) -> Image.Image:
    """
    画像内の指定された領域にぼかしを適用します（オリジナル実装版）

    新しい実装に問題がある場合、この関数を使用してください。

    Args:
        image: 元の画像（PIL形式）
        regions: ぼかしを適用する領域のリスト [[x1, y1, x2, y2], ...]
        padding_ratio: ぼかし領域のパディング率（デフォルト: 0.1）
        blur_strength: ぼかしの強度（デフォルト: 1.0）。値が大きいほどぼかしが強くなります。

    Returns:
        ぼかしを適用した画像（PIL形式）
    """
    # PIL画像をOpenCVのBGR画像に変換
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    height, width = cv_image.shape[:2]

    # ぼかしを適用
    blurred_image = cv_image.copy()

    for box in regions:
        x1, y1, x2, y2 = box

        # 境界チェック
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        if x2 > x1 and y2 > y1:  # 有効な領域のみ処理
            # 領域を少し広げてぼかしを適用（自然な見た目にするため）
            padding = int(min(x2 - x1, y2 - y1) * padding_ratio)
            x1_pad = max(0, x1 - padding)
            y1_pad = max(0, y1 - padding)
            x2_pad = min(width, x2 + padding)
            y2_pad = min(height, y2 + padding)

            region = blurred_image[y1_pad:y2_pad, x1_pad:x2_pad]
            if region.size > 0:  # 領域が空でないことを確認
                # ぼかしのカーネルサイズを領域のサイズと強度に応じて調整
                base_kernel_size = min(
                    1000, (x2_pad - x1_pad) // 4 * 2 + 1, (y2_pad - y1_pad) // 4 * 2 + 1)
                kernel_size = max(3, int(base_kernel_size * blur_strength))
                # 奇数になるように調整
                kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
                # シグマ値も強度に応じて調整
                sigma = blur_strength * 2
                blurred_region = cv2.GaussianBlur(
                    region, (kernel_size, kernel_size), sigma)
                blurred_image[y1_pad:y2_pad, x1_pad:x2_pad] = blurred_region

    # OpenCV画像をPIL画像に変換して返す
    return Image.fromarray(cv2.cvtColor(blurred_image, cv2.COLOR_BGR2RGB))


def apply_blur_to_regions(
    image: Image.Image,
    regions: List[List[int]],
    padding_ratio: float = 0.1,
    blur_strength: float = 1.0
) -> Image.Image:
    """
    画像内の指定された領域にぼかしを適用します（最適化版）

    Args:
        image: 元の画像（PIL形式）
        regions: ぼかしを適用する領域のリスト [[x1, y1, x2, y2], ...]
        padding_ratio: ぼかし領域のパディング率（デフォルト: 0.1）
        blur_strength: ぼかしの強度（デフォルト: 1.0）。値が大きいほどぼかしが強くなります。

    Returns:
        ぼかしを適用した画像（PIL形式）
    """
    # PIL画像をOpenCVのBGR画像に変換
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    height, width = cv_image.shape[:2]

    # マスク画像の作成（ぼかし領域を特定するため）
    mask = np.zeros((height, width), dtype=np.uint8)

    # 処理する領域のみのマスクを作成
    for box in regions:
        x1, y1, x2, y2 = box

        # 境界チェック
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        if x2 > x1 and y2 > y1:  # 有効な領域のみ処理
            # 領域を少し広げる（自然な見た目にするため）
            padding = int(min(x2 - x1, y2 - y1) * padding_ratio)
            x1_pad = max(0, x1 - padding)
            y1_pad = max(0, y1 - padding)
            x2_pad = min(width, x2 + padding)
            y2_pad = min(height, y2 + padding)

            # マスクに領域を追加
            mask[y1_pad:y2_pad, x1_pad:x2_pad] = 255

    # ぼかしを適用する大きさを判断
    total_area = np.sum(mask > 0)
    img_area = height * width
    area_ratio = total_area / img_area

    # 領域が一定以上大きい場合は効率的な方法を使用
    if area_ratio > 0.1:  # 全体の10%以上を占める場合
        # マルチスケールぼかしの適用（大きな領域に効率的）
        return _apply_multiscale_blur(cv_image, mask, blur_strength)
    else:
        # 小さい領域の場合は通常のぼかし
        return _apply_standard_blur(cv_image, mask, blur_strength)


def _apply_standard_blur(
    cv_image: np.ndarray,
    mask: np.ndarray,
    blur_strength: float
) -> Image.Image:
    """
    標準的なぼかし処理を適用します（小さな領域向け）
    """
    height, width = cv_image.shape[:2]
    blurred_image = cv_image.copy()

    # カーネルサイズの計算（ぼかしの強度に比例）
    kernel_size = max(3, int(30 * blur_strength))
    kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    sigma = blur_strength * 2

    # マスクされた領域のみをぼかす
    mask_indices = np.where(mask > 0)
    if len(mask_indices[0]) > 0:
        # 関連する領域の座標を取得
        y_min, y_max = np.min(mask_indices[0]), np.max(mask_indices[0])
        x_min, x_max = np.min(mask_indices[1]), np.max(mask_indices[1])

        # 領域を切り出してぼかす（全画像ではなく必要な部分だけ）
        region = blurred_image[y_min:y_max + 1, x_min:x_max + 1]
        region_mask = mask[y_min:y_max + 1, x_min:x_max + 1]

        # 領域全体をぼかす
        blurred_region = cv2.GaussianBlur(
            region, (kernel_size, kernel_size), sigma)

        # マスクに基づいて元の画像と合成
        blurred_region_masked = np.where(
            np.expand_dims(region_mask, -1) > 0,
            blurred_region,
            region
        )
        blurred_image[y_min:y_max + 1, x_min:x_max + 1] = blurred_region_masked

    # OpenCV画像をPIL画像に変換して返す
    return Image.fromarray(cv2.cvtColor(blurred_image, cv2.COLOR_BGR2RGB))


def _apply_multiscale_blur(
    cv_image: np.ndarray,
    mask: np.ndarray,
    blur_strength: float
) -> Image.Image:
    """
    マルチスケールぼかし処理を適用します（大きな領域向け）
    ピラミッド縮小→ぼかし→拡大の手法で効率化
    """
    height, width = cv_image.shape[:2]
    blurred_image = cv_image.copy()

    # ぼかし強度に基づいて縮小率を決定
    scale_factor = min(0.5, 1.0 / (blur_strength + 1.0))

    # 最小サイズを確保（極端に小さくならないように）
    min_size = 32
    scale_factor = max(scale_factor, min(min_size / width, min_size / height))

    # マスク領域の範囲を取得
    mask_indices = np.where(mask > 0)
    if len(mask_indices[0]) == 0:
        # マスクが空の場合は処理不要
        return Image.fromarray(cv2.cvtColor(blurred_image, cv2.COLOR_BGR2RGB))

    # マスク領域の境界を取得
    y_min, y_max = np.min(mask_indices[0]), np.max(mask_indices[0])
    x_min, x_max = np.min(mask_indices[1]), np.max(mask_indices[1])

    # 領域を少し広げる（ぼかしの境界を自然にするため）
    border = int(min(width, height) * 0.02)  # 2%のボーダー
    y_min = max(0, int(y_min - border))
    x_min = max(0, int(x_min - border))
    y_max = min(height - 1, int(y_max + border))
    x_max = min(width - 1, int(x_max + border))

    # 対象領域を切り出し
    region = blurred_image[y_min:y_max + 1, x_min:x_max + 1].copy()
    region_mask = mask[y_min:y_max + 1, x_min:x_max + 1].copy()

    # 新しいサイズを計算
    new_height = max(min_size, int((y_max - y_min + 1) * scale_factor))
    new_width = max(min_size, int((x_max - x_min + 1) * scale_factor))

    # 縮小
    small_region = cv2.resize(
        region, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    small_mask = cv2.resize(
        region_mask, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

    # 縮小画像にぼかしを適用
    kernel_size = max(3, int(15 * blur_strength))
    kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    sigma = blur_strength

    # 縮小されたサイズに合わせてカーネルサイズを調整
    kernel_size = min(kernel_size, new_width // 2 *
                      2 - 1, new_height // 2 * 2 - 1)
    kernel_size = max(3, kernel_size)

    # ぼかし適用
    blurred_small = cv2.GaussianBlur(
        small_region, (kernel_size, kernel_size), sigma)

    # 拡大して元のサイズに戻す
    blurred_region = cv2.resize(
        blurred_small, (x_max - x_min + 1, y_max - y_min + 1), interpolation=cv2.INTER_LINEAR)
    upscaled_mask = cv2.resize(
        small_mask, (x_max - x_min + 1, y_max - y_min + 1), interpolation=cv2.INTER_LINEAR)

    # マスクを正規化（縮小拡大でマスク値が変化するため）
    upscaled_mask = upscaled_mask / 255.0

    # マスクに基づいて元の画像と合成
    blended_region = np.zeros_like(region)
    for c in range(3):  # BGR各チャンネル
        blended_region[:, :, c] = region[:, :, c] * \
            (1 - upscaled_mask) + blurred_region[:, :, c] * upscaled_mask

    # 結果を元の画像に戻す
    blurred_image[y_min:y_max + 1, x_min:x_max + 1] = blended_region

    # OpenCV画像をPIL画像に変換して返す
    return Image.fromarray(cv2.cvtColor(blurred_image, cv2.COLOR_BGR2RGB))
