"""Stellt sicher, dass Version und Changelog zusammenpassen (Version bei Änderungen erhöhen)."""

import re
from pathlib import Path

from carbon_footprint_api import API_PREFIX, __version__

README = Path(__file__).parent.parent / "README.md"


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_changelog_starts_with_current_version():
    text = README.read_text(encoding="utf-8")
    changelog = text.split("## Changelog", 1)[1]
    first = re.search(r"^### (\d+\.\d+\.\d+)", changelog, re.M)
    assert first, "README enthält keinen Changelog-Eintrag"
    assert first.group(1) == __version__, "Version erhöht, aber kein Changelog-Eintrag (tools/bump_version.py)"


def test_api_prefix_matches_major_version():
    assert f"/api/v{__version__.split('.')[0]}" == API_PREFIX


def test_compose_uses_current_version():
    compose = Path(__file__).parent.parent.parent / "docker-compose.yml"
    if not compose.exists():
        return
    text = compose.read_text(encoding="utf-8")
    assert f"image: dppviewer-api:{__version__}" in text, "docker-compose.yml: tools/bump_version.py verwenden"
    api_block = text.split("\n  api:\n", 1)[1].split("\n  ui:\n", 1)[0]
    assert f'VERSION: "{__version__}"' in api_block
