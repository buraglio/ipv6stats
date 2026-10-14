"""One page per economy: APNIC, 6lab, Vyncke and RIR numbers, history, networks; NIST for the US."""
from dataclasses import replace

from collect.sources.apnic_detail import TOP_ECONOMIES
from web import charts, derive
from web.data import Data, field

NIST_AGENCIES = 25
US = "US"


def _history(detail):
    if detail is None:
        return None
    points = detail.value["history"]
    return replace(detail, value=[
        {"name": "IPv6-capable", "points": [{"x": p["date"], "y": p["capable"]} for p in points]},
        {"name": "Prefers IPv6", "points": [{"x": p["date"], "y": p["preferred"]} for p in points]},
    ])


def context(data: Data, code: str) -> dict:
    row = derive.economy(data, code)
    detail = data.datum("apnic_economy_detail", lambda p: p["economies"].get(code))
    missing = data.datum("apnic_economy_detail", lambda p: code in p["missing"] or None)
    nist = derive.nist(data) if code == US else None
    nist_count = (lambda svc: None if nist is None
                  else replace(nist, value=nist.value["totals"][svc].get("operational", 0)))
    return {
        "page_title": row.value["name"] if row else code,
        "code": code,
        "economy": row,
        "capable": field(row, "capable"),
        "preferred": field(row, "preferred"),
        "samples": field(row, "samples"),
        "sixlab": derive.sixlab_for(data, code),
        "websites": derive.vyncke_for(data, code),
        "allocation": derive.country_allocation(data, code),
        "detail": detail,
        "detail_missing": missing is not None,
        "top_economies": TOP_ECONOMIES,
        "history_chart": charts.multi_line_chart(_history(detail), title="Users able to use and preferring IPv6",
                                                 y_title="Percent"),
        "networks": field(detail, "networks"),
        "nist": nist,
        "nist_web": nist_count("web"),
        "nist_mail": nist_count("mail"),
        "nist_dns": nist_count("dns"),
        "nist_agencies": None if nist is None else replace(nist, value=nist.value["agencies"][:NIST_AGENCIES]),
    }


def pages(data: Data) -> list[tuple[str, dict]]:
    index = derive.economy_index(data)
    if index is None:
        return []
    return [(e["slug"], context(data, e["code"])) for e in index.value]
