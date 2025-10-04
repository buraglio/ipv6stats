#!/usr/bin/env python3
"""
Test script for Cloudflare Radar public API
"""

import requests
import json

def test_cloudflare_public_endpoints():
    """Test various Cloudflare Radar public endpoints"""
    print("Testing Cloudflare Radar Public Endpoints...")
    print("=" * 60)
    
    # Try the public aggregates endpoint (doesn't require auth)
    endpoints = [
        "https://api.cloudflare.com/client/v4/radar/http/summary/ip_version?dateRange=7d",
        "https://api.cloudflare.com/client/v4/radar/http/summary/ip_version?dateRange=30d",
        "https://api.cloudflare.com/client/v4/radar/http/timeseries_groups/ip_version?name=main&dateRange=7d",
    ]
    
    for url in endpoints:
        print(f"\nTrying: {url}")
        try:
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {data.get('success')}")
                if data.get('success'):
                    print("FOUND WORKING ENDPOINT!")
                    print(json.dumps(data, indent=2)[:800])
                    return url, data
                else:
                    print(f"Errors: {data.get('errors', [])}")
            elif response.status_code == 400:
                data = response.json()
                print(f"Error: {data.get('errors', [])}")
        except Exception as e:
            print(f"Exception: {e}")
    
    print("\n" + "=" * 60)
    print("No working public endpoint found")
    return None, None

if __name__ == '__main__':
    test_cloudflare_public_endpoints()
