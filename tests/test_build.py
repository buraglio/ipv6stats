import re
from datetime import datetime, timezone

from tests.sample_data import NOW, write_sample_data
from web.build import build, check_reference_dates

LINK = re.compile(r'(?:href|src)="([^"]*)"')


def built(tmp_path):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data"), out, NOW)
    return out


def test_build_writes_pages_and_assets(tmp_path):
    out = built(tmp_path)
    for rel in ["index.html", "overview/index.html", "static/site.css", "static/theme.js",
                "static/legacy-redirect.js", "static/plotly.min.js"]:
        assert (out / rel).is_file(), rel
    assert (out / "static" / "plotly.min.js").stat().st_size > 1_000_000


def test_internal_links_are_relative_and_resolve(tmp_path):
    out = built(tmp_path)
    for page in out.rglob("*.html"):
        if page.name == "404.html":
            continue
        for link in LINK.findall(page.read_text()):
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            assert not link.startswith("/"), f"{page}: {link} breaks the /ipv6stats/ preview"
            target = (page.parent / link.split("#")[0]).resolve()
            if target.is_dir():
                target = target / "index.html"
            assert target.is_file(), f"{page}: broken link {link}"


def test_root_page_carries_legacy_redirect(tmp_path):
    out = built(tmp_path)
    root = (out / "index.html").read_text()
    assert 'id="legacy-pages"' in root
    assert '"Combined View": "overview/"' in root
    assert 'id="legacy-pages"' not in (out / "overview" / "index.html").read_text()


def test_footer_shows_build_time(tmp_path):
    html = (built(tmp_path) / "overview" / "index.html").read_text()
    assert "Data refreshed daily at 00:00 UTC · Last build: 2026-10-14 01:00 UTC" in html


def test_only_third_party_request_is_the_logo(tmp_path):
    html = (built(tmp_path) / "overview" / "index.html").read_text()
    srcs = re.findall(r'src="(https?://[^"]+)"', html)
    assert srcs == ["https://ipv6.army/images/v6.png"]


def test_reference_dates_warn_when_old(tmp_path):
    (tmp_path / "old.html").write_text('{% call reference(reviewed="2026-01-01") %}x{% endcall %}')
    (tmp_path / "new.html").write_text('{% call reference(reviewed="2026-09-01") %}x{% endcall %}')
    now = datetime(2026, 10, 14, tzinfo=timezone.utc)
    warnings = check_reference_dates(tmp_path, now)
    assert len(warnings) == 1 and "old.html" in warnings[0]


def test_build_survives_plan_1_format_data(tmp_path):
    # The data branch holds files written before by_country/history existed.
    import json
    from collect.manifest import load, save
    data_dir = write_sample_data(tmp_path / "data")
    for key in ("lacnic_delegations", "afrinic_delegations", "apnic"):
        path = data_dir / f"{key}.json"
        payload = json.loads(path.read_text())
        for field in ("by_country", "history", "subregions"):
            payload.pop(field, None)
        path.write_text(json.dumps(payload))
    manifest = load(data_dir)
    for key in ("lacnic_delegations", "afrinic_delegations", "apnic"):
        manifest[key].pop("schema", None)
    save(data_dir, manifest)
    out = tmp_path / "dist"
    build(data_dir, out, NOW)
    assert "3 of 5 registries" in (out / "global-adoption" / "index.html").read_text()


def test_404_page_uses_root_links(tmp_path):
    # GitHub Pages serves 404.html at any depth, so its links must be root-absolute.
    page = (built(tmp_path) / "404.html").read_text()
    assert 'href="/static/site.css"' in page and 'href="/overview/"' in page
    assert "Page not found" in page
