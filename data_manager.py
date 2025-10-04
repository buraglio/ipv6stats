"""
Centralized Data Manager for IPv6 Dashboard
Handles all data loading, caching, and distribution to pages
"""
import streamlit as st
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc

from data_sources import DataCollector
from performance_config import MEMORY_OPTIMIZATION, DATA_LOADING

logger = logging.getLogger(__name__)


class DataManager:
    """
    Centralized manager for all dashboard data
    - Single source of truth for all data
    - Handles caching in session_state
    - Provides conditional loading per page
    - Reduces duplicate API calls
    """

    def __init__(self):
        self.collector = DataCollector()
        self._init_session_state()

    def _init_session_state(self):
        """Initialize session state structure"""
        if 'data_cache' not in st.session_state:
            st.session_state.data_cache = {}
        if 'data_loaded_at' not in st.session_state:
            st.session_state.data_loaded_at = {}
        if 'page_data_loaded' not in st.session_state:
            st.session_state.page_data_loaded = set()

    def get_or_load_data(self, data_key: str, loader_fn: callable, force_reload: bool = False) -> Optional[Any]:
        """
        Get data from cache or load it

        Args:
            data_key: Unique key for this data
            loader_fn: Function to load data if not cached
            force_reload: Force reload even if cached

        Returns:
            Loaded data or None on error
        """
        # Check cache first
        if not force_reload and data_key in st.session_state.data_cache:
            logger.debug(f"Cache hit for {data_key}")
            return st.session_state.data_cache[data_key]

        # Load data
        try:
            logger.info(f"Loading data for {data_key}")
            data = loader_fn()
            st.session_state.data_cache[data_key] = data
            st.session_state.data_loaded_at[data_key] = datetime.now()
            return data
        except Exception as e:
            logger.error(f"Error loading {data_key}: {e}")
            return None

    def load_all_data(self, show_progress: bool = True) -> Dict[str, Any]:
        """
        Load all dashboard data at once (for initial load)

        Args:
            show_progress: Show loading progress bar

        Returns:
            Dictionary of all loaded data
        """
        if 'all_data_loaded' in st.session_state and st.session_state.all_data_loaded:
            logger.info("All data already loaded from cache")
            return st.session_state.data_cache

        # Define all data sources
        data_sources = {
            'google_stats': self.collector.get_google_ipv6_stats,
            'google_country': self.collector.get_google_country_stats,
            'facebook_stats': self.collector.get_facebook_stats,
            'cloudflare_stats': self.collector.get_cloudflare_stats,
            'apnic_stats': self.collector.get_apnic_stats,
            'cisco_6lab': self.collector.get_cisco_6lab_stats,
            'nist_usgv6': self.collector.get_nist_usgv6_stats,
            'bgp_stats': self.collector.get_current_bgp_stats,
            'arin_stats': self.collector.get_arin_stats,
            'ripe_stats': self.collector.get_ripe_stats,
            'lacnic_stats': self.collector.get_lacnic_stats,
            'afrinic_stats': self.collector.get_afrinic_stats,
        }

        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()

        loaded_data = {}
        total = len(data_sources)

        # Load data with limited concurrency
        max_workers = DATA_LOADING.get('concurrent_requests', 3)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {
                executor.submit(loader_fn): key
                for key, loader_fn in data_sources.items()
            }

            completed = 0
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    data = future.result(timeout=DATA_LOADING.get('request_timeout', 10))
                    loaded_data[key] = data
                    st.session_state.data_cache[key] = data
                    st.session_state.data_loaded_at[key] = datetime.now()
                except Exception as e:
                    logger.error(f"Error loading {key}: {e}")
                    loaded_data[key] = None

                completed += 1
                if show_progress:
                    progress_bar.progress(completed / total)
                    status_text.text(f"Loaded {completed}/{total} data sources...")

        if show_progress:
            progress_bar.empty()
            status_text.empty()

        st.session_state.all_data_loaded = True
        gc.collect()  # Cleanup after loading

        return loaded_data

    def load_page_data(self, page_name: str) -> Dict[str, Any]:
        """
        Load only data required for specific page (conditional loading)

        Args:
            page_name: Name of the page

        Returns:
            Dictionary of data for this page
        """
        # Define page-specific data requirements
        page_requirements = {
            'Overview': ['google_stats', 'facebook_stats', 'cloudflare_stats', 'bgp_stats'],
            'Global Adoption': ['google_country', 'apnic_stats', 'cisco_6lab'],
            'Cloud Services': ['cloudflare_stats', 'facebook_stats'],
            'BGP Statistics': ['bgp_stats'],
            'Extended Data': ['arin_stats', 'ripe_stats', 'lacnic_stats', 'afrinic_stats', 'nist_usgv6'],
        }

        required_keys = page_requirements.get(page_name, [])
        page_data = {}

        for key in required_keys:
            # Load individual data source if not cached
            if key not in st.session_state.data_cache:
                loader_fn = getattr(self.collector, f"get_{key.replace('_stats', '_stats').replace('_', '_')}", None)
                if loader_fn:
                    page_data[key] = self.get_or_load_data(key, loader_fn)
            else:
                page_data[key] = st.session_state.data_cache[key]

        st.session_state.page_data_loaded.add(page_name)
        return page_data

    def get_cached_data(self, data_key: str) -> Optional[Any]:
        """
        Get data from cache without loading

        Args:
            data_key: Data cache key

        Returns:
            Cached data or None
        """
        return st.session_state.data_cache.get(data_key)

    def invalidate_cache(self, data_key: Optional[str] = None):
        """
        Invalidate cache for specific key or all data

        Args:
            data_key: Specific key to invalidate, or None for all
        """
        if data_key:
            st.session_state.data_cache.pop(data_key, None)
            st.session_state.data_loaded_at.pop(data_key, None)
            logger.info(f"Invalidated cache for {data_key}")
        else:
            st.session_state.data_cache.clear()
            st.session_state.data_loaded_at.clear()
            st.session_state.all_data_loaded = False
            st.session_state.page_data_loaded.clear()
            logger.info("Invalidated all cache")
        gc.collect()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached data

        Returns:
            Dictionary with cache statistics
        """
        return {
            'cached_items': len(st.session_state.data_cache),
            'loaded_pages': list(st.session_state.page_data_loaded),
            'all_data_loaded': st.session_state.get('all_data_loaded', False),
            'cache_keys': list(st.session_state.data_cache.keys()),
            'oldest_data': min(st.session_state.data_loaded_at.values()) if st.session_state.data_loaded_at else None,
            'newest_data': max(st.session_state.data_loaded_at.values()) if st.session_state.data_loaded_at else None,
        }

    def preload_common_data(self):
        """
        Preload most commonly used data sources
        Call this during app initialization
        """
        common_sources = {
            'google_stats': self.collector.get_google_ipv6_stats,
            'facebook_stats': self.collector.get_facebook_stats,
            'cloudflare_stats': self.collector.get_cloudflare_stats,
        }

        for key, loader_fn in common_sources.items():
            if key not in st.session_state.data_cache:
                self.get_or_load_data(key, loader_fn)


# Singleton pattern - create once and reuse
@st.cache_resource(max_entries=1)
def get_data_manager() -> DataManager:
    """
    Get singleton DataManager instance

    Returns:
        DataManager instance
    """
    return DataManager()


# Convenience functions for common operations
def load_dashboard_data(conditional: bool = True, page_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for loading dashboard data

    Args:
        conditional: If True, load only data for current page
        page_name: Required if conditional=True

    Returns:
        Dictionary of loaded data
    """
    manager = get_data_manager()

    if conditional and page_name:
        return manager.load_page_data(page_name)
    else:
        return manager.load_all_data()


def get_data(key: str) -> Optional[Any]:
    """
    Quick accessor for cached data

    Args:
        key: Data cache key

    Returns:
        Cached data or None
    """
    manager = get_data_manager()
    return manager.get_cached_data(key)


def refresh_data(key: Optional[str] = None):
    """
    Force refresh data

    Args:
        key: Specific key to refresh, or None for all
    """
    manager = get_data_manager()
    manager.invalidate_cache(key)
    st.rerun()
