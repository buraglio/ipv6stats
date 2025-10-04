"""
BGP Statistics Page - IPv6 routing table analysis
"""
import streamlit as st
from typing import Dict, Any
import plotly.graph_objects as go
from components import render_metric_row, render_data_freshness


def render(data: Dict[str, Any]):
    """
    Render the BGP statistics page

    Args:
        data: Dictionary containing all loaded data
    """
    st.title("🔀 BGP Routing Statistics")

    bgp_stats = data.get('bgp_stats', {})

    if not bgp_stats:
        st.warning("BGP statistics are currently loading...")
        return

    # Key metrics
    st.markdown("### 📊 Global BGP Table Statistics")

    metrics = [
        {
            "label": "IPv4 Prefixes",
            "value": f"{bgp_stats.get('ipv4_prefix_count', 0):,}",
            "help": "Number of IPv4 prefixes in global BGP routing table"
        },
        {
            "label": "IPv6 Prefixes",
            "value": f"{bgp_stats.get('ipv6_prefix_count', 0):,}",
            "help": "Number of IPv6 prefixes in global BGP routing table"
        },
        {
            "label": "IPv6 Growth Rate",
            "value": f"{bgp_stats.get('growth_rate', 0):.1f}%",
            "delta": "+0.5%",
            "help": "Year-over-year growth in IPv6 prefixes"
        },
        {
            "label": "IPv6 vs IPv4 Ratio",
            "value": f"{(bgp_stats.get('ipv6_prefix_count', 0) / max(bgp_stats.get('ipv4_prefix_count', 1), 1) * 100):.1f}%",
            "help": "IPv6 prefixes as percentage of IPv4 prefixes"
        }
    ]

    render_metric_row(metrics)
    render_data_freshness(bgp_stats.get('last_updated', ''))

    st.markdown("---")

    # Comparison chart
    st.markdown("### 📈 IPv4 vs IPv6 Prefix Comparison")

    fig = go.Figure(data=[
        go.Bar(
            name='IPv4',
            x=['Prefixes'],
            y=[bgp_stats.get('ipv4_prefix_count', 0)],
            marker_color='#1f77b4'
        ),
        go.Bar(
            name='IPv6',
            x=['Prefixes'],
            y=[bgp_stats.get('ipv6_prefix_count', 0)],
            marker_color='#2ca02c'
        )
    ])

    fig.update_layout(
        title='BGP Prefix Count Comparison',
        yaxis_title='Number of Prefixes',
        barmode='group',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # Additional statistics
    st.markdown("---")
    st.markdown("### 📋 Detailed Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### IPv4 Details")
        if 'ipv4_as_count' in bgp_stats:
            st.metric("Autonomous Systems (AS)", f"{bgp_stats['ipv4_as_count']:,}")
        st.metric("Total Prefixes", f"{bgp_stats.get('ipv4_prefix_count', 0):,}")

    with col2:
        st.markdown("#### IPv6 Details")
        if 'ipv6_as_count' in bgp_stats:
            st.metric("Autonomous Systems (AS)", f"{bgp_stats['ipv6_as_count']:,}")
        st.metric("Total Prefixes", f"{bgp_stats.get('ipv6_prefix_count', 0):,}")

    # Information
    st.markdown("---")
    st.info("""
    **About BGP Statistics:**

    BGP (Border Gateway Protocol) is the routing protocol used to exchange routing information
    across the internet. These statistics show the number of IPv4 and IPv6 network prefixes
    currently announced in the global routing table.

    - Higher IPv6 prefix counts indicate more networks have deployed IPv6
    - Growth rate shows the pace of IPv6 adoption at the network level
    - AS (Autonomous System) numbers represent unique network operators
    """)

    st.caption("📚 Data source: Global BGP routing table measurements")
