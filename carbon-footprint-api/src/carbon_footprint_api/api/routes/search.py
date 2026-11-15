"""Volltextsuche über Shells und Submodels."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ..deps import Repository

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    description="Full-text search (case-insensitive) in all shells and their submodels. Searches idShorts, values, "
    "multi-language texts and descriptions, not semantic IDs. Downloaded (external) shells are only searched if "
    "their id or globalAssetId is passed as `include`.",
)
def search(
    repo: Repository,
    q: Annotated[str, Query(min_length=1, max_length=200, description="Search text")],
    include: Annotated[list[str], Query(max_length=100, description="IDs of downloaded shells to search as well")] = [],  # noqa: B006 (FastAPI kopiert Standardwerte)
    max_matches: Annotated[int, Query(ge=1, le=20, description="Max. matches returned per shell")] = 3,
):
    hits = repo.search(q, include, max_matches=max_matches)
    return {
        "result": [
            {
                "id": hit.id,
                "globalAssetId": hit.global_asset_id,
                "idShort": hit.id_short,
                "total": hit.total,
                "matches": [{"submodel": m.submodel, "path": m.path, "text": m.text} for m in hit.matches],
            }
            for hit in hits
        ]
    }
