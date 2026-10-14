"""AAAA lookups for collectors that measure IPv6 deployment themselves."""
import dns.exception
import dns.resolver

LIFETIME_SECONDS = 5.0

_resolver = dns.resolver.Resolver()
_resolver.lifetime = LIFETIME_SECONDS


def dns_has_aaaa(name: str) -> bool | None:
    """True/False when DNS gave an answer; None when the lookup itself failed."""
    try:
        return len(_resolver.resolve(name, "AAAA")) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    except dns.exception.DNSException:  # timeouts, SERVFAIL, bad names: unknown
        return None
