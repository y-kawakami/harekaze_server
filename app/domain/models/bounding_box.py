from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union


@dataclass
class BoundingBox:
    """
    バウンディングボックスを表すデータクラス

    座標は通常、画像サイズに対する相対値（0〜1）で表されるが、
    絶対座標（ピクセル単位）に変換することも可能
    """
    left: float  # 左端のX座標（0〜1）
    top: float   # 上端のY座標（0〜1）
    width: float  # 幅（0〜1）
    height: float  # 高さ（0〜1）
    confidence: float = 0.0  # 検出の信頼度（0〜100）

    # 絶対座標のキャッシュ
    _abs_coords: Optional[Dict[str, int]] = None

    @property
    def right(self) -> float:
        """右端のX座標（0〜1）"""
        return self.left + self.width

    @property
    def bottom(self) -> float:
        """下端のY座標（0〜1）"""
        return self.top + self.height

    @property
    def area(self) -> float:
        """バウンディングボックスの面積（相対値）"""
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        """バウンディングボックスの中心座標（相対値）"""
        return (self.left + self.width / 2, self.top + self.height / 2)

    @classmethod
    def from_dict(cls, bbox_dict: Dict[str, Any], confidence: float = 0.0) -> 'BoundingBox':
        """
        辞書からBoundingBoxオブジェクトを作成する

        Args:
            bbox_dict: バウンディングボックス情報を含む辞書
                       {left, top, width, height} または {Left, Top, Width, Height}
            confidence: 検出の信頼度（0〜100）

        Returns:
            BoundingBoxオブジェクト
        """
        # AWS Rekognitionの形式に対応（キーが大文字始まり）
        left = bbox_dict.get('left', bbox_dict.get('Left', 0))
        top = bbox_dict.get('top', bbox_dict.get('Top', 0))
        width = bbox_dict.get('width', bbox_dict.get('Width', 0))
        height = bbox_dict.get('height', bbox_dict.get('Height', 0))

        return cls(left=left, top=top, width=width, height=height, confidence=confidence)

    @classmethod
    def from_absolute(cls, left: int, top: int, width: int, height: int,
                      image_width: int, image_height: int, confidence: float = 0.0) -> 'BoundingBox':
        """
        絶対座標からBoundingBoxオブジェクトを作成する

        Args:
            left, top, width, height: ピクセル単位の座標
            image_width, image_height: 元画像のサイズ
            confidence: 検出の信頼度（0〜100）

        Returns:
            BoundingBoxオブジェクト
        """
        return cls(
            left=left / image_width,
            top=top / image_height,
            width=width / image_width,
            height=height / image_height,
            confidence=confidence
        )

    @classmethod
    def from_corners(cls, x1: Union[int, float], y1: Union[int, float],
                     x2: Union[int, float], y2: Union[int, float],
                     is_absolute: bool = False,
                     image_width: Optional[int] = None,
                     image_height: Optional[int] = None,
                     confidence: float = 0.0) -> 'BoundingBox':
        """
        左上と右下の座標からBoundingBoxオブジェクトを作成する

        Args:
            x1, y1: 左上の座標
            x2, y2: 右下の座標
            is_absolute: 絶対座標かどうか
            image_width, image_height: 絶対座標の場合に必要な元画像のサイズ
            confidence: 検出の信頼度（0〜100）

        Returns:
            BoundingBoxオブジェクト
        """
        if is_absolute:
            if not (image_width and image_height):
                raise ValueError("絶対座標の場合はimage_widthとimage_heightが必要です")
            return cls.from_absolute(
                left=x1, top=y1,
                width=x2 - x1, height=y2 - y1,
                image_width=image_width, image_height=image_height,
                confidence=confidence
            )
        else:
            return cls(
                left=x1, top=y1,
                width=x2 - x1, height=y2 - y1,
                confidence=confidence
            )

    def to_absolute(self, image_width: int, image_height: int) -> Dict[str, int]:
        """
        バウンディングボックスを絶対座標（ピクセル単位）に変換する

        Args:
            image_width: 元画像の幅
            image_height: 元画像の高さ

        Returns:
            絶対座標を含む辞書 {left, top, width, height, right, bottom}
        """
        # キャッシュがあれば利用
        cache_key = f"{image_width}x{image_height}"
        if self._abs_coords and cache_key in self._abs_coords:
            return self._abs_coords[cache_key]

        abs_left = int(self.left * image_width)
        abs_top = int(self.top * image_height)
        abs_width = int(self.width * image_width)
        abs_height = int(self.height * image_height)
        abs_right = abs_left + abs_width
        abs_bottom = abs_top + abs_height

        # 結果をキャッシュ
        if self._abs_coords is None:
            self._abs_coords = {}
        self._abs_coords[cache_key] = {
            'left': abs_left,
            'top': abs_top,
            'width': abs_width,
            'height': abs_height,
            'right': abs_right,
            'bottom': abs_bottom
        }

        return self._abs_coords[cache_key]

    def to_corners(self, image_width: Optional[int] = None, image_height: Optional[int] = None) -> Union[Tuple[float, float, float, float], Tuple[int, int, int, int]]:
        """
        バウンディングボックスを左上と右下の座標の形式に変換する

        Args:
            image_width: 元画像の幅（絶対座標に変換する場合に必要）
            image_height: 元画像の高さ（絶対座標に変換する場合に必要）

        Returns:
            相対座標または絶対座標の左上と右下の座標 (x1, y1, x2, y2)
        """
        if image_width is not None and image_height is not None:
            abs_coords = self.to_absolute(image_width, image_height)
            return (abs_coords['left'], abs_coords['top'], abs_coords['right'], abs_coords['bottom'])
        else:
            return (self.left, self.top, self.right, self.bottom)

    def to_dict(self) -> Dict[str, Any]:
        """
        バウンディングボックスを辞書形式に変換する

        Returns:
            バウンディングボックス情報を含む辞書
        """
        return {
            'left': self.left,
            'top': self.top,
            'width': self.width,
            'height': self.height,
            'right': self.right,
            'bottom': self.bottom,
            'confidence': self.confidence
        }

    def to_tuple(self, include_confidence: bool = True) -> Tuple:
        """
        バウンディングボックスをタプル形式に変換する

        Args:
            include_confidence: 信頼度を含めるかどうか

        Returns:
            バウンディングボックス情報を含むタプル
            (left, top, width, height[, confidence])
        """
        if include_confidence:
            return (self.left, self.top, self.width, self.height, self.confidence)
        return (self.left, self.top, self.width, self.height)

    def compute_iou(self, other: 'BoundingBox') -> float:
        """
        別のバウンディングボックスとのIoU（Intersection over Union）を計算する

        Args:
            other: 比較対象のバウンディングボックス

        Returns:
            IoUスコア（0〜1）
        """
        # 交差領域の座標を計算
        inter_left = max(self.left, other.left)
        inter_top = max(self.top, other.top)
        inter_right = min(self.right, other.right)
        inter_bottom = min(self.bottom, other.bottom)

        # 交差領域のサイズを計算
        inter_width = max(0, inter_right - inter_left)
        inter_height = max(0, inter_bottom - inter_top)
        intersection = inter_width * inter_height

        # 和集合のサイズを計算
        union = self.area + other.area - intersection

        # IoUを計算
        return intersection / union if union > 0 else 0.0

    def has_overlap(self, other: 'BoundingBox', threshold: float = 0.1) -> bool:
        """
        別のバウンディングボックスとの重なりを判定する

        Args:
            other: 比較対象のバウンディングボックス
            threshold: 重なりと判定するIoUのしきい値（デフォルト: 0.1）

        Returns:
            重なっている場合はTrue、そうでない場合はFalse
        """
        return self.compute_iou(other) >= threshold
