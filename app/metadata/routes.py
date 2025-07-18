"""
Metadata Blueprint for Assessment Registry

This module provides all routes for viewing and exporting metadata, including:
- Viewing all saved metadata in a table
- Downloading metadata as CSV or Excel

All endpoints are documented and include error handling and logging.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request, Response
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_utils import get_all_metadata
import pandas as pd
from io import StringIO, BytesIO
import logging

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

    Query Parameters:
        format: 'csv' (default) or 'excel'

    Returns:
        File download response (CSV or Excel).

    Errors:
        Redirects to index with a flash message if download fails.
    """
    try:
        data = get_all_metadata(DB_PATH)
        if not data:
            flash("No metadata available for download", "warning")
            return redirect(url_for("main.index"))

        # Get format from query parameter
        format_type = request.args.get('format', 'csv').lower()

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
                    "Content-Disposition": "attachment;filename=humanitarian_assessments_metadata.xlsx",
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
                    "Content-Disposition": "attachment;filename=humanitarian_assessments_metadata.csv",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )

    except Exception as e:
        logger.error(f"Error downloading metadata: {str(e)}")
        flash(f"Error generating download: {str(e)}", "error")
        return redirect(url_for("main.index"))