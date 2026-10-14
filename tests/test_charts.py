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


from web.charts import bar_chart, choropleth, multi_line_chart

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)


def figure_of(html):
    decoder = json.JSONDecoder()
    start = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*', html).end()
    data, i = decoder.raw_decode(html, start)
    layout, i = decoder.raw_decode(html, html.index("{", i))
    config, _ = decoder.raw_decode(html, html.index("{", i))
    return data, layout, config


def test_bar_chart():
    d = Datum([{"name": "Americas", "capable": 51.0}], ("apnic",), NOW, False)
    data, _, _ = figure_of(bar_chart(d, x="name", y="capable", title="T", y_title="Y"))
    assert data[0]["type"] == "bar" and data[0]["x"] == ["Americas"]


def test_multi_line_chart_one_trace_per_series():
    d = Datum([{"name": "A", "points": [{"x": 2000, "y": 1}]}, {"name": "B", "points": [{"x": 2000, "y": 2}]}],
              ("x",), NOW, False)
    data, layout, _ = figure_of(multi_line_chart(d, title="T", y_title="Y", x_type="linear"))
    assert [t["name"] for t in data] == ["A", "B"]
    assert layout["xaxis"]["type"] == "linear"


def test_map_uses_self_hosted_topojson():
    d = Datum([{"iso3": "USA", "name": "United States", "capable": 61.9}], ("apnic",), NOW, False)
    data, _, config = figure_of(choropleth(d, title="T", topojson_url="../static/topojson/"))
    assert data[0]["type"] == "choropleth" and data[0]["locationmode"] == "ISO-3"
    assert config["topojsonURL"] == "../static/topojson/"


def test_new_charts_return_none_without_data():
    assert bar_chart(None, x="a", y="b", title="T", y_title="Y") is None
    assert multi_line_chart(None, title="T", y_title="Y") is None
    assert choropleth(None, title="T", topojson_url="x/") is None
