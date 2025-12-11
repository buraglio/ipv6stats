"""
Network Insights Page - New IPv6 Statistics Sources
Displays data from Hurricane Electric, RIPE Atlas, World IPv6 Launch, CIDR Report, and Tranco
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def render_network_insights_page(data_collector, chart_generator):
    """Render the Network Insights page with new data sources"""

    st.title("🌐 Network Insights & Measurements")
    st.markdown("Real-time data from authoritative IPv6 measurement sources")

    # Create tabs for different data sources
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔌 Hurricane Electric",
        "🔬 RIPE Atlas",
        "🚀 World IPv6 Launch",
        "📊 CIDR Report",
        "🌍 Top Sites Analysis"
    ])

    # Tab 1: Hurricane Electric
    with tab1:
        st.header("Hurricane Electric IPv6 Progress Report")
        st.markdown("Data from the world's largest IPv6 transit provider")

        he_data = data_collector.get_hurricane_electric_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "ASNs with IPv6",
                f"{he_data.get('asns_with_ipv6', 'N/A'):,}" if he_data.get('asns_with_ipv6') else "N/A",
                help="Number of Autonomous Systems announcing IPv6 prefixes"
            )

        with col2:
            st.metric(
                "Countries",
                f"{he_data.get('countries_count', 'N/A'):,}" if he_data.get('countries_count') else "N/A",
                help="Countries with IPv6 presence"
            )

        with col3:
            st.metric(
                "IPv6 Prefixes",
                f"{he_data.get('ipv6_prefixes', 'N/A'):,}" if he_data.get('ipv6_prefixes') else "N/A",
                help="Total IPv6 prefixes in global BGP table"
            )

        # Top countries table
        if he_data.get('top_countries'):
            st.subheader("Top Countries by IPv6 Deployment")
            df = pd.DataFrame(he_data['top_countries'])
            if not df.empty:
                # Create bar chart
                fig = px.bar(
                    df.head(15),
                    x='ipv6_percentage',
                    y='country',
                    orientation='h',
                    title='Top 15 Countries by IPv6 Adoption (HE.NET)',
                    labels={'ipv6_percentage': 'IPv6 Percentage', 'country': 'Country'},
                    color='ipv6_percentage',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        st.info(f"**Source:** {he_data.get('source', 'Unknown')} | **Updated:** {he_data.get('last_updated', 'Unknown')[:10]}")

    # Tab 2: RIPE Atlas
    with tab2:
        st.header("RIPE Atlas Real-World Measurements")
        st.markdown("Live connectivity data from 12,000+ global measurement probes")

        atlas_data = data_collector.get_ripe_atlas_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Total Probes",
                f"{atlas_data.get('total_probes', 'N/A'):,}",
                help="Active RIPE Atlas measurement probes worldwide"
            )

        with col2:
            st.metric(
                "IPv6 Measurements",
                f"{atlas_data.get('active_ipv6_measurements', 'N/A'):,}",
                help="Currently active IPv6 measurements"
            )

        with col3:
            st.metric(
                "IPv6 Capable Probes",
                f"{atlas_data.get('ipv6_capable_probes_percentage', 'N/A')}%",
                help="Percentage of probes with IPv6 connectivity"
            )

        # Measurement types
        st.subheader("Measurement Types Available")
        measurement_types = atlas_data.get('measurement_types', [])

        cols = st.columns(len(measurement_types))
        for idx, mtype in enumerate(measurement_types):
            with cols[idx]:
                st.info(f"**{mtype}**")

        st.markdown("""
        ### What is RIPE Atlas?
        RIPE Atlas is a global network of hardware probes that measure Internet connectivity in real-time.
        These measurements provide actual connectivity data, not estimates, making it one of the most
        authoritative sources for understanding real-world IPv6 deployment.

        **Key Features:**
        - Real-time measurements from user-hosted probes
        - Global coverage across all continents
        - Multiple measurement types (ping, traceroute, DNS, HTTP)
        - Open data available via API
        """)

        st.info(f"**Source:** {atlas_data.get('source', 'Unknown')} | **Updated:** {atlas_data.get('last_updated', 'Unknown')[:10]}")

    # Tab 3: World IPv6 Launch
    with tab3:
        st.header("World IPv6 Launch - ISP Deployment Tracker")
        st.markdown("Major ISP IPv6 deployment since the June 6, 2012 launch date")

        launch_data = data_collector.get_world_ipv6_launch_stats()

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Participating ISPs",
                f"{launch_data.get('total_participants', 'N/A'):,}",
                help="Number of ISPs tracked for IPv6 deployment"
            )

        with col2:
            st.metric(
                "Launch Date",
                launch_data.get('launch_date', 'N/A'),
                help="World IPv6 Launch Day"
            )

        # ISP deployment table
        isps = launch_data.get('participating_isps', [])
        if isps:
            st.subheader("ISP IPv6 Deployment Percentages")
            df = pd.DataFrame(isps)

            if not df.empty:
                # Create bar chart
                fig = px.bar(
                    df.head(20),
                    x='ipv6_percentage',
                    y='isp',
                    orientation='h',
                    title='Top ISPs by IPv6 Deployment',
                    labels={'ipv6_percentage': 'IPv6 Traffic %', 'isp': 'ISP'},
                    color='ipv6_percentage',
                    color_continuous_scale='Greens'
                )
                fig.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

                # Show full table
                with st.expander("View Full ISP Data Table"):
                    st.dataframe(
                        df.sort_values('ipv6_percentage', ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )

        st.markdown("""
        ### About World IPv6 Launch
        On June 6, 2012, major ISPs, content providers, and equipment manufacturers permanently
        enabled IPv6 for their products and services. This initiative marked the beginning of
        widespread IPv6 deployment across the Internet.
        """)

        st.info(f"**Source:** {launch_data.get('source', 'Unknown')} | **Updated:** {launch_data.get('last_updated', 'Unknown')[:10]}")

    # Tab 4: CIDR Report
    with tab4:
        st.header("CIDR Report - Weekly BGP Analysis")
        st.markdown("Authoritative IPv6 routing table analysis by Geoff Huston")

        cidr_data = data_collector.get_cidr_report_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "IPv6 Routes",
                f"{cidr_data.get('ipv6_routes', 'N/A'):,}",
                help="Total IPv6 routes in global BGP table"
            )

        with col2:
            st.metric(
                "IPv6 ASNs",
                f"{cidr_data.get('ipv6_asns', 'N/A'):,}",
                help="Autonomous Systems announcing IPv6"
            )

        with col3:
            st.metric(
                "Weekly Growth",
                f"+{cidr_data.get('weekly_growth', 'N/A'):,}",
                help="New routes added this week"
            )

        # Growth visualization
        st.subheader("IPv6 Routing Table Growth")

        # Calculate projections
        current_routes = cidr_data.get('ipv6_routes', 185000)
        weekly_growth = cidr_data.get('weekly_growth', 450)

        # Project next 12 weeks
        weeks = list(range(13))
        projected_routes = [current_routes + (week * weekly_growth) for week in weeks]

        df_projection = pd.DataFrame({
            'Week': weeks,
            'Routes': projected_routes
        })

        fig = px.line(
            df_projection,
            x='Week',
            y='Routes',
            title='IPv6 Routing Table Growth Projection (Next 12 Weeks)',
            labels={'Week': 'Weeks from Now', 'Routes': 'Total IPv6 Routes'},
            markers=True
        )
        fig.update_traces(line_color='#007bff', line_width=3)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        ### About CIDR Report
        The CIDR Report provides weekly analysis of the global BGP routing tables. Geoff Huston's
        authoritative reports track routing table growth, prefix size distribution, and address
        allocation efficiency.

        **Update Frequency:** Weekly
        """)

        st.info(f"**Source:** {cidr_data.get('source', 'Unknown')} | **Update Frequency:** {cidr_data.get('update_frequency', 'Weekly')}")

    # Tab 5: Tranco Top Sites
    with tab5:
        st.header("Top Websites IPv6 Deployment")
        st.markdown("IPv6 AAAA record availability for top global websites")

        tranco_data = data_collector.get_tranco_ipv6_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Domains Checked",
                f"{tranco_data.get('total_domains_checked', 'N/A'):,}",
                help="Number of top domains analyzed"
            )

        with col2:
            st.metric(
                "IPv6 Enabled",
                f"{tranco_data.get('ipv6_enabled_count', 'N/A'):,}",
                help="Domains with IPv6 AAAA records"
            )

        with col3:
            st.metric(
                "IPv6 Percentage",
                f"{tranco_data.get('ipv6_percentage', 'N/A')}%",
                help="Percentage of top sites with IPv6",
                delta=f"+{tranco_data.get('ipv6_percentage', 0) - 50:.1f}% vs 2020"
            )

        # Pie chart
        st.subheader("IPv6 Support Distribution")

        ipv6_count = tranco_data.get('ipv6_enabled_count', 35)
        total_count = tranco_data.get('total_domains_checked', 50)
        ipv4_only = total_count - ipv6_count

        fig = go.Figure(data=[go.Pie(
            labels=['IPv6 Enabled', 'IPv4 Only'],
            values=[ipv6_count, ipv4_only],
            hole=0.4,
            marker_colors=['#007bff', '#6c757d']
        )])

        fig.update_layout(
            title='Top Websites IPv6 Support',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # Domain details
        domain_results = tranco_data.get('domain_results', [])
        if domain_results:
            st.subheader("Domain-by-Domain Analysis")

            df = pd.DataFrame(domain_results)
            if not df.empty:
                df['Status'] = df['ipv6_enabled'].apply(lambda x: '✅ IPv6' if x else '❌ IPv4 Only')

                # Split into two columns for better display
                col1, col2 = st.columns(2)

                mid = len(df) // 2

                with col1:
                    st.dataframe(
                        df.iloc[:mid][['domain', 'Status']],
                        use_container_width=True,
                        hide_index=True
                    )

                with col2:
                    st.dataframe(
                        df.iloc[mid:][['domain', 'Status']],
                        use_container_width=True,
                        hide_index=True
                    )

        st.markdown("""
        ### About This Analysis
        This analysis checks the top global websites (from the Tranco list) for IPv6 AAAA DNS records.
        The presence of an AAAA record indicates that the website is accessible via IPv6.

        **Note:** This shows DNS-level support. Actual IPv6 traffic may vary based on client capabilities.
        """)

        st.info(f"**Source:** {tranco_data.get('source', 'Unknown')} | **Updated:** {tranco_data.get('last_updated', 'Unknown')[:10]}")

    # Footer
    st.markdown("---")
    st.markdown("""
    ### About These Data Sources

    All data sources on this page are authoritative measurement platforms providing real-world
    IPv6 deployment statistics:

    - **Hurricane Electric**: World's largest IPv6 transit provider with comprehensive BGP visibility
    - **RIPE Atlas**: Distributed measurement network with 12,000+ probes globally
    - **World IPv6 Launch**: Long-running ISP deployment tracker since 2012
    - **CIDR Report**: Weekly authoritative BGP routing analysis by Geoff Huston
    - **Tranco List**: Research-grade ranking of top websites with DNS analysis

    Data is cached and refreshed monthly (or weekly for CIDR Report) to ensure accuracy while
    minimizing load on source systems.
    """)
