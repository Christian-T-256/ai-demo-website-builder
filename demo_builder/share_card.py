"""Generate a 1200 by 630 PNG share card without external services."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1200
HEIGHT = 630


def _font(size: int):
    return ImageFont.load_default(size=size)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int = 32):
    for size in range(start_size, min_size - 1, -2):
        font = _font(size)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
    return _font(min_size)


def generate_share_card(business: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (WIDTH, HEIGHT), "#17332c")
    draw = ImageDraw.Draw(image)

    draw.ellipse((750, -260, 1390, 380), fill="#cc6b4e")
    draw.ellipse((900, 260, 1400, 760), fill="#efb85f")
    draw.rectangle((0, 0, 34, HEIGHT), fill="#efb85f")
    for x in range(720, 1200, 52):
        draw.line((x, 0, x - 260, HEIGHT), fill="#ffffff18", width=3)

    eyebrow = f"{business['town'].upper()}  |  {business['category'].upper()}"
    draw.text((82, 72), eyebrow, fill="#f3c97d", font=_font(24))

    name_font = _fit_text(draw, business["name"], 760, 78)
    draw.text((78, 155), business["name"], fill="#fff9ed", font=name_font)

    tagline_font = _fit_text(draw, business["tagline"], 720, 34, 24)
    draw.text((82, 310), business["tagline"], fill="#d7e5df", font=tagline_font)

    badge = f"Rated {business['rating']:.1f} from {business['review_count']} fictional fixture reviews"
    badge_font = _font(23)
    badge_box = draw.textbbox((0, 0), badge, font=badge_font)
    badge_width = badge_box[2] - badge_box[0]
    draw.rounded_rectangle((78, 430, 126 + badge_width, 492), radius=30, fill="#fff9ed")
    draw.text((102, 445), badge, fill="#17332c", font=badge_font)

    draw.text((82, 550), "Offline demo generated from structured listing data", fill="#b7cbc3", font=_font(20))
    image.save(destination, format="PNG", optimize=True)
