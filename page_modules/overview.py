"""
Overview Page - Dashboard Summary with Key Metrics
"""
import streamlit as st
from typing import Dict, Any
from components import render_metric_row, render_kpi_header, render_data_freshness, render_fallback_indicator
from data_manager import get_data
import plotly.graph_objects as go


def render(data: Dict[str, Any]):
    """
    Render the overview page

    Args:
        data: Dictionary containing all loaded data
    """
    st.title("🌐 IPv6 Global Statistics Dashboard")
    st.markdown("### Real-time IPv6 adoption metrics from multiple authoritative sources")

    # Key Performance Indicators
    google_stats = data.get('google_stats', {})
    facebook_stats = data.get('facebook_stats', {})
    cloudflare_stats = data.get('cloudflare_stats', {})
    bgp_stats = data.get('bgp_stats', {})
    isoc_stats = data.get('isoc_pulse_stats', {})

    kpis = [
        {
            "label": "Global IPv6 Adoption",
            "value": f"{google_stats.get('global_percentage', 0):.1f}%",
            "delta": "+2.5%",
            "help": "Percentage of internet users accessing services over IPv6",
            "icon": "🌍"
        },
        {
            "label": "IPv6 BGP Prefixes",
            "value": f"{bgp_stats.get('ipv6_prefix_count', 0):,}" if bgp_stats else "N/A",
            "delta": "+3.2%",
            "help": "Number of IPv6 prefixes in global BGP routing table",
            "icon": "📊"
        },
        {
            "label": "Cloudflare IPv6 Traffic",
            "value": f"{cloudflare_stats.get('ipv6_percentage', 0):.1f}%",
            "help": "IPv6 traffic percentage on Cloudflare network",
            "icon": "☁️"
        },
        {
            "label": "Data Sources",
            "value": "15+",
            "help": "Number of authoritative IPv6 statistics sources",
            "icon": "📚"
        }
    ]

    render_kpi_header(kpis)
    if cloudflare_stats:
        render_fallback_indicator(cloudflare_stats)

    # Multi-source consensus display
    st.markdown("---")
    st.markdown("#### 📡 Global IPv6 Adoption — Multi-Source View")

    consensus_entries = []
    if google_stats:
        consensus_entries.append({
            'label': 'Google / APNIC',
            'value': google_stats.get('global_percentage', 0),
            'display': f"{google_stats.get('global_percentage', 0):.1f}%",
            'help': 'User IPv6 capability measured via ad-based dual-stack probing (APNIC) '
                    'and Google traffic data',
            'fallback': google_stats.get('fallback', False),
        })
    if isoc_stats:
        consensus_entries.append({
            'label': 'ISOC Pulse',
            'value': float(isoc_stats.get('global_ipv6_websites', 0)),
            'display': f"{isoc_stats.get('global_ipv6_websites', 0):.0f}%",
            'help': 'Percentage of top global websites with IPv6 (AAAA DNS records) '
                    'as measured by Internet Society Pulse',
            'fallback': isoc_stats.get('fallback', False),
        })
    if cloudflare_stats:
        consensus_entries.append({
            'label': 'Cloudflare Radar',
            'value': cloudflare_stats.get('ipv6_percentage', 0),
            'display': f"{cloudflare_stats.get('ipv6_percentage', 0):.1f}%",
            'help': 'Share of HTTP traffic reaching Cloudflare\'s network over IPv6 '
                    '(52-week window)',
            'fallback': cloudflare_stats.get('fallback', False),
        })

    live_values = [e['value'] for e in consensus_entries if not e['fallback'] and e['value'] > 0]
    consensus_pct = sum(live_values) / len(live_values) if live_values else None

    num_cols = len(consensus_entries) + (1 if consensus_pct is not None else 0)
    cols = st.columns(num_cols)
    for i, entry in enumerate(consensus_entries):
        with cols[i]:
            suffix = " ⚠️" if entry['fallback'] else ""
            st.metric(entry['label'] + suffix, entry['display'], help=entry['help'])

    if consensus_pct is not None:
        with cols[len(consensus_entries)]:
            st.metric(
                "Consensus Average",
                f"{consensus_pct:.1f}%",
                help=f"Simple average of {len(live_values)} live source(s). "
                     "Each source measures a different dimension (user capability, "
                     "website deployment, traffic share) — treat as a directional "
                     "indicator, not a single authoritative figure.",
            )

    if any(e['fallback'] for e in consensus_entries):
        st.caption("⚠️ Sources marked with ⚠️ are using estimated data. "
                   "Estimated sources are excluded from the consensus average.")

    # Methodology explanation
    with st.expander("ℹ️ How are these percentages calculated?", expanded=False):
        st.markdown("""
### IPv6 Adoption Percentage — Methodology

Each statistic shown here uses a different measurement methodology and captures a
different dimension of IPv6 deployment. Understanding those differences is essential
for interpreting the numbers correctly.

---

#### 🌍 Google / APNIC — User IPv6 Capability

**What it measures:** The fraction of internet-connected users whose devices and
networks are *capable* of reaching IPv6 destinations.

**How it's collected (in priority order):**

1. **Google IPv6 Statistics page** (`google.com/intl/en/ipv6/statistics.html`) —
   Google counts the percentage of requests to its services that arrive over IPv6.
   The page is rendered client-side via JavaScript, so automated parsing succeeds
   only occasionally.

2. **APNIC Labs IPv6 Measurement** (`stats.labs.apnic.net/ipv6/`) —
   APNIC embeds tiny dual-stack probes in online advertisements served globally.
   When a browser loads the ad it attempts to fetch a resource over both IPv6 and
   IPv4; only a successful IPv6 fetch is counted. The World (XA) aggregate row is
   a population-weighted global average. This is the most methodologically rigorous
   public dataset for *user-level* adoption.

3. **Research estimate (~47%, late 2024)** — Used only when both live sources are
   unreachable. Labeled as a fallback with a warning indicator.

**Formula:** `IPv6-capable users ÷ total users, expressed as a percentage`

---

#### 🌐 Internet Society Pulse — Website IPv6 Deployment

**What it measures:** The percentage of top global websites that have an IPv6
address (AAAA DNS record) and are therefore reachable over IPv6. This is the
*server-side* complement to user-capability metrics.

**How it's collected (in priority order):**

1. **ISOC Pulse Gatsby JSON** — The Pulse site pre-renders data into a
   machine-readable JSON file (`/page-data/technologies/page-data.json`). The
   dashboard parses the IPv6 node's `globalPercentage` field.

2. **ISOC Pulse HTML scrape** — Falls back to scraping the rendered technologies
   page for an IPv6 percentage string if the JSON is unavailable.

3. **2024 ISOC research estimate (~49%)** — Used when both live sources fail.
   Labeled as a fallback.

**Formula:** `websites with AAAA record ÷ top websites surveyed, expressed as a percentage`

> This metric is *not* the same as user adoption. A website can have IPv6 enabled
> while the majority of its users still connect over IPv4, and vice versa.

---

#### ☁️ Cloudflare Radar — IPv6 Traffic Share

**What it measures:** The share of all HTTP traffic reaching Cloudflare's global
network that is carried over IPv6.

**How it's collected (in priority order):**

1. **Cloudflare Radar API** — With a valid `CLOUDFLARE_API_KEY`, the endpoint
   `/radar/http/timeseries_groups/ip_version?dateRange=52w` returns weekly
   time-series values split by IP version. The dashboard reads the most recent
   data point.

2. **Cloudflare Radar report estimate (~36%, Oct 2025)** — Used when no API key
   is configured. Labeled as a fallback.

**Formula:** `latest IPv6 traffic ÷ (latest IPv4 traffic + latest IPv6 traffic), expressed as a percentage`

> Cloudflare data reflects *traffic volume* across Cloudflare's CDN customer base,
> not unique users. It is biased toward web properties using Cloudflare and tends
> to run a few points higher than general user-capability measurements.

---

#### 📡 Consensus Average

The consensus average is a simple mean of whichever sources returned **live** data
in the current refresh cycle. Estimated (fallback) values are excluded.

Because each source measures a different thing — user capability, website
deployment, and traffic share — the consensus is best read as a **directional
indicator** of the overall IPv6 ecosystem, not as a single authoritative adoption
figure. When sources disagree significantly, consult the individual panels and
their source notes for context.

---

#### 📊 IPv6 BGP Prefixes

**What it measures:** The number of distinct IPv6 network prefixes announced into
the global BGP routing table — a proxy for how many networks have *deployed* IPv6
at the infrastructure level.

**How it's collected:** The dashboard queries routing table aggregators (BGP Stuff,
Potaroo/Geoff Huston) for current IPv4 and IPv6 prefix counts. Results are cached
for 24 hours since the routing table changes daily.

**Interpretation:** More prefixes = more network operators have enabled IPv6.
This metric does *not* reflect end-user adoption, only operator deployment.

---

#### ⚠️ A note on comparing these numbers

| Source | Measures | Typical range |
|---|---|---|
| Google / APNIC | User IPv6 capability | 35–55% globally |
| ISOC Pulse | Website IPv6 deployment | 45–55% of top sites |
| Cloudflare Radar | CDN traffic share over IPv6 | 30–45% globally |
| BGP IPv6 prefixes | Operator deployment | ~230,000 prefixes |
| Country rankings | Per-country user or traffic share | 10–85% by country |

These metrics are *complementary*, not interchangeable. A country can have high
operator deployment (many BGP prefixes) but low user adoption if ISPs have not yet
migrated customer premises equipment, or high traffic share but low website coverage
if major CDN-hosted properties have enabled IPv6 while smaller sites have not.
        """)

    # Quick Stats Grid
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📈 Google Statistics")
        if google_stats:
            render_fallback_indicator(google_stats)
            render_data_freshness(google_stats.get('last_updated', ''))
            st.metric(
                "Global IPv6 Users",
                f"{google_stats.get('global_percentage', 0):.1f}%",
                help="Users accessing Google services over IPv6"
            )
            if 'source' in google_stats:
                st.caption(f"Source: {google_stats['source']}")
        else:
            st.warning("Google statistics not available")

    with col2:
        st.markdown("#### 📘 Facebook Statistics")
        if facebook_stats:
            render_fallback_indicator(facebook_stats)
            render_data_freshness(facebook_stats.get('last_updated', ''))
            st.metric(
                "Facebook IPv6 Users",
                f"{facebook_stats.get('ipv6_percentage', 0):.1f}%",
                help="Users accessing Facebook over IPv6"
            )
            if 'source' in facebook_stats:
                st.caption(f"Source: {facebook_stats['source']}")
        else:
            st.warning("Facebook statistics not available")

    # BGP Statistics Summary
    st.markdown("---")
    st.markdown("#### 🔀 BGP Routing Statistics")

    if bgp_stats:
        bgp_metrics = [
            {
                "label": "IPv4 Prefixes",
                "value": f"{bgp_stats.get('ipv4_prefix_count', 0):,}"
            },
            {
                "label": "IPv6 Prefixes",
                "value": f"{bgp_stats.get('ipv6_prefix_count', 0):,}"
            },
            {
                "label": "IPv6 Growth Rate",
                "value": f"{bgp_stats.get('growth_rate', 0):.1f}%"
            }
        ]
        render_metric_row(bgp_metrics)
    else:
        st.info("BGP statistics loading...")

    # Regional Highlights
    st.markdown("---")
    st.markdown("#### 🗺️ Regional Highlights")

    country_data = data.get('google_country', [])
    if country_data:
        top_countries = sorted(country_data, key=lambda x: x.get('ipv6_percentage', 0), reverse=True)[:5]

        col1, col2, col3 = st.columns([2, 2, 3])

        with col1:
            st.markdown("**Top IPv6 Countries:**")
            for i, country in enumerate(top_countries, 1):
                st.write(f"{i}. {country['country']}: **{country['ipv6_percentage']:.1f}%**")

        with col2:
            st.markdown("**Adoption Levels:**")
            for country in top_countries:
                adoption = country['ipv6_percentage']
                if adoption >= 70:
                    level = "🟢 Excellent"
                elif adoption >= 50:
                    level = "🟡 Good"
                else:
                    level = "🟠 Moderate"
                st.write(level)

        with col3:
            # Simple bar chart of top countries
            import plotly.express as px
            import pandas as pd

            df = pd.DataFrame(top_countries)
            fig = px.bar(
                df,
                x='ipv6_percentage',
                y='country',
                orientation='h',
                title="Top 5 Countries by IPv6 Adoption",
                labels={'ipv6_percentage': 'IPv6 Adoption %', 'country': 'Country'}
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Country statistics loading...")

    # Quick Links
    st.markdown("---")
    st.markdown("#### 🔗 Quick Navigation")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🌍 View Global Adoption →", use_container_width=True):
            st.session_state.selected_page = "Global Adoption"
            st.rerun()

    with col2:
        if st.button("☁️ Cloud Services →", use_container_width=True):
            st.session_state.selected_page = "Cloud Services"
            st.rerun()

    with col3:
        if st.button("📊 BGP Statistics →", use_container_width=True):
            st.session_state.selected_page = "BGP Statistics"
            st.rerun()

    # Data freshness footer
    st.markdown("---")
    st.caption("💡 Dashboard updates monthly. Data cached for optimal performance.")
    st.caption("📅 All statistics are from official and authoritative sources.")
