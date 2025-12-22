"""
Global Adoption Page - Country-level IPv6 statistics and world maps
"""
import streamlit as st
from typing import Dict, Any
import pandas as pd
import plotly.express as px
from components import render_metric_row, render_country_table
from dataframe_utils import create_optimized_dataframe


def render(data: Dict[str, Any]):
    """
    Render the global adoption page

    Args:
        data: Dictionary containing all loaded data
    """
    st.title("🌍 Global IPv6 Adoption")

    # Get country statistics
    country_data = data.get('google_country', [])

    if not country_data:
        st.warning("Country statistics are currently loading...")
        return

    # Create optimized DataFrame
    df = create_optimized_dataframe(country_data)

    # Summary metrics
    st.markdown("### 📊 Global Summary")
    avg_adoption = df['ipv6_percentage'].mean() if 'ipv6_percentage' in df.columns else 0
    top_country = df.iloc[0] if len(df) > 0 else None

    metrics = [
        {"label": "Countries Tracked", "value": str(len(df))},
        {"label": "Average Adoption", "value": f"{avg_adoption:.1f}%"},
        {"label": "Top Country", "value": top_country['country'] if top_country is not None else "N/A"},
        {"label": "Top Adoption Rate", "value": f"{top_country['ipv6_percentage']:.1f}%" if top_country is not None else "N/A"}
    ]
    render_metric_row(metrics)

    st.markdown("---")

    # World map visualization
    st.markdown("### 🗺️ IPv6 Adoption World Map")

    # Create choropleth map
    fig = px.choropleth(
        df,
        locations='country',
        locationmode='country names',
        color='ipv6_percentage',
        hover_name='country',
        hover_data={'ipv6_percentage': ':.1f'},
        color_continuous_scale='Viridis',
        title='IPv6 Adoption by Country',
        labels={'ipv6_percentage': 'IPv6 Adoption %'}
    )

    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type='natural earth'),
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Top performers
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🥇 Top Performers (>60%)")
        top_performers = df[df['ipv6_percentage'] >= 60] if 'ipv6_percentage' in df.columns else pd.DataFrame()

        if len(top_performers) > 0:
            render_country_table(
                top_performers.to_dict('records'),
                columns=['country', 'ipv6_percentage', 'rank'],
                max_rows=10
            )
        else:
            st.info("No countries with >60% adoption yet")

    with col2:
        st.markdown("### 📈 Growth Opportunities (<30%)")
        low_adoption = df[df['ipv6_percentage'] < 30] if 'ipv6_percentage' in df.columns else pd.DataFrame()

        if len(low_adoption) > 0:
            render_country_table(
                low_adoption.to_dict('records'),
                columns=['country', 'ipv6_percentage', 'rank'],
                max_rows=10
            )
        else:
            st.info("All countries showing good adoption!")

    st.markdown("---")

    # Distribution chart
    st.markdown("### 📊 Adoption Distribution")

    fig = px.histogram(
        df,
        x='ipv6_percentage',
        nbins=20,
        title='Distribution of IPv6 Adoption Rates',
        labels={'ipv6_percentage': 'IPv6 Adoption %', 'count': 'Number of Countries'}
    )
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # Full country table
    st.markdown("---")
    st.markdown("### 📋 Complete Country Statistics")

    with st.expander("Show all countries", expanded=False):
        st.dataframe(
            df.sort_values('ipv6_percentage', ascending=False),
            use_container_width=True,
            height=400
        )
