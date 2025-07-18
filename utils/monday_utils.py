import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def fetch_monday_assessments(api_token: str, board_id: int = 1246796913, limit: int = 100) -> List[Dict]:
    """Fetch assessments from Monday.com board"""
    try:
        # Placeholder implementation - will be enhanced
        logger.info(f"Fetching Monday.com data with token: {api_token[:10]}...")
        
        # For now, return sample data
        return [{
            "id": "sample_1",
            "title": "Sample Monday.com Assessment",
            "platform_aggr": "Monday.com",
            "source": "Monday.com",
            "country": "Sudan",
            "primary_country": "Sudan",
            "format": "Assessment",
            "date_created": datetime.now().isoformat(),
            "body": "Sample assessment from Monday.com",
            "url": f"https://un-ocha.monday.com/boards/{board_id}/pulses/sample_1"
        }]
        
    except Exception as e:
        logger.error(f"Error fetching Monday.com assessments: {str(e)}")
        raise

def check_duplicates(db_path: str, new_metadata: List[Dict]) -> Dict:
    """Check for duplicates between Monday.com data and existing database records"""
    try:
        from utils.db_utils import get_all_metadata
        
        existing_records = get_all_metadata(db_path)
        
        duplicates = []
        new_records = []
        
        for new_record in new_metadata:
            is_duplicate = False
            
            for existing_record in existing_records:
                # Check for duplicates based on title and source
                if (new_record.get("title", "").lower() == existing_record.get("title", "").lower() and
                    new_record.get("source", "").lower() == existing_record.get("source", "").lower()):
                    is_duplicate = True
                    duplicates.append({
                        "new": new_record,
                        "existing": existing_record
                    })
                    break
            
            if not is_duplicate:
                new_records.append(new_record)
        
        return {
            "duplicates": duplicates,
            "new_records": new_records,
            "total_fetched": len(new_metadata),
            "duplicate_count": len(duplicates),
            "new_count": len(new_records)
        }
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {str(e)}")
        raise