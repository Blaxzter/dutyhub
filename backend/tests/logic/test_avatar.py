"""Unit tests for avatar normalization and remote avatar fetching.

Two rules shape this module:

* **Every fixture image is generated in-process with Pillow.** No binary blobs
  are committed to the repository, so the inputs are readable and tweakable.
* **No test touches the network.** ``fetch_remote_avatar`` is exercised through
  ``httpx.MockTransport`` wired into a real ``httpx.AsyncClient``, so the
  request/response plumbing is genuine while the socket layer is not.
"""

import hashlib
import io
import zlib
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from PIL import Image, ImageOps

from app.logic.avatar import (
    MAX_DIM,
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    AvatarProcessingError,
    fetch_remote_avatar,
    normalize_avatar,
)

MODULE = "app.logic.avatar"
AVATAR_URL = "https://cdn.example.test/avatar.png"

# Captured before any test patches ``httpx.AsyncClient`` so the mock-transport
# factory below can still build a real client without recursing into itself.
_REAL_ASYNC_CLIENT = httpx.AsyncClient

RED = (255, 0, 0)
BLUE = (0, 0, 255)
# WebP (and the JPEG sources) are lossy, so colours are compared as region
# averages with a generous per-channel margin instead of exactly.
COLOR_TOLERANCE = 40


def _encode(img: Image.Image, fmt: str = "PNG", **params: Any) -> bytes:
    """Serialise a Pillow image to bytes in the requested format."""
    buffer = io.BytesIO()
    img.save(buffer, format=fmt, **params)
    return buffer.getvalue()


def _solid_png(width: int, height: int, color: tuple[int, int, int] = RED) -> bytes:
    return _encode(Image.new("RGB", (width, height), color))


def _half_and_half(width: int = 40, height: int = 20) -> Image.Image:
    """A deliberately asymmetric image: left half red, right half blue.

    Asymmetric in both colour and aspect ratio so an EXIF rotation is visible
    in the geometry *and* in the pixels.
    """
    img = Image.new("RGB", (width, height), RED)
    img.paste(Image.new("RGB", (width // 2, height), BLUE), (width // 2, 0))
    return img


def _with_exif_orientation(img: Image.Image, orientation: int) -> bytes:
    """Save ``img`` as JPEG carrying the given EXIF orientation tag."""
    exif = img.getexif()
    exif[0x0112] = orientation  # ExifTags.Base.Orientation
    return _encode(img, "JPEG", quality=95, exif=exif)


def _png_with_corrupt_idat() -> bytes:
    """A PNG whose IDAT payload is garbage but whose CRC still matches.

    ``verify()`` only walks the chunk structure and checks CRCs, so it accepts
    this file; the actual inflate during decode then fails. This is a genuine
    byte sequence -- no mocking involved.
    """
    raw = bytearray(_solid_png(64, 64, (10, 200, 30)))
    pos = 8  # skip the PNG signature
    while pos + 8 <= len(raw):
        length = int.from_bytes(raw[pos : pos + 4], "big")
        chunk_type = bytes(raw[pos + 4 : pos + 8])
        start = pos + 8
        if chunk_type == b"IDAT":
            payload = bytearray(raw[start : start + length])
            # Keep the two-byte zlib header, scramble the deflate stream.
            for i in range(2, len(payload)):
                payload[i] ^= 0xFF
            raw[start : start + length] = payload
            crc = zlib.crc32(chunk_type + bytes(payload)) & 0xFFFFFFFF
            raw[start + length : start + length + 4] = crc.to_bytes(4, "big")
            return bytes(raw)
        pos = start + length + 4
    raise AssertionError("generated PNG contained no IDAT chunk")


def _open_webp(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def _average_rgb(
    img: Image.Image, box: tuple[int, int, int, int]
) -> tuple[int, int, int]:
    """Mean colour of a rectangular region, as an (r, g, b) tuple."""
    rgb = img.convert("RGB")
    left, top, right, bottom = box
    totals = [0, 0, 0]
    count = 0
    for x in range(left, right):
        for y in range(top, bottom):
            pixel = rgb.getpixel((x, y))
            assert isinstance(pixel, tuple)
            for channel in range(3):
                totals[channel] += int(pixel[channel])
            count += 1
    assert count > 0
    return (totals[0] // count, totals[1] // count, totals[2] // count)


def _assert_color(actual: tuple[int, int, int], expected: tuple[int, int, int]) -> None:
    for got, want in zip(actual, expected, strict=True):
        assert abs(got - want) < COLOR_TOLERANCE, f"{actual} is not close to {expected}"


def _mock_client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
    recorded_kwargs: list[dict[str, Any]] | None = None,
) -> Callable[..., httpx.AsyncClient]:
    """Build a drop-in replacement for ``httpx.AsyncClient`` backed by a mock.

    The returned client is a real ``AsyncClient`` (so timeouts, redirects and
    the async context manager behave normally) whose transport answers from
    ``handler`` instead of a socket.
    """

    def factory(**kwargs: Any) -> httpx.AsyncClient:
        if recorded_kwargs is not None:
            recorded_kwargs.append(kwargs)
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    return factory


class TestNormalizeAvatarRejections:
    """Every AvatarProcessingError branch of normalize_avatar."""

    def test_empty_input_is_rejected(self) -> None:
        """Zero bytes never reach Pillow."""
        with pytest.raises(AvatarProcessingError, match="Empty file"):
            normalize_avatar(b"")

    def test_oversize_input_is_rejected_before_pillow_is_invoked(self) -> None:
        """The size cap is a pre-decode guard, not a post-decode one.

        A decompression bomb must be refused before Pillow ever sees it, so the
        test asserts ``Image.open`` was never called.
        """
        payload = b"\xff" * (MAX_INPUT_BYTES + 1)

        with patch(f"{MODULE}.Image.open", new=MagicMock()) as mock_open:
            with pytest.raises(AvatarProcessingError, match="20 MB upload limit"):
                normalize_avatar(payload)

        mock_open.assert_not_called()

    def test_input_exactly_at_the_limit_is_not_rejected_for_size(self) -> None:
        """The cap is exclusive: MAX_INPUT_BYTES itself is still decoded."""
        payload = b"\xff" * MAX_INPUT_BYTES

        with pytest.raises(AvatarProcessingError) as exc_info:
            normalize_avatar(payload)

        # Rejected as a non-image, not for its size.
        assert "not a valid image" in str(exc_info.value)

    def test_non_image_bytes_are_rejected(self) -> None:
        """Arbitrary bytes fail Pillow's format sniffing."""
        with pytest.raises(AvatarProcessingError, match="File is not a valid image"):
            normalize_avatar(b"not an image at all")

    def test_truncated_image_is_rejected(self) -> None:
        """A half-written upload fails at open/verify time."""
        truncated = _solid_png(64, 64)[:32]

        with pytest.raises(AvatarProcessingError, match="File is not a valid image"):
            normalize_avatar(truncated)

    def test_corrupt_pixel_data_that_passes_verify_fails_on_decode(self) -> None:
        """Structurally valid PNG, unusable pixel data -> decode error.

        Uses a real byte sequence (see ``_png_with_corrupt_idat``) rather than
        a patched ``Image.open``, so this exercises the genuine Pillow path.
        """
        corrupt = _png_with_corrupt_idat()

        # Precondition: verify() really does accept this file, otherwise the
        # test would be silently re-testing the branch above.
        with Image.open(io.BytesIO(corrupt)) as probe:
            probe.verify()

        with pytest.raises(AvatarProcessingError, match="Failed to decode image"):
            normalize_avatar(corrupt)

    def test_decode_failure_after_successful_verify_is_reported(self) -> None:
        """Belt-and-braces variant of the above with the second open patched."""
        raw = _solid_png(32, 32)
        real_open = Image.open

        calls: list[int] = []

        def flaky_open(*args: Any, **kwargs: Any) -> Image.Image:
            calls.append(1)
            if len(calls) == 1:
                return real_open(*args, **kwargs)
            raise OSError("broken data stream")

        with patch(f"{MODULE}.Image.open", side_effect=flaky_open):
            with pytest.raises(AvatarProcessingError, match="Failed to decode image"):
                normalize_avatar(raw)

        assert len(calls) == 2

    @patch(f"{MODULE}._encode_webp")
    def test_image_too_large_even_at_lowest_quality(
        self, mock_encode: MagicMock
    ) -> None:
        """When neither quality step fits the budget the upload is refused."""
        too_big = b"\x00" * (MAX_OUTPUT_BYTES + 1)
        mock_encode.side_effect = [too_big, too_big]

        with pytest.raises(
            AvatarProcessingError, match="Image too large after compression"
        ):
            normalize_avatar(_solid_png(64, 64))

        assert mock_encode.call_count == 2


class TestNormalizeAvatarSuccess:
    """Happy paths across input formats and colour modes."""

    def _assert_webp(self, data: bytes, content_type: str, etag: str) -> Image.Image:
        assert content_type == "image/webp"
        assert etag == hashlib.sha256(data).hexdigest()
        assert len(data) <= MAX_OUTPUT_BYTES
        img = _open_webp(data)
        assert img.format == "WEBP"
        return img

    def test_png_is_reencoded_as_webp(self) -> None:
        """A plain RGB PNG comes back as a real WebP with a sha256 etag."""
        data, content_type, etag = normalize_avatar(_solid_png(64, 64, (12, 34, 56)))

        img = self._assert_webp(data, content_type, etag)
        assert img.size == (64, 64)
        _assert_color(_average_rgb(img, (0, 0, 64, 64)), (12, 34, 56))

    def test_jpeg_is_reencoded_as_webp(self) -> None:
        """JPEG input is accepted and normalised to WebP."""
        source = _encode(Image.new("RGB", (48, 48), (200, 30, 90)), "JPEG", quality=95)

        data, content_type, etag = normalize_avatar(source)

        img = self._assert_webp(data, content_type, etag)
        assert img.size == (48, 48)

    def test_rgba_png_keeps_its_alpha_channel(self) -> None:
        """RGBA is already an accepted mode, so no conversion happens."""
        source = _encode(Image.new("RGBA", (32, 32), (255, 0, 0, 128)))

        data, content_type, etag = normalize_avatar(source)

        img = self._assert_webp(data, content_type, etag)
        assert img.mode == "RGBA"

    def test_palette_png_is_converted(self) -> None:
        """Mode "P" is outside the accepted set and is converted to RGB."""
        palette_img = Image.new("P", (32, 32))
        palette_img.putpalette([0, 0, 255] * 256)

        data, content_type, etag = normalize_avatar(_encode(palette_img))

        img = self._assert_webp(data, content_type, etag)
        assert img.mode == "RGB"

    def test_grayscale_png_is_converted(self) -> None:
        """Mode "L" has no alpha, so it becomes RGB."""
        data, content_type, etag = normalize_avatar(
            _encode(Image.new("L", (32, 32), 128))
        )

        img = self._assert_webp(data, content_type, etag)
        assert img.mode == "RGB"

    def test_grayscale_with_alpha_is_converted_to_rgba(self) -> None:
        """Mode "LA" carries alpha, so the RGBA branch of the conversion runs."""
        data, content_type, etag = normalize_avatar(
            _encode(Image.new("LA", (32, 32), (128, 200)))
        )

        img = self._assert_webp(data, content_type, etag)
        assert img.mode == "RGBA"

    def test_etag_is_stable_across_identical_calls(self) -> None:
        """The same input twice yields byte-identical output and etag."""
        source = _solid_png(70, 70, (9, 180, 240))

        first_data, _, first_etag = normalize_avatar(source)
        second_data, _, second_etag = normalize_avatar(source)

        assert first_data == second_data
        assert first_etag == second_etag
        assert first_etag == hashlib.sha256(first_data).hexdigest()

    def test_etag_differs_for_different_images(self) -> None:
        """Different pixels must not collide on the same cache key."""
        _, _, red_etag = normalize_avatar(_solid_png(64, 64, RED))
        _, _, blue_etag = normalize_avatar(_solid_png(64, 64, BLUE))

        assert red_etag != blue_etag

    def test_oversized_dimensions_are_thumbnailed(self) -> None:
        """A 1024x768 upload is scaled down, keeping its aspect ratio."""
        data, content_type, etag = normalize_avatar(_solid_png(1024, 768, (30, 60, 90)))

        img = self._assert_webp(data, content_type, etag)
        assert max(img.size) <= MAX_DIM
        assert img.size == (MAX_DIM, 192)  # 4:3 preserved

    def test_small_images_are_not_upscaled(self) -> None:
        """thumbnail() only shrinks; a tiny avatar stays tiny."""
        data, _, _ = normalize_avatar(_solid_png(16, 24))

        assert _open_webp(data).size == (16, 24)

    @patch(f"{MODULE}._encode_webp")
    def test_retries_at_lower_quality_when_first_encode_is_too_large(
        self, mock_encode: MagicMock
    ) -> None:
        """Quality 80 first; only if that overflows does quality 60 run."""
        small = b"a-small-webp-payload"
        mock_encode.side_effect = [b"\x00" * (MAX_OUTPUT_BYTES + 1), small]

        data, content_type, etag = normalize_avatar(_solid_png(64, 64))

        assert data == small
        assert content_type == "image/webp"
        assert etag == hashlib.sha256(small).hexdigest()
        assert mock_encode.call_count == 2
        qualities = [call.kwargs["quality"] for call in mock_encode.call_args_list]
        assert qualities == [80, 60]
        # Both attempts encode the same already-resized image.
        first_image = mock_encode.call_args_list[0].args[0]
        assert isinstance(first_image, Image.Image)
        assert mock_encode.call_args_list[1].args[0] is first_image

    @patch(f"{MODULE}._encode_webp")
    def test_no_retry_when_the_first_encode_fits(self, mock_encode: MagicMock) -> None:
        """The common case encodes exactly once, at quality 80."""
        mock_encode.return_value = b"tiny"

        normalize_avatar(_solid_png(64, 64))

        mock_encode.assert_called_once()
        assert mock_encode.call_args.kwargs["quality"] == 80


class TestNormalizeAvatarExifOrientation:
    """EXIF orientation must be baked into the pixels, not dropped."""

    def test_orientation_6_rotates_the_actual_pixels(self) -> None:
        """A 40x20 left-red/right-blue image becomes 20x40 top-red/bottom-blue.

        EXIF orientation 6 means "rotate 90 deg clockwise for display", which
        Pillow applies as ROTATE_270. The assertions below check the output
        pixels, not merely that no exception was raised.
        """
        source_img = _half_and_half(40, 20)
        source = _with_exif_orientation(source_img, orientation=6)

        data, _, _ = normalize_avatar(source)
        img = _open_webp(data)

        # Geometry: the axes swapped.
        assert img.size == (20, 40)

        # Pixels: the left half moved to the top, the right half to the bottom.
        _assert_color(_average_rgb(img, (2, 2, 18, 16)), RED)
        _assert_color(_average_rgb(img, (2, 24, 18, 38)), BLUE)

        # And it matches what Pillow's own transpose would have produced.
        with Image.open(io.BytesIO(source)) as reopened:
            expected = ImageOps.exif_transpose(reopened)
        assert expected is not None
        assert img.size == expected.size
        for box in ((2, 2, 18, 16), (2, 24, 18, 38)):
            _assert_color(_average_rgb(img, box), _average_rgb(expected, box))

    def test_orientation_3_flips_the_image_end_to_end(self) -> None:
        """Orientation 3 is a 180 deg rotation: red and blue trade places."""
        source = _with_exif_orientation(_half_and_half(40, 20), orientation=3)

        data, _, _ = normalize_avatar(source)
        img = _open_webp(data)

        assert img.size == (40, 20)  # 180 deg keeps the aspect ratio
        _assert_color(_average_rgb(img, (2, 2, 18, 18)), BLUE)
        _assert_color(_average_rgb(img, (22, 2, 38, 18)), RED)

    def test_image_without_exif_is_left_alone(self) -> None:
        """Control case: no orientation tag means no transposition."""
        source = _encode(_half_and_half(40, 20), "JPEG", quality=95)

        data, _, _ = normalize_avatar(source)
        img = _open_webp(data)

        assert img.size == (40, 20)
        _assert_color(_average_rgb(img, (2, 2, 18, 18)), RED)
        _assert_color(_average_rgb(img, (22, 2, 38, 18)), BLUE)


@pytest.mark.asyncio
class TestFetchRemoteAvatar:
    """Remote download helper. Never hits the network."""

    async def test_returns_body_on_200(self) -> None:
        """A successful response yields the raw bytes."""
        body = _solid_png(16, 16)
        requested: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested.append(str(request.url))
            return httpx.Response(200, content=body)

        recorded: list[dict[str, Any]] = []
        with patch(
            f"{MODULE}.httpx.AsyncClient",
            new=_mock_client_factory(handler, recorded),
        ):
            result = await fetch_remote_avatar(AVATAR_URL)

        assert result == body
        assert requested == [AVATAR_URL]
        # The client is configured defensively: bounded timeout, redirects on.
        assert recorded == [{"timeout": 10.0, "follow_redirects": True}]

    @pytest.mark.parametrize("status_code", [204, 301, 401, 404, 500])
    async def test_returns_none_on_non_200(self, status_code: int) -> None:
        """Anything other than 200 is treated as "no avatar"."""

        def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
            return httpx.Response(status_code, content=b"nope")

        with patch(f"{MODULE}.httpx.AsyncClient", new=_mock_client_factory(handler)):
            assert await fetch_remote_avatar(AVATAR_URL) is None

    async def test_returns_none_when_body_exceeds_the_input_limit(self) -> None:
        """An oversize body is dropped rather than handed to the normaliser."""
        oversize = b"\x00" * (MAX_INPUT_BYTES + 1)

        def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
            return httpx.Response(200, content=oversize)

        with patch(f"{MODULE}.httpx.AsyncClient", new=_mock_client_factory(handler)):
            assert await fetch_remote_avatar(AVATAR_URL) is None

    async def test_body_exactly_at_the_limit_is_accepted(self) -> None:
        """The size check is exclusive, mirroring normalize_avatar."""
        body = b"\x00" * MAX_INPUT_BYTES

        def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
            return httpx.Response(200, content=body)

        with patch(f"{MODULE}.httpx.AsyncClient", new=_mock_client_factory(handler)):
            result = await fetch_remote_avatar(AVATAR_URL)

        assert result is not None
        assert len(result) == MAX_INPUT_BYTES

    async def test_returns_none_on_connection_error(self) -> None:
        """Network failures are swallowed: seeding an avatar is best-effort."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with patch(f"{MODULE}.httpx.AsyncClient", new=_mock_client_factory(handler)):
            assert await fetch_remote_avatar(AVATAR_URL) is None

    async def test_returns_none_on_timeout(self) -> None:
        """Read timeouts are an httpx.HTTPError subclass and are handled too."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("too slow", request=request)

        with patch(f"{MODULE}.httpx.AsyncClient", new=_mock_client_factory(handler)):
            assert await fetch_remote_avatar(AVATAR_URL) is None

    async def test_returns_none_on_os_error(self) -> None:
        """A bare OSError from the transport is caught as well."""

        def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
            raise OSError("socket exploded")

        with patch(f"{MODULE}.httpx.AsyncClient", new=_mock_client_factory(handler)):
            assert await fetch_remote_avatar(AVATAR_URL) is None
