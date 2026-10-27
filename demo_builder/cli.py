"""Command line interface for builds, QA, and optional deploys."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build import build_business, build_prospect
from .copy_gate import CopyGateError
from .deploy import deploy_vercel
from .qa import run_qa


REPO_ROOT = Path(__file__).resolve().parent.parent


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m demo_builder",
        description="Build static local business demos and per-prospect landing pages.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="build fictional fixtures and run local browser QA")
    demo.add_argument("--output", default=str(REPO_ROOT / "out"))
    demo.add_argument("--skip-qa", action="store_true")

    business = sub.add_parser("build-business", help="build one local business website")
    business.add_argument("--input", required=True)
    business.add_argument("--output", required=True)
    business.add_argument("--demo-mode", action="store_true")

    prospect = sub.add_parser("build-prospect", help="build one per-prospect landing page")
    prospect.add_argument("--input", required=True)
    prospect.add_argument("--output", required=True)
    prospect.add_argument("--demo-mode", action="store_true")

    qa = sub.add_parser("qa", help="capture 390px and 1280px screenshots")
    qa.add_argument("--output-root", required=True)
    qa.add_argument("--sites", required=True, help="comma separated output folders")
    qa.add_argument("--qa-dir", required=True)

    deploy = sub.add_parser("deploy", help="deploy a built folder with the Vercel CLI")
    deploy.add_argument("--site-dir", required=True)
    deploy.add_argument("--project-name", required=True)
    deploy.add_argument("--confirm-deploy", action="store_true")
    return parser


def _run_demo(args) -> dict:
    output = _path(args.output)
    business_path = build_business(
        REPO_ROOT / "fixtures" / "fictional-business.json",
        output / "business",
        demo_mode=True,
    )
    prospect_path = build_prospect(
        REPO_ROOT / "fixtures" / "fictional-prospect.json",
        output / "prospect",
        demo_mode=True,
    )
    result = {"business": str(business_path), "prospect": str(prospect_path)}
    if not args.skip_qa:
        qa_report = run_qa(output, ["business", "prospect"], output / "qa")
        result["qa"] = qa_report["summary"]
    return result


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        if args.command == "demo":
            result = _run_demo(args)
        elif args.command == "build-business":
            result = {
                "business": str(
                    build_business(_path(args.input), _path(args.output), demo_mode=args.demo_mode)
                )
            }
        elif args.command == "build-prospect":
            result = {
                "prospect": str(
                    build_prospect(_path(args.input), _path(args.output), demo_mode=args.demo_mode)
                )
            }
        elif args.command == "qa":
            names = [item.strip() for item in args.sites.split(",") if item.strip()]
            result = run_qa(_path(args.output_root), names, _path(args.qa_dir))["summary"]
        else:
            result = {
                "url": deploy_vercel(
                    _path(args.site_dir),
                    args.project_name,
                    confirmed=args.confirm_deploy,
                )
            }
    except (CopyGateError, RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2))
