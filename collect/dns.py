"""AAAA lookups for collectors that measure IPv6 deployment themselves."""
import dns.exception
import dns.resolver

_resolver = dns.resolver.Resolver()
_resolver.lifetime = 5.0


def dns_has_aaaa(name: str) -> bool:
    try:
        return len(_resolver.resolve(name, "AAAA")) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
