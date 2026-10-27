"""Explicit opt-in deployment adapter."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


PROJECT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,98}[a-z0-9]$")


def deploy_vercel(site_dir: Path, project_name: str, *, confirmed: bool) -> str:
    if not confirmed:
        raise ValueError("deployment requires --confirm-deploy")
    if not (site_dir / "index.html").is_file():
        raise ValueError(f"no index.html found in {site_dir}")
    if not PROJECT_PATTERN.fullmatch(project_name):
        raise ValueError("project name must use lowercase letters, numbers, and internal hyphens")

    result = subprocess.run(
        ["npx", "vercel", "deploy", "--prod", "--yes", "--name", project_name],
        cwd=site_dir,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"deployment failed with exit code {result.returncode}: {result.stderr.strip()}")
    matches = re.findall(r"https://[a-z0-9.-]+", result.stdout + "\n" + result.stderr)
    if not matches:
        raise RuntimeError("deployment completed but no public URL was returned")
    return matches[-1]
