import sys
import os

# Add the parent directory to the path so we can import from utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

print(f"Added to path: {parent_dir}")
print(f"Current working directory: {os.getcwd()}")

try:
    from utils.reliefweb_api import fetch_assessments
    print("✅ Successfully imported fetch_assessments")
except ImportError as e:
    print(f"❌ Failed to import fetch_assessments: {e}")
    print("Available modules in utils:")
    utils_path = os.path.join(parent_dir, 'utils')
    if os.path.exists(utils_path):
        print(f"Utils directory exists: {utils_path}")
        print(f"Files in utils: {os.listdir(utils_path)}")
    else:
        print(f"Utils directory not found: {utils_path}")
    sys.exit(1)

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_basic_extraction():
    """Test basic extraction functionality"""
    print("\n🧪 Testing Basic Extraction")
    print("=" * 50)
    
    params = {
        'country': 'Sudan',
        'country_filter_type': 'primary',
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
        print("\n🚀 Starting extraction...")
        downloads_dir = os.path.join(parent_dir, 'temp_downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        metadata, downloads = fetch_assessments(params, downloads_dir)
        
        print(f"\n✅ Extraction completed successfully!")
        print(f"📊 Results: {len(metadata)} records extracted")
        
        if metadata:
            print(f"\n📋 Sample Records (first 3):")
            for i, record in enumerate(metadata[:3]):
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.get('report_id', 'N/A')}")
                print(f"  Title: {record.get('title', 'N/A')[:100]}...")
                print(f"  Primary Country: '{record.get('primary_country', 'N/A')}'")
                print(f"  All Countries: '{record.get('country', 'N/A')}'")
                print(f"  Source: {record.get('source', 'N/A')}")
                print(f"  Date: {record.get('date_created', 'N/A')[:10]}")
        else:
            print("\n⚠️ No records returned - this might indicate a filtering issue!")
            
    except Exception as e:
        print(f"\n❌ Extraction failed with error: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

def test_country_variations():
    """Test different country filter types"""
    print("\n🔍 Testing Country Filter Variations")
    print("=" * 50)
    
    base_params = {
        'country': 'Sudan',
        'format': 'Assessment',
        'date_from': '2024-01-01',
        'date_to': '2025-06-19',
        'limit': '10',
        'download_docs': False
    }
    
    filter_types = ['primary', 'associated', 'all']
    results = {}
    
    for filter_type in filter_types:
        print(f"\n🎯 Testing filter type: {filter_type}")
        
        params = base_params.copy()
        params['country_filter_type'] = filter_type
        
        try:
            downloads_dir = os.path.join(parent_dir, 'temp_downloads')
            metadata, downloads = fetch_assessments(params, downloads_dir)
            results[filter_type] = len(metadata)
            print(f"  ✅ {filter_type}: {len(metadata)} records")
            
        except Exception as e:
            print(f"  ❌ {filter_type}: Failed with error: {e}")
            results[filter_type] = 0
    
    print(f"\n📊 Filter Type Comparison:")
    for filter_type, count in results.items():
        print(f"  {filter_type:12}: {count:3} records")
    
    if results.get('primary', 0) == 0 and results.get('all', 0) > 0:
        print("\n⚠️ WARNING: Primary filter returned 0 but 'all' returned results")
        print("   This suggests potential issues with primary country data quality")

def test_date_ranges():
    """Test different date ranges"""
    print("\n📅 Testing Date Range Variations")
    print("=" * 50)
    
    base_params = {
        'country': 'Sudan',
        'country_filter_type': 'primary',
        'format': 'Assessment',
        'limit': '10',
        'download_docs': False
    }
    
    date_ranges = [
        ('2025-01-01', '2025-06-19', '2025 Only'),
        ('2024-01-01', '2024-12-31', '2024 Only'),
        ('2023-01-01', '2023-12-31', '2023 Only'),
        ('2023-01-01', '2025-06-19', 'All Years')
    ]
    
    for date_from, date_to, description in date_ranges:
        print(f"\n📆 Testing: {description} ({date_from} to {date_to})")
        
        params = base_params.copy()
        params['date_from'] = date_from
        params['date_to'] = date_to
        
        try:
            downloads_dir = os.path.join(parent_dir, 'temp_downloads')
            metadata, downloads = fetch_assessments(params, downloads_dir)
            print(f"  ✅ {description}: {len(metadata)} records")
            
        except Exception as e:
            print(f"  ❌ {description}: Failed with error: {e}")

def main():
    """Run all tests"""
    print("🧪 SUDAN ASSESSMENT FILTERING VALIDATION")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Parent directory: {parent_dir}")
    
    try:
        # Test 1: Basic extraction
        test_basic_extraction()
        
        # Test 2: Country filter variations
        test_country_variations()
        
        # Test 3: Date range variations
        test_date_ranges()
        
        print("\n🎉 ALL TESTS COMPLETED")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Unexpected error in test suite: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()