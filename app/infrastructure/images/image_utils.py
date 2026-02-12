import io

from PIL import Image, ImageOps


def exif_transpose_bytes(
    image_bytes: bytes,
    output_format: str = "JPEG",
) -> bytes:
    """EXIF情報に基づいて画像を回転する。"""
    img = Image.open(io.BytesIO(image_bytes))
    rotated = ImageOps.exif_transpose(img)
    if rotated is None:
        return image_bytes
    buf = io.BytesIO()
    rotated.save(buf, format=output_format)
    return buf.getvalue()


def resize_image_bytes(
    image_bytes: bytes,
    max_long_edge: int,
    output_format: str = "JPEG",
) -> bytes:
    """長辺が max_long_edge を超える場合にリサイズする。

    アスペクト比を維持し LANCZOS リサンプリングで縮小する。
    既に収まっている場合は元のバイト列をそのまま返す。
    """
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    if width <= max_long_edge and height <= max_long_edge:
        return image_bytes
    if width > height:
        new_w = max_long_edge
        new_h = int(height * (max_long_edge / width))
    else:
        new_h = max_long_edge
        new_w = int(width * (max_long_edge / height))
    img = img.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS,
    )
    buf = io.BytesIO()
    img.save(buf, format=output_format)
    return buf.getvalue()
