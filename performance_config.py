# Performance Configuration for IPv6 Dashboard
"""
Memory and CPU optimization settings for the IPv6 Dashboard application.
"""

import streamlit as st
import gc

# Memory optimization settings
MEMORY_OPTIMIZATION = {
    'cache_ttl': 2592000,  # 30 days (monthly) cache for all data
    'max_cache_entries': 1,  # Single cache entry to save maximum memory
    'lazy_loading': True,  # Enable lazy loading of expensive operations
    'garbage_collection': True,  # Enable periodic garbage collection
}

# Data loading optimization
DATA_LOADING = {
    'concurrent_requests': 3,  # Limit concurrent HTTP requests
    'request_timeout': 10,  # Shorter timeout for faster failures
    'max_retries': 1,  # Limit retries to reduce CPU usage
    'connection_pool_size': 5,  # Smaller connection pool
}

# UI optimization settings
UI_OPTIMIZATION = {
    'default_expanded': False,  # Keep expanders collapsed by default
    'pagination_size': 5,  # Show fewer items per page
    'chart_height': 400,  # Fixed chart height
    'lazy_charts': True,  # Load charts only when requested
}

def optimize_memory():
    """Force garbage collection to free up memory."""
    if MEMORY_OPTIMIZATION['garbage_collection']:
        gc.collect()

def clear_old_cache():
    """Clear old cache entries to prevent memory buildup."""
    try:
        st.cache_data.clear()
        optimize_memory()
    except Exception:
        pass  # Ignore if cache clearing fails

def get_optimized_cache_params():
    """Get optimized cache parameters for monthly polling."""
    return {
        'ttl': MEMORY_OPTIMIZATION['cache_ttl'],  # 30 days
        'max_entries': MEMORY_OPTIMIZATION['max_cache_entries']  # 1 entry
    }