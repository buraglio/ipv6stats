import json
import re
from datetime import datetime, timezone

from web.charts import line_chart
from web.data import Datum

POINTS = [{"date": "2026-10-13", "prefixes": 1}, {"date": "2026-10-14", "prefixes": 2}]


def layout_of(html):
    # Plotly.newPlot("id", data, layout, config)
    args = re.search(r"Plotly\.newPlot\(\s*\"[^\"]+\",\s*(\[.*?\]),\s*(\{.*?\}),\s*\{\"displaylogo\"", html, re.S)
    return json.loads(args.group(2))


def test_range_buttons_sit_right_of_the_title():
    d = Datum(POINTS, ("bgp_v6_table",), datetime(2026, 10, 14, tzinfo=timezone.utc), False)
    selector = layout_of(line_chart(d, x="date", y="prefixes", title="T", y_title="Y"))["xaxis"]["rangeselector"]
    assert selector["x"] == 1 and selector["xanchor"] == "right"
