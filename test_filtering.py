import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.reliefweb_api import manual_validation_check, fetch_assessments
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

def test_filtering():
    print("🧪 Testing Filtering Logic")
    print("=" * 50)
    
    # Test 1: Manual validation check
    print("\n1️⃣ Manual Validation Check...")
    manual_validation_check('Sudan', 'primary', 20)
    
    # Test 2: Full extraction test
    print("\n2️⃣ Full Extraction Test...")
    params = {
        'country': 'Sudan',
        'country_filter_type': 'primary',
        'format': 'Assessment',
        'limit': '50',
        'download_docs': False
    }
    
    try:
        metadata, downloads = fetch_assessments(params, 'temp_downloads')
        print(f"✅ Extraction successful: {len(metadata)} records")
        
        if metadata:
            print("\n📋 Sample Results:")
            for i, record in enumerate(metadata[:3]):
                print(f"Record {i+1}:")
                print(f"  Title: {record['title'][:100]}...")
                print(f"  Primary: {record['primary_country']}")
                print(f"  All: {record['country']}")
                print("---")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")

if __name__ == "__main__":
    test_filtering()