"""Image conversion using Pillow."""
from PIL import Image
from typing import List

# Mapping: file extension → Pillow format string
EXT_TO_PILLOW = {
    "jpg":  "JPEG",
    "jpeg": "JPEG",
    "png":  "PNG",
    "webp": "WEBP",
    "gif":  "GIF",
    "bmp":  "BMP",
    "tiff": "TIFF",
    "tif":  "TIFF",
    "ico":  "ICO",
}

ALL_IMAGE_EXTS = list(EXT_TO_PILLOW.keys())
# De-duplicated display names for targets
DISPLAY_TARGETS = ["jpg", "png", "webp", "gif", "bmp", "tiff", "ico"]


def get_image_targets(from_ext: str) -> List[str]:
    """Return valid output formats for a given input extension."""
    from_ext = from_ext.lower()
    if from_ext not in EXT_TO_PILLOW:
        return []
    # Exclude same format
    return [t for t in DISPLAY_TARGETS if t != from_ext and not (from_ext == "jpeg" and t == "jpg")]


def _prepare_for_jpeg(img: Image.Image) -> Image.Image:
    """Convert image mode to RGB, compositing alpha over white if needed."""
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "LA":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode == "P":
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def convert_image(input_path: str, output_path: str, output_format: str) -> None:
    """Convert an image file to the specified output format."""
    fmt = output_format.lower()
    pillow_fmt = EXT_TO_PILLOW.get(fmt)
    if not pillow_fmt:
        raise ValueError(f"지원하지 않는 이미지 포맷: {output_format}")

    img = Image.open(input_path)

    # ── Animated GIF passthrough / GIF save ───────────────────────────────────
    if fmt == "gif":
        frames = []
        try:
            while True:
                frame = img.copy()
                if frame.mode not in ("P", "RGBA"):
                    frame = frame.convert("P")
                frames.append(frame)
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        if not frames:
            frames = [img.convert("P")]
        frames[0].save(
            output_path, format="GIF",
            append_images=frames[1:], save_all=True, loop=0
        )
        return

    # ── ICO (multi-size) ──────────────────────────────────────────────────────
    if fmt == "ico":
        ico_img = img.convert("RGBA")
        sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        ico_img.save(output_path, format="ICO", sizes=sizes)
        return

    # ── JPEG / BMP need RGB ───────────────────────────────────────────────────
    if pillow_fmt in ("JPEG", "BMP"):
        img = _prepare_for_jpeg(img)
    elif fmt in ("png", "webp"):
        # Keep or convert to RGBA for transparency support
        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGBA")
    else:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    # ── Save ──────────────────────────────────────────────────────────────────
    save_kwargs = {}
    if pillow_fmt == "JPEG":
        save_kwargs["quality"] = 95
        save_kwargs["subsampling"] = 0
    elif pillow_fmt == "PNG":
        save_kwargs["optimize"] = True
    elif pillow_fmt == "WEBP":
        save_kwargs["quality"] = 90
        save_kwargs["method"] = 6

    img.save(output_path, format=pillow_fmt, **save_kwargs)
