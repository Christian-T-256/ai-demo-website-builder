"""Generate honest placeholder media for offline demo fixtures."""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


def _safe_name(label: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return f"{index:02d}-{slug or 'placeholder'}.svg"


def placeholder_svg(label: str, alt: str, color_start: str, color_end: str, index: int) -> str:
    safe_label = html.escape(label)
    safe_alt = html.escape(alt)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100" viewBox="0 0 1600 1100" role="img" aria-labelledby="title desc">
  <title id="title">{safe_label}</title>
  <desc id="desc">{safe_alt}. Fictional placeholder artwork.</desc>
  <rect width="1600" height="1100" fill="{color_start}"/>
  <path d="M0 880 L760 0 H1600 V360 L940 1100 H0 Z" fill="{color_end}" fill-opacity=".56"/>
  <circle cx="{260 + index * 125}" cy="{230 + index * 40}" r="260" fill="#ffffff" fill-opacity=".08"/>
  <circle cx="{1220 - index * 65}" cy="{820 - index * 55}" r="410" fill="#1d2c28" fill-opacity=".16"/>
  <path d="M-100 360 L520 -100 M160 700 L900 -100 M520 1100 L1500 -100 M980 1200 L1700 320" stroke="#ffffff" stroke-opacity=".1" stroke-width="24"/>
  <g transform="translate(110 840)">
    <rect width="620" height="112" rx="56" fill="#10201c" fill-opacity=".82"/>
    <text x="48" y="72" fill="#fff9ed" font-family="serif" font-size="46">{safe_label}</text>
  </g>
</svg>
'''


def generate_placeholders(photos: list[dict], media_dir: Path) -> list[dict]:
    media_dir.mkdir(parents=True, exist_ok=True)
    generated: list[dict] = []
    for index, photo in enumerate(photos, start=1):
        filename = _safe_name(photo["label"], index)
        destination = media_dir / filename
        destination.write_text(
            placeholder_svg(
                photo["label"],
                photo["alt"],
                photo["color_start"],
                photo["color_end"],
                index,
            ),
            encoding="utf-8",
        )
        generated.append({"src": f"media/{filename}", "alt": photo["alt"], "label": photo["label"]})
    return generated


def prepare_media(photos: list[dict], media_dir: Path, source_dir: Path) -> list[dict]:
    """Copy reviewed local photos or generate placeholders when no path is supplied."""
    media_dir.mkdir(parents=True, exist_ok=True)
    prepared: list[dict] = []
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
    for index, photo in enumerate(photos, start=1):
        if photo.get("path"):
            source = Path(photo["path"])
            if not source.is_absolute():
                source = source_dir / source
            source = source.resolve()
            if not source.is_file() or source.suffix.lower() not in allowed_suffixes:
                raise ValueError(f"photo path must point to a supported local image: {source}")
            filename = _safe_name(photo["label"], index).replace(".svg", source.suffix.lower())
            shutil.copy2(source, media_dir / filename)
        else:
            filename = _safe_name(photo["label"], index)
            (media_dir / filename).write_text(
                placeholder_svg(
                    photo["label"],
                    photo["alt"],
                    photo["color_start"],
                    photo["color_end"],
                    index,
                ),
                encoding="utf-8",
            )
        prepared.append({"src": f"media/{filename}", "alt": photo["alt"], "label": photo["label"]})
    return prepared
