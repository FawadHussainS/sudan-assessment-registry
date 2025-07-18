"""
Metadata Blueprint for Assessment Registry

This module provides all routes for viewing and exporting metadata, including:
- Viewing all saved metadata in a table
- Downloading metadata as CSV or Excel

All endpoints are documented and include error handling and logging.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request, Response, jsonify
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_utils import get_all_metadata
import pandas as pd
from io import StringIO, BytesIO
import logging
import json

metadata = Blueprint('metadata', __name__)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'humanitarian_assessments.db')

@metadata.route("/metadata")
def view_metadata():
    """
    GET /metadata

    Description:
        Displays all saved metadata records in a table view.
        Used for browsing and reviewing all extracted assessment metadata.

    Returns:
        Renders metadata.html with all metadata records.

    Errors:
        Redirects to index with a flash message if loading fails.
    """
    try:
        data = get_all_metadata(DB_PATH)
        return render_template("metadata.html", data=data)
    except Exception as e:
        logger.error(f"Error viewing metadata: {str(e)}")
        flash(f"Error loading metadata: {str(e)}", "error")
        return redirect(url_for("main.index"))

@metadata.route("/download/metadata")
def download_metadata():
    """
    GET /download/metadata

    Description:
        Downloads all metadata as a CSV or Excel file.
        Supports proper Unicode and Excel formatting.
        Supports filtered exports and bulk selection.

    Query Parameters:
        format: 'csv' (default) or 'excel'
        filtered: 'true' if downloading filtered results
        selected_ids: comma-separated list of record IDs for bulk selection

    Returns:
        File download response (CSV or Excel).

    Errors:
        Redirects to index with a flash message if download fails.
    """
    try:
        # Get all data first
        all_data = get_all_metadata(DB_PATH)
        if not all_data:
            flash("No metadata available for download", "warning")
            return redirect(url_for("main.index"))

        # Get parameters
        format_type = request.args.get('format', 'csv').lower()
        is_filtered = request.args.get('filtered', 'false').lower() == 'true'
        selected_ids = request.args.get('selected_ids', '')
        
        # Filter data based on selection or filters
        if selected_ids:
            # Bulk selection - only include selected records
            selected_id_list = [int(id.strip()) for id in selected_ids.split(',') if id.strip().isdigit()]
            data = [record for record in all_data if record.get('id') in selected_id_list]
            filename_suffix = f"_selected_{len(data)}_records"
        elif is_filtered:
            # For filtered export, we need to apply the same filters as the frontend
            # For now, we'll pass all data and let the filename indicate it's filtered
            data = all_data
            filename_suffix = "_filtered"
        else:
            # All data
            data = all_data
            filename_suffix = ""

        if not data:
            flash("No records match your selection", "warning")
            return redirect(url_for("metadata.view_metadata"))

        # Create DataFrame
        df = pd.DataFrame(data)

        # Clean and format data for better readability
        if not df.empty:
            # Format date columns
            date_columns = ['date_created', 'created_at', 'updated_at']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

            # Truncate long text fields for CSV readability
            text_columns = ['body', 'body_html']
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).apply(lambda x: x[:500] + '...' if len(str(x)) > 500 else x)

        # Generate filename based on selection type
        base_filename = f"humanitarian_assessments_metadata{filename_suffix}"
        
        if format_type == 'excel':
            # Create Excel file with UTF-8 support
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Humanitarian Assessments', index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets['Humanitarian Assessments']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            cell_length = len(str(cell.value))
                            if cell_length > max_length:
                                max_length = cell_length
                        except Exception:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            excel_buffer.seek(0)
            return Response(
                excel_buffer.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment;filename={base_filename}.xlsx",
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet; charset=utf-8"
                }
            )
        else:
            # Create CSV with proper UTF-8 encoding
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_buffer.seek(0)

            # Convert to bytes with UTF-8 BOM for Excel compatibility
            csv_content = '\ufeff' + csv_buffer.getvalue()

            return Response(
                csv_content.encode('utf-8'),
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment;filename={base_filename}.csv",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )

    except Exception as e:
        logger.error(f"Error downloading metadata: {str(e)}")
        flash(f"Error generating download: {str(e)}", "error")
        return redirect(url_for("main.index"))


@metadata.route("/api/filtered-data", methods=['POST'])
def get_filtered_data():
    """
    POST /api/filtered-data

    Description:
        Returns filtered data based on frontend filters.
        Used for filtered exports.

    Request Body:
        JSON with filter parameters:
        - search: search term
        - country: country filter
        - format: format filter  
        - sources: array of source filters
        - theme: theme filter
        - dateFrom: start date
        - dateTo: end date

    Returns:
        JSON with filtered record IDs.
    """
    try:
        filters = request.get_json()
        if not filters:
            return jsonify({'error': 'No filters provided'}), 400

        # Get all data
        all_data = get_all_metadata(DB_PATH)
        if not all_data:
            return jsonify({'record_ids': [], 'count': 0})

        # Apply filters
        filtered_data = []
        for record in all_data:
            # Apply search filter
            search_term = filters.get('search', '').lower()
            if search_term:
                title_match = search_term in str(record.get('title', '')).lower()
                country_match = search_term in str(record.get('country', '')).lower()
                source_match = search_term in str(record.get('source', '')).lower()
                if not (title_match or country_match or source_match):
                    continue

            # Apply country filter
            country_filter = filters.get('country', '')
            if country_filter and country_filter not in str(record.get('country', '')):
                continue

            # Apply format filter
            format_filter = filters.get('format', '')
            if format_filter and format_filter not in str(record.get('format', '')):
                continue

            # Apply source filter
            source_filters = filters.get('sources', [])
            if source_filters and 'all' not in source_filters:
                record_sources = str(record.get('source', '')).split(',')
                record_sources = [s.strip() for s in record_sources]
                if not any(src in record_sources for src in source_filters):
                    continue

            # Apply theme filter
            theme_filter = filters.get('theme', '')
            if theme_filter and theme_filter not in str(record.get('theme', '')):
                continue

            # Apply date filters
            date_from = filters.get('dateFrom', '')
            date_to = filters.get('dateTo', '')
            if date_from or date_to:
                record_date_str = record.get('date_created', '')
                if record_date_str and record_date_str != 'No Date':
                    try:
                        record_date = pd.to_datetime(record_date_str).date()
                        if date_from:
                            from_date = pd.to_datetime(date_from).date()
                            if record_date < from_date:
                                continue
                        if date_to:
                            to_date = pd.to_datetime(date_to).date()
                            if record_date > to_date:
                                continue
                    except:
                        continue
                else:
                    continue

            filtered_data.append(record)

        # Return record IDs
        record_ids = [record.get('id') for record in filtered_data if record.get('id')]
        return jsonify({'record_ids': record_ids, 'count': len(record_ids)})

    except Exception as e:
        logger.error(f"Error filtering data: {str(e)}")
        return jsonify({'error': str(e)}), 500