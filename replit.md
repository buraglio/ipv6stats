# Global IPv6 Statistics Dashboard

## Overview

This is a Streamlit-based web application that provides comprehensive analysis and visualization of worldwide IPv6 adoption statistics. The dashboard aggregates data from multiple sources to present global IPv6 deployment trends, country-specific adoption rates, BGP routing statistics, and historical progression data through interactive charts, maps, and metrics.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit for rapid web application development
- **Visualization Library**: Plotly for interactive charts and graphs
- **Mapping**: Folium integration via streamlit-folium for geographic visualizations
- **Layout**: Multi-page application with sidebar navigation supporting Overview, Combined View, Cloud Services, Extended Data Sources, IPv6 Compatibility Check, ASN/ISP Query, Global Adoption, Country Analysis, BGP Statistics, Historical Trends, and Data Sources sections
- **Interactive Navigation**: Functional hyperlinks in sidebar with URL parameters for direct section access  
- **External Resources**: Direct links to IPv6 Compatibility Database and related external tools

### Data Collection and Processing
- **Modular Data Sources**: Separate `DataCollector` class handles data aggregation from multiple IPv6 statistics providers
- **Web Scraping**: Uses Trafilatura for extracting IPv6 statistics from web sources like Google's IPv6 statistics page
- **Data Caching**: Implements Streamlit's caching mechanisms (@st.cache_data, @st.cache_resource) for performance optimization with 1-hour TTL
- **Custom Session Management**: HTTP session handling with appropriate User-Agent headers for web scraping

### Visualization Architecture
- **Chart Generator**: Dedicated `ChartGenerator` class for creating consistent visualizations
- **Chart Types**: Supports choropleth world maps, bar charts, and custom Plotly graphs
- **Color Scheme**: Consistent color palette across all visualizations
- **Interactive Elements**: Hover data and responsive design for enhanced user experience

### Utility Functions
- **Data Formatting**: Number formatting utilities for large statistics
- **Geographic Mapping**: Country coordinate lookup for map visualizations
- **Caching System**: Custom data caching with expiry management for improved performance

### Code Organization
- **Separation of Concerns**: Clear division between data collection (`data_sources.py`), visualization (`visualization.py`), utilities (`utils.py`), and main application logic (`app.py`)
- **Class-Based Design**: Object-oriented approach for data collectors and chart generators
- **Error Handling**: Logging and fallback mechanisms for data collection failures

### Recent Updates (August 2025)
- **Expanded Cloud Services Coverage**: Added 16 additional cloud providers including Mythic Beasts, Hetzner, Scaleway, OVHcloud, UpCloud, BinaryLane, Fly.io, and others with detailed IPv6 support analysis (August 16, 2025)
- **IPv6.army Theme Integration**: Applied IPv6.army color scheme (#007bff primary, #eaedf0 background) with logo integration in header and sidebar (August 16, 2025)
- **Mobile Optimization**: Complete responsive design implementation with auto-collapsing sidebar, optimized CSS, and mobile-friendly layouts (August 16, 2025)
- **Navigation Streamlining**: Removed IPv6 Compatibility Check and ASN/ISP Query pages while maintaining external IPv6 Compatibility Database link (August 16, 2025)
- **Enhanced Navigation**: Functional sidebar hyperlinks with URL parameter routing for direct section access
- **Extended Data Sources**: Five additional IPv6 measurement sources with interactive tabbed visualization
- **Combined View Page**: Standalone comprehensive statistics page accessible directly from sidebar navigation with guaranteed data display (Fixed August 15, 2025)

## External Dependencies

### Core Framework
- **Streamlit**: Web application framework and UI components
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing support

### Visualization
- **Plotly Express & Graph Objects**: Interactive charting and plotting
- **Folium**: Geographic mapping and choropleth visualizations
- **streamlit-folium**: Streamlit integration for Folium maps

### Data Collection
- **Requests**: HTTP client for API calls and web scraping
- **Trafilatura**: Web content extraction and text processing
- **JSON**: Data serialization and API response handling

### Data Sources
- **Internet Society Pulse**: Comprehensive technology adoption measurements including IPv6, HTTPS, TLS 1.3, and DNSSEC across top 1000 websites with regional breakdowns
- **World IPv6 Launch**: Network operator IPv6 deployment measurements from participating ISPs and network providers worldwide
- **Akamai IPv6 Statistics**: Real-time IPv6 adoption visualization based on Akamai's global CDN traffic analysis with country and network-level data
- **Eric Vyncke IPv6 Status**: IPv6 deployment status tracking for top websites per country and top-level domain analysis
- **Google IPv6 Statistics**: Primary source for global IPv6 adoption percentages
- **BGP Stuff**: Real-time BGP routing table statistics with current IPv4 and IPv6 prefix counts
- **Cisco 6lab**: Comprehensive IPv6 deployment statistics by Regional Internet Registry (RIR)
- **APNIC IPv6 Measurements**: IPv6 capability measurements across Asia-Pacific networks and regions
- **Cloudflare Radar IPv6 Report**: Global IPv6 adoption analysis based on traffic to Cloudflare's network with country-level insights and mobile traffic data
- **Cloudflare DNS Analysis**: DNS-based IPv6 adoption analysis from 1.1.1.1 resolver showing client-side vs server-side IPv6 deployment gaps
- **Telecom SudParis RIR Statistics**: Historical IPv6 address allocation statistics from Regional Internet Registries with detailed timeline from 1999-2025
- **IPv6 Matrix**: Real-time IPv6 enabled host connectivity measurements tracking deployment status across networks (15-year historical data)
- **IPv6-Test.com Statistics**: Monthly statistics on IPv6 protocol usage evolution, address types, and bandwidth analysis from connection tests (200+ countries)
- **RIPE NCC IPv6 Allocations**: Country-level IPv6 address allocation statistics within RIPE region covering Europe, Central Asia, and Middle East (182,113 total addresses)
- **ARIN Statistics & Research**: Comprehensive IPv6 delegation, transfer, and membership statistics for North American region (26,292 member organizations)

### Development & Deployment
- **Python Standard Library**: datetime, time, re, hashlib, logging for core functionality
- **Typing**: Type hints for code maintainability and IDE support