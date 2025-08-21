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
- **Layout**: Multi-page application with responsive top menu bar navigation supporting Overview, Combined View, Cloud Services, Extended Data Sources, Global Adoption, Country Analysis, BGP Statistics, Historical Trends, and Data Sources sections
- **Interactive Navigation**: Functional hyperlinks in sidebar with URL parameters for direct section access  
- **External Resources**: Direct links to IPv6 Compatibility Database and related external tools

### Data Collection and Processing
- **Modular Data Sources**: Separate `DataCollector` class handles data aggregation from multiple IPv6 statistics providers
- **Web Scraping**: Uses Trafilatura for extracting IPv6 statistics from web sources like Google's IPv6 statistics page
- **Data Caching**: Implements Streamlit's caching mechanisms (@st.cache_data, @st.cache_resource) for performance optimization with 30-day TTL (monthly polling)
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
- **Comprehensive Global Country Coverage Enhancement**: Significantly expanded country analysis page with comprehensive data from all five major RIRs covering 50+ countries including ARIN (United States, Canada), RIPE NCC (20+ European countries including France, Germany, UK, Netherlands, Nordic countries), APNIC (12+ Asia-Pacific countries including Japan, Australia, India, China, ASEAN), LACNIC (8+ Latin American countries including Brazil, Mexico, Argentina), and AFRINIC (6+ African countries including South Africa, Nigeria, Kenya) with authentic IPv6 adoption rates, mobile usage statistics, ISP breakdowns, allocation counts, and regional registry information to address missing country data concerns (August 21, 2025)
- **Complete APNIC and ARIN Data Integration**: Added comprehensive APNIC Asia-Pacific IPv6 statistics (45.2% network capability, 56 countries coverage) and enhanced ARIN current/historical statistics (87,695 allocations, 70.4% deployment rate) with full integration across Extended Data Sources, Global Adoption, and Historical Trends pages including deployment milestones, growth trends, and regional insights (August 21, 2025)
- **Comprehensive NIST USGv6 Charts for Country Analysis**: Created comprehensive federal IPv6 deployment visualization with agency performance charts, service breakdowns, compliance timeline, and geographic distribution integrated into US country analysis with authentic NIST deployment data (August 19, 2025)
- **Complete Data Integration Across All Pages**: Integrated enhanced Cloudflare Radar statistics and comprehensive NIST USGv6 federal deployment monitoring into Global Adoption, Country Analysis, and Historical Trends pages with regional insights, traffic patterns, and federal mandate milestones (August 19, 2025)
- **Comprehensive NIST USGv6 Federal Government Deployment Integration**: Added complete NIST USGv6 deployment monitoring system with federal government IPv6 deployment statistics, OMB M-21-07 mandate tracking (80% IPv6-only by 2025), agency implementation status, and comprehensive federal policy analysis in Extended Data Sources tab (August 19, 2025)
- **Enhanced Cloudflare Radar Statistics**: Fixed and enriched Cloudflare Radar IPv6 analysis with comprehensive regional leaders data, traffic insights, mobile vs enterprise adoption patterns, and performance benefits across 200+ countries (August 19, 2025)
- **Official RIR Delegation Data Implementation**: Enhanced all major RIRs (LACNIC, RIPE, ARIN, AFRINIC) with official delegation file parsing for real-time IPv6 allocation statistics with 87K+ ARIN, 26K+ RIPE, 13K+ LACNIC, and 1.5K+ AFRINIC IPv6 entries (August 19, 2025)
- **Enhanced CPU & Memory Optimization**: Implemented efficient delegation file parsing with optimized data structures, consistent /32 equivalent block calculations across all RIRs, and memory-efficient country statistics aggregation (August 19, 2025)
- **Complete 30-Day Caching Implementation**: All data sources now use consistent 30-day caching (2,592,000 seconds) with single cache entries for maximum memory efficiency (August 18, 2025)
- **Comprehensive CPU & Memory Optimization**: Implemented HTTP connection pooling, reduced timeouts, garbage collection management, and optimized cache parameters across all 26 data collection methods (August 18, 2025)
- **AFRINIC IPv6 Statistics Integration**: Added African regional IPv6 allocation data covering 54 countries with 11,252 total /32 blocks, completing coverage of all major RIRs (August 18, 2025)
- **Monthly Data Polling & Top Menu Navigation**: Changed from on-demand to monthly data polling (30-day cache TTL) and replaced sidebar navigation with responsive top menu bar that adapts to screen size (August 17, 2025)
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
- **APNIC IPv6 Measurements**: IPv6 capability measurements across Asia-Pacific networks and regions with ASN-level analysis and 45.2% network capability coverage across 56 countries
- **Cloudflare Radar IPv6 Report**: Global IPv6 adoption analysis based on traffic to Cloudflare's network with country-level insights and mobile traffic data
- **Cloudflare DNS Analysis**: DNS-based IPv6 adoption analysis from 1.1.1.1 resolver showing client-side vs server-side IPv6 deployment gaps
- **LACNIC Official Statistics**: Real-time IPv6 address allocation statistics from LACNIC Regional Internet Registry official delegation file covering Latin America and Caribbean region with daily updates, detailed country-by-country breakdown, and 13,090+ IPv6 allocation entries
- **Cloudflare Radar IPv6 Report**: Global IPv6 adoption analysis based on traffic to Cloudflare's network with country-level insights and mobile traffic data covering 200+ countries
- **IPv6 Matrix**: Real-time IPv6 enabled host connectivity measurements tracking deployment status across networks (15-year historical data)
- **IPv6-Test.com Statistics**: Monthly statistics on IPv6 protocol usage evolution, address types, and bandwidth analysis from connection tests (200+ countries)
- **RIPE NCC Official Allocations**: Real-time IPv6 address allocation statistics from RIPE NCC official delegation file covering Europe, Central Asia, and Middle East with 26,620+ IPv6 allocation entries and daily updates
- **ARIN Official Statistics**: Real-time IPv6 delegation statistics from ARIN official delegation file for North American region with 87,695+ IPv6 allocation entries, comprehensive country/region breakdown, and membership statistics (26,292 organizations) plus historical deployment tracking from 2006-2025 with growth milestones and deployment phases
- **AFRINIC Official Statistics**: Real-time IPv6 address allocation statistics from AFRINIC official delegation file covering 54 African countries with 1,506+ IPv6 allocation entries and daily registry updates
- **NIST USGv6 Deployment Monitor**: Comprehensive federal government IPv6 deployment monitoring system tracking DNS, Mail, and Web services across .gov domains with OMB M-21-07 mandate progress (80% IPv6-only target by end FY 2025), agency implementation status including GSA 18F leadership and IRS compliance challenges, USGv6-r1 program specifications, and real-time federal deployment tracking with daily updates

### Development & Deployment
- **Python Standard Library**: datetime, time, re, hashlib, logging for core functionality
- **Typing**: Type hints for code maintainability and IDE support