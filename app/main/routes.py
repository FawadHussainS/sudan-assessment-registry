from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.reliefweb_api import fetch_assessments, get_filter_options
from utils.db_utils import save_metadata, get_database_stats
import traceback
import sqlite3

# Create the blueprint - this is what needs to be imported
main = Blueprint('main', __name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'humanitarian_assessments.db')
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'documents')

def extract_rw(filters, download_files=False):
    """
    Extract metadata from ReliefWeb API
    
    Args:
        filters (dict): Filters for the API request
        download_files (bool): Whether to download PDF files
        
    Returns:
        dict: Result with success status, message, and data
    """
    try:
        current_app.logger.info(f"🚀 Starting ReliefWeb extraction with filters: {filters}")
        
        # Validate required filters
        if not filters.get('country') or not filters.get('format'):
            return {
                'success': False,
                'message': 'Country and Document Format are required.',
                'data': None
            }
        
        # Fetch assessments from ReliefWeb
        assessments = fetch_assessments(filters, DOCUMENTS_DIR)
        
        if not assessments:
            return {
                'success': False,
                'message': 'No assessments found matching your criteria.',
                'data': None
            }
        
        # Save to database
        saved_count = save_metadata(DB_PATH, assessments)
        
        current_app.logger.info(f"✅ Successfully extracted {len(assessments)} assessments, saved {saved_count} new records")
        
        return {
            'success': True,
            'message': f'Successfully extracted and saved {saved_count} new assessments from {len(assessments)} total!',
            'data': {
                'total_fetched': len(assessments),
                'new_saved': saved_count,
                'existing_skipped': len(assessments) - saved_count
            }
        }
        
    except Exception as e:
        current_app.logger.error(f"❌ Error in ReliefWeb extraction: {e}")
        current_app.logger.error(traceback.format_exc())
        return {
            'success': False,
            'message': f'Error extracting from ReliefWeb: {str(e)}',
            'data': None
        }

@main.route('/', methods=['GET', 'POST'])
def index():
    """Main dashboard page with extraction form and recent records."""
    try:
        # Get database statistics
        db_stats = get_database_stats(DB_PATH)
        
        # Get filter options for the form
        filter_options = get_filter_options()
        
        # Handle POST request for extraction
        if request.method == 'POST':
            try:
                # Get form data
                country = request.form.get('country')
                format_type = request.form.get('format')
                theme = request.form.get('theme', '')
                source = request.form.get('source', '')
                language = request.form.get('language', '')
                date_from = request.form.get('date_from', '')
                date_to = request.form.get('date_to', '')
                limit = int(request.form.get('limit', 1000))
                download_docs = 'download_docs' in request.form
                country_filter_type = request.form.get('country_filter_type', 'all')
                
                # Build filters for API
                filters = {
                    'country': country,
                    'format': format_type,
                    'limit': min(limit, 1000)  # Enforce API limit
                }
                
                if theme:
                    filters['theme'] = theme
                if source:
                    filters['source'] = source
                if language:
                    filters['language'] = language
                if date_from:
                    filters['date.from'] = date_from
                if date_to:
                    filters['date.to'] = date_to
                
                # Set country filter type
                filters['country_filter_type'] = country_filter_type
                
                # Extract from ReliefWeb
                result = extract_rw(filters, download_docs)
                
                if result['success']:
                    flash(result['message'], 'success')
                else:
                    flash(result['message'], 'error')
                
                # Redirect to prevent form resubmission
                return redirect(url_for('main.index'))
                
            except Exception as e:
                current_app.logger.error(f"Error processing form: {e}")
                flash(f'Error processing request: {str(e)}', 'error')
        
        return render_template('index.html', 
                             db_stats=db_stats, 
                             filter_options=filter_options,
                             request=request)
        
    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {e}")
        current_app.logger.error(traceback.format_exc())
        return render_template('index.html', 
                             db_stats={'total_records': 0, 'recent_records': []}, 
                             filter_options={'countries': [], 'formats': []},
                             request=request,
                             error="An error occurred while loading the dashboard.")

@main.route('/extract', methods=['POST'])
def extract_assessments():
    """Handle assessment extraction via AJAX."""
    try:
        data = request.get_json()
        
        # Validate required fields
        country = data.get('country')
        format_type = data.get('format')
        
        if not country or not format_type:
            return jsonify({'success': False, 'message': 'Country and format are required'})
        
        # Build filters
        filters = {
            'country': country,
            'format': format_type,
            'limit': min(int(data.get('limit', 1000)), 1000)
        }
        
        # Add optional filters
        for field in ['theme', 'source', 'language']:
            if data.get(field):
                filters[field] = data[field]
        
        if data.get('date_from'):
            filters['date.from'] = data['date_from']
        if data.get('date_to'):
            filters['date.to'] = data['date_to']
        
        filters['country_filter_type'] = data.get('country_filter_type', 'all')
        
        # Extract from ReliefWeb
        download_docs = data.get('download_docs', False)
        result = extract_rw(filters, download_docs)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in extract_assessments: {e}")
        return jsonify({'success': False, 'message': str(e)})

@main.route('/api/extract_rw', methods=['POST'])
def api_extract_rw():
    """
    API endpoint specifically for ReliefWeb extraction
    Can be called from any module
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('filters'):
            return jsonify({'success': False, 'message': 'Filters are required'})
        
        filters = data['filters']
        download_files = data.get('download_files', False)
        
        # Extract from ReliefWeb
        result = extract_rw(filters, download_files)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in api_extract_rw: {e}")
        return jsonify({'success': False, 'message': str(e)})

@main.route('/api/record/<int:record_id>')
def get_record_details(record_id):
    """Get detailed information for a specific record"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM assessments WHERE id = ?", (record_id,))
        record = c.fetchone()
        conn.close()
        
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        # Convert Row object to dictionary
        record_dict = dict(record)
        
        return jsonify({'record': record_dict})
        
    except Exception as e:
        current_app.logger.error(f"Error getting record details: {e}")
        return jsonify({'error': 'Internal server error'}), 500