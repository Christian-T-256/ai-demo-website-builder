from pathlib import Path

import pytest

from demo_builder.deploy import deploy_vercel


def test_deploy_requires_confirmation(tmp_path: Path):
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    with pytest.raises(ValueError, match="confirm"):
        deploy_vercel(tmp_path, "sample-project", confirmed=False)


def test_deploy_rejects_unsafe_project_name(tmp_path: Path):
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    with pytest.raises(ValueError, match="project name"):
        deploy_vercel(tmp_path, "Sample Project; rm", confirmed=True)
