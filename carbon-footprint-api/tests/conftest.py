import tarfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from carbon_footprint_api.config import Settings
from carbon_footprint_api.main import create_app
from carbon_footprint_api.repository import InMemoryAssetRepository

TESTS = Path(__file__).parent
REPO = TESTS.parent.parent / "repo"
SNAPSHOT_ARCHIVE = TESTS / "snapshots.tar.gz"


def repo_files() -> list[Path]:
    return sorted(REPO.glob("*.aasx"))


@pytest.fixture(scope="session")
def repo_provider() -> InMemoryAssetRepository:
    if not repo_files():
        pytest.skip(f"Keine AASX-Dateien in {REPO}")
    provider = InMemoryAssetRepository()
    provider.load_files(aasx_files=repo_files())
    return provider


@pytest.fixture(scope="session")
def client(repo_provider) -> TestClient:
    with TestClient(create_app(Settings(), repo_provider)) as c:
        yield c


@pytest.fixture(scope="session")
def snapshot_dir(tmp_path_factory) -> Path:
    if not SNAPSHOT_ARCHIVE.exists():
        pytest.skip("Referenzdaten fehlen")
    target = tmp_path_factory.mktemp("snapshots")
    with tarfile.open(SNAPSHOT_ARCHIVE) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(target, filter="data")
        else:  # Python < 3.10.12
            tar.extractall(target)  # noqa: S202 - eigene, versionierte Referenzdaten
    return target / "snapshots"
