import sys
import os

# Add the parent directory to the path so we can import from utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from utils.reliefweb_api import fetch_assessments
    print("✅ Successfully imported fetch_assessments")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_inclusive_filtering():
    """Test the new inclusive Sudan filtering logic"""
    print("\n🧪 Testing INCLUSIVE Sudan Filtering")
    print("=" * 60)
    
    # Test with the scenario that was previously failing
    params = {
        'country': 'Sudan',
        'country_filter_type': 'all',  # Use 'all' to capture regional reports
        'format': 'Assessment',
        'date_from': '2024-01-01',
        'date_to': '2025-06-19',
        'limit': '20',
        'download_docs': False
    }
    
    print(f"📋 Test Parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    try:
        print("\n🚀 Starting inclusive extraction...")
        downloads_dir = os.path.join(parent_dir, 'temp_downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        metadata, downloads = fetch_assessments(params, downloads_dir)
        
        print(f"\n✅ Extraction completed!")
        print(f"📊 Results: {len(metadata)} records extracted")
        
        # Analyze the results
        pure_sudan = 0
        regional_sudan = 0
        
        for record in metadata:
            primary = record.get('primary_country', '')
            all_countries = record.get('country', '')
            
            if 'Sudan' in primary and 'South Sudan' not in primary:
                if 'South Sudan' in all_countries:
                    regional_sudan += 1
                else:
                    pure_sudan += 1
            elif 'Sudan' in all_countries and 'South Sudan' not in primary:
                regional_sudan += 1
        
        print(f"\n📊 BREAKDOWN:")
        print(f"  Pure Sudan records: {pure_sudan}")
        print(f"  Regional Sudan records: {regional_sudan}")
        print(f"  Total: {len(metadata)}")
        
        if metadata:
            print(f"\n📋 Sample Records:")
            for i, record in enumerate(metadata[:5]):
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.get('report_id', 'N/A')}")
                print(f"  Title: {record.get('title', 'N/A')[:100]}...")
                print(f"  Primary: '{record.get('primary_country', 'N/A')}'")
                print(f"  All: '{record.get('country', 'N/A')}'")
                
                # Highlight the previously problematic record
                if 'Sudan Displacement Tracking Matrix' in record.get('title', ''):
                    print(f"  🎯 FOUND: The DTM record that was previously filtered out!")
        
        return len(metadata)
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

def compare_filtering_approaches():
    """Compare old vs new filtering approaches"""
    print("\n🔍 Comparing Filtering Approaches")
    print("=" * 60)
    
    base_params = {
        'country': 'Sudan',
        'format': 'Assessment',
        'date_from': '2024-01-01',
        'date_to': '2025-06-19',
        'limit': '15',
        'download_docs': False
    }
    
    filter_types = ['primary', 'associated', 'all']
    results = {}
    
    for filter_type in filter_types:
        print(f"\n🎯 Testing {filter_type} filter...")
        
        params = base_params.copy()
        params['country_filter_type'] = filter_type
        
        try:
            downloads_dir = os.path.join(parent_dir, 'temp_downloads')
            metadata, downloads = fetch_assessments(params, downloads_dir)
            results[filter_type] = len(metadata)
            print(f"  ✅ {filter_type}: {len(metadata)} records")
            
        except Exception as e:
            print(f"  ❌ {filter_type}: Failed - {e}")
            results[filter_type] = 0
    
    print(f"\n📊 INCLUSIVE FILTERING COMPARISON:")
    print(f"  Primary Only: {results.get('primary', 0):3} records")
    print(f"  Associated:   {results.get('associated', 0):3} records")
    print(f"  All Mentions: {results.get('all', 0):3} records")
    
    total_unique = results.get('all', 0)  # 'all' should be most comprehensive
    print(f"\n🎯 RECOMMENDED: Use 'All Mentions' filter for maximum Sudan coverage ({total_unique} records)")

def main():
    """Run inclusive filtering tests"""
    print("🧪 INCLUSIVE SUDAN FILTERING VALIDATION")
    print("=" * 70)
    
    try:
        # Test 1: Inclusive filtering
        count = test_inclusive_filtering()
        
        # Test 2: Compare approaches
        compare_filtering_approaches()
        
        print(f"\n🎉 INCLUSIVE FILTERING TESTS COMPLETED")
        print(f"💡 The new logic should capture more relevant Sudan records!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()