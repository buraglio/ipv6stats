"""
Cloud Services Page - Comprehensive IPv6 support in major cloud providers
Including NAT-free egress and prefix delegation capabilities
"""
import streamlit as st
from typing import Dict, Any
from components import render_metric_row
from cloud_data import CLOUD_PROVIDERS, get_provider_summary


def render(data: Dict[str, Any]):
    """
    Render the cloud services page

    Args:
        data: Dictionary containing all loaded data
    """
    st.title("Cloud Services IPv6 Support")

    st.markdown("""
    Comprehensive assessment of IPv6 support across major cloud providers,
    including NAT-free egress capabilities and prefix delegation options.
    """)

    # Summary metrics
    st.markdown("### Summary")

    total_providers = len(CLOUD_PROVIDERS)
    full_support = sum(1 for p in CLOUD_PROVIDERS.values() if p.get('ipv6_support') == 'Full')

    metrics = [
        {"label": "Cloud Providers", "value": str(total_providers)},
        {"label": "Full IPv6 Support", "value": str(full_support)},
        {"label": "NAT-Free Egress", "value": "All Major Providers"},
        {"label": "Prefix Delegation", "value": "6 of 7 Providers"}
    ]
    render_metric_row(metrics)

    # Cloudflare real-time stats
    cloudflare_stats = data.get('cloudflare_stats', {})
    if cloudflare_stats:
        st.markdown("---")
        st.markdown("### Real-Time Statistics")
        st.markdown("#### Cloudflare Network Traffic")
        metrics = [
            {"label": "IPv6 Traffic", "value": f"{cloudflare_stats.get('ipv6_percentage', 0):.1f}%"},
            {"label": "IPv4 Traffic", "value": f"{cloudflare_stats.get('ipv4_percentage', 0):.1f}%"},
            {"label": "Measurement Period", "value": cloudflare_stats.get('time_period', 'N/A')}
        ]
        render_metric_row(metrics)
        st.caption(f"Source: {cloudflare_stats.get('source', 'Cloudflare Radar')}")

    st.markdown("---")
    st.markdown("### Detailed Provider Assessments")

    # Provider details
    provider_order = ['aws', 'gcp', 'azure', 'oracle', 'digitalocean', 'linode', 'cloudflare']

    for provider_key in provider_order:
        if provider_key not in CLOUD_PROVIDERS:
            continue

        provider = CLOUD_PROVIDERS[provider_key]
        summary = get_provider_summary(provider_key)

        with st.expander(f"{summary['name']} - {summary['status']}", expanded=False):
            # Provider overview
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("IPv6 Support", summary['ipv6_support'])
            with col2:
                st.metric("Services Covered", summary['services_count'])
            with col3:
                st.metric("Global Availability", "Yes" if provider.get('global_availability') else "Limited")

            # Cost benefits
            if provider.get('cost_benefits'):
                st.info(f"**Cost Benefits:** {provider['cost_benefits']}")

            # Services breakdown
            st.markdown("#### Services")

            for service_name, service_info in provider.get('services', {}).items():
                if not isinstance(service_info, dict):
                    continue

                st.markdown(f"**{service_name}**")

                # Service support level
                support_cols = st.columns(4)
                with support_cols[0]:
                    support_status = "Full" if service_info.get('support') == 'Full' else service_info.get('support', 'Unknown')
                    st.write(f"Support: **{support_status}**")
                with support_cols[1]:
                    dual = "Yes" if service_info.get('dual_stack') else "No"
                    st.write(f"Dual-Stack: {dual}")
                with support_cols[2]:
                    ipv6_only = "Yes" if service_info.get('ipv6_only') else "No"
                    st.write(f"IPv6-Only: {ipv6_only}")

                # NAT-free egress
                nat_free = service_info.get('nat_free_egress', {})
                if nat_free.get('supported'):
                    st.markdown("**NAT-Free Egress:**")
                    st.write(f"- Method: {nat_free.get('method', 'N/A')}")
                    st.write(f"- {nat_free.get('description', '')}")
                    if nat_free.get('cost'):
                        st.success(f"Cost Savings: {nat_free['cost']}")
                    if nat_free.get('notes'):
                        st.caption(nat_free['notes'])

                # Prefix delegation
                prefix_del = service_info.get('prefix_delegation', {})
                if prefix_del.get('supported'):
                    st.markdown("**Prefix Delegation:**")
                    st.write(f"- Method: {prefix_del.get('method', 'N/A')}")
                    if prefix_del.get('prefix_size'):
                        st.write(f"- Prefix Size: {prefix_del['prefix_size']}")
                    st.write(f"- {prefix_del.get('description', '')}")
                    if prefix_del.get('automatic'):
                        st.write("- Automatic: Yes")
                    if prefix_del.get('notes'):
                        st.caption(prefix_del['notes'])
                elif 'prefix_delegation' in service_info:
                    st.markdown("**Prefix Delegation:**")
                    st.write(f"- Supported: No")
                    if prefix_del.get('notes'):
                        st.caption(prefix_del['notes'])

                # Additional notes
                if service_info.get('notes'):
                    st.caption(f"Note: {service_info['notes']}")

                st.markdown("")  # Spacing

            # Documentation link
            if provider.get('documentation'):
                st.markdown(f"**Documentation:** [{provider['name']} IPv6 Guide]({provider['documentation']})")

            st.caption(f"Last updated: {provider.get('last_updated', 'N/A')}")

    # Key capabilities comparison
    st.markdown("---")
    st.markdown("### Key Capabilities Comparison")

    comparison_data = []
    for provider_key in provider_order:
        if provider_key not in CLOUD_PROVIDERS:
            continue

        provider = CLOUD_PROVIDERS[provider_key]
        summary = get_provider_summary(provider_key)

        comparison_data.append({
            'Provider': summary['name'],
            'IPv6 Support': summary['ipv6_support'],
            'NAT-Free Services': summary['nat_free_services'],
            'Prefix Delegation': summary['prefix_delegation_services'],
            'Total Services': summary['services_count']
        })

    if comparison_data:
        import pandas as pd
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Cost savings information
    st.markdown("---")
    st.markdown("### Cost Savings with IPv6")

    st.markdown("""
    **NAT-Free Egress Benefits:**
    - **AWS**: Eliminates NAT Gateway costs (~$45/month per Availability Zone)
    - **GCP**: No Cloud NAT costs for IPv6 traffic
    - **Azure**: Free IPv6 public IPs, no NAT Gateway needed
    - **Oracle**: No NAT costs in always-free tier
    - **DigitalOcean**: Free IPv6 for all droplets
    - **Linode**: Free IPv6 addresses and pools

    **Typical Savings:** $45-135/month for small deployments, $500-2000/month for larger deployments
    """)

    # Best practices
    st.markdown("---")
    st.markdown("### Implementation Best Practices")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **NAT-Free Egress:**
        1. Enable IPv6 on VPC/VNet
        2. Assign IPv6 addresses to instances
        3. Configure egress-only gateway (AWS) or direct routing
        4. Update security groups for IPv6
        5. Test connectivity
        """)

    with col2:
        st.markdown("""
        **Prefix Delegation:**
        1. Request IPv6 CIDR block for VPC
        2. Enable IPv6 on subnets
        3. Configure automatic assignment
        4. Delegate prefixes to hosts/containers
        5. Monitor IPv6 address usage
        """)

    st.markdown("---")
    st.caption("Data compiled from official provider documentation and real-world deployments")
