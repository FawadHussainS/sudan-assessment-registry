#!/usr/bin/env python3
"""
Test extraction functionality after fixes
"""
import sys
import os
sys.path.append('.')

from utils.db_utils import get_document_downloads, record_content_extraction
from utils.content_extractors import ContentExtractorFactory

def test_extraction():
    """Test the fixed extraction functionality"""
    print("🧪 Testing Content Extraction Fixes")
    print("=" * 50)
    
    # Test extraction
    db_path = 'database/humanitarian_assessments.db'
    downloads = get_document_downloads(db_path)
    print(f"📥 Found {len(downloads)} downloads")
    
    if downloads:
        doc = downloads[0]
        print(f"📄 Testing with document: {doc.get('filename')}")
        
        file_path = doc.get('file_path')
        if file_path and os.path.exists(file_path):
            print(f"✅ File exists: {file_path}")
            
            extractor = ContentExtractorFactory.get_extractor(file_path)
            if extractor:
                print("🔧 Extractor found, extracting...")
                extracted = extractor.extract(file_path)
                print(f"📊 Extracted {len(extracted.text)} characters")
                print(f"📑 Page count: {extracted.page_count}")
                print(f"🎯 Confidence: {extracted.confidence}")
                
                # Test recording
                metadata = {
                    'document_id': doc['id'],
                    'assessment_id': doc.get('assessment_id'),
                    'content_text': extracted.text[:1000],  # First 1000 chars for testing
                    'word_count': len(extracted.text.split()),
                    'page_count': extracted.page_count or 1,
                    'extraction_method': 'test_fix',
                    'extraction_confidence': extracted.confidence or 0.95,
                    'processing_time': 0.5
                }
                
                print("💾 Attempting to record extraction...")
                result = record_content_extraction(db_path, metadata)
                print(f"✅ Recording result: {result}")
                
                if result:
                    print("🎉 Extraction and recording successful!")
                else:
                    print("❌ Failed to record extraction")
                    
            else:
                print("❌ No extractor found for this file type")
        else:
            print(f"❌ File does not exist: {file_path}")
    else:
        print("❌ No documents found to test")
    
    print("=" * 50)
    print("✅ Test completed")

if __name__ == "__main__":
    test_extraction()
