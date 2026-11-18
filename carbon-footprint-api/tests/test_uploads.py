"""Temporary uploads (/uploads)."""

import pytest
from fastapi.testclient import TestClient

from carbon_footprint_api.config import Settings
from carbon_footprint_api.main import create_app
from carbon_footprint_api.repository import InMemoryAssetRepository
from carbon_footprint_api.services import HiddenShellLeases, UploadError, UploadService
from carbon_footprint_api.services.uploads import clean_filename
from test_app import API, make_aasx


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def _client(repo=None, clock=None, **settings):
    repo = repo or InMemoryAssetRepository()
    config = Settings(**settings)
    app = create_app(config, repo)
    if clock is not None:
        app.state.upload_service = UploadService(
            repo,
            max_bytes=config.upload_max_bytes,
            ttl_seconds=config.upload_ttl_seconds,
            max_uploads=config.upload_max_count,
            clock=clock,
        )
    return TestClient(app), repo


def _upload(client, data, filename="test.aasx"):
    return client.post(
        f"{API}/uploads",
        params={"filename": filename},
        content=data,
        headers={"Content-Type": "application/octet-stream"},
    )


def test_limits_default_to_25_mb_and_3_hours():
    c, _ = _client()
    assert c.get(f"{API}/uploads").json() == {"enabled": True, "maxBytes": 25 * 1024 * 1024, "ttlSeconds": 3 * 3600}


def test_upload_get_and_delete():
    c, repo = _client()
    r = _upload(c, make_aasx("urn:upload"))
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "test.aasx"
    assert [s["id"] for s in body["shells"]] == ["urn:upload"]
    assert body["expiresAt"].endswith("Z")
    # hidden: reachable by id, but not listed among the pre-loaded shells
    assert repo.has_shell("urn:upload")
    assert "urn:upload" not in repo.available_shell_ids()
    assert c.get(f"{API}/uploads/{body['id']}").json()["shells"][0]["id"] == "urn:upload"
    assert c.delete(f"{API}/uploads/{body['id']}").status_code == 204
    assert not repo.has_shell("urn:upload")
    assert c.get(f"{API}/uploads/{body['id']}").status_code == 404
    assert c.delete(f"{API}/uploads/{body['id']}").status_code == 404


def test_upload_expires_after_ttl():
    clock = FakeClock()
    c, repo = _client(clock=clock, upload_ttl_hours=1)
    token = _upload(c, make_aasx("urn:temp")).json()["id"]
    clock.now += 3599
    assert c.get(f"{API}/uploads/{token}").status_code == 200
    clock.now += 2
    assert c.get(f"{API}/uploads/{token}").status_code == 404
    assert not repo.has_shell("urn:temp")


def test_upload_size_limit_and_invalid_content():
    c, _ = _client(upload_max_mb=0.001)
    assert _upload(c, b"x" * 2000).status_code == 413
    c, _ = _client()
    assert _upload(c, b"kein AAS", "x.aasx").status_code == 422
    assert _upload(c, b"", "x.aasx").status_code == 422


def test_uploads_can_be_disabled():
    c, _ = _client(uploads_enabled=False)
    assert c.get(f"{API}/uploads").json()["enabled"] is False
    assert _upload(c, make_aasx()).status_code == 403


@pytest.mark.parametrize("token", ["kurz", "../../etc/passwd", "a" * 65])
def test_invalid_tokens_are_rejected(token):
    c, _ = _client()
    assert c.get(f"{API}/uploads/{token}").status_code in (400, 404, 422)


def test_upload_never_replaces_existing_shells(tmp_path):
    path = tmp_path / "repo.aasx"
    path.write_bytes(make_aasx())
    repo = InMemoryAssetRepository()
    repo.load_files(aasx_files=[path])
    c, _ = _client(repo)
    token = _upload(c, make_aasx(id_short="BOESE")).json()["id"]
    assert repo.get_shell("urn:shell")["idShort"] == "S"
    c.delete(f"{API}/uploads/{token}")
    assert repo.has_shell("urn:shell")


def test_oldest_uploads_are_removed_beyond_limit():
    c, repo = _client(upload_max_count=2)
    for i in range(3):
        _upload(c, make_aasx(f"urn:up:{i}"))
    assert not repo.has_shell("urn:up:0")
    assert repo.has_shell("urn:up:1") and repo.has_shell("urn:up:2")


def test_shared_shell_stays_while_still_used():
    repo = InMemoryAssetRepository()
    leases = HiddenShellLeases(repo)
    service = UploadService(repo, max_bytes=10**6, ttl_seconds=60, max_uploads=5, leases=leases)
    first, _ = service.add(make_aasx("urn:same"), "a.aasx")
    second, _ = service.add(make_aasx("urn:same"), "b.aasx")
    service.remove(first.token)
    assert repo.has_shell("urn:same")
    service.remove(second.token)
    assert not repo.has_shell("urn:same")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, "upload"), ("C:\\Users\\x\\file.aasx", "file.aasx"), ("../../a.json", "a.json"), ("a\nb.xml", "ab.xml")],
)
def test_clean_filename(raw, expected):
    assert clean_filename(raw) == expected


def test_uploads_are_stored_in_directory_and_deleted(tmp_path):
    directory = tmp_path / "uploads"
    directory.mkdir()
    # files of an earlier run are removed on startup, other files are kept
    (directory / ("a" * 24 + ".aasx")).write_bytes(b"old")
    (directory / "README.txt").write_text("keep")
    clock = FakeClock()
    repo = InMemoryAssetRepository()
    service = UploadService(repo, max_bytes=10**6, ttl_seconds=60, max_uploads=5, clock=clock, directory=directory)
    assert sorted(p.name for p in directory.iterdir()) == ["README.txt"]
    upload, _ = service.add(make_aasx("urn:disk"), "Datei.aasx")
    assert upload.path == directory / f"{upload.token}.aasx" and upload.path.exists()
    # attachments are read from the stored file
    assert repo.get_thumbnail("urn:disk") is not None
    clock.now += 61
    service.purge_expired()
    assert not upload.path.exists() and not repo.has_shell("urn:disk")
    assert sorted(p.name for p in directory.iterdir()) == ["README.txt"]


def test_invalid_upload_leaves_no_file(tmp_path):
    service = UploadService(
        InMemoryAssetRepository(), max_bytes=10**6, ttl_seconds=60, max_uploads=5, directory=tmp_path
    )
    with pytest.raises(UploadError):
        service.add(b"kein AAS", "x.aasx")
    assert list(tmp_path.iterdir()) == []


def test_unusable_directory_falls_back_to_memory(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    service = UploadService(
        InMemoryAssetRepository(), max_bytes=10**6, ttl_seconds=60, max_uploads=5, directory=blocker / "uploads"
    )
    assert service.directory is None
    upload, shells = service.add(make_aasx("urn:mem"), "x.aasx")
    assert upload.path is None and shells


def test_upload_dir_setting(tmp_path):
    c, _ = _client(upload_dir=tmp_path)
    token = _upload(c, make_aasx("urn:via-api")).json()["id"]
    assert (tmp_path / f"{token}.aasx").exists()
    c.delete(f"{API}/uploads/{token}")
    assert not (tmp_path / f"{token}.aasx").exists()
