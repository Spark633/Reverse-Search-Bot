from __future__ import annotations

import io

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 100_000_000


class InvalidImage(Exception):
    pass


def _to_jpeg(img: Image.Image, max_side: int | None = None, min_side: int | None = None) -> bytes:
    img = img.copy()
    if min_side:
        # kürzeste Seite auf min_side verkleinern (Fluffle empfiehlt 256px)
        w, h = img.size
        scale = min_side / min(w, h)
        if scale < 1:
            img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    if max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return out.getvalue()


def prepare(data: bytes) -> tuple[bytes, bytes]:
    """Gibt (großes JPEG für SauceNAO/IQDB/Upload, kleines JPEG für Fluffle) zurück."""
    try:
        img = Image.open(io.BytesIO(data))
        img.seek(0)  # bei GIF/WebP-Animationen erstes Frame
        img = ImageOps.exif_transpose(img)
    except Exception as exc:  # noqa: BLE001 - Pillow wirft diverse Typen
        raise InvalidImage(str(exc)) from exc

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.getchannel("A"))
        img = background
    else:
        img = img.convert("RGB")

    return _to_jpeg(img, max_side=2000), _to_jpeg(img, min_side=256, max_side=1024)
