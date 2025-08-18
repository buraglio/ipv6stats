import streamlit as st
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional
import hashlib

def format_number(number: int) -> str:
    """Format large numbers with appropriate suffixes"""
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}K"
    else:
        return str(number)

def get_all_country_coordinates() -> Dict[str, Dict[str, float]]:
    """Get all country coordinates for mapping"""
    return {
        'United States': {'lat': 39.8283, 'lon': -98.5795},
        'France': {'lat': 46.2276, 'lon': 2.2137},
        'Germany': {'lat': 51.1657, 'lon': 10.4515},
        'India': {'lat': 20.5937, 'lon': 78.9629},
        'United Kingdom': {'lat': 55.3781, 'lon': -3.4360},
        'Japan': {'lat': 36.2048, 'lon': 138.2529},
        'Canada': {'lat': 56.1304, 'lon': -106.3468},
        'Australia': {'lat': -25.2744, 'lon': 133.7751},
        'Netherlands': {'lat': 52.1326, 'lon': 5.2913},
        'Belgium': {'lat': 50.5039, 'lon': 4.4699},
        'Brazil': {'lat': -14.2350, 'lon': -51.9253},
        'China': {'lat': 35.8617, 'lon': 104.1954},
        'Russia': {'lat': 61.5240, 'lon': 105.3188},
        'South Korea': {'lat': 35.9078, 'lon': 127.7669},
        'Italy': {'lat': 41.8719, 'lon': 12.5674},
        'Spain': {'lat': 40.4637, 'lon': -3.7492}
    }

def get_country_coordinates(country_name: str) -> Optional[tuple]:
    """Get coordinates for a specific country"""
    coords_dict = get_all_country_coordinates()
    country_data = coords_dict.get(country_name)
    if country_data:
        return (country_data['lat'], country_data['lon'])
    return None

def cache_data(key: str, data: Any, expiry_hours: int = 1) -> None:
    """Cache data with expiry time"""
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {}
    
    expiry_time = datetime.now() + timedelta(hours=expiry_hours)
    st.session_state.data_cache[key] = {
        'data': data,
        'expiry': expiry_time
    }

def get_cached_data(key: str) -> Optional[Any]:
    """Get cached data if not expired"""
    if 'data_cache' not in st.session_state:
        return None
    
    cache_entry = st.session_state.data_cache.get(key)
    if cache_entry and datetime.now() < cache_entry['expiry']:
        return cache_entry['data']
    
    return None

def generate_cache_key(*args) -> str:
    """Generate a cache key from arguments"""
    key_string = '_'.join(str(arg) for arg in args)
    return hashlib.md5(key_string.encode()).hexdigest()

def validate_percentage(value: float) -> bool:
    """Validate percentage values"""
    return 0 <= value <= 100

def format_date(date_str: str) -> str:
    """Format date string for display"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%B %d, %Y')
    except:
        return date_str

def calculate_growth_rate(current: float, previous: float) -> float:
    """Calculate growth rate percentage"""
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def get_status_color(percentage: float) -> str:
    """Get color based on IPv6 adoption percentage"""
    if percentage >= 70:
        return 'green'
    elif percentage >= 50:
        return 'orange'
    elif percentage >= 30:
        return 'yellow'
    else:
        return 'red'

def create_download_link(data: Dict[str, Any], filename: str) -> str:
    """Create a download link for data"""
    json_string = json.dumps(data, indent=2, default=str)
    return f"data:application/json;base64,{json_string}"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    if denominator == 0:
        return default
    return numerator / denominator

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def validate_country_name(country: str) -> bool:
    """Validate if country name is in our supported list"""
    supported_countries = get_all_country_coordinates().keys()
    return country in supported_countries

def get_time_range_dates(time_range: str) -> tuple:
    """Get start and end dates for time range"""
    end_date = datetime.now()
    
    if time_range == "Last 6 Months":
        start_date = end_date - timedelta(days=180)
    elif time_range == "Last Year":
        start_date = end_date - timedelta(days=365)
    elif time_range == "Last 2 Years":
        start_date = end_date - timedelta(days=730)
    elif time_range == "Last 5 Years":
        start_date = end_date - timedelta(days=1825)
    else:  # All Time
        start_date = end_date - timedelta(days=3650)  # 10 years
    
    return start_date, end_date

def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable format"""
    bytes_float = float(bytes_value)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_float < 1024.0:
            return f"{bytes_float:.1f} {unit}"
        bytes_float /= 1024.0
    return f"{bytes_float:.1f} PB"

def clean_percentage_string(percentage_str: str) -> float:
    """Clean and convert percentage string to float"""
    try:
        # Remove % sign and any whitespace
        clean_str = percentage_str.replace('%', '').strip()
        return float(clean_str)
    except (ValueError, AttributeError):
        return 0.0

def is_valid_ipv6_prefix(prefix: str) -> bool:
    """Validate IPv6 prefix format"""
    import re
    # Simple IPv6 prefix validation
    pattern = r'^([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{0,4}/\d{1,3}$'
    return bool(re.match(pattern, prefix))

def get_data_freshness_indicator(last_updated: str) -> str:
    """Get data freshness indicator"""
    try:
        update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        time_diff = datetime.now() - update_time
        
        if time_diff.days == 0:
            if time_diff.seconds < 3600:  # Less than 1 hour
                return "🟢 Fresh"
            else:
                return "🟡 Recent"
        elif time_diff.days < 7:
            return "🟡 This week"
        else:
            return "🔴 Stale"
    except:
        return "❓ Unknown"
