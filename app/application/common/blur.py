import logging
from typing import Any, Dict, List, Optional

from PIL import Image

from app.domain.utils import blur

logger = logging.getLogger(__name__)


def blur_persons_in_image(
    image: Image.Image,
    labels: Dict[str, List[Any]],
    image_service=None,
    padding_ratio: float = 0.1,
    blur_strength: float = 1.0
) -> tuple[Image.Image, Optional[bytes]]:
    """
    画像内の人物を検出し、必要に応じてぼかしを適用します。

    Args:
        image: ぼかしを適用する元のPIL画像
        labels: 物体検出結果の辞書（キーはラベル名、値はバウンディングボックスのリスト）
        image_service: 画像をバイトデータに変換するサービス（指定された場合のみバイトデータを返す）
        padding_ratio: ぼかし領域の余白比率
        blur_strength: ぼかしの強度

    Returns:
        (ぼかし処理後の画像, バイトデータ) のタプル。
        image_serviceが指定されていない場合、バイトデータはNoneになります。
    """
    logger.debug("人物検出とぼかし処理を開始")
    person_labels = labels.get('Person', [])

    if len(person_labels) == 0:
        logger.debug("人物は検出されませんでした")
        if image_service:
            return image, image_service.pil_to_bytes(image, 'jpeg')
        return image, None

    logger.debug(f"{len(person_labels)}人の人物が検出されたためぼかしを適用")
    blurred_image = blur.apply_blur_to_bbox(
        image, person_labels, padding_ratio, blur_strength)

    image_data = None
    if image_service:
        image_data = image_service.pil_to_bytes(blurred_image, 'jpeg')

    return blurred_image, image_data
