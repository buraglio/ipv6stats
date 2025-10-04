#!/usr/bin/env python3
"""
Test script to verify all optimization modules are working correctly
Run this before deploying to production
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all new modules can be imported"""
    print("Testing module imports...")

    try:
        import data_manager
        print(" data_manager imported successfully")
    except ImportError as e:
        print(f" Failed to import data_manager: {e}")
        return False

    try:
        import components
        print(" components imported successfully")
    except ImportError as e:
        print(f" Failed to import components: {e}")
        return False

    try:
        import dataframe_utils
        print(" dataframe_utils imported successfully")
    except ImportError as e:
        print(f" Failed to import dataframe_utils: {e}")
        return False

    try:
        from pages import overview, global_adoption, cloud_services, bgp_statistics
        print(" All page modules imported successfully")
    except ImportError as e:
        print(f" Failed to import page modules: {e}")
        return False

    return True


def test_data_manager():
    """Test DataManager functionality"""
    print("\nTesting DataManager...")

    try:
        from data_manager import get_data_manager

        manager = get_data_manager()
        print(" DataManager instance created")

        # Test cache stats
        stats = manager.get_cache_stats()
        print(f" Cache stats retrieved: {stats['cached_items']} items cached")

        return True
    except Exception as e:
        print(f" DataManager test failed: {e}")
        return False


def test_components():
    """Test component functions"""
    print("\nTesting Components...")

    try:
        from components import (
            render_metric_row,
            render_data_source_section,
            render_country_table,
            create_simple_bar_chart
        )

        print(" Component functions imported")

        # Test that functions exist and are callable
        assert callable(render_metric_row)
        assert callable(render_data_source_section)
        assert callable(render_country_table)
        assert callable(create_simple_bar_chart)

        print(" All component functions are callable")
        return True
    except Exception as e:
        print(f" Components test failed: {e}")
        return False


def test_dataframe_utils():
    """Test DataFrame optimization utilities"""
    print("\nTesting DataFrame Utils...")

    try:
        import pandas as pd
        from dataframe_utils import optimize_dataframe, create_optimized_dataframe

        # Create test DataFrame
        test_data = [
            {'country': 'France', 'ipv6_percentage': 80.0, 'rank': 1},
            {'country': 'Germany', 'ipv6_percentage': 75.0, 'rank': 2},
            {'country': 'India', 'ipv6_percentage': 74.0, 'rank': 3},
        ]

        df = create_optimized_dataframe(test_data)
        print(f" Created optimized DataFrame with {len(df)} rows")

        # Check memory optimization
        memory_mb = df.memory_usage(deep=True).sum() / 1024**2
        print(f" DataFrame memory usage: {memory_mb:.3f} MB")

        return True
    except Exception as e:
        print(f" DataFrame utils test failed: {e}")
        return False


def test_performance_config():
    """Test performance configuration"""
    print("\nTesting Performance Config...")

    try:
        from performance_config import (
            MEMORY_OPTIMIZATION,
            DATA_LOADING,
            UI_OPTIMIZATION,
            RENDERING_OPTIMIZATION,
            optimize_memory
        )

        print(f" MEMORY_OPTIMIZATION loaded: {len(MEMORY_OPTIMIZATION)} settings")
        print(f" DATA_LOADING loaded: {len(DATA_LOADING)} settings")
        print(f" UI_OPTIMIZATION loaded: {len(UI_OPTIMIZATION)} settings")
        print(f" RENDERING_OPTIMIZATION loaded: {len(RENDERING_OPTIMIZATION)} settings")

        # Check new settings exist
        assert 'session_state_caching' in MEMORY_OPTIMIZATION
        assert 'conditional_page_loading' in MEMORY_OPTIMIZATION
        assert 'lazy_charts' in UI_OPTIMIZATION

        print(" All new configuration settings present")

        # Test optimize_memory function
        optimize_memory()
        print(" optimize_memory() executed successfully")

        return True
    except Exception as e:
        print(f" Performance config test failed: {e}")
        return False


def test_startup_script():
    """Test that startup script exists and is executable"""
    print("\nTesting Startup Script...")

    script_path = Path("start_ipv6stats.sh")

    if not script_path.exists():
        print(" start_ipv6stats.sh not found")
        return False

    print(" start_ipv6stats.sh exists")

    if not script_path.stat().st_mode & 0o111:
        print("  start_ipv6stats.sh is not executable (run: chmod +x start_ipv6stats.sh)")
        return False

    print(" start_ipv6stats.sh is executable")
    return True


def test_service_file():
    """Test that systemd service file exists"""
    print("\nTesting Service File...")

    service_path = Path("ipv6stats.service")

    if not service_path.exists():
        print(" ipv6stats.service not found")
        return False

    print(" ipv6stats.service exists")

    # Check service file has basic content
    content = service_path.read_text()
    if '[Unit]' in content and '[Service]' in content and '[Install]' in content:
        print(" ipv6stats.service has valid structure")
        return True
    else:
        print(" ipv6stats.service appears malformed")
        return False


def test_documentation():
    """Test that all documentation files exist"""
    print("\nTesting Documentation...")

    docs = [
        'README.md',
        'OPTIMIZATIONS.md',
        'INTEGRATION_GUIDE.md',
        'IMPLEMENTATION_SUMMARY.md'
    ]

    all_exist = True
    for doc in docs:
        if Path(doc).exists():
            print(f" {doc} exists")
        else:
            print(f" {doc} not found")
            all_exist = False

    return all_exist


def main():
    """Run all tests"""
    print("=" * 60)
    print("IPv6 Statistics Dashboard - Optimization Test Suite")
    print("=" * 60)

    results = {
        'Imports': test_imports(),
        'DataManager': test_data_manager(),
        'Components': test_components(),
        'DataFrame Utils': test_dataframe_utils(),
        'Performance Config': test_performance_config(),
        'Startup Script': test_startup_script(),
        'Service File': test_service_file(),
        'Documentation': test_documentation(),
    }

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = " PASS" if result else " FAIL"
        print(f"{test_name:.<30} {status}")

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n All tests passed! Optimizations are ready for deployment.")
        return 0
    else:
        print(f"\n  {total - passed} test(s) failed. Please fix before deployment.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
