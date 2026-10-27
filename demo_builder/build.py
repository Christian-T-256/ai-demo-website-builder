"""High-level build orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from .copy_gate import enforce_copy_gate, report
from .media import prepare_media
from .render import render_business_site, render_prospect_page
from .share_card import generate_share_card
from .validation import validate_business, validate_prospect


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"top-level JSON value must be an object: {path}")
    return data


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_business(input_path: Path, output_dir: Path, *, demo_mode: bool = False) -> Path:
    business = validate_business(load_json(input_path), demo_mode=demo_mode)
    media_dir = output_dir / "media"
    photos = prepare_media(business["photos"], media_dir, input_path.parent)
    rendered = render_business_site(business, photos)
    gate_result = enforce_copy_gate(rendered)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(rendered, encoding="utf-8")
    generate_share_card(business, media_dir / "share-card.png")
    _write_json(output_dir / "listing.json", business)
    _write_json(output_dir / "copy-report.json", {**gate_result, **report(rendered)})
    return output_dir / "index.html"


def build_prospect(input_path: Path, output_dir: Path, *, demo_mode: bool = False) -> Path:
    prospect = validate_prospect(load_json(input_path), demo_mode=demo_mode)
    rendered = render_prospect_page(prospect)
    gate_result = enforce_copy_gate(rendered)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(rendered, encoding="utf-8")
    _write_json(output_dir / "prospect.json", prospect)
    _write_json(output_dir / "copy-report.json", {**gate_result, **report(rendered)})
    return output_dir / "index.html"
