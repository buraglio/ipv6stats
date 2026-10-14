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
