"""
Download-RW Blueprint: Download ReliefWeb documents for selected records.
"""
import os
import sys
import logging
from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for
import threading
import requests
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_utils import get_all_metadata, get_assessment_with_downloads, record_document_download

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

def download_document(url, filename, assessment_id):
    try:
        logger.info(f"Downloading: {url} -> {filename}")
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            file_path = os.path.join(DOCUMENTS_DIR, filename)
            with open(file_path, 'wb') as f:
                f.write(resp.content)
            
            # Record download in database
            file_size = len(resp.content)
            mime_type = resp.headers.get('content-type', 'application/octet-stream')
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
            record_document_download(db_path, assessment_id, filename, url, file_path, file_size, mime_type)
            
            logger.info(f"Downloaded successfully: {filename}")
            return True, None
        else:
            logger.error(f"Failed to download {url}: HTTP {resp.status_code}")
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        logger.error(f"Exception downloading {url}: {e}")
        return False, str(e)

@download_rw_bp.route('/download_rw/documents', methods=['GET'])
def download_documents():
    """
    GET /download_rw/documents
    Show the download documents page with assessments that can be downloaded.
    """
    try:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
        assessments = get_assessment_with_downloads(db_path, limit=100)
        
        # Add file info analysis for each assessment
        for assessment in assessments:
            file_info = assessment.get('file_info')
            urls = extract_urls(file_info)
            assessment['available_files'] = len(urls)
            assessment['has_downloadable_files'] = len(urls) > 0
            
        return render_template('download_documents.html', assessments=assessments)
    except Exception as e:
        logger.error(f"Error in download_documents GET: {e}", exc_info=True)
        flash(f'Error loading download page: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@download_rw_bp.route('/download_rw/documents', methods=['POST'])
def download_documents_api():
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
                success, err = download_document(url, fname, rid)
                results.append({
                    "id": rid,
                    "url": url,
                    "filename": fname,
                    "status": "downloaded" if success else "failed",
                    "error": err
                })
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Error in download_documents_api: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@download_rw_bp.route('/download_rw/bulk_download', methods=['POST'])
def bulk_download():
    """
    POST /download_rw/bulk_download
    Form submission to download selected documents
    """
    try:
        selected_ids = request.form.getlist('selected_assessments')
        if not selected_ids:
            flash('Please select at least one assessment to download.', 'warning')
            return redirect(url_for('download_rw.download_documents'))
        
        # Convert to integers
        ids = [int(id_str) for id_str in selected_ids]
        
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
        records = get_all_metadata(db_path)
        id_to_record = {rec['id']: rec for rec in records if rec.get('id') in ids}
        
        download_count = 0
        error_count = 0
        
        for rid in ids:
            rec = id_to_record.get(rid)
            if not rec:
                continue
            file_info = rec.get('file_info')
            title = rec.get('title', '')
            urls = extract_urls(file_info)
            
            for url in urls:
                ext = os.path.splitext(url)[1] or '.bin'
                safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
                fname = f"record_{rid}_{safe_title[:30]}{ext}"
                success, err = download_document(url, fname, rid)
                if success:
                    download_count += 1
                else:
                    error_count += 1
        
        if download_count > 0:
            flash(f'Successfully downloaded {download_count} documents!', 'success')
        if error_count > 0:
            flash(f'{error_count} downloads failed. Check logs for details.', 'warning')
        
        return redirect(url_for('download_rw.download_documents'))
        
    except Exception as e:
        logger.error(f"Error in bulk_download: {e}", exc_info=True)
        flash(f'Error during bulk download: {str(e)}', 'error')
        return redirect(url_for('download_rw.download_documents'))
