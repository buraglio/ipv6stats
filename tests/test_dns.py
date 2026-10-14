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
