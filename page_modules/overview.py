"""
Overview Page - Dashboard Summary with Key Metrics
"""
import streamlit as st
from typing import Dict, Any
from components import render_metric_row, render_kpi_header, render_data_freshness
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

    # Quick Stats Grid
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📈 Google Statistics")
        if google_stats:
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
