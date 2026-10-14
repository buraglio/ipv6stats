from collect.registry import SOURCES
from tests.sample_data import NOW, write_sample_data
from web.build import LEGACY_PAGES, build
from web.pages.data_sources import describe

OLD_PAGES = ["Overview", "Combined View", "Global Adoption", "Country Analysis", "Cloud Services",
             "Extended Data Sources", "BGP Statistics", "Historical Trends", "Data Sources"]


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "data-sources" / "index.html").read_text()


def test_every_source_is_described(tmp_path):
    _, html = render(tmp_path)
    for key, src in SOURCES.items():
        if key.startswith("test_"):
            continue
        assert src.title in html, key
        assert describe(src), key


def test_description_comes_from_the_collector_module():
    assert describe(SOURCES["bgp_v6_table"]).startswith("IPv6 BGP table size and AS count history")


def test_reference_files_and_keys(tmp_path):
    _, html = render(tmp_path, not_configured=("isoc_pulse",))
    for name in ("cloud_providers.toml", "carriers.toml", "government_domains.toml"):
        assert name in html
    assert "ISOC_PULSE_API_KEY" in html and "CLOUDFLARE_API_KEY" in html


def test_every_old_page_name_redirects():
    assert set(OLD_PAGES) <= set(LEGACY_PAGES)
    assert LEGACY_PAGES["Data Sources"] == "data-sources/"


def test_each_source_description_fits_its_source():
    assert "AS count" in describe(SOURCES["bgp_v6_ases"])
    assert "ISOC_PULSE_API_KEY" not in describe(SOURCES["isoc_pulse"])   # the page lists the secret separately


def test_provenance_prose_does_not_overstate(tmp_path):
    _, html = render(tmp_path)
    assert "Nothing is estimated" in html
    assert "except the reference lists" not in html
    assert "“Reference” boxes" in html or "Reference boxes" in html
