import pytest

from carbon_footprint_api.cli import parse_arguments


def test_defaults(monkeypatch):
    monkeypatch.delenv("CFA_AASX", raising=False)
    s = parse_arguments([])
    assert (s.port, s.host, s.cors_origins, s.aasx_files(), s.suppress_404) == (8080, "127.0.0.1", [], [], False)


def test_globs_and_comma_separated_aas(tmp_path):
    for name in ("a.aasx", "b.aasx", "c.xml", "d.json"):
        (tmp_path / name).write_bytes(b"")
    s = parse_arguments(
        [
            "--aasx",
            str(tmp_path / "*.aasx"),
            "--aas",
            f"{tmp_path / 'c.xml'},{tmp_path / 'd.json'}",
            "--port",
            "9000",
            "--cors",
            "http://localhost:5173",
        ]
    )
    assert [p.name for p in s.aasx_files()] == ["a.aasx", "b.aasx"]
    assert [p.name for p in s.aas_files()] == ["c.xml", "d.json"]
    assert s.port == 9000 and s.cors_origins == ["http://localhost:5173"]


def test_environment_variables(tmp_path, monkeypatch):
    (tmp_path / "a.aasx").write_bytes(b"")
    monkeypatch.setenv("CFA_AASX", str(tmp_path / "*.aasx"))
    monkeypatch.setenv("CFA_CORS_ORIGINS", "http://a.example, http://b.example")
    monkeypatch.setenv("CFA_HOST", "0.0.0.0")  # noqa: S104
    s = parse_arguments(["--port", "8081"])
    assert [p.name for p in s.aasx_files()] == ["a.aasx"]
    assert s.cors_origins == ["http://a.example", "http://b.example"]
    assert (s.host, s.port) == ("0.0.0.0", 8081)  # noqa: S104
    # Kommandozeile hat Vorrang
    assert parse_arguments(["--host", "127.0.0.1"]).host == "127.0.0.1"


def test_check_repos_not_empty(tmp_path):
    assert parse_arguments(["--aasx", str(tmp_path / "*.aasx")]).aasx_files() == []
    with pytest.raises(SystemExit):
        parse_arguments(["--aasx", str(tmp_path / "*.aasx"), "--checkReposNotEmpty"])


@pytest.mark.parametrize(
    "argv",
    [
        ["--notFoundResource", "/index.html"],
        ["--static", ".", "--suppress404"],
        ["--port", "70000"],
        ["--logLevel", "LAUT"],
    ],
)
def test_invalid_options(argv):
    with pytest.raises(SystemExit):
        parse_arguments(argv)
