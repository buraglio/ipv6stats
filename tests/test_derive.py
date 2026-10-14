from tests.sample_data import NOW, write_sample_data
from web import derive
from web.data import Data


def data(tmp_path, **kwargs):
    return Data(write_sample_data(tmp_path, **kwargs), NOW)


def test_consensus_of_three_sources(tmp_path):
    d = derive.consensus(derive.consensus_components(data(tmp_path)))
    assert d.value == 47.7  # (43.6 + 38.4 + 61.2) / 3
    assert d.sources == ("apnic", "cloudflare_ip_version", "tranco_aaaa")


def test_consensus_skips_missing_component(tmp_path):
    components = derive.consensus_components(data(tmp_path, omit=("cloudflare_ip_version",)))
    assert [d is None for _, d in components] == [False, True, False]
    assert derive.consensus(components).value == 52.4  # (43.6 + 61.2) / 2


def test_consensus_none_without_sources(tmp_path):
    d = data(tmp_path, omit=("apnic", "cloudflare_ip_version", "tranco_aaaa"))
    assert derive.consensus(derive.consensus_components(d)) is None


def test_bgp_values(tmp_path):
    d = data(tmp_path)
    assert derive.bgp_current(d).value == 258009
    assert derive.bgp_change(d, 365).value == 27009  # vs 2025-10-14
    assert derive.bgp_change(d, 30).value == 3009    # vs 2026-09-14
    assert derive.bgp_change(d, 4000) is None        # not enough history


def test_economy_rankings_ignore_small_samples(tmp_path):
    d = data(tmp_path)
    assert derive.economies_above(d, 50).value == 2   # FR, US; BL has too few samples
    assert derive.economies_considered(d).value == 3  # DE, FR, US
    assert derive.top_economy(d).value["name"] == "France"
    assert derive.economy(d, "US").value["capable"] == 61.9
    assert derive.economy(d, "ZZ") is None


def test_regions_sorted_without_unclassified(tmp_path):
    assert [r["name"] for r in derive.regions(data(tmp_path)).value] == ["Americas", "Europe"]


def test_economy_table_joins_by_code(tmp_path):
    rows = derive.economy_table(data(tmp_path)).value
    assert [r["code"] for r in rows] == ["FR", "US", "DE"]  # BL has too few samples
    fr, us, de = rows
    assert (fr["sixlab"], fr["web"], fr["slug"]) == (39.0, 44.0, "fr")
    assert (us["sixlab"], us["web"]) == (57.2, 50.0)
    assert (de["sixlab"], de["web"]) == (None, None)


def test_economy_table_without_optional_sources(tmp_path):
    d = derive.economy_table(data(tmp_path, omit=("cisco_6lab", "vyncke")))
    assert d.sources == ("apnic",)
    assert d.value[0]["sixlab"] is None


def test_index_and_map_cover_every_economy(tmp_path):
    d = data(tmp_path)
    assert [e["code"] for e in derive.economy_index(d).value] == ["FR", "DE", "BL", "US"]  # by name
    points = {p["code"]: p for p in derive.map_points(d).value}
    assert points["US"]["iso3"] == "USA" and points["BL"]["iso3"] == "BLM"
    assert derive.iso3("ZZ") is None


def test_rir_comparison_and_total(tmp_path):
    d = data(tmp_path)
    assert [r["name"] for r in derive.rir_comparison(d).value] == ["AFRINIC", "APNIC", "ARIN", "LACNIC", "RIPE NCC"]
    assert derive.rir_total(d).value == 171550.0
    assert derive.rir_total(data(tmp_path / "x", omit=("arin_delegations",))).value == 108550.0


def test_country_lookups(tmp_path):
    d = data(tmp_path)
    assert derive.country_allocation(d, "US").value == {"blocks_32": 60000.0, "registries": ["ARIN"]}
    assert derive.country_allocation(d, "BL") is None
    assert derive.sixlab_for(d, "US").value == 57.2
    assert derive.sixlab_for(d, "DE") is None
    assert derive.vyncke_for(d, "US").value == {"web": 50.0, "email": 52.0, "dns": 92.0}
    assert derive.vyncke_for(d, "FR").value == {"web": 44.0, "email": None, "dns": None}
    assert derive.vyncke_for(d, "DE") is None


def test_website_table_sorted_by_web(tmp_path):
    rows = derive.website_table(data(tmp_path), 10).value
    assert [r["code"] for r in rows] == ["US", "FR"]
    assert rows[1] == {"code": "FR", "name": "France", "web": 44.0, "email": None, "dns": None}


def test_field_extracts_from_a_dict_datum(tmp_path):
    from web.data import field
    row = derive.economy(data(tmp_path), "US")
    assert field(row, "capable").value == 61.9
    assert field(row, "missing_key") is None
    assert field(None, "capable") is None
