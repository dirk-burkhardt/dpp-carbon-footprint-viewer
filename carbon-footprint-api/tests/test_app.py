import base64
import io
import zipfile
from contextlib import contextmanager
from urllib.parse import quote

import httpx2
import pytest
from fastapi.testclient import TestClient

from carbon_footprint_api.config import Settings
from carbon_footprint_api.main import create_app
from carbon_footprint_api.repository import InMemoryAssetRepository
from carbon_footprint_api.services import ExternalShellService
from test_parser import XML

API = "/api/v4"


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def make_aasx(
    shell_id: str = "urn:shell",
    submodel_id: str = "urn:sm",
    extra_files: dict | None = None,
    id_short: str = "S",
    padding: int = 0,
) -> bytes:
    xml = XML.replace(b"urn:shell", shell_id.encode()).replace(b">urn:sm<", f">{submodel_id}<".encode())
    xml = xml.replace(b"<idShort>S</idShort>", f"<idShort>{id_short}</idShort>".encode())
    xml = xml.replace(b"</environment>", b" " * padding + b"</environment>")
    xml = xml.replace(
        b"<assetInformation><assetKind>Instance</assetKind></assetInformation>",
        b"<assetInformation><assetKind>Instance</assetKind><globalAssetId>urn:asset:"
        + shell_id.encode()
        + b"</globalAssetId>"
        b"<defaultThumbnail><path>/aasx/thumb.png</path><contentType>image/png</contentType></defaultThumbnail>"
        b"</assetInformation>",
    ).replace(
        b"</submodelElements>",
        b"<file><idShort>F</idShort><value>/aasx/doc.pdf</value><contentType></contentType></file>"
        b"<file><idShort>H</idShort><value>/aasx/evil.html</value><contentType>text/html</contentType></file>"
        b"</submodelElements>",
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        rel = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'
        zf.writestr(
            "_rels/.rels",
            rel.format(
                '<Relationship Type="http://admin-shell.io/aasx/relationships/aasx-origin" Target="/aasx/aasx-origin" '
                'Id="R1"/>'
            ),
        )
        zf.writestr("aasx/aasx-origin", "")
        zf.writestr(
            "aasx/_rels/aasx-origin.rels",
            rel.format(
                '<Relationship Type="http://admin-shell.io/aasx/relationships/aas-spec" Target="/aasx/env.aas.xml" '
                'Id="R2"/>'
            ),
        )
        zf.writestr("aasx/env.aas.xml", xml)
        zf.writestr("aasx/thumb.png", b"PNGDATA")
        zf.writestr("aasx/doc.pdf", b"%PDF-1.4")
        zf.writestr("aasx/evil.html", b"<script>alert(1)</script>")
        for name, content in (extra_files or {}).items():
            zf.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture
def aasx_file(tmp_path):
    path = tmp_path / "test.aasx"
    path.write_bytes(make_aasx())
    return path


@contextmanager
def build(aasx_file=None, **kwargs):
    settings = Settings(aasx=[str(aasx_file)] if aasx_file else [], **kwargs)
    with TestClient(create_app(settings)) as client:
        yield client


def test_endpoints(aasx_file):
    with build(aasx_file) as c:
        for ident in ("urn:shell", "urn:asset:urn:shell"):
            assert c.get(f"{API}/shells/{b64(ident)}").json()["idShort"] == "S"
            r = c.get(f"{API}/shells/{b64(ident)}/asset-information/thumbnail")
            assert (r.status_code, r.content, r.headers["content-type"]) == (200, b"PNGDATA", "image/png")
        assert c.get(f"{API}/asset/all").json() == {"urn:shell": "S"}
        assert c.get(f"{API}/asset/urn:asset:urn:shell/submodel/all").json() == ["urn:sm"]
        assert c.get(f"{API}/asset/urn:asset:urn:shell/submodel/urn:sm").json()["idShort"] == "SM"
        base = f"{API}/shells/{b64('urn:shell')}/submodels/{b64('urn:sm')}"
        assert c.get(f"{base}/submodel-elements/C.Inner").json()["value"] == "x"
        assert c.get(f"{base}/submodel-elements/C.Fehlt").content == b""
        r = c.get(f"{base}/submodel-elements/F/attachment")
        assert (r.status_code, r.content, r.headers["content-type"]) == (200, b"%PDF-1.4", "application/pdf")
        assert "content-disposition" not in r.headers
        assert c.get(f"{base}/submodel-elements/B/attachment").content == b"hallo"
        assert c.get(f"{base}/submodel-elements/P1/attachment").status_code == 404
        assert c.get(f"{API}/shells/nicht-base64!").status_code == 400
        assert len(c.get(f"{API}/shell-descriptors").json()["result"]) == 1
        assert c.get("/api/health").json()["shells"] == 1


def test_active_attachments_are_downloads(aasx_file):
    with build(aasx_file) as c:
        r = c.get(f"{API}/shells/{b64('urn:shell')}/submodels/{b64('urn:sm')}/submodel-elements/H/attachment")
        assert r.headers["content-disposition"] == "attachment"
        assert "sandbox" in r.headers["content-security-policy"]


def test_security_headers_and_errors(aasx_file):
    with build(aasx_file) as c:
        r = c.get("/irgendwas")
        assert (r.status_code, r.text) == (404, "Error 404 - Not Found")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "server" not in r.headers or "uvicorn" not in r.headers["server"].lower()
        assert c.get("/api/docs").status_code == 200
        assert c.get("/api/openapi.json").json()["info"]["title"] == "AAS(X) Carbon Footprint API"
    with build(aasx_file, docs_enabled=False) as c:
        assert c.get("/api/docs").status_code == 404


def test_static_and_spa_fallback(aasx_file, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>SPA</html>")
    (static / "app.js").write_text("console.log(1)")
    with build(aasx_file, static_dir=static, not_found_resource="/index.html", suppress_404=True) as c:
        assert c.get("/").text == "<html>SPA</html>"
        r = c.get("/app.js")
        assert r.text == "console.log(1)" and r.headers["content-type"].startswith("text/javascript")
        r = c.get("/shells/irgendwo")
        assert (r.status_code, r.text) == (200, "<html>SPA</html>")
        assert c.get("/%2e%2e/%2e%2e/etc/passwd").text == "<html>SPA</html>"
        assert c.get(f"{API}/shells/{b64('urn:shell')}").json()["idShort"] == "S"
    with build(aasx_file, static_dir=static, not_found_resource="/index.html") as c:
        assert c.get("/fehlt").status_code == 404


def test_cors_only_for_api(aasx_file):
    with build(aasx_file, cors_origins=["http://localhost:5173"]) as c:
        headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
        r = c.options(f"{API}/asset/all", headers=headers)
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-credentials" not in r.headers
        r = c.get("/api/docs", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in r.headers
        r = c.options(f"{API}/asset/all", headers={**headers, "Origin": "http://evil.example"})
        assert "access-control-allow-origin" not in r.headers


def test_standard_base64_from_btoa(tmp_path):
    """Das Frontend codiert mit btoa: "+" und "/" (als %2F) müssen funktionieren."""
    shell_id, submodel_id = "urn:???", "urn:sm>>>"
    assert "/" in base64.b64encode(shell_id.encode()).decode()
    assert "+" in base64.b64encode(submodel_id.encode()).decode()
    path = tmp_path / "ids.aasx"
    path.write_bytes(make_aasx(shell_id, submodel_id.replace(">", "&gt;")))

    def std(s: str) -> str:
        return quote(base64.b64encode(s.encode()).decode(), safe="")

    with build(path) as c:
        assert c.get(f"{API}/shells/{std(shell_id)}").json()["id"] == shell_id
        assert c.get(f"{API}/shells/{std(shell_id)}/submodels/{std(submodel_id)}").json()["id"] == submodel_id
        r = c.get(f"{API}/shells/{std(shell_id)}/submodels/{std(submodel_id)}/submodel-elements/C.Inner")
        assert r.json()["value"] == "x"
        assert c.get(f"{API}/shells/{b64(shell_id)}").json()["id"] == shell_id


def test_damaged_and_oversized_aasx_are_skipped(tmp_path, aasx_file):
    broken = tmp_path / "kaputt.aasx"
    data = bytearray(aasx_file.read_bytes())
    data[100:400] = b"x" * 300
    broken.write_bytes(bytes(data))
    big = tmp_path / "gross.aasx"
    big.write_bytes(make_aasx("urn:big", padding=5000))
    repo = InMemoryAssetRepository(max_entry_bytes=4000)
    repo.load_files(aasx_files=[broken, big, aasx_file])  # darf nicht abbrechen
    assert repo.has_shell("urn:shell") and not repo.has_shell("urn:big")


# ----------------------------------------------------------------------------------------------------------------
# /external-shells
# ----------------------------------------------------------------------------------------------------------------


def _external_client(handler, addresses=("93.184.215.14",), **settings):
    repo = InMemoryAssetRepository()
    repo.load_files(aasx_files=[])
    app = create_app(Settings(**settings), repo)

    async def resolver(host, port):
        return list(addresses)

    app.state.external_service = ExternalShellService(
        repo,
        max_bytes=settings.get("external_max_bytes", 1_000_000),
        timeout_seconds=5,
        max_cached=settings.get("external_max_cached", 10),
        transport=httpx2.MockTransport(handler),
        resolver=resolver,
    )
    return TestClient(app), repo


def test_external_shells_load_and_cache():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx2.Response(200, content=make_aasx())

    c, _ = _external_client(handler)
    url = "https://example.com/datei.aasx"
    r = c.get(f"{API}/external-shells/{b64(url)}")
    assert r.status_code == 200 and [s["id"] for s in r.json()] == ["urn:shell"]
    c.get(f"{API}/external-shells/{b64(url)}")
    assert calls == [url]  # zweiter Aufruf aus dem Cache
    # versteckt: nicht in der Übersicht, aber direkt abrufbar
    assert c.get(f"{API}/asset/all").json() == {}
    assert c.get(f"{API}/shells/{b64('urn:shell')}/asset-information/thumbnail").content == b"PNGDATA"


@pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/passwd", "kein-url"])
def test_external_shells_rejects_schemes(url):
    c, _ = _external_client(lambda r: httpx2.Response(200, content=make_aasx()))
    assert c.get(f"{API}/external-shells/{b64(url)}").status_code == 422


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "192.168.1.1", "::1", "fd00::1"])
def test_external_shells_blocks_private_networks(address):
    c, _ = _external_client(lambda r: httpx2.Response(200, content=make_aasx()), addresses=[address])
    r = c.get(f"{API}/external-shells/{b64('http://intern.example/x.aasx')}")
    assert r.status_code == 422 and "öffentlich" in r.json()["message"]


def test_external_shells_checks_redirect_targets():
    def handler(request):
        return httpx2.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})

    repo = InMemoryAssetRepository()
    app = create_app(Settings(), repo)

    async def resolver(host, port):
        return ["169.254.169.254"] if host == "169.254.169.254" else ["93.184.215.14"]

    app.state.external_service = ExternalShellService(
        repo,
        max_bytes=1_000_000,
        timeout_seconds=5,
        max_cached=10,
        transport=httpx2.MockTransport(handler),
        resolver=resolver,
    )
    r = TestClient(app).get(f"{API}/external-shells/{b64('https://example.com/x.aasx')}")
    assert r.status_code == 422


def test_external_shells_size_limit_and_errors():
    c, _ = _external_client(lambda r: httpx2.Response(200, content=b"x" * 2000), external_max_bytes=1000)
    assert c.get(f"{API}/external-shells/{b64('https://example.com/a')}").status_code == 422
    c, _ = _external_client(lambda r: httpx2.Response(404))
    assert c.get(f"{API}/external-shells/{b64('https://example.com/b')}").status_code == 204
    c, _ = _external_client(lambda r: httpx2.Response(200, content=b"kein AAS"))
    assert c.get(f"{API}/external-shells/{b64('https://example.com/c')}").status_code == 422

    def failing(request):
        raise httpx2.ConnectError("nicht erreichbar")

    c, _ = _external_client(failing)
    assert c.get(f"{API}/external-shells/{b64('https://example.com/d')}").status_code == 502
    c, _ = _external_client(lambda r: httpx2.Response(200, content=make_aasx()), external_shells_enabled=False)
    assert c.get(f"{API}/external-shells/{b64('https://example.com/e')}").status_code == 403


def test_external_shells_never_replace_existing(aasx_file):
    evil = make_aasx(id_short="BOESE")
    repo = InMemoryAssetRepository()
    repo.load_files(aasx_files=[aasx_file])
    app = create_app(Settings(), repo)

    async def resolver(host, port):
        return ["93.184.215.14"]

    app.state.external_service = ExternalShellService(
        repo,
        max_bytes=1_000_000,
        timeout_seconds=5,
        max_cached=1,
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=evil)),
        resolver=resolver,
    )
    c = TestClient(app)
    r = c.get(f"{API}/external-shells/{b64('https://example.com/boese.aasx')}")
    assert r.status_code == 200 and r.json()[0]["idShort"] == "S"
    # Verdrängung aus dem Cache entfernt keine Shells aus dem Repository
    c.get(f"{API}/external-shells/{b64('https://example.com/anderes.aasx')}")
    assert repo.get_shell("urn:shell")["idShort"] == "S"


def test_external_cache_eviction_removes_hidden_shells():
    counter = iter(range(100))

    def handler(request):
        n = next(counter)
        return httpx2.Response(200, content=make_aasx(f"urn:extern:{n}"))

    c, repo = _external_client(handler, external_max_cached=2)
    for i in range(3):
        c.get(f"{API}/external-shells/{b64(f'https://example.com/{i}.aasx')}")
    assert not repo.has_shell("urn:extern:0")
    assert repo.has_shell("urn:extern:1") and repo.has_shell("urn:extern:2")
