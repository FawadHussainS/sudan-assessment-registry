from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.reliefweb_api import fetch_assessments, get_filter_options
from utils.db_utils import save_metadata, get_database_stats
import traceback

# Create the blueprint - this is what needs to be imported
main = Blueprint('main', __name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'humanitarian_assessments.db')

@main.route('/')
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
                
                if not country or not format_type:
                    flash('Country and Document Format are required.', 'error')
                    return render_template('index.html', 
                                         db_stats=db_stats, 
                                         filter_options=filter_options,
                                         request=request)
                
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
                
                # Fetch assessments
                assessments = fetch_assessments(filters)
                
                if assessments:
                    # Save to database
                    saved_count = save_metadata(assessments, DB_PATH, download_files=download_docs)
                    flash(f'Successfully extracted and saved {saved_count} assessments!', 'success')
                else:
                    flash('No assessments found matching your criteria.', 'warning')
                
                # Redirect to prevent form resubmission
                return redirect(url_for('main.index'))
                
            except Exception as e:
                current_app.logger.error(f"Error extracting assessments: {e}")
                flash(f'Error extracting assessments: {str(e)}', 'error')
        
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
        
        # Fetch assessments
        assessments = fetch_assessments(filters)
        
        if assessments:
            # Save to database
            download_docs = data.get('download_docs', False)
            saved_count = save_metadata(assessments, DB_PATH, download_files=download_docs)
            
            return jsonify({
                'success': True, 
                'message': f'Successfully extracted and saved {saved_count} assessments!'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'No assessments found matching your criteria.'
            })
        
    except Exception as e:
        current_app.logger.error(f"Error in extract_assessments: {e}")
        return jsonify({'success': False, 'message': str(e)})