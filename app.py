from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from utils.reliefweb_api import fetch_assessments, get_filter_options, get_document_count, get_all_format_counts_for_country, get_available_fields
from utils.db_utils import save_metadata, init_db, get_all_metadata, get_database_stats, delete_records, get_record_by_id
import pandas as pd
from io import StringIO, BytesIO
import os
import logging
import sqlite3

# Configure logging with UTF-8 support
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "humanitarian-assessment-registry-2025"

# Configuration
DB_PATH = "database/humanitarian_assessments.db"
DOWNLOADS_DIR = "downloads"

# Ensure directories exist
os.makedirs("database", exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Initialize database
init_db(DB_PATH)

# Get filter options (cache these for better performance)
try:
    FILTER_OPTIONS = get_filter_options()
    logger.info(f"Loaded filter options: {len(FILTER_OPTIONS.get('countries', []))} countries, {len(FILTER_OPTIONS.get('formats', []))} formats")
except Exception as e:
    logger.error(f"Failed to load filter options: {e}")
    FILTER_OPTIONS = {
        "countries": ["Sudan", "South Sudan", "Chad", "Ethiopia", "Somalia", "Yemen", "Syria", "Afghanistan"],
        "sources": ["OCHA", "UNHCR", "WFP", "UNICEF", "WHO"],
        "themes": ["Food and Nutrition", "Health", "Protection and Human Rights"],
        "languages": ["English", "French", "Arabic", "Spanish"],
        "formats": ["Assessment", "Evaluation", "Report", "Analysis", "Bulletin", "Infographic", "Map"]
    }

@app.route("/", methods=["GET", "POST"])
def index():
    """Main dashboard and extraction interface"""
    if request.method == "POST":
        try:
            # Get form data with validation
            params = {
                "country": request.form.get("country", "").strip(),
                "country_filter_type": request.form.get("country_filter_type", "primary"),
                "format": request.form.get("format", "").strip(),
                "theme": request.form.get("theme", "").strip(),
                "source": request.form.get("source", "").strip(),
                "language": request.form.get("language", "").strip(),
                "date_from": request.form.get("date_from", "").strip(),
                "date_to": request.form.get("date_to", "").strip(),
                "limit": request.form.get("limit", "1000"),
                "download_docs": request.form.get("download_docs") == "on"
            }
            
            # Validate required fields
            if not params["country"] or not params["format"]:
                flash("Country and Format are required fields", "error")
                return redirect(url_for("index"))
            
            logger.info(f"User submitted parameters: {params}")
            
            # Fetch assessments
            metadata, download_paths = fetch_assessments(params, DOWNLOADS_DIR)
            
            if not metadata:
                flash("No assessments found for the given criteria", "warning")
                return redirect(url_for("index"))
            
            # Save to database
            saved_count = save_metadata(DB_PATH, metadata)
            
            # Provide user feedback
            filter_type_desc = {
                "primary": "primary country",
                "associated": "associated country", 
                "all": "any mention"
            }
            
            message = f"Successfully processed {len(metadata)} assessments for {params['country']} "
            message += f"({filter_type_desc[params['country_filter_type']]}). "
            message += f"Saved {saved_count} new records to database. "
            if download_paths:
                message += f"Downloaded {len(download_paths)} documents."
            
            flash(message, "success")
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            flash(f"Error fetching data: {str(e)}", "error")
        
        return redirect(url_for("index"))
    
    # Get database statistics for dashboard
    try:
        db_stats = get_database_stats(DB_PATH)
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        db_stats = {
            'total_records': 0,
            'unique_countries': 0,
            'unique_sources': 0,
            'last_7_days': 0,
            'countries_list': [],
            'recent_records': []
        }
    
    return render_template("index.html", db_stats=db_stats, filter_options=FILTER_OPTIONS)

@app.route("/metadata")
def view_metadata():
    """View saved metadata with enhanced display"""
    try:
        data = get_all_metadata(DB_PATH)
        return render_template("metadata.html", data=data)
    except Exception as e:
        logger.error(f"Error viewing metadata: {str(e)}")
        flash(f"Error loading metadata: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/manage", methods=["GET", "POST"])
def manage_database():
    """Database management interface"""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "delete_filtered":
            try:
                filters = {
                    "country": request.form.get("filter_country", ""),
                    "primary_country": request.form.get("filter_primary_country", ""),
                    "source": request.form.get("filter_source", ""),
                    "date_from": request.form.get("filter_date_from", ""),
                    "date_to": request.form.get("filter_date_to", "")
                }
                
                # Remove empty filters
                filters = {k: v for k, v in filters.items() if v}
                
                if not filters:
                    flash("Please specify at least one filter for deletion", "warning")
                else:
                    deleted_count = delete_records(DB_PATH, filters)
                    flash(f"Deleted {deleted_count} records matching the criteria", "success")
                    
            except Exception as e:
                logger.error(f"Error deleting records: {str(e)}")
                flash(f"Error deleting records: {str(e)}", "error")
        
        return redirect(url_for("manage_database"))
    
    # Get current database stats
    try:
        db_stats = get_database_stats(DB_PATH)
        data = get_all_metadata(DB_PATH)
    except Exception as e:
        logger.error(f"Error loading management data: {str(e)}")
        db_stats = {}
        data = []
    
    return render_template("manage.html", db_stats=db_stats, data=data, filter_options=FILTER_OPTIONS)

@app.route("/manage/delete_record", methods=["POST"])
def delete_single_record():
    """Delete a single record by ID"""
    try:
        data = request.get_json()
        record_id = data.get('id')
        
        if not record_id:
            return jsonify({"success": False, "message": "No record ID provided"})
        
        deleted_count = delete_records(DB_PATH, {"id": record_id})
        
        if deleted_count > 0:
            logger.info(f"Deleted record {record_id}")
            return jsonify({"success": True, "message": f"Record {record_id} deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Record not found"})
            
    except Exception as e:
        logger.error(f"Error deleting single record: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/manage/delete_selected", methods=["POST"])
def delete_selected_records():
    """Delete multiple selected records"""
    try:
        data = request.get_json()
        record_ids = data.get('ids', [])
        
        if not record_ids:
            return jsonify({"success": False, "message": "No record IDs provided"})
        
        deleted_count = 0
        for record_id in record_ids:
            deleted_count += delete_records(DB_PATH, {"id": record_id})
        
        logger.info(f"Deleted {deleted_count} selected records")
        return jsonify({"success": True, "message": f"Deleted {deleted_count} records successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting selected records: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/record/<int:record_id>")
def get_record_for_modal(record_id):
    """Get record details for modal display on index page"""
    try:
        record = get_record_by_id(DB_PATH, record_id)
        
        if record:
            # Format the record for display
            formatted_record = dict(record)
            
            # Clean up empty fields and provide defaults
            for key, value in formatted_record.items():
                if value is None or (isinstance(value, str) and value.strip() == ''):
                    formatted_record[key] = 'Not specified'
            
            return jsonify(formatted_record)
        else:
            return jsonify({"error": "Record not found"}), 404
            
    except Exception as e:
        logger.error(f"Error getting record for modal: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/manage/record/<int:record_id>")
def get_record_details(record_id):
    """Get detailed information for a specific record"""
    try:
        record = get_record_by_id(DB_PATH, record_id)
        
        if record:
            return jsonify({"success": True, "record": record})
        else:
            return jsonify({"success": False, "message": "Record not found"})
            
    except Exception as e:
        logger.error(f"Error getting record details: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/download/metadata")
def download_metadata():
    """Download metadata as CSV or Excel with proper Unicode support"""
    try:
        data = get_all_metadata(DB_PATH)
        if not data:
            flash("No metadata available for download", "warning")
            return redirect(url_for("index"))
        
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
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Humanitarian Assessments']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            cell_length = len(str(cell.value))
                            if cell_length > max_length:
                                max_length = cell_length
                        except:
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
        return redirect(url_for("index"))

@app.route("/api/fields")
def api_fields():
    """Show available API fields"""
    try:
        fields = get_available_fields()
        return render_template("fields.html", fields=fields)
    except Exception as e:
        logger.error(f"Error fetching API fields: {str(e)}")
        flash(f"Error fetching API fields: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route('/api/count', methods=['POST'])
def get_count():
    """Get document count without downloading"""
    try:
        # Log the request
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

@app.route('/api/format-counts/<country>')
def get_format_counts(country):
    """Get all format counts for a country"""
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

@app.route('/api/test', methods=['GET', 'POST'])
def test_api():
    """Test endpoint to verify API is working"""
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

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('index.html', filter_options=FILTER_OPTIONS, db_stats={'total_records': 0}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    flash("An internal error occurred. Please try again.", "error")
    return render_template('index.html', filter_options=FILTER_OPTIONS, db_stats={'total_records': 0}), 500

if __name__ == "__main__":
    print("🚀 Starting Sudan Assessment Registry...")
    print("📊 Database initialized successfully")
    print("🔗 API connection verified")
    print("📁 Templates and static files loaded")
    print()
    print("🌐 Application will be available at:")
    print("   http://localhost:5000")
    print("   http://127.0.0.1:5000")
    print()
    print("📋 Available routes:")
    print("   / - Main dashboard and extraction")
    print("   /metadata - View all records")
    print("   /manage - Database management")
    print("   /api/fields - API field reference")
    print()
    print("✨ Ready to extract humanitarian assessments!")
    print("=" * 50)
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=False  # Disable reloader to prevent double startup
    )

