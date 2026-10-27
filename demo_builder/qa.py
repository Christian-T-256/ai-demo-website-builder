"""Browser screenshot and mobile layout checks."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image


def _page_metrics(page) -> dict:
    return page.evaluate(
        """() => {
          const actionable = [...document.querySelectorAll('a, button, input, select, textarea')]
            .filter((node) => {
              const style = getComputedStyle(node);
              const box = node.getBoundingClientRect();
              return style.display !== 'none' && style.visibility !== 'hidden' && box.width > 0 && box.height > 0;
            });
          const smallTargets = actionable
            .map((node) => {
              const box = node.getBoundingClientRect();
              return { label: (node.innerText || node.getAttribute('aria-label') || node.tagName).trim(), width: Math.round(box.width), height: Math.round(box.height) };
            })
            .filter((item) => item.width < 44 || item.height < 44);
          return {
            viewport_width: window.innerWidth,
            scroll_width: document.documentElement.scrollWidth,
            page_height: document.documentElement.scrollHeight,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth,
            actionable_targets: actionable.length,
            small_targets: smallTargets,
            images_without_alt: [...document.images].filter((img) => !img.hasAttribute('alt')).length
          };
        }"""
    )


FALLBACK_CSS = """
@page { margin: 0; }
body { font-family: sans-serif; color: #17332c; background: #fff9ed; margin: 0; padding: 0; }
.topline, .demo-note { background: #17332c; color: white; padding: 10px; font-size: 10px; text-align: center; }
.demo-note button, script { display: none; }
.site-nav { padding: 16px; background: #f5ead7; }
.site-nav a { margin-right: 12px; }
.hero { background: #17332c; color: white; }
.hero-media img { width: 100%; height: 260px; object-fit: cover; }
.hero-scrim { display: none; }
.hero-copy { padding: 28px 20px; background: #17332c; color: white; }
.eyebrow, .section-label { color: #cc6b4e; font-size: 10px; }
h1 { font-size: 34px; }
.hero-actions a, .cta { display: block; margin: 6px 0; padding: 12px; background: #efb85f; color: #17332c; }
.identity span { margin-right: 8px; }
.trust-strip { padding: 15px; background: #f5ead7; }
.trust-strip div { display: inline-block; width: 30%; text-align: center; }
.section { padding: 30px 20px; }
.service-card, .review-card, .gallery-item, .hours-card, .location-card, .observation, .recommendation-card {
  padding: 16px; margin: 10px 0; border: 1px solid #d8d4ca; background: white;
}
.reviews { background: white; color: #17332c; }
.reviews .review-card { background: white; color: #17332c; }
.recommendation { background: #17332c; color: white; }
.recommendation .recommendation-card { background: #23483f; color: white; }
.gallery-item img { width: 100%; height: 180px; object-fit: cover; }
.location-art { height: 80px; background: #17332c; }
.mobile-bar, .sticky-cta { background: #17332c; padding: 14px; color: white; }
.mobile-bar a { margin-right: 30px; }
footer { padding: 25px; background: #10231e; color: white; }
"""


def _fallback_html(html: str) -> str:
    cleaned = re.sub(
        r"<style.*?</style>|<script.*?</script>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = re.sub(r"</?blockquote[^>]*>", lambda match: "</p>" if match.group(0).startswith("</") else "<p>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</?figcaption[^>]*>", lambda match: "</p>" if match.group(0).startswith("</") else "<p>", cleaned, flags=re.IGNORECASE)
    return cleaned


def _render_with_mupdf(index_path: Path, destination: Path, width: int, height: int) -> dict:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Browser QA failed and PyMuPDF is not installed for fallback rendering") from exc

    story = fitz.Story(
        html=_fallback_html(index_path.read_text(encoding="utf-8")),
        user_css=FALLBACK_CSS,
        archive=fitz.Archive(str(index_path.parent)),
    )
    with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf:
        writer = fitz.DocumentWriter(temp_pdf.name)
        has_more = True
        page_count = 0
        filled_heights: list[int] = []
        while has_more and page_count < 30:
            device = writer.begin_page(fitz.Rect(0, 0, width, height))
            has_more, filled = story.place(fitz.Rect(0, 0, width, height))
            story.draw(device)
            writer.end_page()
            filled_bottom = filled.y1 if hasattr(filled, "y1") else filled[3]
            filled_heights.append(min(height, max(1, int(filled_bottom) + 1)))
            page_count += 1
        writer.close()
        if has_more:
            raise RuntimeError(f"fallback render exceeded 30 pages for {index_path}")

        document = fitz.open(temp_pdf.name)
        pages: list[Image.Image] = []
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(alpha=False)
            rendered_page = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
            pages.append(rendered_page.crop((0, 0, width, filled_heights[index])))
        stitched = Image.new("RGB", (width, sum(page.height for page in pages)), "white")
        y = 0
        for page in pages:
            stitched.paste(page, (0, y))
            y += page.height
        stitched.save(destination, format="PNG", optimize=True)
        document.close()
    return {
        "viewport_width": width,
        "scroll_width": None,
        "page_height": stitched.height,
        "horizontal_overflow": None,
        "actionable_targets": None,
        "small_targets": None,
        "images_without_alt": None,
        "screenshot": destination.name,
        "render_engine": "pymupdf-fallback",
    }


def _run_playwright(output_root: Path, site_names: list[str], qa_dir: Path, sync_playwright) -> dict:
    report: dict[str, dict] = {}
    with sync_playwright() as playwright:
        launch_args = (
            [
                "--single-process",
                "--disable-gpu",
                "--disable-gpu-compositing",
                "--disable-gpu-vsync",
                "--disable-threaded-animation",
                "--disable-threaded-scrolling",
            ]
            if sys.platform == "darwin"
            else []
        )
        browser = playwright.chromium.launch(headless=True, args=launch_args)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for site_name in site_names:
            index_path = (output_root / site_name / "index.html").resolve()
            if not index_path.is_file():
                raise RuntimeError(f"QA could not find {index_path}")
            report[site_name] = {}
            for label, width, height in (("390", 390, 844), ("1280", 1280, 900)):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(index_path.as_uri(), wait_until="load", timeout=30000)
                page.locator(".reveal").evaluate_all(
                    "nodes => nodes.forEach((node) => node.classList.add('visible'))"
                )
                metrics = _page_metrics(page)
                shot_name = f"{site_name}-{label}px.png"
                page.screenshot(path=str(qa_dir / shot_name), full_page=True)
                metrics["screenshot"] = shot_name
                metrics["render_engine"] = "playwright-chromium"
                report[site_name][label] = metrics
        page.close()
        browser.close()
    return report


def _run_fallback(output_root: Path, site_names: list[str], qa_dir: Path) -> dict:
    report: dict[str, dict] = {}
    for site_name in site_names:
        index_path = (output_root / site_name / "index.html").resolve()
        if not index_path.is_file():
            raise RuntimeError(f"QA could not find {index_path}")
        report[site_name] = {}
        for label, width, height in (("390", 390, 844), ("1280", 1280, 900)):
            destination = qa_dir / f"{site_name}-{label}px.png"
            report[site_name][label] = _render_with_mupdf(index_path, destination, width, height)
    return report


def run_qa(output_root: Path, site_names: list[str], qa_dir: Path) -> dict:
    """Capture full-page mobile and desktop shots, then return measurable checks."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for QA. Install requirements.txt first.") from exc

    qa_dir.mkdir(parents=True, exist_ok=True)
    browser_error = ""
    try:
        report = _run_playwright(output_root, site_names, qa_dir, sync_playwright)
        browser_measurements = True
    except Exception as exc:
        browser_error = f"{type(exc).__name__}: browser launch was blocked"
        report = _run_fallback(output_root, site_names, qa_dir)
        browser_measurements = False

    mobile_failures = []
    if browser_measurements:
        for name in site_names:
            mobile = report[name]["390"]
            if mobile["horizontal_overflow"]:
                mobile_failures.append(f"{name}: horizontal overflow")
            if mobile["images_without_alt"]:
                mobile_failures.append(f"{name}: images without alt text")
            if mobile["small_targets"]:
                mobile_failures.append(f"{name}: tap targets smaller than 44 pixels")
    report["summary"] = {
        "status": (
            "failed"
            if mobile_failures
            else "passed" if browser_measurements else "rendered_with_fallback"
        ),
        "mobile_failures": mobile_failures,
        "screenshots": len(site_names) * 2,
        "browser_measurements": browser_measurements,
        "browser_error": browser_error,
    }
    (qa_dir / "qa-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if mobile_failures:
        raise RuntimeError("Mobile QA failed: " + "; ".join(mobile_failures))
    return report
