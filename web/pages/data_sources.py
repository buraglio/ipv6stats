"""Data Sources: every source the site collects, how often, and how it's doing; plus the
hand-maintained reference files. Generated from the registry so it can't drift."""
import inspect
import re

from collect.registry import SOURCES, Source
from web import reference
from web.data import Data


def describe(src: Source) -> str:
    doc = inspect.getmodule(src.fetch).__doc__ or ""
    return re.sub(r"\s+", " ", doc.strip().split("\n\n")[0])


def context(data: Data) -> dict:
    rows = []
    for row in data.status_rows():
        src = SOURCES[row["key"]]
        rows.append({**row, "description": describe(src), "requires_env": src.requires_env})
    return {
        "sources": rows,
        "references": [
            {"file": "reference/cloud_providers.toml", "what": "Curated IPv6 support details for cloud providers",
             "last_reviewed": min(p["last_reviewed"] for p in reference.load_cloud_providers())},
            {"file": "reference/carriers.toml", "what": "Which access networks are shown",
             "last_reviewed": reference.load_carriers()["last_reviewed"]},
            {"file": "reference/government_domains.toml", "what": "Which government websites are checked",
             "last_reviewed": reference.load_government()["last_reviewed"]},
        ],
    }
