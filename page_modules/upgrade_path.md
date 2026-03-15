The repo is a solid, well-architected Streamlit dashboard with ~48 data collection methods from 20+ sources. The main weaknesses are:

Hardcoded/stale data — Facebook stats are fully hardcoded, several scrapers likely broken
Fragile scraping — Google stats, Cloudflare DNS blog, Cisco 6lab all scrape HTML (brittle)
30-day cache is too coarse — BGP data changes daily but sits stale for a month
Missing dimensions — No mobile carrier data, no RPKI/routing security angle, no ISP-level breakdown, no historical time series
Backlog (saved to memory)
Organized into 4 priority tiers:

P1 — Fix broken sources: Facebook (hardcoded), Cisco 6lab (format changed), Google scraper, Cloudflare DNS blog scraper, Internet Society Pulse validator

P2 — New high-value sources: PeeringDB API, BGP.tools, MANRS Observatory (RPKI), Routeviews, Euro-IX, M-Lab, PCH route data

P3 — New angles: Mobile carrier IPv6, ISP-level APNIC per-AS data, top website IPv6 by category, RPKI/ROA coverage for IPv6 prefixes, government sector tracking, updated and refinement for AWS and Azure.

Routeviews per-ASN RPKI enrichment — add RPKI state breakdown to the existing mobile carrier tab. For each ASN, query Routeviews /asn/{asn} to get prefix list with validation states, computing %_valid, %_invalid, %_notfound. Makes the mobile carrier tab significantly richer.

Routeviews /rirtimeseries as BGP enrichment — lightweight call, gives per-RIR IPv6 prefix counts from Routeviews vantage points to cross-reference existing BGP data.

P4 — Quality/reliability: Shorter TTL for BGP, visible fallback indicators in UI, data freshness timestamps, input validation layer
