#!/usr/bin/env python3
"""
Debug script for Content Extraction system
"""
import sys
import os
sys.path.append(os.path.abspath('.'))

from utils.db_schema_update import debug_database_structure, verify_schema
from utils.db_utils import get_document_downloads, get_extracted_content_simple

def main():
    print("🔍 Content Extraction Debug Report")
    print("=" * 60)
    
    # 1. Database structure
    print("\n1️⃣  Database Structure:")
    debug_database_structure()
    
    # 2. Schema verification
    print("\n2️⃣  Schema Verification:")
    schema_ok = verify_schema()
    print(f"   Schema valid: {'✅' if schema_ok else '❌'}")
    
    # 3. Test data retrieval
    print("\n3️⃣  Data Retrieval Test:")
    db_path = "database/humanitarian_assessments.db"
    
    try:
        downloads = get_document_downloads(db_path)
        print(f"   📥 Downloads: {len(downloads)} found")
        
        if downloads:
            print(f"   📄 Sample: {downloads[0].get('filename', 'N/A')}")
            
    except Exception as e:
        print(f"   ❌ Downloads error: {e}")
    
    try:
        extracted = get_extracted_content_simple(db_path, limit=5)
        print(f"   📊 Extracted content: {len(extracted)} found")
        
    except Exception as e:
        print(f"   ❌ Extracted content error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Debug report complete")

if __name__ == "__main__":
    main()