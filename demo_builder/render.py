"""Render the local business site and per-prospect landing page."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote


TEMPLATE_DIR = Path(__file__).parent / "templates"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _render_template(name: str, values: dict[str, str]) -> str:
    output = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", value)
    return output


def _format_phone(raw: str) -> tuple[str, str]:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    tel = f"+1{digits}"
    display = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return tel, display


def _safe_json(data: dict) -> str:
    return (
        json.dumps(data, indent=2, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def render_business_site(business: dict, photos: list[dict]) -> str:
    tel, phone_display = _format_phone(business["phone"])
    page_url = business["public_url"].rstrip("/") + "/"
    image_url = page_url + "media/share-card.png"
    directions_url = "https://maps.apple.com/?daddr=" + quote(business["address"])

    services = "\n".join(
        f'''<article class="service-card reveal">
          <span class="service-number">{index:02d}</span>
          <h3>{_escape(item["name"])}</h3>
          <p>{_escape(item["description"])}</p>
        </article>'''
        for index, item in enumerate(business["services"], start=1)
    )
    reviews = "\n".join(
        f'''<figure class="review-card reveal">
          <blockquote>{_escape(item["quote"])}</blockquote>
          <figcaption>{_escape(item["author"])}, fictional fixture review</figcaption>
        </figure>'''
        for item in business["reviews"]
    )
    hours = "\n".join(
        f'<div><dt>{_escape(item["day"])}</dt><dd>{_escape(item["hours"])}</dd></div>'
        for item in business["hours"]
    )
    gallery = "\n".join(
        f'''<figure class="gallery-item reveal">
          <img src="{_escape(item["src"])}" alt="{_escape(item["alt"])}" loading="lazy" width="1600" height="1100">
          <figcaption>{_escape(item["label"])}</figcaption>
        </figure>'''
        for item in photos
    )
    hero = photos[0]
    schema = {
        "@context": "https://schema.org",
        "@type": "Bakery",
        "name": business["name"],
        "description": business["description"],
        "telephone": tel,
        "address": {"@type": "PostalAddress", "streetAddress": business["address"]},
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": business["rating"],
            "reviewCount": business["review_count"],
        },
        "url": page_url,
        "image": image_url,
    }

    values = {
        "NAME": _escape(business["name"]),
        "CATEGORY": _escape(business["category"]),
        "TOWN": _escape(business["town"]),
        "ADDRESS": _escape(business["address"]),
        "TAGLINE": _escape(business["tagline"]),
        "DESCRIPTION": _escape(business["description"]),
        "PHONE_TEL": _escape(tel),
        "PHONE_DISPLAY": _escape(phone_display),
        "RATING": f"{business['rating']:.1f}",
        "REVIEW_COUNT": str(business["review_count"]),
        "PAGE_URL": _escape(page_url),
        "IMAGE_URL": _escape(image_url),
        "DIRECTIONS_URL": _escape(directions_url),
        "HERO_SRC": _escape(hero["src"]),
        "HERO_ALT": _escape(hero["alt"]),
        "SERVICES": services,
        "REVIEWS": reviews,
        "HOURS": hours,
        "GALLERY": gallery,
        "SCHEMA": _safe_json(schema),
    }
    return _render_template("business.html", values)


def render_prospect_page(prospect: dict) -> str:
    observations = "\n".join(
        f'''<article class="observation reveal">
          <span>{index:02d}</span>
          <h2>{_escape(item["title"])}</h2>
          <p>{_escape(item["detail"])}</p>
        </article>'''
        for index, item in enumerate(prospect["observations"], start=1)
    )
    values = {
        "FIRST_NAME": _escape(prospect["first_name"]),
        "LAST_NAME": _escape(prospect["last_name"]),
        "COMPANY": _escape(prospect["company_name"]),
        "ROLE": _escape(prospect["role"]),
        "HEADLINE": _escape(prospect["headline"]),
        "SUBHEAD": _escape(prospect["subhead"]),
        "CONTEXT": _escape(prospect["context"]),
        "OBSERVATIONS": observations,
        "RECOMMENDATION_TITLE": _escape(prospect["recommendation_title"]),
        "RECOMMENDATION_BODY": _escape(prospect["recommendation_body"]),
        "CTA_LABEL": _escape(prospect["cta_label"]),
        "CTA_URL": _escape(prospect["cta_url"]),
    }
    return _render_template("prospect.html", values)
