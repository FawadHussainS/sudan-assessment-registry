"""
Content Extraction Blueprint: Extract, embed, and analyze document content
"""
import os
import sys
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

content_extraction_bp = Blueprint('content_extraction', __name__, url_prefix='/content_extraction')
logger = logging.getLogger(__name__)

@content_extraction_bp.route('/')
def extraction():  # Change from content_dashboard to extraction
    """Content extraction dashboard"""
    try:
        # Import here to avoid circular imports
        from utils.db_utils import get_document_downloads
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        # Get basic statistics
        try:
            downloads = get_document_downloads(db_path)
        except Exception as e:
            logger.warning(f"Could not get downloads: {e}")
            downloads = []
        
        stats = {
            'total_documents': len(downloads),
            'extracted': 0,  # Placeholder
            'pending': len(downloads),  # All pending for now
            'failed': 0,
            'total_embeddings': 0
        }
        
        return render_template('content_extraction.html',  # Use existing template
                             stats=stats, 
                             downloads=downloads[:20] if downloads else [])
                             
    except Exception as e:
        logger.error(f"Error loading content extraction dashboard: {e}")
        flash(f"Error loading dashboard: {e}", "error")
        return redirect(url_for('main.index'))

@content_extraction_bp.route('/process_document/<int:document_id>', methods=['POST'])
def process_document(document_id):
    """Process a single document (basic implementation)"""
    try:
        return jsonify({
            'success': True,
            'message': 'Document processing feature coming soon',
            'document_id': document_id
        })
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        return jsonify({'error': str(e)}), 500

@content_extraction_bp.route('/api/stats')
def get_stats():
    """Get content extraction statistics"""
    try:
        return jsonify({
            'total_documents': 0,
            'extracted': 0,
            'pending': 0,
            'failed': 0
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500