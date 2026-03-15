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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
        "🔌 Hurricane Electric",
        "🔬 RIPE Atlas",
        "🚀 World IPv6 Launch",
        "📊 CIDR Report",
        "🌍 Top Sites Analysis",
        "🏢 PeeringDB",
        "🛡️ RPKI Security",
        "🔄 IXP Data",
        "📱 Mobile Carriers",
        "🏛️ Government IPv6",
        "☁️ AWS Coverage",
        "🔷 Azure Coverage",
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

    # Tab 6: PeeringDB
    with tab6:
        st.header("PeeringDB — Network Operator IPv6 Adoption")
        st.markdown("Self-reported IPv6 capability from the authoritative registry for peering information")

        pdb_data = data_collector.get_peeringdb_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Total Networks",
                f"{pdb_data.get('total_networks', 0):,}",
                help="Active networks registered in PeeringDB"
            )

        with col2:
            st.metric(
                "IPv6-Enabled Networks",
                f"{pdb_data.get('ipv6_enabled_networks', 0):,}",
                help="Networks with IPv6 self-reported (info_ipv6 flag)"
            )

        with col3:
            st.metric(
                "IPv6 Adoption",
                f"{pdb_data.get('ipv6_adoption_pct', 0)}%",
                help="Percentage of registered networks reporting IPv6 support"
            )

        top_nets = pdb_data.get('top_ipv6_networks', [])
        if top_nets:
            st.subheader("Sample IPv6-Enabled Networks")
            df = pd.DataFrame(top_nets)
            if not df.empty:
                display_cols = [c for c in ['name', 'asn', 'info_type', 'policy_general'] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        if pdb_data.get('error'):
            st.warning(f"Data unavailable: {pdb_data['error']}")

        st.info(
            f"**Source:** {pdb_data.get('source', 'PeeringDB')} | "
            f"**Note:** {pdb_data.get('note', '')} | "
            f"**Updated:** {pdb_data.get('last_updated', '')[:10]}"
        )

    # Tab 7: RPKI Security
    with tab7:
        st.header("RPKI Route Origin Authorization — IPv6 Routing Security")
        st.markdown("RPKI ROA coverage for the global IPv6 routing table (RIPE STAT)")

        rpki_data = data_collector.get_rpki_ipv6_stats()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "IPv6 Prefixes",
                f"{rpki_data.get('ipv6_total_prefixes', 0):,}",
                help="Total IPv6 prefixes in the global routing table"
            )

        with col2:
            st.metric(
                "Valid ROAs",
                f"{rpki_data.get('ipv6_valid_roas', 0):,}",
                help="IPv6 prefixes with a valid RPKI ROA"
            )

        with col3:
            st.metric(
                "IPv6 RPKI Coverage",
                f"{rpki_data.get('ipv6_valid_pct', 0)}%",
                help="% of IPv6 prefixes with a valid ROA"
            )

        with col4:
            st.metric(
                "IPv4 RPKI Coverage",
                f"{rpki_data.get('ipv4_valid_pct', 0)}%",
                help="% of IPv4 prefixes with a valid ROA (for comparison)"
            )

        # Donut chart comparing IPv6 vs IPv4 RPKI coverage
        ipv6_pct = rpki_data.get('ipv6_valid_pct', 0)
        ipv4_pct = rpki_data.get('ipv4_valid_pct', 0)

        if ipv6_pct or ipv4_pct:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='IPv6',
                x=['IPv6', 'IPv4'],
                y=[ipv6_pct, ipv4_pct],
                marker_color=['#0066cc', '#ff6600'],
                text=[f'{ipv6_pct}%', f'{ipv4_pct}%'],
                textposition='outside',
            ))
            fig.update_layout(
                title='RPKI ROA Coverage: IPv6 vs IPv4',
                yaxis_title='% Prefixes with Valid ROA',
                yaxis_range=[0, 100],
                height=350,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **What is RPKI?** Resource Public Key Infrastructure (RPKI) is a cryptographic framework
        that allows network operators to publish Route Origin Authorizations (ROAs), binding
        an AS number to the prefixes it is authorized to announce. Higher coverage means fewer
        route hijack opportunities. IPv6 has historically trailed IPv4 in RPKI deployment.
        """)

        if rpki_data.get('error'):
            st.warning(f"Data unavailable: {rpki_data['error']}")

        st.info(
            f"**Source:** {rpki_data.get('source', 'RIPE STAT')} | "
            f"**Updated:** {rpki_data.get('last_updated', '')[:10]}"
        )

    # Tab 8: IXP Data (Euro-IX)
    with tab8:
        st.header("IXP IPv6 Adoption — Major Internet Exchange Points")
        st.markdown(
            "IPv6 member adoption at major IXPs, sourced from Euro-IX IXPDB "
            "and per-IXP IX-F member exports"
        )

        ixp_data = data_collector.get_euro_ix_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "IXPs Sampled",
                f"{ixp_data.get('total_ixps_sampled', 0)}",
                help="Major IXPs with live IXF member exports"
            )

        with col2:
            st.metric(
                "Members Analyzed",
                f"{ixp_data.get('total_members_sampled', 0):,}",
                help="Total IXP member connections across sampled IXPs"
            )

        with col3:
            st.metric(
                "IPv6 Member Adoption",
                f"{ixp_data.get('aggregate_ipv6_pct', 0)}%",
                help="% of IXP members with at least one IPv6 connection"
            )

        ixp_results = ixp_data.get('ixp_results', [])
        if ixp_results:
            st.subheader("Per-IXP IPv6 Adoption")
            df = pd.DataFrame(ixp_results)

            fig = px.bar(
                df,
                x='ipv6_pct',
                y='name',
                orientation='h',
                title='IPv6 Member Adoption by IXP',
                labels={'ipv6_pct': 'Members with IPv6 (%)', 'name': 'IXP'},
                color='ipv6_pct',
                color_continuous_scale='Blues',
                text='ipv6_pct',
            )
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            fig.update_layout(height=max(300, len(df) * 50), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("View IXP Detail Table"):
                display_cols = [c for c in
                                ['name', 'country', 'total_members', 'ipv6_members', 'ipv6_pct', 'manrs']
                                if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        if ixp_data.get('error'):
            st.warning(f"Data unavailable: {ixp_data['error']}")
        else:
            st.caption(ixp_data.get('note', ''))

        st.info(
            f"**Source:** {ixp_data.get('source', 'Euro-IX IXPDB')} | "
            f"**Updated:** {ixp_data.get('last_updated', '')[:10]}"
        )

    # Tab 9: Mobile Carriers
    with tab9:
        st.header("Mobile & Broadband Carrier IPv6 Deployment")
        st.markdown(
            "IPv6 prefix announcements (RIPE STAT live) and estimated user adoption "
            "percentages (APNIC/research) for major global carriers."
        )

        carrier_data = data_collector.get_mobile_carrier_ipv6_stats()
        carriers = carrier_data.get('carriers', [])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Carriers Checked",
                carrier_data.get('total_carriers', 0),
                help="Number of carrier ASNs queried via RIPE STAT"
            )
        with col2:
            st.metric(
                "Announcing IPv6",
                carrier_data.get('carriers_with_ipv6', 0),
                help="Carriers with at least one IPv6 prefix in BGP"
            )
        with col3:
            st.metric(
                "IPv6 Prefix Rate",
                f"{carrier_data.get('adoption_pct', 0)}%",
                help="% of checked carriers advertising IPv6 prefixes"
            )

        if carriers:
            df_c = pd.DataFrame(carriers)

            # Bar chart of estimated adoption %
            fig = px.bar(
                df_c.sort_values('est_ipv6_pct', ascending=True),
                x='est_ipv6_pct',
                y='name',
                orientation='h',
                title='Estimated IPv6 User Adoption by Carrier',
                labels={'est_ipv6_pct': 'IPv6 Adoption % (estimate)', 'name': 'Carrier'},
                color='est_ipv6_pct',
                color_continuous_scale='Blues',
                text='est_ipv6_pct',
            )
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            fig.update_layout(height=max(300, len(df_c) * 40), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("View Carrier Detail Table"):
                display_cols = [c for c in
                    ['name', 'country', 'asn', 'est_ipv6_pct', 'ipv6_prefixes', 'ipv4_prefixes', 'has_ipv6']
                    if c in df_c.columns]
                st.dataframe(df_c[display_cols], use_container_width=True, hide_index=True)

        if carrier_data.get('error'):
            st.warning(f"Data partially unavailable: {carrier_data['error']}")

        st.caption(carrier_data.get('note', ''))
        st.info(
            f"**Source:** {carrier_data.get('source', 'RIPE STAT')} | "
            f"**Updated:** {carrier_data.get('last_updated', '')[:10]}"
        )

        # Routeviews enrichment: BGP prefix visibility per carrier
        st.markdown("---")
        st.subheader("🌐 Routeviews BGP Prefix Visibility")
        st.markdown(
            "IPv4 and IPv6 prefix counts as observed by "
            "[Routeviews](https://api.routeviews.org/) global route collectors — "
            "an independent vantage point alongside RIPE STAT data above."
        )

        rv_carrier = data_collector.get_routeviews_carrier_bgp()
        rv_carriers = rv_carrier.get('carriers', [])

        if rv_carriers:
            rvc_col1, rvc_col2 = st.columns(2)
            with rvc_col1:
                st.metric(
                    "Carriers with IPv6 BGP",
                    f"{rv_carrier.get('carriers_with_ipv6_bgp', 0)} / {rv_carrier.get('total_carriers', 0)}",
                    help="Carriers advertising at least one IPv6 prefix into Routeviews collectors"
                )
            with rvc_col2:
                st.metric(
                    "Total IPv6 Prefixes Observed",
                    f"{rv_carrier.get('total_ipv6_prefixes_seen', 0):,}",
                    help="Sum of all IPv6 prefixes across all carrier ASNs"
                )

            rv_df = pd.DataFrame(rv_carriers)
            fig_rv = go.Figure()
            fig_rv.add_trace(go.Bar(
                name='IPv6',
                x=rv_df['name'],
                y=rv_df['ipv6_prefixes'],
                marker_color='#0066cc',
                text=rv_df['ipv6_prefixes'],
                textposition='outside',
            ))
            fig_rv.add_trace(go.Bar(
                name='IPv4',
                x=rv_df['name'],
                y=rv_df['ipv4_prefixes'],
                marker_color='#aaaaaa',
                text=rv_df['ipv4_prefixes'],
                textposition='outside',
            ))
            fig_rv.update_layout(
                title='Carrier BGP Prefix Counts (Routeviews View)',
                barmode='group',
                xaxis_tickangle=-30,
                yaxis_title='Prefix Count',
                height=420,
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
            )
            st.plotly_chart(fig_rv, use_container_width=True)

            with st.expander("View Routeviews Carrier Detail Table"):
                rv_display = [c for c in
                    ['name', 'asn', 'ipv6_prefixes', 'ipv4_prefixes', 'has_ipv6_bgp']
                    if c in rv_df.columns]
                st.dataframe(rv_df[rv_display], use_container_width=True, hide_index=True)
        else:
            st.info("Routeviews carrier BGP data unavailable.")

        st.caption(rv_carrier.get('note', ''))
        st.info(
            f"**Source:** {rv_carrier.get('source', 'Routeviews')} | "
            f"**Updated:** {rv_carrier.get('last_updated', '')[:10]}"
        )

    # Tab 10: Government IPv6
    with tab10:
        st.header("Government Website IPv6 Adoption")
        st.markdown(
            "Live DNS AAAA record check for representative government domains across "
            "the US, EU, UK, and Australia."
        )

        gov_data = data_collector.get_government_ipv6_stats()
        categories = gov_data.get('categories', {})

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Domains Checked",
                gov_data.get('total_domains', 0),
                help="Total government domains tested for IPv6 AAAA records"
            )
        with col2:
            st.metric(
                "IPv6 Enabled",
                gov_data.get('total_ipv6', 0),
                help="Domains with at least one AAAA DNS record"
            )
        with col3:
            st.metric(
                "Overall IPv6 Rate",
                f"{gov_data.get('overall_pct', 0)}%",
                help="% of tested government domains with IPv6"
            )

        # Per-region bar chart
        if categories:
            region_df = pd.DataFrame([
                {'Region': region, 'IPv6 %': v['pct'], 'IPv6': v['ipv6_count'], 'Total': v['total']}
                for region, v in categories.items()
            ])
            fig = px.bar(
                region_df,
                x='Region',
                y='IPv6 %',
                title='Government Domain IPv6 Adoption by Region',
                labels={'IPv6 %': 'Domains with IPv6 (%)'},
                color='IPv6 %',
                color_continuous_scale='Greens',
                text='IPv6 %',
            )
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            fig.update_layout(yaxis_range=[0, 105], height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # Per-region domain tables
            for region, v in categories.items():
                with st.expander(f"{region} — {v['ipv6_count']}/{v['total']} domains IPv6 ({v['pct']}%)"):
                    domain_df = pd.DataFrame(v['domains'])
                    domain_df['ipv6'] = domain_df['ipv6'].map({True: '✅ Yes', False: '❌ No'})
                    domain_df.columns = ['Domain', 'IPv6 Enabled']
                    st.dataframe(domain_df, use_container_width=True, hide_index=True)

        st.caption(gov_data.get('note', ''))
        st.info(
            f"**Source:** {gov_data.get('source', 'DNS AAAA check')} | "
            f"**Updated:** {gov_data.get('last_updated', '')[:10]}"
        )

    # Tab 11: AWS Service IPv6 Coverage
    with tab11:
        st.header("AWS Service IPv6 Coverage")
        st.markdown(
            "Per-service IPv6 prefix coverage derived from the AWS IP ranges JSON "
            "(ip-ranges.amazonaws.com). A service is IPv6-enabled when AWS publishes "
            "at least one IPv6 prefix for it."
        )

        aws_data = data_collector.get_aws_ipv6_coverage()
        services = aws_data.get('services', [])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Services",
                aws_data.get('total_services', 0),
                help="Distinct AWS service names in ip-ranges.json"
            )
        with col2:
            st.metric(
                "IPv6-Enabled Services",
                aws_data.get('ipv6_services', 0),
                help="Services with at least one IPv6 prefix published"
            )
        with col3:
            st.metric(
                "IPv6 Coverage",
                f"{aws_data.get('ipv6_coverage_pct', 0)}%",
                help="% of AWS services with IPv6 prefixes"
            )

        if services:
            df_aws = pd.DataFrame(services)
            ipv6_enabled = df_aws[df_aws['ipv6'] == True]
            ipv4_only = df_aws[df_aws['ipv6'] == False]

            # Pie chart
            fig = px.pie(
                names=['IPv6-Enabled', 'IPv4-Only'],
                values=[len(ipv6_enabled), len(ipv4_only)],
                title='AWS Services: IPv6 vs IPv4-Only',
                color_discrete_map={'IPv6-Enabled': '#0066cc', 'IPv4-Only': '#ff6600'},
            )
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("IPv6-Enabled Services")
                st.dataframe(
                    ipv6_enabled[['service']].rename(columns={'service': 'Service'}),
                    use_container_width=True, hide_index=True
                )
            with col_b:
                st.subheader("IPv4-Only Services")
                st.dataframe(
                    ipv4_only[['service']].rename(columns={'service': 'Service'}),
                    use_container_width=True, hide_index=True
                )

        if aws_data.get('error'):
            st.warning(f"Data unavailable: {aws_data['error']}")
        else:
            st.caption(aws_data.get('note', ''))
            create_date = aws_data.get('create_date', '')
            if create_date:
                st.caption(f"AWS IP ranges published: {create_date}")

        st.info(
            f"**Source:** {aws_data.get('source', 'AWS IP Ranges')} | "
            f"**Updated:** {aws_data.get('last_updated', '')[:10]}"
        )

    # Tab 12: Azure Service IPv6 Coverage
    with tab12:
        st.header("Azure Service IPv6 Coverage")
        st.markdown(
            "Per-service IPv6 coverage derived from the Microsoft Azure ServiceTags JSON "
            "(published weekly to the Microsoft Download Center). A service tag is IPv6-enabled "
            "when any of its address prefix entries use IPv6 CIDR notation."
        )

        azure_data = data_collector.get_azure_ipv6_coverage()
        az_services = azure_data.get('services', [])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Service Tags",
                azure_data.get('total_services', 0),
                help="Distinct Azure service names in the ServiceTags JSON"
            )
        with col2:
            st.metric(
                "IPv6-Enabled Services",
                azure_data.get('ipv6_services', 0),
                help="Services with at least one IPv6 prefix published"
            )
        with col3:
            st.metric(
                "IPv6 Coverage",
                f"{azure_data.get('ipv6_coverage_pct', 0)}%",
                help="% of Azure service tags with IPv6 prefixes"
            )

        if az_services:
            df_az = pd.DataFrame(az_services)
            ipv6_enabled = df_az[df_az['ipv6'] == True]
            ipv4_only = df_az[df_az['ipv6'] == False]

            fig = px.pie(
                names=['IPv6-Enabled', 'IPv4-Only'],
                values=[len(ipv6_enabled), len(ipv4_only)],
                title='Azure Services: IPv6 vs IPv4-Only',
                color_discrete_map={'IPv6-Enabled': '#0078d4', 'IPv4-Only': '#ff6600'},
            )
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("IPv6-Enabled Services")
                st.dataframe(
                    ipv6_enabled[['service']].rename(columns={'service': 'Service'}),
                    use_container_width=True, hide_index=True
                )
            with col_b:
                st.subheader("IPv4-Only Services")
                st.dataframe(
                    ipv4_only[['service']].rename(columns={'service': 'Service'}),
                    use_container_width=True, hide_index=True
                )

        if azure_data.get('error'):
            st.warning(f"Data unavailable: {azure_data['error']}")
        else:
            publish_date = azure_data.get('publish_date', '')
            change_number = azure_data.get('change_number', '')
            if publish_date:
                st.caption(f"ServiceTags file published: {publish_date} (change #{change_number})")
            st.caption(azure_data.get('note', ''))

        st.info(
            f"**Source:** {azure_data.get('source', 'Azure ServiceTags')} | "
            f"**Updated:** {azure_data.get('last_updated', '')[:10]}"
        )

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
    - **PeeringDB**: Self-reported IPv6 capability from registered network operators
    - **RIPE STAT RPKI**: RPKI ROA coverage for IPv6 and IPv4 global routing tables
    - **Euro-IX IXPDB**: IXP member IPv6 adoption via IX-F standard member exports
    - **RIPE STAT (ASN prefixes)**: Live BGP prefix counts for mobile/broadband carrier ASNs
    - **DNS AAAA checks**: Live resolver queries for AAAA records on government domains
    - **AWS IP Ranges**: Official AWS JSON listing IPv4 and IPv6 prefixes by service
    - **Azure ServiceTags**: Microsoft's weekly IP ranges JSON with per-service IPv4/IPv6 prefixes

    Data is cached for 24 hours to balance freshness with source API load.
    """)
