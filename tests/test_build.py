import json
from pathlib import Path

from PIL import Image

from demo_builder.build import build_business, build_prospect


ROOT = Path(__file__).resolve().parents[1]


def test_business_build_creates_static_site_and_share_card(tmp_path):
    destination = tmp_path / "business"
    result = build_business(ROOT / "fixtures" / "fictional-business.json", destination, demo_mode=True)

    html = result.read_text(encoding="utf-8")
    assert "Northwind Bakery" in html
    assert 'href="tel:+12125550148"' in html
    assert 'property="og:image"' in html
    assert "https://demo.example.com/business/media/share-card.png" in html
    assert 'type="application/ld+json"' in html
    assert "{{" not in html
    assert len(list((destination / "media").glob("*.svg"))) == 5

    with Image.open(destination / "media" / "share-card.png") as image:
        assert image.size == (1200, 630)

    copy_report = json.loads((destination / "copy-report.json").read_text())
    assert copy_report["status"] == "passed"


def test_prospect_build_creates_personalized_page(tmp_path):
    destination = tmp_path / "prospect"
    result = build_prospect(ROOT / "fixtures" / "fictional-prospect.json", destination, demo_mode=True)
    html = result.read_text(encoding="utf-8")
    assert "Jamie" in html
    assert "Northwind Dental" in html
    assert html.count('class="observation reveal"') == 3
    assert "{{" not in html


def test_real_build_copies_reviewed_local_photos(tmp_path):
    source_image = tmp_path / "reviewed-photo.png"
    Image.new("RGB", (32, 24), "#17332c").save(source_image)
    business = json.loads((ROOT / "fixtures" / "fictional-business.json").read_text())
    for photo in business["photos"]:
        photo.pop("color_start")
        photo.pop("color_end")
        photo["path"] = source_image.name
    input_path = tmp_path / "business.json"
    input_path.write_text(json.dumps(business), encoding="utf-8")

    destination = tmp_path / "real-build"
    build_business(input_path, destination)
    assert len(list((destination / "media").glob("*.png"))) == 6
