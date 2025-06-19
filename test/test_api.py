import sys
import os
# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.reliefweb_api import reliefweb_api
import json

def test_basic_connection():
    """Test basic API connection"""
    print("Testing API connection...")
    if reliefweb_api.test_connection():
        print("✅ API connection successful")
    else:
        print("❌ API connection failed")

def test_simple_query():
    """Test a simple query"""
    print("\nTesting simple Sudan assessment query...")
    
    filters = {
        'country': 'Sudan',
        'country_filter_type': 'primary',
        'format': 'Assessment',
        'limit': 5
    }
    
    try:
        result = reliefweb_api.fetch_reports(filters)
        print(f"✅ Query successful. Found {result.get('totalCount', 0)} total results")
        
        if result.get('data'):
            print(f"Returned {len(result['data'])} records in this batch")
            
            # Show first result
            first_record = result['data'][0]
            print(f"\nFirst result:")
            print(f"- Title: {first_record.get('fields', {}).get('title', 'N/A')}")
            print(f"- Date: {first_record.get('fields', {}).get('date', {}).get('created', 'N/A')}")
            print(f"- Source: {first_record.get('fields', {}).get('source', [{}])[0].get('name', 'N/A') if first_record.get('fields', {}).get('source') else 'N/A'}")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")

def test_filter_options():
    """Test fetching filter options"""
    print("\nTesting filter options...")
    
    try:
        options = reliefweb_api.get_filter_options()
        print(f"✅ Filter options retrieved")
        print(f"- Countries: {len(options.get('countries', []))} available")
        print(f"- Formats: {len(options.get('formats', []))} available")
        print(f"- Themes: {len(options.get('themes', []))} available")
        print(f"- Sources: {len(options.get('sources', []))} available")
        
        if options.get('formats'):
            print(f"\nAvailable formats: {', '.join(options['formats'][:10])}")
            
    except Exception as e:
        print(f"❌ Filter options failed: {e}")

def test_date_range_query():
    """Test query with date range"""
    print("\nTesting date range query...")
    
    filters = {
        'country': 'Sudan',
        'country_filter_type': 'primary',
        'format': 'Assessment',
        'date_from': '2024-01-01',
        'date_to': '2024-12-31',
        'limit': 3
    }
    
    try:
        result = reliefweb_api.fetch_reports(filters)
        print(f"✅ Date range query successful. Found {result.get('totalCount', 0)} total results")
        
        if result.get('data'):
            print(f"Returned {len(result['data'])} records")
            for i, record in enumerate(result['data'][:3], 1):
                fields = record.get('fields', {})
                title = fields.get('title', 'N/A')[:50] + '...' if len(fields.get('title', '')) > 50 else fields.get('title', 'N/A')
                date_created = fields.get('date', {}).get('created', 'N/A')
                print(f"  {i}. {title} ({date_created})")
        
    except Exception as e:
        print(f"❌ Date range query failed: {e}")

if __name__ == "__main__":
    print("=== ReliefWeb API Test Suite ===\n")
    test_basic_connection()
    test_simple_query()
    test_date_range_query()
    test_filter_options()
    print("\n=== Test Suite Complete ===")