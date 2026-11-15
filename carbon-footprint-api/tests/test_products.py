"""Fachliche Endpunkte unter /products."""

import base64

API = "/api/v4"


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _id(client, id_short: str) -> str:
    shells = client.get(f"{API}/asset/all").json()
    return next(i for i, s in shells.items() if s == id_short)


def test_supported_templates(client):
    data = client.get(f"{API}/products/submodel-templates").json()
    keys = {f["key"] for f in data["families"]}
    assert {"carbon-footprint", "nameplate", "hierarchical-structures"} <= keys
    cf = next(f for f in data["families"] if f["key"] == "carbon-footprint")
    assert cf["versions"] == ["0.9", "1.0"]
    assert "1/0/3" in cf["knownVersions"]


def test_carbon_footprint(client):
    r = client.get(f"{API}/products/{b64(_id(client, 'Fairphone-One'))}/carbon-footprint")
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["primaryMethod"] == "ISO 14044"
    assert data["summary"]["totalCo2eq"] > 0
    assert all(t["family"] == "carbon-footprint" for t in data["templates"])
    first = data["footprints"][0]
    assert {"kind", "templateVersion", "co2eq", "lifeCyclePhases", "goodsHandoverAddress"} <= set(first)


def test_templates_and_nameplate(client):
    shell = b64(_id(client, "AAS_DPDM-Q-10-30-PA_1"))
    templates = client.get(f"{API}/products/{shell}/templates").json()
    cf = next(t for t in templates if t["family"] == "carbon-footprint")
    assert (cf["version"], cf["variant"]) == ("1.0", "1.0-Entwurf")
    plate = client.get(f"{API}/products/{shell}/nameplate").json()
    assert plate["manufacturerName"] == "Festo SE & Co. KG"
    assert plate["address"]["cityTown"] == "Esslingen am Neckar"


def test_tree(client):
    tree = client.get(f"{API}/products/{b64(_id(client, 'Fairphone-One'))}/tree").json()
    assert tree["nodeCount"] == 14
    assert tree["root"]["carbonFootprint"]["summary"]["totalCo2eq"] > 0
    assert any(c["bulkCount"] == 6 for c in tree["root"]["children"])


def test_tree_by_global_asset_id(client):
    shell = client.get(f"{API}/shells/{b64(_id(client, 'Fairphone-One'))}").json()
    global_id = shell["assetInformation"]["globalAssetId"]
    assert client.get(f"{API}/products/{b64(global_id)}/tree").json()["nodeCount"] == 14


def test_unknown_shell(client):
    r = client.get(f"{API}/products/{b64('urn:unbekannt')}/carbon-footprint")
    assert r.status_code == 404
    assert client.get(f"{API}/products/%%%/tree").status_code in (400, 404)
