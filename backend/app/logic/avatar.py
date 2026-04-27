"""Avatar image normalization: validate, resize, re-encode as WebP.

The output is bounded by both pixel dimensions and final byte size so an
attacker can't blow up the database with a single request.
"""

import hashlib
import io
import logging
from typing import Final

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Pre-decode upload size cap. Anything larger is rejected before we hand
# bytes to Pillow (defense against decompression bombs).
MAX_INPUT_BYTES: Final = 20 * 1024 * 1024  # 20 MB
MAX_DIM: Final = 256
MAX_OUTPUT_BYTES: Final = 64 * 1024  # 64 KB


class AvatarProcessingError(ValueError):
    """Raised when an avatar image is invalid or exceeds limits."""


def _encode_webp(img: Image.Image, quality: int) -> bytes:
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=quality, method=6)
    return out.getvalue()


def normalize_avatar(raw: bytes) -> tuple[bytes, str, str]:
    """Validate, orient, resize, and encode an image as WebP.

    Returns ``(data, content_type, etag)``.
    """
    if len(raw) == 0:
        raise AvatarProcessingError("Empty file")
    if len(raw) > MAX_INPUT_BYTES:
        raise AvatarProcessingError("Image exceeds 20 MB upload limit")

    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise AvatarProcessingError("File is not a valid image") from exc

    # verify() consumes the file; reopen for actual processing.
    try:
        with Image.open(io.BytesIO(raw)) as src:
            oriented = ImageOps.exif_transpose(src) or src
            if oriented.mode not in ("RGB", "RGBA"):
                oriented = oriented.convert("RGBA" if "A" in oriented.mode else "RGB")
            oriented.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
            data = _encode_webp(oriented, quality=80)
            if len(data) > MAX_OUTPUT_BYTES:
                data = _encode_webp(oriented, quality=60)
    except (UnidentifiedImageError, OSError) as exc:
        raise AvatarProcessingError("Failed to decode image") from exc

    if len(data) > MAX_OUTPUT_BYTES:
        raise AvatarProcessingError("Image too large after compression")

    etag = hashlib.sha256(data).hexdigest()
    return data, "image/webp", etag


async def fetch_remote_avatar(url: str) -> bytes | None:
    """Best-effort download of an external avatar URL.

    Returns ``None`` on any failure (network, non-200, oversize).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            content = response.content
            if len(content) > MAX_INPUT_BYTES:
                return None
            return content
    except (httpx.HTTPError, OSError):
        logger.debug("Failed to fetch remote avatar from %s", url, exc_info=True)
        return None
