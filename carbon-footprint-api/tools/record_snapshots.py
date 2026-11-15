"""Zeichnet die Antworten einer laufenden Carbon-Footprint-API als Referenz (Snapshot) auf.

Aufruf: python tools/record_snapshots.py <base_url> <ausgabe_ordner> [api_präfix]
Beispiel: python tools/record_snapshots.py http://localhost:8080 snapshots /api/v4
Die Ausgabe ist ein Ordner mit einer JSON-Datei pro Shell plus allgemeinen Dateien.
Binärantworten (Thumbnails, Attachments) werden als Status, Content-Type, Länge und SHA-256 gespeichert.
"""

import base64
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")


class Client:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def get(self, path: str):
        url = self.base + path
        try:
            with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - Werkzeug, Adresse vom Aufrufer
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type", ""), e.read()

    def record(self, path: str, binary: bool = False):
        status, ctype, body = self.get(path)
        entry = {"path": path, "status": status, "contentType": ctype.split(";")[0].strip()}
        if binary or not ctype.startswith("application/json"):
            entry["length"] = len(body)
            entry["sha256"] = hashlib.sha256(body).hexdigest()
        else:
            try:
                data = json.loads(body)
            except ValueError:
                data = body.decode("utf-8", "replace")
            if isinstance(data, dict):
                # Zeitstempel und Pfad in Fehlermeldungen sind nicht deterministisch
                data.pop("timestamp", None)
            entry["body"] = data
        return entry


def element_paths(elements, prefix=""):
    """Liefert (idShortPath, element) für alle Elemente rekursiv, wie AAS-Spezifikation (a.b[0].c)."""
    for idx, el in enumerate(elements or []):
        if prefix.endswith("]") or el.get("idShort") is None:
            path = f"{prefix}[{idx}]"
        else:
            path = f"{prefix}.{el['idShort']}" if prefix else el["idShort"]
        yield path, el
        children = el.get("value")
        if (
            isinstance(children, list)
            and children
            and isinstance(children[0], dict)
            and ("idShort" in children[0] or "valueType" in children[0] or "value" in children[0])
        ):
            if _is_list(el):
                for i, child in enumerate(children):
                    cpath = f"{path}[{i}]"
                    yield cpath, child
                    sub = child.get("value")
                    if isinstance(sub, list) and sub and isinstance(sub[0], dict) and "idShort" in sub[0]:
                        yield from element_paths(sub, cpath)
            else:
                yield from element_paths(children, path)
        for key in ("statements", "annotations"):
            if isinstance(el.get(key), list):
                yield from element_paths(el[key], path)


def _is_list(el):
    return "typeValueListElement" in el or "orderRelevant" in el


def main(base, out, prefix="/api/v4"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    c = Client(base + prefix)

    common = {
        "shell-descriptors": c.record("/shell-descriptors"),
        "asset-all": c.record("/asset/all"),
        "errors": [
            c.record("/shells/" + b64("gibt-es-nicht")),
            c.record("/shells/" + b64("gibt-es-nicht") + "/submodels/" + b64("x")),
            c.record("/shells/" + b64("gibt-es-nicht") + "/submodel-refs"),
            c.record("/shells/" + b64("gibt-es-nicht") + "/asset-information/thumbnail"),
            c.record("/gibt/es/nicht"),
        ],
    }
    (out / "_common.json").write_text(json.dumps(common, indent=1, ensure_ascii=False), "utf-8")

    descriptors = common["shell-descriptors"]["body"]["result"]
    for d in descriptors:
        rec = {"descriptor": d, "byId": {}, "byGlobalAssetId": {}}
        for key, ident in (("byId", d.get("id")), ("byGlobalAssetId", d.get("globalAssetId"))):
            if not ident:
                continue
            e = b64(ident)
            r = rec[key]
            r["shell"] = c.record(f"/shells/{e}")
            r["submodelRefs"] = c.record(f"/shells/{e}/submodel-refs")
            r["thumbnail"] = c.record(f"/shells/{e}/asset-information/thumbnail", binary=True)
            r["assetSubmodelAll"] = c.record("/asset/" + urllib.parse.quote(ident, safe="") + "/submodel/all")
            r["submodels"] = {}
            refs = r["submodelRefs"].get("body") or {}
            for ref in refs.get("result", []) if isinstance(refs, dict) else []:
                keys = ref.get("keys") or []
                if not keys:
                    continue
                smid = keys[-1]["value"]
                se = b64(smid)
                sm = c.record(f"/shells/{e}/submodels/{se}")
                entry = {"submodel": sm, "elements": {}, "attachments": {}}
                if key == "byGlobalAssetId":
                    raw_ident, raw_smid = urllib.parse.quote(ident, safe=""), urllib.parse.quote(smid, safe="")
                    entry["assetSubmodel"] = c.record(f"/asset/{raw_ident}/submodel/{raw_smid}")
                body = sm.get("body")
                if sm["status"] == 200 and isinstance(body, dict):
                    for path, el in element_paths(body.get("submodelElements")):
                        qp = urllib.parse.quote(path, safe="")
                        entry["elements"][path] = c.record(f"/shells/{e}/submodels/{se}/submodel-elements/{qp}")
                        if "contentType" in el and ("value" in el) and not isinstance(el.get("value"), list):
                            entry["attachments"][path] = c.record(
                                f"/shells/{e}/submodels/{se}/submodel-elements/{qp}/attachment", binary=True
                            )
                    entry["elements"]["__gibt_es_nicht__"] = c.record(
                        f"/shells/{e}/submodels/{se}/submodel-elements/gibt_es_nicht"
                    )
                r["submodels"][smid] = entry
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", d.get("idShort") or d.get("id"))[:80]
        (out / f"{name}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), "utf-8")
        print(name, sum(len(s["elements"]) for s in rec["byId"].get("submodels", {}).values()))


if __name__ == "__main__":
    main(*sys.argv[1:4])
