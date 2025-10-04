"""
Reusable UI components for IPv6 Dashboard
Reduces code duplication and improves maintainability
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


def render_metric_row(metrics: List[Dict[str, Any]], cols: Optional[int] = None):
    """
    Render a row of metrics in columns

    Args:
        metrics: List of dicts with keys: label, value, delta (optional), help (optional)
        cols: Number of columns (defaults to len(metrics))

    Example:
        render_metric_row([
            {"label": "Global IPv6", "value": "47%", "delta": "+2%"},
            {"label": "Countries", "value": "150", "delta": "5"}
        ])
    """
    if not metrics:
        return

    num_cols = cols or len(metrics)
    cols_list = st.columns(num_cols)

    for idx, metric in enumerate(metrics):
        if idx >= num_cols:
            break
        with cols_list[idx]:
            st.metric(
                label=metric.get('label', ''),
                value=metric.get('value', 'N/A'),
                delta=metric.get('delta'),
                help=metric.get('help')
            )


def render_data_source_section(
    title: str,
    data: Optional[Dict[str, Any]],
    chart_fn: Optional[Callable] = None,
    expanded: bool = False,
    show_last_updated: bool = True
):
    """
    Standard pattern for displaying data source sections with optional charts

    Args:
        title: Section title
        data: Data dictionary
        chart_fn: Optional function that takes data and returns a plotly figure
        expanded: Whether expander is expanded by default
        show_last_updated: Show last updated timestamp
    """
    with st.expander(title, expanded=expanded):
        if data is None:
            st.warning(f"No data available for {title}")
            return

        # Show last updated if available
        if show_last_updated and 'last_updated' in data:
            st.caption(f"Last updated: {data['last_updated']}")

        # Display metrics if available
        if 'metrics' in data:
            render_metric_row(data['metrics'])

        # Display chart if function provided
        if chart_fn:
            # Lazy load - only render when expander is opened
            expander_key = f"{title}_chart_rendered"
            if st.session_state.get(expander_key, False) or expanded:
                try:
                    fig = chart_fn(data)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error rendering chart: {e}")
            else:
                st.session_state[expander_key] = True

        # Display raw data option
        if st.checkbox(f"Show raw data for {title}", key=f"{title}_raw"):
            st.json(data)


def render_country_table(
    countries_data: List[Dict[str, Any]],
    columns: List[str] = None,
    sortable: bool = True,
    max_rows: int = 10
):
    """
    Render a formatted country statistics table

    Args:
        countries_data: List of country data dictionaries
        columns: Columns to display (None = all)
        sortable: Enable sorting
        max_rows: Maximum rows to display
    """
    if not countries_data:
        st.info("No country data available")
        return

    import pandas as pd
    df = pd.DataFrame(countries_data)

    if columns:
        df = df[columns]

    if max_rows and len(df) > max_rows:
        st.dataframe(df.head(max_rows), use_container_width=True)
        st.caption(f"Showing {max_rows} of {len(df)} countries")
    else:
        st.dataframe(df, use_container_width=True)


def render_stats_grid(stats: Dict[str, Any], grid_cols: int = 2):
    """
    Render statistics in a grid layout

    Args:
        stats: Dictionary of label: value pairs
        grid_cols: Number of columns in grid
    """
    items = list(stats.items())
    rows = [items[i:i + grid_cols] for i in range(0, len(items), grid_cols)]

    for row in rows:
        cols = st.columns(grid_cols)
        for idx, (label, value) in enumerate(row):
            with cols[idx]:
                st.metric(label, value)


def render_error_message(error: Exception, context: str = ""):
    """
    Standardized error message display

    Args:
        error: Exception object
        context: Additional context about where error occurred
    """
    st.error(f"❌ Error{f' in {context}' if context else ''}: {str(error)}")


def render_loading_message(message: str = "Loading data..."):
    """
    Standardized loading message
    """
    return st.spinner(message)


def render_info_card(title: str, content: str, icon: str = "ℹ️"):
    """
    Render an information card

    Args:
        title: Card title
        content: Card content
        icon: Icon to display
    """
    st.markdown(f"""
    <div style="padding: 1rem; border-left: 4px solid #007bff; background-color: #f8f9fa; margin: 1rem 0;">
        <h4>{icon} {title}</h4>
        <p>{content}</p>
    </div>
    """, unsafe_allow_html=True)


def create_simple_bar_chart(
    data: List[Dict[str, Any]],
    x_field: str,
    y_field: str,
    title: str,
    color_field: Optional[str] = None,
    height: int = 400
) -> go.Figure:
    """
    Create a simple bar chart with consistent styling

    Args:
        data: List of data dictionaries
        x_field: Field name for x-axis
        y_field: Field name for y-axis
        title: Chart title
        color_field: Optional field for color coding
        height: Chart height in pixels
    """
    import pandas as pd
    df = pd.DataFrame(data)

    fig = px.bar(
        df,
        x=x_field,
        y=y_field,
        title=title,
        color=color_field,
        height=height
    )

    fig.update_layout(
        xaxis_title=x_field.replace('_', ' ').title(),
        yaxis_title=y_field.replace('_', ' ').title(),
        showlegend=True if color_field else False
    )

    return fig


def render_kpi_header(kpis: List[Dict[str, Any]]):
    """
    Render a prominent KPI header section

    Args:
        kpis: List of KPI dicts with label, value, delta, icon
    """
    st.markdown("### 📊 Key Performance Indicators")
    render_metric_row(kpis)
    st.markdown("---")


def render_data_freshness(last_updated: str, ttl_days: int = 30):
    """
    Show data freshness indicator

    Args:
        last_updated: ISO format timestamp
        ttl_days: Cache TTL in days
    """
    try:
        update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        time_diff = datetime.now() - update_time

        if time_diff.days == 0:
            freshness = "🟢 Fresh (Today)"
        elif time_diff.days < 7:
            freshness = f"🟡 Recent ({time_diff.days}d ago)"
        elif time_diff.days < ttl_days:
            freshness = f"🟠 Cached ({time_diff.days}d ago)"
        else:
            freshness = f"🔴 Stale ({time_diff.days}d ago)"

        st.caption(f"Data freshness: {freshness}")
    except Exception:
        pass


def render_comparison_metrics(current: float, previous: float, label: str, format_str: str = "%.1f%%"):
    """
    Render comparison metrics with delta

    Args:
        current: Current value
        previous: Previous value
        label: Metric label
        format_str: Format string for values
    """
    delta = current - previous
    delta_pct = (delta / previous * 100) if previous != 0 else 0

    st.metric(
        label=label,
        value=format_str % current,
        delta=f"{delta_pct:+.1f}%"
    )


def render_source_attribution(sources: List[Dict[str, str]]):
    """
    Render data source attributions

    Args:
        sources: List of dicts with 'name' and 'url' keys
    """
    st.markdown("#### 📚 Data Sources")
    for source in sources:
        st.markdown(f"- [{source['name']}]({source['url']})")


def paginate_data(data: List[Any], page_size: int = 10, page_key: str = "page"):
    """
    Paginate data with controls

    Args:
        data: List of items to paginate
        page_size: Items per page
        page_key: Session state key for page number

    Returns:
        Paginated subset of data
    """
    if f"{page_key}_num" not in st.session_state:
        st.session_state[f"{page_key}_num"] = 0

    total_pages = (len(data) - 1) // page_size + 1
    current_page = st.session_state[f"{page_key}_num"]

    # Pagination controls
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Previous", disabled=current_page == 0):
            st.session_state[f"{page_key}_num"] -= 1
            st.rerun()
    with col2:
        st.write(f"Page {current_page + 1} of {total_pages}")
    with col3:
        if st.button("Next →", disabled=current_page >= total_pages - 1):
            st.session_state[f"{page_key}_num"] += 1
            st.rerun()

    # Return paginated data
    start_idx = current_page * page_size
    end_idx = start_idx + page_size
    return data[start_idx:end_idx]
