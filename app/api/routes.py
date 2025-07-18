"""
API Blueprint for Assessment Registry

This module provides API endpoints for:
- Listing available API fields
- Fetching record details for modal display
- Getting document counts based on filters
- Getting format breakdowns for a country
- Testing API connectivity

All endpoints are documented and include error handling and logging.
"""

from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.reliefweb_api import get_available_fields, get_document_count, get_all_format_counts_for_country
from utils.db_utils import get_record_by_id
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'humanitarian_assessments.db')

@api_bp.route("/api/fields")
def api_fields():
    """
    GET /api/fields

    Description:
        Renders a template listing all available fields from the ReliefWeb API.
        Useful for users to see what metadata fields are available for extraction.

    Returns:
        HTML page with a table/list of available fields.

    Errors:
        Redirects to main index with a flash message if fetching fields fails.
    """
    try:
        fields = get_available_fields()
        return render_template("fields.html", fields=fields)
    except Exception as e:
        logger.error(f"Error fetching API fields: {str(e)}")
        flash(f"Error fetching API fields: {str(e)}", "error")
        return redirect(url_for("main.index"))

@api_bp.route("/api/record/<int:record_id>")
def get_record_for_modal(record_id):
    """
    GET /api/record/<record_id>

    Description:
        Returns all metadata fields for a single record as JSON.
        Used for modal popups or AJAX detail views.

    Args:
        record_id (int): The database ID of the record.

    Returns:
        JSON object with all record fields, or error message if not found.

    Errors:
        404 if record not found.
        500 if database error occurs.
    """
    try:
        record = get_record_by_id(DB_PATH, record_id)
        if record:
            # Clean up empty fields and provide defaults
            formatted_record = dict(record)
            for key, value in formatted_record.items():
                if value is None or (isinstance(value, str) and value.strip() == ''):
                    formatted_record[key] = 'Not specified'
            return jsonify(formatted_record)
        else:
            return jsonify({"error": "Record not found"}), 404
    except Exception as e:
        logger.error(f"Error getting record for modal: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/count', methods=['POST'])
def get_count():
    """
    POST /api/count

    Description:
        Returns the count of documents matching the provided filters.
        Does not download or process the documents, just counts them.

    Request JSON:
        {
            "country": "Country Name",
            "format": "Assessment",
            "country_filter_type": "primary" | "associated" | "all",
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD"
        }

    Returns:
        JSON object with total count and filter summary.

    Errors:
        400 if required parameters are missing or request is not JSON.
        500 if an error occurs during count.
    """
    try:
        logger.info(f"Count API called. Content-Type: {request.content_type}")
        logger.info(f"Request data: {request.get_data()}")

        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()
        logger.info(f"Parsed JSON data: {data}")

        country = data.get('country', '').strip()
        format_type = data.get('format', '').strip() or None
        country_filter_type = data.get('country_filter_type', 'primary')
        date_from = data.get('date_from', '').strip() or None
        date_to = data.get('date_to', '').strip() or None

        logger.info(f"Processed parameters: country={country}, format={format_type}, filter={country_filter_type}, from={date_from}, to={date_to}")

        if not country:
            return jsonify({'error': 'Country is required'}), 400

        result = get_document_count(country, format_type, country_filter_type, date_from, date_to)
        logger.info(f"Count result: {result['total_count']} documents")

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"Error in count endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/format-counts/<country>')
def get_format_counts(country):
    """
    GET /api/format-counts/<country>?type=primary|associated|all

    Description:
        Returns a breakdown of document formats for the specified country.
        Useful for analytics and dashboard visualizations.

    Args:
        country (str): Country name (URL parameter)
        type (str): Filter type (query string, default 'primary')

    Returns:
        JSON object with format counts.

    Errors:
        500 if an error occurs during processing.
    """
    try:
        country_filter_type = request.args.get('type', 'primary')
        result = get_all_format_counts_for_country(country, country_filter_type)
        return jsonify({
            'success': True,
            'country': country,
            'filter_type': country_filter_type,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error in format counts endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/test', methods=['GET', 'POST'])
def test_api():
    """
    GET/POST /api/test

    Description:
        Simple endpoint to verify API is working.
        - GET: Returns a success message.
        - POST: Echoes back received JSON data.

    Returns:
        JSON object with success message and (for POST) received data.
    """
    if request.method == 'POST':
        data = request.get_json() if request.is_json else {}
        return jsonify({
            'success': True,
            'message': 'POST API test successful',
            'received_data': data
        })
    else:
        return jsonify({
            'success': True,
            'message': 'GET API test successful'
        })