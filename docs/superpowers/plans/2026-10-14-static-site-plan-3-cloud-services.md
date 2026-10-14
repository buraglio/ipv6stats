# Static Site Plan 3: Cloud Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Cloud Services page that combines measured IPv6 data for 23 cloud providers with a hand-maintained, dated reference file. No grades.

**Architecture:** Three new kinds of collectors: provider hostname AAAA checks, AWS's per-service IPv6 table, and seven providers' published IP-range files. A TOML reference file (`reference/cloud_providers.toml`), loaded at build time, replaces the hand-typed dicts in `data_sources.py` and `cloud_data.py` (those Streamlit files stay untouched). The page joins both by provider key.

**Tech Stack:** As before. `tomllib` (stdlib) reads the reference file.

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`. **Amendment 3** (end of file) is the approved scope.

## Global Constraints

- Work on `staging`; commits carry **no** Claude attribution (no `Co-Authored-By`).
- Do not modify the Streamlit files (`app.py`, `data_sources.py`, `cloud_data.py`, …); the migration script only *reads* them.
- Collectors return parsed data or raise. All new sources `MONTH`. `tests/test_no_static_stats.py` stays green.
- Endpoint statuses: `ipv6` (AAAA present), `ipv4_only` (no AAAA, A present), `unknown` (lookup failed or the name no longer resolves). Fail the source if unknown > `MAX_UNKNOWN = 0.05` of lookups.
- AWS table values: `Yes`/`No`/`Partial`/blank → `"yes"`/`"no"`/`"partial"`/`None`; anything else raises.
- IP ranges are shown as prefix **counts**, never as a percentage.
- Reference file: required `key`, `name`, `last_reviewed` (ISO date); no `%` anywhere; keys unique and equal to `cloud_endpoints` provider keys. Build warns when `last_reviewed` is more than 180 days old. No grades.
- Page at `/cloud-services/`, nav after Country Analysis; legacy `"Cloud Services": "cloud-services/"`.

## Review Focus

1. **A provider renames or retires a hostname.** It must show as "unknown", not "IPv4-only". Test: `test_unresolvable_name_is_unknown_not_ipv4`.
2. **A DNS outage on the runner.** Must fail the source (keep last good), not publish "no IPv6" for everyone. Test: `test_too_many_unknown_lookups_fail`.
3. **The reference file drifts from the code**: a key typo, a missing date, a statistic pasted in. Tests: `test_reference_keys_match_endpoint_providers`, `test_reference_has_no_statistics`, `test_reference_requires_fields`.
4. **One provider's IP-range file breaks.** Only that provider's numbers go stale or unavailable. Each provider is its own source; test: `test_each_provider_is_its_own_source`.
5. **Curated text shown as if it were measured.** Every curated block renders inside a reference note with its review date. Test: `test_provider_reference_shows_review_date`.

---

### Task 1: A-record lookups for telling "IPv4-only" from "unknown"

**Files:** Modify `collect/dns.py`, `collect/registry.py`, `collect/run.py`, `tests/fakes.py`; Test `tests/test_dns.py` (append)

**Interfaces:** Produces `collect.dns.dns_has_a(name) -> bool | None`; `Context.has_a: Callable[[str], bool | None]` (default: always True); `make_ctx(..., a=None)` (when given, `has_a = name in a`).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_dns.py`:

```python


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
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_dns.py -q` → FAIL (`AttributeError: ... 'dns_has_a'`).

- [ ] **Step 3: Implement** — replace the body of `collect/dns.py` below the resolver setup with:

```python
def _has(name: str, rdtype: str) -> bool | None:
    """True/False when DNS gave an answer; None when the lookup itself failed."""
    try:
        return len(_resolver.resolve(name, rdtype)) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    except dns.exception.DNSException:  # timeouts, SERVFAIL, bad names: unknown
        return None


def dns_has_aaaa(name: str) -> bool | None:
    return _has(name, "AAAA")


def dns_has_a(name: str) -> bool | None:
    return _has(name, "A")
```

In `collect/registry.py`, after the `has_aaaa` field of `Context`, add:

```python
    has_a: Callable[[str], bool | None] = lambda name: True  # None = lookup failed
```

In `collect/run.py`, change `from collect.dns import dns_has_aaaa` to `from collect.dns import dns_has_a, dns_has_aaaa` and the `Context(...)` call's last argument line to `has_aaaa=dns_has_aaaa, has_a=dns_has_a)`.

In `tests/fakes.py`, replace `make_ctx` with:

```python
def make_ctx(routes=None, env=None, now=None, aaaa=None, a=None) -> Context:
    names = set(aaaa or ())
    v4_names = None if a is None else set(a)
    return Context(
        session=FakeSession(routes),
        env=env or {},
        now=now or datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc),
        has_aaaa=lambda name: name in names,
        has_a=(lambda name: True) if v4_names is None else (lambda name: name in v4_names),
    )
```

- [ ] **Step 4: Verify** — `uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/ tests/ && git commit -m "Add A-record lookups so collectors can tell IPv4-only from unresolvable"`

---

### Task 2: Cloud provider hostname check

**Files:** Create `collect/sources/cloud_endpoints.py`, `tests/test_cloud_endpoints.py`; Modify `collect/sources/__init__.py`

**Interfaces:** Produces source `cloud_endpoints`; `ENDPOINTS: dict[key, {"name": str, "hosts": {role: host}}]`; `ROLES`; `check(host, has_aaaa, has_a) -> "ipv6"|"ipv4_only"|"unknown"`; `measure(endpoints, has_aaaa, has_a) -> {"providers": [{"key","name","hosts": [{"role","host","status"}],"with_ipv6": int,"checked": int}], "unknown": int, "total": int}`.

- [ ] **Step 1: Write the failing tests** — `tests/test_cloud_endpoints.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import cloud_endpoints as ce
from tests.fakes import make_ctx

SMALL = {"p": {"name": "P", "hosts": {"website": "www.p.example", "api": "api.p.example", "docs": "docs.p.example"}}}


def test_check_statuses():
    v6, v4 = {"six.example"}.__contains__, {"four.example", "six.example"}.__contains__
    assert ce.check("six.example", v6, v4) == "ipv6"
    assert ce.check("four.example", v6, v4) == "ipv4_only"


def test_unresolvable_name_is_unknown_not_ipv4():
    assert ce.check("gone.example", lambda n: False, lambda n: False) == "unknown"
    assert ce.check("slow.example", lambda n: None, lambda n: True) == "unknown"


def test_measure_counts_known_hosts_only():
    v6 = {"www.p.example"}.__contains__
    result = ce.measure(SMALL, v6, {"www.p.example", "api.p.example"}.__contains__, max_unknown=0.5)
    p = result["providers"][0]
    assert (p["with_ipv6"], p["checked"]) == (1, 2)              # docs.p.example doesn't resolve
    assert [h["status"] for h in p["hosts"]] == ["ipv6", "ipv4_only", "unknown"]
    assert (result["unknown"], result["total"]) == (1, 3)


def test_too_many_unknown_lookups_fail():
    with pytest.raises(ValueError, match="lookups failed"):
        ce.measure(SMALL, lambda n: None, lambda n: None)


def test_endpoint_list_shape():
    assert len(ce.ENDPOINTS) == 23
    for key, entry in ce.ENDPOINTS.items():
        assert set(entry["hosts"]) <= set(ce.ROLES), key
        assert entry["name"]


def test_fetch_uses_context_dns():
    hosts = {h for e in ce.ENDPOINTS.values() for h in e["hosts"].values()}
    result = SOURCES["cloud_endpoints"].fetch(make_ctx(aaaa=hosts))
    assert all(p["with_ipv6"] == p["checked"] for p in result["providers"])
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_cloud_endpoints.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/cloud_endpoints.py`:

```python
"""Whether cloud providers' own default hostnames publish IPv6 (AAAA) records.

Measured from GitHub's runners, which have no IPv6: this shows published IPv6, not
end-to-end reachability.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from collect.registry import MONTH, Context, source

METHOD = "https://github.com/buraglio/ipv6stats/blob/main/collect/sources/cloud_endpoints.py"
ROLES = ("website", "console", "api", "docs", "storage", "status")
MAX_UNKNOWN = 0.05
WORKERS = 16

ENDPOINTS = {
    "aws": {"name": "AWS", "hosts": {"website": "aws.amazon.com", "console": "console.aws.amazon.com", "api": "ec2.us-east-1.amazonaws.com", "docs": "docs.aws.amazon.com", "storage": "s3.us-east-1.amazonaws.com", "status": "health.aws.amazon.com"}},
    "azure": {"name": "Microsoft Azure", "hosts": {"website": "azure.microsoft.com", "console": "portal.azure.com", "api": "management.azure.com", "docs": "learn.microsoft.com", "storage": "azureopendatastorage.blob.core.windows.net", "status": "azure.status.microsoft"}},
    "gcp": {"name": "Google Cloud Platform", "hosts": {"website": "cloud.google.com", "console": "console.cloud.google.com", "api": "compute.googleapis.com", "docs": "docs.cloud.google.com", "storage": "storage.googleapis.com", "status": "status.cloud.google.com"}},
    "oracle": {"name": "Oracle Cloud", "hosts": {"website": "www.oracle.com", "console": "cloud.oracle.com", "api": "iaas.us-ashburn-1.oraclecloud.com", "docs": "docs.oracle.com", "storage": "objectstorage.us-ashburn-1.oraclecloud.com", "status": "ocistatus.oraclecloud.com"}},
    "digitalocean": {"name": "DigitalOcean", "hosts": {"website": "www.digitalocean.com", "console": "cloud.digitalocean.com", "api": "api.digitalocean.com", "docs": "docs.digitalocean.com", "storage": "nyc3.digitaloceanspaces.com", "status": "status.digitalocean.com"}},
    "vultr": {"name": "Vultr", "hosts": {"website": "www.vultr.com", "console": "my.vultr.com", "api": "api.vultr.com", "docs": "docs.vultr.com", "storage": "ewr1.vultrobjects.com", "status": "status.vultr.com"}},
    "linode": {"name": "Linode (Akamai)", "hosts": {"website": "www.linode.com", "console": "cloud.linode.com", "api": "api.linode.com", "docs": "techdocs.akamai.com", "storage": "us-east-1.linodeobjects.com", "status": "status.linode.com"}},
    "cloudflare": {"name": "Cloudflare", "hosts": {"website": "www.cloudflare.com", "console": "dash.cloudflare.com", "api": "api.cloudflare.com", "docs": "developers.cloudflare.com", "storage": "r2.cloudflarestorage.com", "status": "www.cloudflarestatus.com"}},
    "mythic-beasts": {"name": "Mythic Beasts", "hosts": {"website": "www.mythic-beasts.com", "api": "api.mythic-beasts.com", "status": "status.mythic-beasts.com"}},
    "hetzner": {"name": "Hetzner", "hosts": {"website": "www.hetzner.com", "console": "console.hetzner.cloud", "api": "api.hetzner.cloud", "docs": "docs.hetzner.com", "storage": "fsn1.your-objectstorage.com", "status": "status.hetzner.com"}},
    "scaleway": {"name": "Scaleway", "hosts": {"website": "www.scaleway.com", "console": "console.scaleway.com", "api": "api.scaleway.com", "storage": "s3.fr-par.scw.cloud", "status": "status.scaleway.com"}},
    "ovhcloud": {"name": "OVHcloud", "hosts": {"website": "www.ovhcloud.com", "console": "www.ovh.com", "api": "eu.api.ovh.com", "docs": "help.ovhcloud.com", "storage": "s3.gra.io.cloud.ovh.net", "status": "public-cloud.status-ovhcloud.com"}},
    "contabo": {"name": "Contabo", "hosts": {"website": "contabo.com", "console": "my.contabo.com", "api": "api.contabo.com", "docs": "docs.contabo.com", "storage": "eu2.contabostorage.com", "status": "contabo-status.com"}},
    "ionos": {"name": "IONOS", "hosts": {"website": "www.ionos.com", "console": "my.ionos.com", "api": "api.ionos.com", "docs": "docs.ionos.com", "storage": "s3.eu-central-1.ionoscloud.com", "status": "status.ionos.cloud"}},
    "upcloud": {"name": "UpCloud", "hosts": {"website": "upcloud.com", "console": "hub.upcloud.com", "api": "api.upcloud.com", "status": "status.upcloud.com"}},
    "binarylane": {"name": "BinaryLane", "hosts": {"website": "www.binarylane.com.au", "console": "home.binarylane.com.au", "api": "api.binarylane.com.au", "docs": "support.binarylane.com.au", "status": "status.binarylane.com.au"}},
    "kamatera": {"name": "Kamatera", "hosts": {"website": "www.kamatera.com", "console": "console.kamatera.com", "api": "cloudcli.cloudwm.com", "status": "status.kamatera.com"}},
    "hostinger": {"name": "Hostinger", "hosts": {"website": "www.hostinger.com", "console": "hpanel.hostinger.com", "api": "developers.hostinger.com", "docs": "support.hostinger.com", "status": "statuspage.hostinger.com"}},
    "fastly": {"name": "Fastly", "hosts": {"website": "www.fastly.com", "console": "manage.fastly.com", "api": "api.fastly.com", "docs": "docs.fastly.com", "status": "www.fastlystatus.com"}},
    "backblaze": {"name": "Backblaze", "hosts": {"website": "www.backblaze.com", "console": "secure.backblaze.com", "api": "api.backblazeb2.com", "storage": "s3.us-west-004.backblazeb2.com", "status": "status.backblaze.com"}},
    "railway": {"name": "Railway", "hosts": {"website": "railway.com", "api": "backboard.railway.com", "docs": "docs.railway.com", "status": "status.railway.com"}},
    "render": {"name": "Render", "hosts": {"website": "render.com", "console": "dashboard.render.com", "api": "api.render.com", "status": "status.render.com"}},
    "fly-io": {"name": "Fly.io", "hosts": {"website": "fly.io", "api": "api.machines.dev", "status": "status.flyio.net"}},
}


def check(host: str, has_aaaa: Callable, has_a: Callable) -> str:
    v6 = has_aaaa(host)
    if v6:
        return "ipv6"
    v4 = has_a(host)
    if v6 is None or not v4:  # lookup failed, or the name no longer resolves at all
        return "unknown"
    return "ipv4_only"


def measure(endpoints: dict, has_aaaa: Callable, has_a: Callable, max_unknown: float = MAX_UNKNOWN) -> dict:
    jobs = [(key, role, host) for key, entry in endpoints.items() for role, host in entry["hosts"].items()]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        statuses = list(pool.map(lambda job: check(job[2], has_aaaa, has_a), jobs))
    unknown = statuses.count("unknown")
    if unknown > max_unknown * len(jobs):
        raise ValueError(f"{unknown} of {len(jobs)} hostname lookups failed; not trusting the result")
    by_key: dict[str, list] = {}
    for (key, role, host), status in zip(jobs, statuses):
        by_key.setdefault(key, []).append({"role": role, "host": host, "status": status})
    providers = [{"key": key, "name": endpoints[key]["name"], "hosts": hosts,
                  "with_ipv6": sum(h["status"] == "ipv6" for h in hosts),
                  "checked": sum(h["status"] != "unknown" for h in hosts)}
                 for key, hosts in by_key.items()]
    return {"providers": providers, "unknown": unknown, "total": len(jobs)}


@source("cloud_endpoints", MONTH, title="Cloud provider hostnames with IPv6 (AAAA lookups, measured)", url=METHOD)
def fetch(ctx: Context) -> dict:
    return measure(ENDPOINTS, ctx.has_aaaa, ctx.has_a)
```

Add `cloud_endpoints` to the import list in `collect/sources/__init__.py` (keep alphabetical order).

- [ ] **Step 4: Verify** — `uv run pytest tests/test_cloud_endpoints.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_cloud_endpoints.py && git commit -m "Add cloud provider hostname IPv6 check for 23 providers"`

---

### Task 3: AWS per-service IPv6 table

**Files:** Create `collect/sources/aws_ipv6.py`, `tests/test_aws_ipv6.py`, `tests/fixtures/aws/aws-ipv6-support.html`; Modify `collect/sources/__init__.py`

**Interfaces:** Produces source `aws_ipv6_services`; `parse(page, min_services=MIN_SERVICES) -> {"services": [{"name","dual_stack","ipv6_only","public_endpoints","private_endpoints"}], "counts": {column: {"yes","partial","no": int}}, "total": int, "url"}`; `COLUMNS`, `URL`.

- [ ] **Step 1: Record fixture** — `mkdir -p tests/fixtures/aws && curl -sL https://docs.aws.amazon.com/vpc/latest/userguide/aws-ipv6-support.html -o tests/fixtures/aws/aws-ipv6-support.html && grep -c '<td' tests/fixtures/aws/aws-ipv6-support.html` → about 950.

- [ ] **Step 2: Write the failing tests** — `tests/test_aws_ipv6.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import aws_ipv6
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "aws" / "aws-ipv6-support.html").read_text(encoding="utf-8")


def row(*cells):
    return "<tr>" + "".join(f'<td tabindex="-1">{c}</td>' for c in cells) + "</tr>"


SAMPLE = ("<table><thead><tr><th>Service name</th></tr></thead>"
          + row("AWS Amplify", "Yes", "No", "Yes", "")
          + row("Amazon EC2", "Yes", "Partial", "Yes", "Yes") + "</table>")


def test_parse_sample():
    parsed = aws_ipv6.parse(SAMPLE, min_services=1)
    assert parsed["services"][0] == {"name": "AWS Amplify", "dual_stack": "yes", "ipv6_only": "no",
                                     "public_endpoints": "yes", "private_endpoints": None}
    assert parsed["counts"]["ipv6_only"] == {"yes": 0, "partial": 1, "no": 1}
    assert parsed["total"] == 2


def test_parse_recorded_page():
    parsed = aws_ipv6.parse(FIXTURE)
    assert parsed["total"] >= aws_ipv6.MIN_SERVICES
    assert parsed["counts"]["dual_stack"]["yes"] > 0


def test_rejects_unexpected_value():
    with pytest.raises(ValueError, match="AWS IPv6 table format changed"):
        aws_ipv6.parse(SAMPLE.replace(">Partial<", ">Coming soon<"), min_services=1)


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="AWS IPv6 table format changed"):
        aws_ipv6.parse("<html>moved</html>")


def test_fetch():
    assert SOURCES["aws_ipv6_services"].fetch(make_ctx(routes={aws_ipv6.URL: FakeResponse(text=FIXTURE)}))["total"]
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_aws_ipv6.py -q` → FAIL (`ImportError`).

- [ ] **Step 4: Implement** — `collect/sources/aws_ipv6.py`:

```python
"""AWS's own table of which services support IPv6 (dual-stack, IPv6-only, endpoints)."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://docs.aws.amazon.com/vpc/latest/userguide/aws-ipv6-support.html"
COLUMNS = ("dual_stack", "ipv6_only", "public_endpoints", "private_endpoints")
VALUES = {"yes": "yes", "no": "no", "partial": "partial", "": None}
ROW = re.compile(r"<tr>\s*((?:<td[^>]*>.*?</td>\s*){5})</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
MIN_SERVICES = 100


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cell))).strip()


def parse(page: str, min_services: int = MIN_SERVICES) -> dict:
    services = []
    for row in ROW.findall(page):
        name, *flags = (_text(c) for c in CELL.findall(row))
        values = []
        for flag in flags:
            if flag.lower() not in VALUES:
                raise ValueError(f"AWS IPv6 table format changed: unexpected value {flag!r} for {name}")
            values.append(VALUES[flag.lower()])
        services.append({"name": name, **dict(zip(COLUMNS, values))})
    if len(services) < min_services:
        raise ValueError(f"AWS IPv6 table format changed: {len(services)} services")
    counts = {c: {v: sum(1 for s in services if s[c] == v) for v in ("yes", "partial", "no")} for c in COLUMNS}
    return {"services": services, "counts": counts, "total": len(services), "url": URL}


@source("aws_ipv6_services", MONTH, title="AWS services that support IPv6 (AWS documentation)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
```

Add `aws_ipv6` to the import list in `collect/sources/__init__.py`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_aws_ipv6.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add collect/sources/ tests/test_aws_ipv6.py tests/fixtures/aws/ && git commit -m "Add AWS per-service IPv6 support table source"`

---

### Task 4: Published IP ranges, one source per provider

**Files:** Create `collect/sources/cloud_ranges.py`, `tests/test_cloud_ranges.py`; Modify `collect/sources/__init__.py`

**Interfaces:** Produces sources `ip_ranges_aws`, `ip_ranges_gcp`, `ip_ranges_oracle`, `ip_ranges_digitalocean`, `ip_ranges_linode`, `ip_ranges_cloudflare`, `ip_ranges_fastly`; `PROVIDERS: dict[key, (title, urls: tuple[str, ...], parser)]`; payload `{"ipv4_prefixes": int, "ipv6_prefixes": int, "url": first url}` plus, for AWS, `"services": int, "services_with_ipv6": int`.

- [ ] **Step 1: Write the failing tests** — `tests/test_cloud_ranges.py`:

```python
import json

import pytest

from collect.registry import SOURCES
from collect.sources import cloud_ranges as cr
from tests.fakes import FakeResponse, make_ctx

AWS = {"prefixes": [{"ip_prefix": "3.0.0.0/15", "service": "AMAZON"}, {"ip_prefix": "3.2.0.0/16", "service": "EC2"}],
       "ipv6_prefixes": [{"ipv6_prefix": "2600:1f00::/24", "service": "AMAZON"}]}
SAMPLES = {
    "aws": [json.dumps(AWS)],
    "gcp": [json.dumps({"prefixes": [{"ipv4Prefix": "34.1.0.0/16"}, {"ipv6Prefix": "2600:1900::/28"}]})],
    "oracle": [json.dumps({"regions": [{"cidrs": [{"cidr": "129.80.0.0/16"}, {"cidr": "130.35.0.0/16"}]}]})],
    "digitalocean": ["5.101.96.0/21,NL,NL-NH,Amsterdam,1098 XG\n2a03:b0c0::/32,NL,NL-NH,Amsterdam,\n"],
    "linode": ["# comment\n69.164.192.0/18,US,US-NJ,Cedar Knolls,\n2600:3c00::/32,US,US-TX,Richardson,\n"],
    "cloudflare": ["173.245.48.0/20\n103.21.244.0/22\n", "2400:cb00::/32\n"],
    "fastly": [json.dumps({"addresses": ["23.235.32.0/20"], "ipv6_addresses": ["2a04:4e40::/32"]})],
}


def ctx_for(key, bodies):
    return make_ctx(routes={url: FakeResponse(text=body) for url, body in zip(cr.PROVIDERS[key][1], bodies)})


@pytest.mark.parametrize("key,v4,v6", [("aws", 2, 1), ("gcp", 1, 1), ("oracle", 2, 0), ("digitalocean", 1, 1),
                                       ("linode", 1, 1), ("cloudflare", 2, 1), ("fastly", 1, 1)])
def test_counts_per_provider(key, v4, v6):
    payload = SOURCES[f"ip_ranges_{key}"].fetch(ctx_for(key, SAMPLES[key]))
    assert (payload["ipv4_prefixes"], payload["ipv6_prefixes"]) == (v4, v6)


def test_aws_counts_services():
    payload = SOURCES["ip_ranges_aws"].fetch(ctx_for("aws", SAMPLES["aws"]))
    assert (payload["services"], payload["services_with_ipv6"]) == (2, 1)


def test_rejects_empty_or_changed_file():
    with pytest.raises(ValueError, match="format changed"):
        SOURCES["ip_ranges_gcp"].fetch(ctx_for("gcp", [json.dumps({"prefixes": []})]))
    with pytest.raises(Exception):
        SOURCES["ip_ranges_aws"].fetch(ctx_for("aws", ["<html>moved</html>"]))


def test_each_provider_is_its_own_source():
    assert {f"ip_ranges_{k}" for k in cr.PROVIDERS} <= set(SOURCES)
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_cloud_ranges.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/cloud_ranges.py`:

```python
"""IPv4 and IPv6 prefix counts from cloud providers' published IP-range files.

One source per provider, so one broken file only affects that provider.
"""
import json

from collect.registry import MONTH, Context, source


def _counts(v4: int, v6: int, **extra) -> dict:
    if v4 + v6 == 0:
        raise ValueError("IP range file format changed: no prefixes found")
    return {"ipv4_prefixes": v4, "ipv6_prefixes": v6, **extra}


def _aws(texts):
    d = json.loads(texts[0])
    v4_services = {p["service"] for p in d["prefixes"]}
    v6_services = {p["service"] for p in d["ipv6_prefixes"]}
    return _counts(len(d["prefixes"]), len(d["ipv6_prefixes"]),
                   services=len(v4_services | v6_services), services_with_ipv6=len(v6_services))


def _gcp(texts):
    prefixes = json.loads(texts[0])["prefixes"]
    return _counts(sum("ipv4Prefix" in p for p in prefixes), sum("ipv6Prefix" in p for p in prefixes))


def _oracle(texts):
    cidrs = [c["cidr"] for region in json.loads(texts[0])["regions"] for c in region["cidrs"]]
    return _counts(sum(":" not in c for c in cidrs), sum(":" in c for c in cidrs))


def _first_column(texts):  # CSV geofeeds: prefix,country,region,city,postal
    prefixes = [line.split(",")[0].strip() for line in texts[0].splitlines()
                if line.strip() and not line.startswith("#")]
    return _counts(sum(":" not in p for p in prefixes), sum(":" in p for p in prefixes))


def _cloudflare(texts):
    return _counts(len(texts[0].split()), len(texts[1].split()))


def _fastly(texts):
    d = json.loads(texts[0])
    return _counts(len(d["addresses"]), len(d["ipv6_addresses"]))


PROVIDERS = {
    "aws": ("AWS published IP ranges", ("https://ip-ranges.amazonaws.com/ip-ranges.json",), _aws),
    "gcp": ("Google Cloud published IP ranges", ("https://www.gstatic.com/ipranges/cloud.json",), _gcp),
    "oracle": ("Oracle Cloud published IP ranges", ("https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json",), _oracle),
    "digitalocean": ("DigitalOcean published IP ranges", ("https://digitalocean.com/geo/google.csv",), _first_column),
    "linode": ("Linode published IP ranges", ("https://geoip.linode.com/",), _first_column),
    "cloudflare": ("Cloudflare published IP ranges", ("https://www.cloudflare.com/ips-v4", "https://www.cloudflare.com/ips-v6"), _cloudflare),
    "fastly": ("Fastly published IP ranges", ("https://api.fastly.com/public-ip-list",), _fastly),
}


def _register(key: str, title: str, urls: tuple, parser) -> None:
    def fetch(ctx: Context) -> dict:
        texts = []
        for url in urls:
            response = ctx.session.get(url, timeout=60)
            response.raise_for_status()
            texts.append(response.text)
        return {**parser(texts), "url": urls[0]}

    source(f"ip_ranges_{key}", MONTH, title=title, url=urls[0])(fetch)


for _key, (_title, _urls, _parser) in PROVIDERS.items():
    _register(_key, _title, _urls, _parser)
```

Add `cloud_ranges` to the import list in `collect/sources/__init__.py`.

- [ ] **Step 4: Verify** — `uv run pytest tests/test_cloud_ranges.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_cloud_ranges.py && git commit -m "Add published IP-range sources for seven cloud providers"`

---

### Task 5: Curated reference file, loader and migration

**Files:** Create `reference/cloud_providers.toml` (generated once by the Step 3 script, then hand-maintained), `web/reference.py`, `tests/test_cloud_reference.py`; Modify `web/build.py` (warnings)

**Interfaces:** Produces `web.reference.CLOUD_FILE`, `load_cloud_providers(path=CLOUD_FILE) -> list[dict]` (each dict has `key`, `name`, `last_reviewed`, and the list fields `limitations`, `recent_progress`, `special_features`, `notes`, `service` defaulted to `[]`); `stale_reviews(providers, now, max_age_days=180) -> list[str]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_cloud_reference.py`:

```python
from datetime import datetime, timezone

import pytest

from collect.sources.cloud_endpoints import ENDPOINTS
from web import reference


def test_reference_loads_with_defaults():
    providers = reference.load_cloud_providers()
    assert len(providers) == 23
    aws = next(p for p in providers if p["key"] == "aws")
    assert aws["name"] == "AWS" and aws["service"] and isinstance(aws["limitations"], list)
    assert "grade" not in aws


def test_reference_keys_match_endpoint_providers():
    assert {p["key"] for p in reference.load_cloud_providers()} == set(ENDPOINTS)


def test_reference_has_no_statistics():
    assert "%" not in reference.CLOUD_FILE.read_text()


def test_reference_requires_fields(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[[provider]]\nkey = "x"\nname = "X"\n')
    with pytest.raises(ValueError, match="last_reviewed"):
        reference.load_cloud_providers(bad)
    bad.write_text('[[provider]]\nkey = "x"\nname = "X"\nlast_reviewed = "soon"\n')
    with pytest.raises(ValueError, match="last_reviewed"):
        reference.load_cloud_providers(bad)
    bad.write_text('[[provider]]\nkey = "x"\nname = "X"\nlast_reviewed = "2026-01-01"\n' * 2)
    with pytest.raises(ValueError, match="duplicate"):
        reference.load_cloud_providers(bad)


def test_stale_reviews_warn():
    providers = [{"name": "Old", "last_reviewed": "2025-10-04"}, {"name": "New", "last_reviewed": "2026-10-01"}]
    warnings = reference.stale_reviews(providers, datetime(2026, 10, 14, tzinfo=timezone.utc))
    assert len(warnings) == 1 and "Old" in warnings[0]
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_cloud_reference.py -q` → FAIL (`ImportError: cannot import name 'reference'`).

- [ ] **Step 3: Generate the reference file once from the Streamlit data** (script is not committed):

```bash
mkdir -p reference && uv run python - <<'EOF'
"""One-time migration of the hand-typed cloud data into reference/cloud_providers.toml."""
import ast, importlib.util, json

KEYS = {"AWS": "aws", "Microsoft Azure": "azure", "Google Cloud Platform": "gcp", "Oracle Cloud": "oracle",
        "DigitalOcean": "digitalocean", "Vultr": "vultr", "Linode (Akamai)": "linode", "Cloudflare": "cloudflare",
        "Mythic Beasts": "mythic-beasts", "Hetzner": "hetzner", "Scaleway": "scaleway", "OVHcloud": "ovhcloud",
        "Contabo": "contabo", "IONOS": "ionos", "UpCloud": "upcloud", "BinaryLane": "binarylane",
        "Kamatera": "kamatera", "Hostinger": "hostinger", "Fastly": "fastly", "Backblaze": "backblaze",
        "Railway": "railway", "Render": "render", "Fly.io": "fly-io"}
src = open("data_sources.py").read()
fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "get_cloud_ipv6_status")
status = ast.literal_eval(next(n for n in ast.walk(fn) if isinstance(n, ast.Assign)
                               and getattr(n.targets[0], "id", "") == "cloud_providers").value)
spec = importlib.util.spec_from_file_location("cloud_data", "cloud_data.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
matrix = module.CLOUD_PROVIDERS

def s(v): return json.dumps(v, ensure_ascii=False)
def as_list(v): return [] if v is None else (v if isinstance(v, list) else [v])
def clean(items): return [str(i) for i in items if "%" not in str(i)]
def yes_no(v): return "Yes" if v is True else "No" if v is False else str(v)

out = ["# Curated IPv6 support of cloud providers, shown on the Cloud Services page as reference",
       "# material. Edit by hand and set last_reviewed to the date you checked an entry against",
       "# the provider's documentation. No statistics here: anything measurable is collected by",
       "# collect/sources/. Keys must match collect/sources/cloud_endpoints.py.", ""]
for name, info in status.items():
    if name not in KEYS:
        continue
    key = KEYS[name]; mx = matrix.get(key, {})
    out += ["[[provider]]", f"key = {s(key)}", f"name = {s(name)}", 'last_reviewed = "2025-10-04"']
    if mx.get("documentation"):
        out.append(f"documentation = {s(mx['documentation'])}")
    for field, src_field in (("overall_support", "overall_support"), ("ipv6_only_support", "ipv6_only_support"),
                             ("cost_impact", "cost_impact"), ("outlook", "ipv6_timeline")):
        if info.get(src_field) and "%" not in str(info[src_field]):
            out.append(f"{field} = {s(str(info[src_field]))}")
    for field, items in (("limitations", info.get("major_limitations")), ("recent_progress", info.get("recent_progress")),
                         ("special_features", info.get("special_features")), ("notes", mx.get("notes"))):
        kept = clean(as_list(items))
        if kept:
            out.append(f"{field} = {s(kept)}")
    for svc_name, svc in (mx.get("services") or {}).items():
        egress, pd = svc.get("nat_free_egress") or {}, svc.get("prefix_delegation") or {}
        out += ["", "[[provider.service]]", f"name = {s(svc_name)}",
                f"dual_stack = {s(yes_no(svc.get('dual_stack')))}", f"ipv6_only = {s(yes_no(svc.get('ipv6_only')))}",
                f"nat_free_egress = {s(egress.get('method', 'Yes') if egress.get('supported') else 'No')}",
                f"prefix_delegation = {s((pd.get('prefix_size') or pd.get('method') or 'Yes') if pd.get('supported') else 'No')}"]
        notes = clean(as_list(svc.get("notes")))
        if notes:
            out.append(f"notes = {s(notes)}")
    out.append("")
open("reference/cloud_providers.toml", "w").write("\n".join(out))
print(sum(1 for line in out if line == "[[provider]]"), "providers")
EOF
grep -c '%' reference/cloud_providers.toml; grep -c grade reference/cloud_providers.toml
```
Expected: `23 providers`, then `0` and `0`.

- [ ] **Step 4: Implement** — `web/reference.py`:

```python
"""Hand-maintained reference data (reference/*.toml), validated when loaded."""
from __future__ import annotations

import tomllib
from datetime import date, datetime
from pathlib import Path

CLOUD_FILE = Path(__file__).resolve().parent.parent / "reference" / "cloud_providers.toml"
REQUIRED = ("key", "name", "last_reviewed")
LIST_FIELDS = ("limitations", "recent_progress", "special_features", "notes", "service")
MAX_AGE_DAYS = 180


def load_cloud_providers(path: Path = CLOUD_FILE) -> list[dict]:
    providers = tomllib.loads(Path(path).read_text(encoding="utf-8")).get("provider", [])
    seen = set()
    for p in providers:
        for field in REQUIRED:
            if not p.get(field):
                raise ValueError(f"{path.name}: provider {p.get('key', '?')} is missing {field}")
        try:
            date.fromisoformat(p["last_reviewed"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path.name}: {p['key']} has an invalid last_reviewed {p['last_reviewed']!r}") from exc
        if p["key"] in seen:
            raise ValueError(f"{path.name}: duplicate provider key {p['key']}")
        seen.add(p["key"])
        for field in LIST_FIELDS:
            p.setdefault(field, [])
    return providers


def stale_reviews(providers: list[dict], now: datetime, max_age_days: int = MAX_AGE_DAYS) -> list[str]:
    warnings = []
    for p in providers:
        age = (now.date() - date.fromisoformat(p["last_reviewed"])).days
        if age > max_age_days:
            warnings.append(f"cloud_providers.toml: {p['name']} last reviewed {p['last_reviewed']} ({age} days ago)")
    return warnings
```

In `web/build.py`, add `from web import reference` with the other `web` imports and change `return check_reference_dates(TEMPLATES, now)` to:

```python
    return check_reference_dates(TEMPLATES, now) + reference.stale_reviews(reference.load_cloud_providers(), now)
```

- [ ] **Step 5: Verify** — `uv run pytest tests/test_cloud_reference.py -q && uv run pytest -q` → all pass. (`test_reference_dates_warn_when_old` in `tests/test_build.py` calls `check_reference_dates` directly, so it is unaffected.)
- [ ] **Step 6: Commit** — `git add reference/ web/reference.py web/build.py tests/test_cloud_reference.py && git commit -m "Move curated cloud provider data into a dated reference file, without grades"`

---

### Task 6: Cloud Services page

**Files:** Create `web/pages/cloud_services.py`, `web/templates/cloud-services.html`, `tests/test_cloud_services.py`; Modify `web/build.py` (`PAGES`, `LEGACY_PAGES`, imports), `tests/sample_data.py` (payloads)

**Interfaces:** Consumes Tasks 2–5. Produces `web.pages.cloud_services.context(data) -> dict` with `rows` (`[{"key","name","endpoints": dict|None,"ranges": dict|None,"reference": dict}]`), `endpoints`, `ranges` (Datum combining present `ip_ranges_*`), `aws`, `providers_count`.

- [ ] **Step 1: Sample data** — add to `PAYLOADS` in `tests/sample_data.py`:

```python
    "cloud_endpoints": {
        "providers": [
            {"key": "aws", "name": "AWS", "with_ipv6": 2, "checked": 6,
             "hosts": [{"role": "website", "host": "aws.amazon.com", "status": "ipv6"},
                       {"role": "console", "host": "console.aws.amazon.com", "status": "ipv4_only"},
                       {"role": "api", "host": "ec2.us-east-1.amazonaws.com", "status": "ipv4_only"},
                       {"role": "docs", "host": "docs.aws.amazon.com", "status": "ipv6"},
                       {"role": "storage", "host": "s3.us-east-1.amazonaws.com", "status": "ipv4_only"},
                       {"role": "status", "host": "health.aws.amazon.com", "status": "ipv4_only"}]},
            {"key": "gcp", "name": "Google Cloud Platform", "with_ipv6": 1, "checked": 1,
             "hosts": [{"role": "website", "host": "cloud.google.com", "status": "ipv6"}]},
        ],
        "unknown": 0, "total": 7,
    },
    "aws_ipv6_services": {
        "services": [{"name": "AWS Amplify", "dual_stack": "yes", "ipv6_only": "no", "public_endpoints": "yes",
                      "private_endpoints": None},
                     {"name": "Amazon EC2", "dual_stack": "yes", "ipv6_only": "partial", "public_endpoints": "yes",
                      "private_endpoints": "yes"}],
        "counts": {"dual_stack": {"yes": 2, "partial": 0, "no": 0}, "ipv6_only": {"yes": 0, "partial": 1, "no": 1},
                   "public_endpoints": {"yes": 2, "partial": 0, "no": 0},
                   "private_endpoints": {"yes": 1, "partial": 0, "no": 0}},
        "total": 2, "url": "https://docs.aws.amazon.com/vpc/latest/userguide/aws-ipv6-support.html",
    },
    "ip_ranges_aws": {"ipv4_prefixes": 10628, "ipv6_prefixes": 6944, "services": 27, "services_with_ipv6": 16,
                      "url": "https://ip-ranges.amazonaws.com/ip-ranges.json"},
    "ip_ranges_oracle": {"ipv4_prefixes": 900, "ipv6_prefixes": 0,
                         "url": "https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json"},
```

- [ ] **Step 2: Write the failing tests** — `tests/test_cloud_services.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "cloud-services" / "index.html").read_text()


def test_comparison_table_joins_measured_and_reference(tmp_path):
    _, html = render(tmp_path)
    table = html[html.index("Provider comparison"):html.index("AWS services")]
    assert "Mythic Beasts" in table and "Fly.io" in table        # every reference provider listed
    assert "2 of 6" in table                                      # AWS hostnames with IPv6
    assert "6,944 IPv6 / 10,628 IPv4" in table                    # AWS published prefixes
    assert "0 IPv6 / 900 IPv4" in table                           # Oracle


def test_aws_service_summary(tmp_path):
    _, html = render(tmp_path)
    aws = html[html.index("AWS services"):]
    assert "2 of 2 services" in aws and "Amazon EC2" in aws


def test_provider_reference_shows_review_date(tmp_path):
    _, html = render(tmp_path)
    assert html.count("Reference — last reviewed 2025-10-04") == 23


def test_no_grades(tmp_path):
    _, html = render(tmp_path)
    assert "Grade" not in html   # lowercase "grade" can appear legitimately, e.g. in "upgrade"


def test_hostname_statuses_listed(tmp_path):
    _, html = render(tmp_path)
    assert "console.aws.amazon.com" in html and "IPv4 only" in html


def test_without_measured_sources(tmp_path):
    _, html = render(tmp_path, omit=("cloud_endpoints", "aws_ipv6_services", "ip_ranges_aws", "ip_ranges_oracle"))
    assert "— source unavailable" in html
    assert "Mythic Beasts" in html                                # reference still shown


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Cloud Services' in html
    assert '"Cloud Services": "cloud-services/"' in (out / "index.html").read_text()
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_cloud_services.py -q` → FAIL (`FileNotFoundError`).

- [ ] **Step 4: Implement** — `web/pages/cloud_services.py`:

```python
"""Cloud Services: measured IPv6 for 23 providers next to a dated, curated reference."""
from collect.sources.cloud_ranges import PROVIDERS as RANGE_PROVIDERS
from web import reference
from web.data import Data, combine


def context(data: Data) -> dict:
    providers = reference.load_cloud_providers()
    endpoints = data.datum("cloud_endpoints", lambda p: {e["key"]: e for e in p["providers"]})
    ranges = {key: data.datum(f"ip_ranges_{key}", lambda p: p) for key in RANGE_PROVIDERS}
    present = [d for d in ranges.values() if d is not None]
    rows = [{"key": p["key"], "name": p["name"],
             "endpoints": endpoints.value.get(p["key"]) if endpoints else None,
             "ranges": ranges[p["key"]].value if ranges.get(p["key"]) else None,
             "reference": p}
            for p in providers]
    return {
        "rows": rows,
        "providers_count": len(providers),
        "endpoints": endpoints,
        "ranges": combine({k: d.value for k, d in ranges.items() if d}, present) if present else None,
        "aws": data.datum("aws_ipv6_services", lambda p: p),
    }
```

`web/templates/cloud-services.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import provenance, unavailable, reference, freshness_table %}
{% macro status_label(s) %}{{ {"ipv6": "IPv6", "ipv4_only": "IPv4 only", "unknown": "unknown"}[s] }}{% endmacro %}
{% macro prefixes(r) %}{% if r %}{{ r.ipv6_prefixes | format_value("int") }} IPv6 / {{ r.ipv4_prefixes | format_value("int") }} IPv4{% else %}—{% endif %}{% endmacro %}
{% block content %}
<h1>Cloud Services</h1>
<p>Measured columns are refreshed automatically: whether each provider's own hostnames (website, console, API, docs, storage, status page) publish IPv6 addresses, and how many IPv4 and IPv6 prefixes each provider publishes. The support columns come from a curated reference that shows when it was last reviewed.</p>

<h2>Provider comparison</h2>
<div class="table-wrap"><table>
  <thead><tr><th>Provider</th><th>Own hostnames with IPv6</th><th>Published prefixes</th><th>IPv6 support</th><th>IPv6-only</th><th>Reviewed</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr><td><a href="#{{ r.key }}">{{ r.name }}</a></td>
      <td>{% if r.endpoints %}{{ r.endpoints.with_ipv6 }} of {{ r.endpoints.checked }}{% else %}—{% endif %}</td>
      <td>{{ prefixes(r.ranges) }}</td>
      <td>{{ r.reference.get("overall_support", "—") }}</td>
      <td>{{ r.reference.get("ipv6_only_support", "—") }}</td>
      <td>{{ r.reference.last_reviewed }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
{% if endpoints %}{{ provenance(endpoints) }}{% else %}{{ unavailable() }}{% endif %}
{% if ranges %}{{ provenance(ranges) }}{% endif %}
<p class="provenance">Hostname checks show whether IPv6 addresses are published (AAAA records), not end-to-end reachability. Prefix counts don't compare address space: one IPv6 prefix covers far more addresses than one IPv4 prefix.</p>

<h2>AWS services</h2>
{% if aws %}
<p>Of {{ aws.value.total }} services AWS lists: {{ aws.value.counts.dual_stack.yes }} of {{ aws.value.total }} services support dual-stack ({{ aws.value.counts.dual_stack.partial }} partly), {{ aws.value.counts.ipv6_only.yes }} support IPv6-only ({{ aws.value.counts.ipv6_only.partial }} partly), and {{ aws.value.counts.public_endpoints.yes }} have public endpoints reachable over IPv6.</p>
<details class="source"><summary>All AWS services</summary>
<div class="table-wrap"><table>
  <thead><tr><th>Service</th><th>Dual-stack</th><th>IPv6-only</th><th>Public endpoints</th><th>Private endpoints</th></tr></thead>
  <tbody>
  {% for s in aws.value.services %}
    <tr><td>{{ s.name }}</td><td>{{ s.dual_stack or "—" }}</td><td>{{ s.ipv6_only or "—" }}</td><td>{{ s.public_endpoints or "—" }}</td><td>{{ s.private_endpoints or "—" }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
</details>
{{ provenance(aws) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Providers</h2>
{% for r in rows %}
<details class="source" id="{{ r.key }}">
  <summary>{{ r.name }}</summary>
  <h3>Measured</h3>
  {% if r.endpoints %}
  <ul>{% for h in r.endpoints.hosts %}<li>{{ h.role }}: <code>{{ h.host }}</code> — {{ status_label(h.status) }}</li>{% endfor %}</ul>
  {% else %}<p class="missing">— source unavailable</p>{% endif %}
  {% if r.ranges %}<p>Published prefixes: {{ prefixes(r.ranges) }}{% if r.ranges.services_with_ipv6 is defined %}; {{ r.ranges.services_with_ipv6 }} of {{ r.ranges.services }} services have IPv6 ranges{% endif %}.</p>{% endif %}
  {% call reference(reviewed=r.reference.last_reviewed) %}
    {% set ref = r.reference %}
    <dl>
      {% if ref.get("overall_support") %}<dt>IPv6 support</dt><dd>{{ ref.overall_support }}</dd>{% endif %}
      {% if ref.get("ipv6_only_support") %}<dt>IPv6-only</dt><dd>{{ ref.ipv6_only_support }}</dd>{% endif %}
      {% if ref.get("cost_impact") %}<dt>Cost</dt><dd>{{ ref.cost_impact }}</dd>{% endif %}
      {% if ref.get("outlook") %}<dt>Outlook</dt><dd>{{ ref.outlook }}</dd>{% endif %}
    </dl>
    {% if ref.limitations %}<p><strong>Limitations</strong></p><ul>{% for x in ref.limitations %}<li>{{ x }}</li>{% endfor %}</ul>{% endif %}
    {% if ref.recent_progress %}<p><strong>Recent progress</strong></p><ul>{% for x in ref.recent_progress %}<li>{{ x }}</li>{% endfor %}</ul>{% endif %}
    {% if ref.special_features %}<p><strong>Notable</strong></p><ul>{% for x in ref.special_features %}<li>{{ x }}</li>{% endfor %}</ul>{% endif %}
    {% if ref.service %}
    <div class="table-wrap"><table>
      <thead><tr><th>Service</th><th>Dual-stack</th><th>IPv6-only</th><th>NAT-free IPv6 egress</th><th>Prefix delegation</th></tr></thead>
      <tbody>{% for s in ref.service %}<tr><td>{{ s.name }}</td><td>{{ s.dual_stack }}</td><td>{{ s.ipv6_only }}</td><td>{{ s.nat_free_egress }}</td><td>{{ s.prefix_delegation }}</td></tr>{% endfor %}</tbody>
    </table></div>
    {% endif %}
    {% if ref.notes %}<ul>{% for x in ref.notes %}<li>{{ x }}</li>{% endfor %}</ul>{% endif %}
    {% if ref.get("documentation") %}<p><a href="{{ ref.documentation }}">Provider documentation</a></p>{% endif %}
  {% endcall %}
</details>
{% endfor %}

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

In `web/build.py`: add `cloud_services` to the `from web.pages import ...` line; append `Page("cloud-services", "Cloud Services", cloud_services.context),` as the last `PAGES` entry and `"Cloud Services": "cloud-services/",` as the last `LEGACY_PAGES` entry.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_cloud_services.py -q && uv run pytest -q` → all pass. If `tests/test_no_static_stats.py` flags the template, the cause is a typed number; the template above has none.
- [ ] **Step 6: Commit** — `git add web/ tests/ && git commit -m "Add Cloud Services page: measured provider IPv6 next to a dated reference"`

---

### Task 7: End-to-end run and visual check

- [ ] **Step 1: Live collection** — `uv run python -m collect.run --data-dir data --force --only cloud_endpoints --only aws_ipv6_services --only ip_ranges_aws --only ip_ranges_gcp --only ip_ranges_oracle --only ip_ranges_digitalocean --only ip_ranges_linode --only ip_ranges_cloudflare --only ip_ranges_fastly` → `failed=0`. Then check `data/cloud_endpoints.json` has `unknown` 0 (or a handful) and `data/aws_ipv6_services.json` `total` ≈ 191.
- [ ] **Step 2: Build and look** — `uv run python -m web.build --data-dir data --out dist`; serve `dist/` and open `/cloud-services/` at desktop and 375px width: comparison table, AWS section, provider sections with "Reference — last reviewed" notes. The build prints warnings for the 2025-10-04 review dates (expected, a prompt to review).
- [ ] **Step 3: README** — in the "Pages so far" bullet, change `Country Analysis, and one page per economy` to `Country Analysis, Cloud Services, and one page per economy`, and add a bullet: `- reference/cloud_providers.toml is hand-maintained: update an entry's last_reviewed when you check it; the build warns after 180 days.`
- [ ] **Step 4: Commit** — `uv run pytest -q` → all pass; `git add README.md && git commit -m "Document the Cloud Services page and its reference file"`
