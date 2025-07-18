from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, session
from utils.reliefweb_api import fetch_assessments, get_filter_options, get_document_count, get_all_format_counts_for_country, get_available_fields
from utils.db_utils import save_metadata, init_db, get_all_metadata, get_database_stats, delete_records, get_record_by_id
from utils.content_utils import clean_html_content, format_date_for_display, truncate_text
from utils.monday_utils import fetch_monday_assessments, check_duplicates
from utils.db_schema_update import update_database_schema
import pandas as pd
from io import StringIO, BytesIO
import os
import logging
import sqlite3
import traceback  # Add this import
from collections import Counter

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
    logger.info(f"Loaded filter options: {FILTER_OPTIONS}")
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
        # Get existing countries from database for the extraction form
        existing_records = get_all_metadata(DB_PATH)
        db_countries = set()
        for record in existing_records:
            if record.get('primary_country'):
                db_countries.add(record['primary_country'])
            if record.get('country'):
                countries = [c.strip() for c in record['country'].split(';') if c.strip()]
                db_countries.update(countries)
        
        # Combine API countries with database countries
        combined_filter_options = FILTER_OPTIONS.copy()
        if db_countries:
            # Merge and sort countries
            all_countries = set(FILTER_OPTIONS.get('countries', []))
            all_countries.update(db_countries)
            combined_filter_options['countries'] = sorted(list(all_countries))
        
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
        combined_filter_options = FILTER_OPTIONS
    
    return render_template("index.html", db_stats=db_stats, filter_options=combined_filter_options)

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
    # --- 1. Gather filter values from request (GET or POST) ---
    filters = {
        "title": request.values.get("searchTitle", "").strip(),
        "body": request.values.get("searchBody", "").strip(),
        "primary_country": request.values.get("filterPrimaryCountry", "").strip(),
        "secondary_country": request.values.get("filterSecondaryCountry", "").strip(),
        "country": request.values.get("filterCountry", "").strip(),
        "source": request.values.get("filterSource", "").strip(),
        "format": request.values.get("filterFormat", "").strip(),
        "date_from": request.values.get("filterDateFrom", "").strip(),
        "date_to": request.values.get("filterDateTo", "").strip(),
    }

    # Get sorting parameters
    sort_by = request.values.get("sort", "date_created")
    sort_order = request.values.get("order", "desc")
    
    # --- 2. Fetch all records ---
    try:
        db_stats = get_database_stats(DB_PATH)
        records = get_all_metadata(DB_PATH)
    except Exception as e:
        logger.error(f"Error loading management data: {str(e)}")
        db_stats = {}
        records = []

    # --- Add this block to compute top countries and sources ---
    country_counter = Counter()
    source_counter = Counter()
    for r in records:
        if r.get('primary_country'):
            country_counter[r['primary_country']] += 1
        if r.get('source'):
            source_counter[r['source']] += 1

    db_stats['top_countries'] = country_counter.most_common(5)
    db_stats['top_sources'] = source_counter.most_common(5)

    # --- 3. Get available countries, sources, and formats from all records for filter options ---
    all_countries = set()
    primary_countries = set()
    secondary_countries = set()
    all_sources = set()
    all_formats = set()
    
    for record in records:
        # Primary countries
        if record.get('primary_country'):
            primary_countries.add(record['primary_country'])
            all_countries.add(record['primary_country'])
        
        # All countries (including secondary)
        if record.get('country'):
            countries = [c.strip() for c in record['country'].split(';') if c.strip()]
            for country in countries:
                all_countries.add(country)
                if country != record.get('primary_country'):
                    secondary_countries.add(country)
        
        # Sources
        if record.get('source'):
            all_sources.add(record['source'])
        
        # Formats
        if record.get('format'):
            all_formats.add(record['format'])

    # Create filter options from database data
    filter_options = {
        'primary_countries': sorted(list(primary_countries)),
        'secondary_countries': sorted(list(secondary_countries)),
        'all_countries': sorted(list(all_countries)),
        'sources': sorted(list(all_sources)),
        'formats': sorted(list(all_formats))
    }

    # --- 4. Filter records in Python ---
    def record_matches_filters(r):
        # Convert fields to lowercase for case-insensitive comparison
        rec_title = (r.get("title") or "").lower()
        rec_body = (r.get("body") or "").lower()
        rec_country = (r.get("country") or "").lower()
        rec_primary = (r.get("primary_country") or "").lower()
        rec_source = (r.get("source") or "").lower()
        rec_format = (r.get("format") or "").lower()
        rec_date = r.get("date_created") or ""

        # Title filter - case insensitive substring match
        if filters["title"] and filters["title"].lower() not in rec_title:
            return False
            
        # Body filter - case insensitive substring match
        if filters["body"] and filters["body"].lower() not in rec_body:
            return False
            
        # Primary country filter - exact match (case insensitive)
        if filters["primary_country"] and rec_primary != filters["primary_country"].lower():
            return False
            
        # General country filter (matches primary or any in country list) - case insensitive
        if filters["country"]:
            country_filter = filters["country"].lower()
            # Check if filter matches primary country or any country in the list
            country_matches = False
            if country_filter == rec_primary:
                country_matches = True
            elif rec_country:
                # Split countries and check each one
                countries_list = [c.strip().lower() for c in rec_country.split(";") if c.strip()]
                if country_filter in countries_list:
                    country_matches = True
            
            if not country_matches:
                return False
                
        # Secondary country filter - case insensitive
        if filters["secondary_country"]:
            secondary_filter = filters["secondary_country"].lower()
            if rec_country:
                # Split countries and check if the filter matches any secondary country
                countries_list = [c.strip().lower() for c in rec_country.split(";") if c.strip()]
                # Remove primary country from the list to get only secondary countries
                secondary_countries_list = [c for c in countries_list if c != rec_primary]
                if secondary_filter not in secondary_countries_list:
                    return False
            else:
                return False
                
        # Source filter - case insensitive substring match
        if filters["source"] and filters["source"].lower() not in rec_source:
            return False
            
        # Format filter - case insensitive substring match
        if filters["format"] and filters["format"].lower() not in rec_format:
            return False
            
        # Date from filter
        if filters["date_from"] and rec_date:
            try:
                if rec_date < filters["date_from"]:
                    return False
            except (ValueError, TypeError):
                pass
            
        # Date to filter
        if filters["date_to"] and rec_date:
            try:
                if rec_date > filters["date_to"]:
                    return False
            except (ValueError, TypeError):
                pass
            
        return True

    # Apply filters - only filter if at least one filter has a value
    filtered_records = []
    if any(filter_value for filter_value in filters.values() if filter_value):
        filtered_records = [r for r in records if record_matches_filters(r)]
        logger.info(f"Applied filters: {filters}")
        logger.info(f"Filtered {len(records)} records down to {len(filtered_records)}")
    else:
        filtered_records = records
        logger.info(f"No filters applied, showing all {len(records)} records")

    # --- 5. Sort filtered records ---
    def safe_get_sort_value(record, key):
        """Safely get sort value, handling None and different data types"""
        value = record.get(key)
        if value is None:
            return ""
        if key in ['date_created', 'created_at', 'updated_at']:
            # Handle date sorting
            try:
                if isinstance(value, str):
                    # Try to parse ISO format dates
                    from datetime import datetime
                    return datetime.fromisoformat(value.replace('Z', '+00:00').replace('T', ' '))
                return value
            except:
                return ""
        elif key == 'id':
            # Handle numeric ID sorting
            try:
                return int(value) if value else 0
            except:
                return 0
        else:
            # Handle string sorting
            return str(value).lower() if value else ""

    # Sort the filtered records
    reverse_order = (sort_order == "desc")
    try:
        filtered_records.sort(key=lambda x: safe_get_sort_value(x, sort_by), reverse=reverse_order)
    except Exception as e:
        logger.error(f"Error sorting records: {e}")
        # Fallback to default sorting by date
        filtered_records.sort(key=lambda x: safe_get_sort_value(x, "date_created"), reverse=True)

    # --- 6. Process records for better display ---
    import re
    from html import unescape
    
    

    # Process records for display
    for record in filtered_records:
        # Clean content preview
        if record.get('body'):
            record['content_preview'] = clean_html_content(record['body'])
        elif record.get('body_html'):
            record['content_preview'] = clean_html_content(record['body_html'])
        else:
            record['content_preview'] = "No content available"
        
        # Format date for display
        if record.get('date_created'):
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(record['date_created'].replace('Z', '+00:00'))
                record['formatted_date'] = date_obj.strftime('%Y-%m-%d')
            except:
                record['formatted_date'] = record['date_created'][:10] if len(record['date_created']) >= 10 else record['date_created']

    # --- 7. Get country counts for dropdown display based on filtered results ---
    country_counts = {}
    secondary_country_counts = {}
    all_country_counts = {}
    
    # Calculate counts for each country type based on filtered records
    for country in filter_options['primary_countries']:
        count = len([r for r in filtered_records if (r.get('primary_country') or '').lower() == country.lower()])
        if count > 0:  # Only include countries that have records
            country_counts[country] = count
    
    for country in filter_options['secondary_countries']:
        count = len([r for r in filtered_records 
                    if country.lower() in [c.strip().lower() for c in (r.get('country', '') or '').split(';')]])
        if count > 0:  # Only include countries that have records
            secondary_country_counts[country] = count
    
    for country in filter_options['all_countries']:
        count = len([r for r in filtered_records 
                    if (country.lower() in [c.strip().lower() for c in (r.get('country', '') or '').split(';')] or 
                        (r.get('primary_country') or '').lower() == country.lower())])
        if count > 0:  # Only include countries that have records
            all_country_counts[country] = count
    
    # --- 8. Render template with filtered and sorted data ---
    return render_template(
        "manage.html",
        db_stats=db_stats,
        filter_options=filter_options,
        data=filtered_records,
        country_counts=country_counts,
        secondary_country_counts=secondary_country_counts,
        all_country_counts=all_country_counts,
        current_filters=filters,
        current_sort=sort_by,
        current_order=sort_order
    )

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

@app.route("/update-ar-monday", methods=["GET", "POST"])
def update_ar_monday():
    """Fetch and manage Monday.com assessment data - DEBUG VERSION"""
    
    logger.info(f"=== DEBUG: update_ar_monday route called ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request endpoint: {request.endpoint}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request form: {dict(request.form) if request.form else 'No form data'}")
    
    try:
        # Ensure database schema is updated
        from utils.db_schema_update import update_database_schema
        update_database_schema(DB_PATH)
        
        if request.method == "GET":
            logger.info("GET request - rendering template")
            return render_template("update_ar_monday.html", results=None)
        
        elif request.method == "POST":
            logger.info("POST request - processing form data")
            
            # Get API token from form
            api_token = request.form.get("api_token", "").strip()
            board_id = request.form.get("board_id", "1246796913")
            limit = request.form.get("limit", "100")
            
            logger.info(f"Form data extracted - Token: {len(api_token) if api_token else 0} chars, Board: {board_id}, Limit: {limit}")
            
            if not api_token:
                logger.warning("No API token provided")
                flash("API token is required", "error")
                return redirect(url_for("update_ar_monday"))
            
            # Convert to proper types
            try:
                board_id = int(board_id)
                limit = int(limit)
            except ValueError as e:
                logger.error(f"Invalid form data: {str(e)}")
                flash("Invalid board ID or limit", "error")
                return redirect(url_for("update_ar_monday"))
            
            # Import Monday.com utilities
            try:
                from utils.monday_utils import fetch_monday_assessments, check_duplicates
                logger.info("Monday.com utilities imported successfully")
            except ImportError as e:
                logger.error(f"Import error: {str(e)}")
                flash(f"System error: {str(e)}", "error")
                return redirect(url_for("update_ar_monday"))
            
            # Fetch data from Monday.com
            try:
                logger.info("Fetching Monday.com data...")
                monday_metadata = fetch_monday_assessments(api_token, board_id, limit)
                logger.info(f"Fetched {len(monday_metadata)} items from Monday.com")
            except Exception as e:
                logger.error(f"Error fetching Monday.com data: {str(e)}")
                flash(f"Error fetching Monday.com data: {str(e)}", "error")
                return redirect(url_for("update_ar_monday"))
            
            if not monday_metadata:
                flash("No data found in Monday.com board", "warning")
                return redirect(url_for("update_ar_monday"))
            
            # Check for duplicates
            try:
                logger.info("Checking for duplicates...")
                duplicate_check = check_duplicates(DB_PATH, monday_metadata)
                logger.info(f"Duplicate check complete: {duplicate_check['duplicate_count']} duplicates, {duplicate_check['new_count']} new records")
            except Exception as e:
                logger.error(f"Error checking duplicates: {str(e)}")
                flash(f"Error checking duplicates: {str(e)}", "error")
                return redirect(url_for("update_ar_monday"))
            
            # Save new records to database
            if duplicate_check["new_records"]:
                try:
                    from utils.db_utils import save_metadata
                    saved_count = save_metadata(DB_PATH, duplicate_check["new_records"])
                    logger.info(f"Saved {saved_count} new records to database")
                    
                    message = f"Successfully processed {duplicate_check['total_fetched']} items from Monday.com. "
                    message += f"Found {duplicate_check['duplicate_count']} duplicates. "
                    message += f"Saved {saved_count} new records to database."
                    
                    flash(message, "success")
                except Exception as e:
                    logger.error(f"Error saving records: {str(e)}")
                    flash(f"Error saving records: {str(e)}", "error")
                    return redirect(url_for("update_ar_monday"))
            else:
                flash("All items from Monday.com already exist in database", "info")
            
            # Store results for display
            try:
                session['monday_results'] = {
                    'duplicates': duplicate_check['duplicates'],
                    'new_records': duplicate_check['new_records'],
                    'stats': {
                        'total_fetched': duplicate_check['total_fetched'],
                        'duplicate_count': duplicate_check['duplicate_count'],
                        'new_count': duplicate_check['new_count']
                    }
                }
                logger.info("Results stored in session")
            except Exception as e:
                logger.error(f"Error storing session data: {str(e)}")
            
            return redirect(url_for("update_ar_monday"))
            
        else:
            logger.error(f"Unsupported method: {request.method}")
            flash("Method not allowed", "error")
            return redirect(url_for("index"))
            
    except Exception as e:
        logger.error(f"Unexpected error in update_ar_monday: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f"Unexpected error: {str(e)}", "error")
        return redirect(url_for("index"))
    
    # Get results from session if available
    results = session.pop('monday_results', None)
    logger.info(f"Results from session: {results is not None}")
    
    return render_template("update_ar_monday.html", results=results)

# Add this after creating the Flask app but before the routes
@app.before_request
def debug_routes_once():
    if not hasattr(app, '_routes_printed'):
        print("Registered routes:")
        for rule in app.url_map.iter_rules():
            print(f"  {rule.endpoint}: {rule.rule}")
        app._routes_printed = True

def debug_routes():
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint}: {rule.rule}")

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
    
    # Call debug_routes before starting the app
    debug_routes()
    
    print("✨ Ready to extract humanitarian assessments!")
    print("=" * 50)
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=False  # Disable reloader to prevent double startup
    )

