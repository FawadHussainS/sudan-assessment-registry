"""
Test script for downloading ReliefWeb documents using file.url field.
Logs all errors and successes for debugging.
"""
import os
import sys
import logging
import requests
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('test_download_reliefweb_docs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import get_record_by_id or similar utility
try:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.db_utils import get_all_metadata
except Exception as e:
    logger.error(f"Could not import db_utils: {e}")
    get_all_metadata = None

# Directory to save downloads
download_dir = os.path.join(os.path.dirname(__file__), '..', 'temp_downloads')
os.makedirs(download_dir, exist_ok=True)

def get_sample_records(limit=10):
    """Get a sample of records with file.url field from the database."""
    if not get_all_metadata:
        logger.error("get_all_metadata not available.")
        return []
    try:
        # Construct the database path relative to this script
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db'))
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return []
        records = get_all_metadata(db_path)
        sample = []
        import re
        for rec in records:
            file_info = rec.get('file_info')
            if not file_info or (isinstance(file_info, str) and file_info.strip() == ''):
                continue
            urls = []
            if isinstance(file_info, str):
                # Split by | for multiple files
                file_parts = [part.strip() for part in file_info.split('|') if part.strip()]
                for part in file_parts:
                    # Try to extract URL after '- URL:'
                    url_idx = part.find('- URL:')
                    if url_idx != -1:
                        url = part[url_idx + 6:].strip()
                        # Validate URL (basic check)
                        if url.startswith('http'):
                            urls.append(url)
                    else:
                        # Try regex as fallback
                        match = re.search(r'https?://\S+', part)
                        if match:
                            urls.append(match.group(0))
            elif isinstance(file_info, dict):
                url = file_info.get('url')
                if url:
                    urls.append(url)
            elif isinstance(file_info, list):
                for f in file_info:
                    url = f.get('url')
                    if url:
                        urls.append(url)
            # Add found urls to sample
            for url in urls:
                sample.append({'id': rec.get('id'), 'url': url, 'title': rec.get('title', '')})
                if len(sample) >= limit:
                    return sample
        return sample
    except Exception as e:
        logger.error(f"Error fetching records: {e}")
        return []

def download_document(url, filename):
    """Download a document from ReliefWeb."""
    try:
        logger.info(f"Downloading: {url} -> {filename}")
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(resp.content)
            logger.info(f"Downloaded successfully: {filename}")
            return True
        else:
            logger.error(f"Failed to download {url}: HTTP {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Exception downloading {url}: {e}")
        return False

def main():
    logger.info("Starting ReliefWeb document download test...")
    sample = get_sample_records(limit=10)
    if not sample:
        logger.error("No sample records found with file.url.")
        return
    for rec in sample:
        url = rec['url']
        rid = rec['id']
        title = rec['title']
        ext = os.path.splitext(url)[1] or '.bin'
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        fname = f"record_{rid}_{safe_title[:30]}{ext}"
        fpath = os.path.join(download_dir, fname)
        success = download_document(url, fpath)
        if not success:
            logger.error(f"Failed to download for record {rid} ({title})")
    logger.info("Test complete.")

if __name__ == "__main__":
    main()
