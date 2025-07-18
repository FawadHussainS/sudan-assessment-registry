"""
Manage Blueprint for Assessment Registry

This module provides all routes for database management, including:
- Viewing and filtering records
- Sorting and searching
- Deleting single or multiple records
- Fetching record details for modals or detail views

All endpoints are documented and include error handling and logging.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
# FIXED: Use existing utils database functions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_utils import get_all_metadata, get_database_stats, get_record_by_id, delete_records
import traceback
from datetime import datetime, timedelta
import sqlite3

manage = Blueprint('manage', __name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'humanitarian_assessments.db')

def safe_get_sort_value(record, field):
    """Safely get a sortable value from a record field, handling various data types."""
    try:
        # Handle dictionary access for record data
        if isinstance(record, dict):
            value = record.get(field, None)
        else:
            value = getattr(record, field, None)
        
        if value is None:
            # Return appropriate default values for different field types
            if field in ['date_created', 'created_at']:
                return datetime.min.replace(tzinfo=None)  # Ensure timezone-naive
            elif field in ['id', 'report_id']:
                return 0
            else:
                return ''
        
        # Handle datetime fields specifically
        if field in ['date_created', 'created_at']:
            if isinstance(value, str):
                try:
                    # Parse string dates and ensure they're timezone-naive
                    parsed_date = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    # Convert to naive datetime (remove timezone info)
                    if parsed_date.tzinfo is not None:
                        parsed_date = parsed_date.replace(tzinfo=None)
                    return parsed_date
                except (ValueError, AttributeError):
                    return datetime.min.replace(tzinfo=None)
            elif hasattr(value, 'replace') and hasattr(value, 'tzinfo'):
                # It's a datetime object - make it timezone-naive
                if value.tzinfo is not None:
                    return value.replace(tzinfo=None)
                return value
            else:
                return datetime.min.replace(tzinfo=None)
        
        # Handle numeric fields
        if field in ['id', 'report_id']:
            try:
                return int(value) if value is not None else 0
            except (ValueError, TypeError):
                return 0
        
        # Handle string fields
        return str(value).lower() if value is not None else ''
        
    except Exception as e:
        # Fallback for any unexpected errors
        if field in ['date_created', 'created_at']:
            return datetime.min.replace(tzinfo=None)
        elif field in ['id', 'report_id']:
            return 0
        else:
            return ''

def get_filter_options():
    """Get all unique values for filter dropdowns using existing data."""
    try:
        # Get all records from database
        all_records = get_all_metadata(DB_PATH)
        
        options = {
            'primary_countries': [],
            'secondary_countries': [],
            'all_countries': []
        }
        
        if not all_records:
            return options
        
        # Extract unique values
        primary_countries = set()
        secondary_countries = set()
        
        for record in all_records:
            # Primary countries
            primary_country = record.get('primary_country', '').strip()
            if primary_country:
                primary_countries.add(primary_country)
            
            # Secondary countries (from country field)
            all_countries_str = record.get('country', '').strip()
            if all_countries_str:
                countries = [c.strip() for c in all_countries_str.split(',')]
                for country in countries:
                    if country and country != primary_country:
                        secondary_countries.add(country)
        
        # Combine all countries
        all_countries = primary_countries.union(secondary_countries)
        
        options['primary_countries'] = sorted(list(primary_countries))
        options['secondary_countries'] = sorted(list(secondary_countries))
        options['all_countries'] = sorted(list(all_countries))
        
        return options
        
    except Exception as e:
        current_app.logger.error(f"Error getting filter options: {e}")
        return {
            'primary_countries': [],
            'secondary_countries': [],
            'all_countries': []
        }

def apply_filters(records, filters):
    """Apply client-side filtering to records."""
    filtered_records = []
    
    for record in records:
        include_record = True
        
        # Title search
        if filters.get('searchTitle'):
            title = record.get('title', '').lower()
            if filters['searchTitle'].lower() not in title:
                include_record = False
                continue
        
        # Body search
        if filters.get('searchBody'):
            body = record.get('body', '').lower()
            if filters['searchBody'].lower() not in body:
                include_record = False
                continue
        
        # Primary country filter
        if filters.get('filterPrimaryCountry'):
            primary_country = record.get('primary_country', '')
            if filters['filterPrimaryCountry'] != primary_country:
                include_record = False
                continue
        
        # Secondary country filter
        if filters.get('filterSecondaryCountry'):
            all_countries = record.get('country', '')
            if filters['filterSecondaryCountry'] not in all_countries:
                include_record = False
                continue
        
        # Any country filter
        if filters.get('filterCountry'):
            primary_country = record.get('primary_country', '')
            all_countries = record.get('country', '')
            target_country = filters['filterCountry']
            if target_country not in primary_country and target_country not in all_countries:
                include_record = False
                continue
        
        # Date filters
        if filters.get('filterDateFrom'):
            record_date = record.get('date_created', '')
            if record_date and record_date < filters['filterDateFrom']:
                include_record = False
                continue
        
        if filters.get('filterDateTo'):
            record_date = record.get('date_created', '')
            if record_date and record_date > filters['filterDateTo']:
                include_record = False
                continue
        
        if include_record:
            filtered_records.append(record)
    
    return filtered_records

@manage.route('/manage')
def manage_database():
    """Main database management page with advanced filtering."""
    try:
        # Get database statistics using existing utility
        db_stats = get_database_stats(DB_PATH)
        
        # Get filter options
        filter_options = get_filter_options()
        
        # Get all records using existing utility
        all_records = get_all_metadata(DB_PATH)
        
        # Get query parameters
        filters = {
            'searchTitle': request.args.get('searchTitle', '').strip(),
            'searchBody': request.args.get('searchBody', '').strip(),
            'filterPrimaryCountry': request.args.get('filterPrimaryCountry', '').strip(),
            'filterSecondaryCountry': request.args.get('filterSecondaryCountry', '').strip(),
            'filterCountry': request.args.get('filterCountry', '').strip(),
            'filterDateFrom': request.args.get('filterDateFrom', '').strip(),
            'filterDateTo': request.args.get('filterDateTo', '').strip()
        }
        
        sort_by = request.args.get('sort', 'date_created')
        sort_order = request.args.get('order', 'desc')
        
        # Apply filters
        filtered_records = apply_filters(all_records, filters)
        
        # Sort records with safe comparison
        reverse_order = sort_order.lower() == 'desc'
        
        try:
            # Try to sort by the requested field
            filtered_records.sort(key=lambda x: safe_get_sort_value(x, sort_by), reverse=reverse_order)
        except Exception as sort_error:
            current_app.logger.warning(f"Error sorting by {sort_by}: {sort_error}")
            # Fallback to sorting by date_created
            filtered_records.sort(key=lambda x: safe_get_sort_value(x, "date_created"), reverse=True)
        
        # Convert records to objects for template compatibility
        class Record:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        data = [Record(**record) for record in filtered_records]
        
        return render_template('manage.html', 
                             data=data,
                             db_stats=db_stats,
                             filter_options=filter_options,
                             request=request)
        
    except Exception as e:
        current_app.logger.error(f"Error in manage_database: {e}")
        current_app.logger.error(traceback.format_exc())
        return render_template('manage.html', 
                             data=[],
                             db_stats={
                                 'total_records': 0,
                                 'unique_countries': 0,
                                 'unique_sources': 0,
                                 'records_last_7_days': 0,
                                 'top_countries': [],
                                 'top_sources': [],
                                 'recent_records': []
                             },
                             filter_options={
                                 'primary_countries': [],
                                 'secondary_countries': [],
                                 'all_countries': []
                             },
                             request=request,
                             error="An error occurred while loading the database management page.")

@manage.route('/delete_record', methods=['POST'])
def delete_record():
    """Delete a single record using existing utility."""
    try:
        data = request.get_json()
        record_id = data.get('id')
        
        if not record_id:
            return jsonify({'success': False, 'message': 'No record ID provided'})
        
        # Use existing delete utility
        deleted_count = delete_records(DB_PATH, {'id': record_id})
        
        if deleted_count > 0:
            return jsonify({'success': True, 'message': 'Record deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Record not found'})
        
    except Exception as e:
        current_app.logger.error(f"Error deleting record: {e}")
        return jsonify({'success': False, 'message': str(e)})

@manage.route('/delete_selected', methods=['POST'])
def delete_selected():
    """Delete multiple selected records."""
    try:
        data = request.get_json()
        record_ids = data.get('ids', [])
        
        if not record_ids:
            return jsonify({'success': False, 'message': 'No record IDs provided'})
        
        total_deleted = 0
        for record_id in record_ids:
            try:
                deleted_count = delete_records(DB_PATH, {'id': record_id})
                total_deleted += deleted_count
            except Exception as e:
                current_app.logger.warning(f"Failed to delete record {record_id}: {e}")
                continue
        
        return jsonify({
            'success': True, 
            'message': f'{total_deleted} records deleted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting selected records: {e}")
        return jsonify({'success': False, 'message': str(e)})

@manage.route('/record/<int:record_id>')
def get_record_details(record_id):
    """Get detailed information about a specific record using existing utility."""
    try:
        # Use existing utility to get record
        record = get_record_by_id(DB_PATH, record_id)
        
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        return jsonify({'record': record})
        
    except Exception as e:
        current_app.logger.error(f"Error getting record details: {e}")
        return jsonify({'error': str(e)}), 500