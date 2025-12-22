#!/usr/bin/env python3
"""
Debug script to inspect Cloudflare Radar API response
"""

import requests
import json
import os
import sys

api_key = os.environ.get('CLOUDFLARE_API_KEY')

if not api_key:
    print("ERROR: CLOUDFLARE_API_KEY environment variable not set")
    print("\nUsage:")
    print("  export CLOUDFLARE_API_KEY='your-token-here'")
    print("  python3 debug_cloudflare_api.py")
    sys.exit(1)

print(f"Using API key: {api_key[:10]}...{api_key[-4:]}")
print("=" * 80)

# Test the endpoint used in the code
url = "https://api.cloudflare.com/client/v4/radar/http/timeseries_groups/ip_version?name=main&dateRange=52w"

headers = {
    'Authorization': f'Bearer {api_key}'
}

print(f"\nTesting URL: {url}")
print("-" * 80)

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nSuccess: {data.get('success')}")
        print(f"\nFull JSON response (first 2000 chars):")
        print(json.dumps(data, indent=2)[:2000])

        # Show the structure
        print("\n" + "=" * 80)
        print("RESPONSE STRUCTURE:")
        print("-" * 80)

        if 'result' in data:
            result = data['result']
            print(f"result keys: {list(result.keys())}")

            # Check different possible structures
            if 'serie_0' in result:
                print(f"result['serie_0'] keys: {list(result['serie_0'].keys())}")
            if 'series' in result:
                print(f"result['series'] type: {type(result['series'])}")
                if isinstance(result['series'], dict):
                    print(f"result['series'] keys: {list(result['series'].keys())}")
            if 'timestamps' in result:
                print(f"result['timestamps'] length: {len(result['timestamps'])}")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
