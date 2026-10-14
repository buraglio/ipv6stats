import dns.exception
import dns.resolver

from collect import dns as collect_dns


def raising(exc):
    def resolve(name, rdtype):
        raise exc
    return resolve


def test_missing_record_is_false(monkeypatch):
    monkeypatch.setattr(collect_dns._resolver, "resolve", raising(dns.resolver.NXDOMAIN()))
    assert collect_dns.dns_has_aaaa("example.invalid") is False
    monkeypatch.setattr(collect_dns._resolver, "resolve", raising(dns.resolver.NoAnswer()))
    assert collect_dns.dns_has_aaaa("example.com") is False


def test_lookup_failure_is_unknown(monkeypatch):
    monkeypatch.setattr(collect_dns._resolver, "resolve", raising(dns.exception.Timeout()))
    assert collect_dns.dns_has_aaaa("example.com") is None
    monkeypatch.setattr(collect_dns._resolver, "resolve", raising(dns.resolver.NoNameservers()))
    assert collect_dns.dns_has_aaaa("example.com") is None


def test_has_a_mirrors_aaaa_semantics(monkeypatch):
    monkeypatch.setattr(collect_dns._resolver, "resolve", raising(dns.resolver.NXDOMAIN()))
    assert collect_dns.dns_has_a("gone.example") is False
    monkeypatch.setattr(collect_dns._resolver, "resolve", raising(dns.exception.Timeout()))
    assert collect_dns.dns_has_a("slow.example") is None


def test_context_has_a_defaults_to_true_and_can_be_faked():
    from tests.fakes import make_ctx
    assert make_ctx().has_a("anything.example") is True
    ctx = make_ctx(a={"v4.example"})
    assert ctx.has_a("v4.example") is True and ctx.has_a("gone.example") is False
