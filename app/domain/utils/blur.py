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
        blur_strength: float = 1.0
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
        blur_strength: float = 1.0
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


def apply_blur_to_regions(
    image: Image.Image,
    regions: List[List[int]],
    padding_ratio: float = 0.1,
    blur_strength: float = 1.0
) -> Image.Image:
    """
    画像内の指定された領域にぼかしを適用します

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
                    99, (x2_pad - x1_pad) // 4 * 2 + 1, (y2_pad - y1_pad) // 4 * 2 + 1)
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
