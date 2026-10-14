import json

from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, history=None, **kwargs):
    data = write_sample_data(tmp_path / "data", **kwargs)
    if history is not None:
        (data / "history.json").write_text(json.dumps(history))
    out = tmp_path / "dist"
    build(data, out, NOW)
    return out, (out / "historical-trends" / "index.html").read_text()


def test_real_series_charts(tmp_path):
    _, html = render(tmp_path)
    # world, regions, BGP table, ASes, RIR allocations, Cloudflare
    assert html.count("Plotly.newPlot") == 6
    assert "Africa" in html and "Oceania" in html


def test_snapshots_note_until_two_days(tmp_path):
    _, html = render(tmp_path, history=[{"date": "2026-10-14", "values": {"tranco_aaaa": 61.2}}])
    assert "This site started recording daily snapshots on 2026-10-14" in html
    assert html.count("Plotly.newPlot") == 6


def test_snapshot_chart_with_two_days(tmp_path):
    days = [{"date": "2026-10-14", "values": {"tranco_aaaa": 61.2, "apnic_world_capable": 43.6}},
            {"date": "2026-10-15", "values": {"tranco_aaaa": 61.3}}]
    _, html = render(tmp_path, history=days)
    assert html.count("Plotly.newPlot") == 7
    assert "Top 1000 sites with AAAA (Tranco)" in html


def test_milestones_are_dated_reference(tmp_path):
    _, html = render(tmp_path)
    assert "Reference — last reviewed 2026-10-14" in html
    assert "World IPv6 Launch" in html


def test_without_sources(tmp_path):
    _, html = render(tmp_path, omit=("apnic_region_history", "bgp_v6_table", "bgp_v6_ases", "cloudflare_ip_version"))
    assert html.count("— source unavailable") >= 4


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Historical Trends' in html
    assert '"Historical Trends": "historical-trends/"' in (out / "index.html").read_text()
