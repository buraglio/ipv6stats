"""Country Analysis: world map, leaders, regions and an index of every economy."""
from dataclasses import replace

from web import charts, derive
from web.data import Data

TOPOJSON_URL = "../" + charts.TOPOJSON_DIR  # the page lives one directory below the site root
LEADERS = 20


def context(data: Data) -> dict:
    points = derive.map_points(data)
    nist = derive.nist(data)
    return {
        "map_points": points,
        "map_chart": charts.choropleth(points, title="Users able to use IPv6 (APNIC)", topojson_url=TOPOJSON_URL),
        "leaders_size": LEADERS,
        "leaders": derive.economy_table(data, LEADERS),
        "regions": derive.regions(data),
        "index": derive.economy_index(data),
        "nist": nist,
        "nist_web": None if nist is None else replace(nist, value=nist.value["totals"]["web"].get("operational", 0)),
    }
