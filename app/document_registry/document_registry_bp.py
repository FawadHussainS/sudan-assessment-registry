"""
Document Registry Blueprint: Manage and track downloaded documents with metadata.
"""
import os
import sys
import logging
from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for
import threading
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_utils import get_all_metadata, get_document_downloads, get_document_registry_status


document_registry_bp = Blueprint('document_registry', __name__)
logger = logging.getLogger(__name__)

DOCUMENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'documents'))

# Helper to get registry info for all downloaded documents
def get_document_registry():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
    records = get_all_metadata(db_path)
    registry = []
    for rec in records:
        rid = rec.get('id')
        title = rec.get('title', '')
        file_info = rec.get('file_info')
        # Check for downloaded files in documents dir
        files = []
        if file_info:
            # Use same logic as download_rw to determine filenames
            urls = []
            import re
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
            for url in urls:
                ext = os.path.splitext(url)[1] or '.bin'
                safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
                fname = f"record_{rid}_{safe_title[:30]}{ext}"
                fpath = os.path.join(DOCUMENTS_DIR, fname)
                exists = os.path.exists(fpath)
                files.append({
                    'filename': fname,
                    'url': url,
                    'exists': exists
                })
        registry.append({
            'id': rid,
            'title': title,
            'files': files,
            'metadata': rec
        })
    return registry

@document_registry_bp.route('/document_registry/registry', methods=['GET'])
def registry():
    """
    GET /document_registry/registry
    Show the document registry page with all downloaded documents and their status.
    """
    try:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
        registry_data = get_document_registry_status(db_path)
        downloads_data = get_document_downloads(db_path)
        
        # Get summary statistics
        total_downloads = len(downloads_data)
        total_registry_entries = len(registry_data)
        pending_processing = len([r for r in registry_data if r.get('processing_status') == 'pending'])
        
        stats = {
            'total_downloads': total_downloads,
            'total_registry_entries': total_registry_entries,
            'pending_processing': pending_processing,
            'processed': total_registry_entries - pending_processing
        }
        
        return render_template('document_registry.html', 
                             registry=registry_data, 
                             downloads=downloads_data,
                             stats=stats)
    except Exception as e:
        logger.error(f"Error in registry GET: {e}", exc_info=True)
        flash(f'Error loading document registry: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@document_registry_bp.route('/document_registry/api/registry', methods=['GET'])
def get_registry_api():
    """
    GET /document_registry/api/registry
    API endpoint - Returns a list of all records with their downloaded files and metadata.
    """
    try:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db'))
        registry_data = get_document_registry_status(db_path)
        return jsonify({'registry': registry_data})
    except Exception as e:
        logger.error(f"Error in get_registry_api: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@document_registry_bp.route('/document_registry/record/<int:record_id>', methods=['GET'])
def get_record(record_id):
    """
    GET /document_registry/record/<record_id>
    Returns metadata and file info for a single record.
    """
    try:
        registry = get_document_registry()
        for rec in registry:
            if rec['id'] == record_id:
                return jsonify({'record': rec})
        return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_record: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
