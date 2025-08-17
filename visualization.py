import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import folium
from typing import Dict, List, Any
import streamlit as st

class ChartGenerator:
    """Handles creation of all visualizations for the IPv6 dashboard"""
    
    def __init__(self):
        self.color_palette = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'warning': '#d62728',
            'info': '#9467bd'
        }
    
    def create_world_map(self, df: pd.DataFrame, value_column: str) -> go.Figure:
        """Create a choropleth world map for IPv6 adoption"""
        fig = px.choropleth(
            df,
            locations='country',
            locationmode='country names',
            color=value_column,
            hover_name='country',
            hover_data={value_column: ':.1f%'},
            color_continuous_scale='Blues',
            title='Global IPv6 Adoption by Country'
        )
        
        fig.update_layout(
            title_font_size=16,
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='equirectangular'
            ),
            height=500
        )
        
        return fig
    
    def create_bar_chart(self, df: pd.DataFrame, x_column: str, y_column: str, title: str) -> go.Figure:
        """Create a horizontal bar chart"""
        fig = px.bar(
            df,
            x=y_column,
            y=x_column,
            orientation='h',
            title=title,
            color=y_column,
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(
            title_font_size=16,
            xaxis_title='IPv6 Adoption (%)',
            yaxis_title='Country',
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_line_chart(self, data: List[Dict[str, Any]], x_column: str, y_column: str, title: str) -> go.Figure:
        """Create a line chart for trends"""
        df = pd.DataFrame(data)
        df[x_column] = pd.to_datetime(df[x_column])
        
        fig = px.line(
            df,
            x=x_column,
            y=y_column,
            title=title,
            markers=True
        )
        
        fig.update_layout(
            title_font_size=16,
            xaxis_title='Date',
            yaxis_title='Adoption Rate (%)',
            height=400
        )
        
        fig.update_traces(
            line_color=self.color_palette['primary'],
            marker_color=self.color_palette['primary']
        )
        
        return fig
    
    def create_regional_comparison_chart(self, regional_data: Dict[str, float]) -> go.Figure:
        """Create a regional comparison chart"""
        regions = list(regional_data.keys())
        values = list(regional_data.values())
        
        fig = go.Figure(data=[
            go.Bar(
                x=regions,
                y=values,
                marker_color=self.color_palette['primary'],
                text=[f'{v:.1f}%' for v in values],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title='IPv6 Adoption by Region',
            title_font_size=16,
            xaxis_title='Region',
            yaxis_title='IPv6 Adoption (%)',
            height=400
        )
        
        return fig
    
    def create_bgp_growth_chart(self, historical_data: List[Dict[str, Any]]) -> go.Figure:
        """Create BGP table growth chart"""
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['total_prefixes'],
            mode='lines+markers',
            name='Total IPv6 Prefixes',
            line=dict(color=self.color_palette['primary'], width=3),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title='IPv6 BGP Table Growth Over Time',
            title_font_size=16,
            xaxis_title='Date',
            yaxis_title='Number of Prefixes',
            height=400,
            hovermode='x unified'
        )
        
        return fig
    
    def create_prefix_distribution_chart(self, prefix_data: Dict[str, float]) -> go.Figure:
        """Create prefix size distribution pie chart"""
        labels = list(prefix_data.keys())
        values = list(prefix_data.values())
        
        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                textinfo='label+percent',
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title='IPv6 Prefix Size Distribution',
            title_font_size=16,
            height=400
        )
        
        return fig
    
    def create_top_asns_chart(self, asn_data: List[Dict[str, Any]]) -> go.Figure:
        """Create top ASNs chart"""
        df = pd.DataFrame(asn_data)
        
        fig = px.bar(
            df,
            x='prefixes',
            y='name',
            orientation='h',
            title='Top 10 ASNs by IPv6 Prefix Count',
            color='prefixes',
            color_continuous_scale='Blues',
            text='prefixes'
        )
        
        fig.update_layout(
            title_font_size=16,
            xaxis_title='Number of IPv6 Prefixes',
            yaxis_title='Organization',
            height=500,
            showlegend=False
        )
        
        fig.update_traces(texttemplate='%{text}', textposition='inside')
        
        return fig
    
    def create_adoption_timeline(self, timeline_data: List[Dict[str, Any]]) -> go.Figure:
        """Create global adoption timeline chart"""
        df = pd.DataFrame(timeline_data)
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['global_adoption'],
            mode='lines+markers',
            name='Global Adoption',
            line=dict(color=self.color_palette['primary'], width=3),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['mobile_adoption'],
            mode='lines+markers',
            name='Mobile Adoption',
            line=dict(color=self.color_palette['success'], width=2),
            marker=dict(size=4)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['desktop_adoption'],
            mode='lines+markers',
            name='Desktop Adoption',
            line=dict(color=self.color_palette['warning'], width=2),
            marker=dict(size=4)
        ))
        
        fig.update_layout(
            title='Global IPv6 Adoption Timeline',
            title_font_size=16,
            xaxis_title='Date',
            yaxis_title='Adoption Rate (%)',
            height=500,
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig
    
    def create_regional_trends_chart(self, trends_data: Dict[str, List[Dict[str, Any]]]) -> go.Figure:
        """Create regional trends comparison chart"""
        fig = go.Figure()
        
        colors = [self.color_palette['primary'], self.color_palette['secondary'], 
                 self.color_palette['success'], self.color_palette['warning']]
        
        for i, (region, data) in enumerate(trends_data.items()):
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['adoption_rate'],
                mode='lines+markers',
                name=region,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=4)
            ))
        
        fig.update_layout(
            title='IPv6 Adoption Trends by Region',
            title_font_size=16,
            xaxis_title='Date',
            yaxis_title='Adoption Rate (%)',
            height=500,
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig
    
    def create_bgp_timeline_chart(self, timeline_data: List[Dict[str, Any]]) -> go.Figure:
        """Create BGP timeline chart"""
        df = pd.DataFrame(timeline_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Create subplot with secondary y-axis
        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            subplot_titles=['BGP IPv6 Table Growth Timeline']
        )
        
        # Add prefix count
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['total_prefixes'],
                mode='lines+markers',
                name='Total Prefixes',
                line=dict(color=self.color_palette['primary'], width=3),
                marker=dict(size=6)
            ),
            secondary_y=False
        )
        
        # Add growth rate
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['growth_rate'],
                mode='lines',
                name='Monthly Growth',
                line=dict(color=self.color_palette['secondary'], width=2, dash='dash'),
                opacity=0.7
            ),
            secondary_y=True
        )
        
        # Update axes
        fig.update_xaxes(title_text='Date')
        fig.update_yaxes(title_text='Number of Prefixes', secondary_y=False)
        fig.update_yaxes(title_text='Monthly Growth', secondary_y=True)
        
        fig.update_layout(
            title='BGP IPv6 Table Growth Over Time',
            title_font_size=16,
            height=500,
            hovermode='x unified'
        )
        
        return fig
