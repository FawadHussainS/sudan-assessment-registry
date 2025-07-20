"""
Download-RW Blueprint: Download ReliefWeb documents for selected records.
"""
import os
import sys
import logging
from flask import Blueprint, request, jsonify, current_app
import threading
import requests
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_utils import get_all_metadata

download_rw_bp = Blueprint('download_rw', __name__)
logger = logging.getLogger(__name__)

DOCUMENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'documents'))
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Helper to extract URLs from file_info (same logic as test script)
def extract_urls(file_info):
    urls = []
    if not file_info or (isinstance(file_info, str) and file_info.strip() == ''):
        return urls
    if isinstance(file_info, str):
        file_parts = [part.strip() for part in file_info.split('|') if part.strip()]
        for part in file_parts:
            url_idx = part.find('- URL:')
            if url_idx != -1:
                url = part[url_idx + 6:].strip()
                if url.startswith('http'):
                    urls.append(url)
            else:
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
    return urls

def download_document(url, filename):
    try:
        logger.info(f"Downloading: {url} -> {filename}")
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(resp.content)
            logger.info(f"Downloaded successfully: {filename}")
            return True, None
        else:
            logger.error(f"Failed to download {url}: HTTP {resp.status_code}")
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        logger.error(f"Exception downloading {url}: {e}")
        return False, str(e)

@download_rw_bp.route('/download_rw/documents', methods=['POST'])
def download_documents():
    """
    POST /download_rw/documents
    Request JSON: { "ids": [record_id1, record_id2, ...] }
    Downloads all files for the given record IDs into the documents folder.
    Returns per-file status.
    """
    try:
        data = request.get_json()
        if not data or 'ids' not in data or not isinstance(data['ids'], list):
            return jsonify({"error": "Missing or invalid 'ids' list in request."}), 400
        ids = set(data['ids'])
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
        records = get_all_metadata(db_path)
        id_to_record = {rec['id']: rec for rec in records if rec.get('id') in ids}
        results = []
        for rid in ids:
            rec = id_to_record.get(rid)
            if not rec:
                results.append({"id": rid, "status": "not_found"})
                continue
            file_info = rec.get('file_info')
            title = rec.get('title', '')
            urls = extract_urls(file_info)
            if not urls:
                results.append({"id": rid, "status": "no_files"})
                continue
            for url in urls:
                ext = os.path.splitext(url)[1] or '.bin'
                safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
                fname = f"record_{rid}_{safe_title[:30]}{ext}"
                fpath = os.path.join(DOCUMENTS_DIR, fname)
                success, err = download_document(url, fpath)
                results.append({
                    "id": rid,
                    "url": url,
                    "filename": fname,
                    "status": "downloaded" if success else "failed",
                    "error": err
                })
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Error in download_documents: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
