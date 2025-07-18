"""
Monday.com Integration Blueprint for Assessment Registry

This module provides the route for integrating and importing assessment data from Monday.com.
- Handles GET (form display) and POST (fetch, deduplicate, and save) requests.
- Ensures database schema is up to date.
- Checks for duplicates before saving.
- Stores results in session for display.

All logic is refactored, documented, and matches the original app.py functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.db_schema_update import update_database_schema
from utils.monday_utils import fetch_monday_assessments, check_duplicates
from utils.db_utils import save_metadata
import logging
import traceback

# Create the monday blueprint
monday = Blueprint('monday', __name__)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'humanitarian_assessments.db')

@monday.route("/monday/update", methods=["GET", "POST"])
def update_ar_monday():
    """
    GET/POST /update-ar-monday

    Description:
        - GET: Renders the Monday.com integration form.
        - POST: Processes the form, fetches data from Monday.com, checks for duplicates,
          saves new records, and displays results.

    Returns:
        Renders update_ar_monday.html with results or redirects with flash messages.

    Errors:
        Handles and logs all errors, flashes user-friendly messages.
    """
    logger.info(f"=== DEBUG: update_ar_monday route called ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request endpoint: {request.endpoint}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request form: {dict(request.form) if request.form else 'No form data'}")

    try:
        # Ensure database schema is updated
        update_database_schema(DB_PATH)

        if request.method == "GET":
            logger.info("GET request - rendering template")
            # Show results from session if available
            results = session.pop('monday_results', None)
            return render_template("update_ar_monday.html", results=results)

        elif request.method == "POST":
            logger.info("POST request - processing form data")

            # Get API token and other form data
            api_token = request.form.get("api_token", "").strip()
            board_id = request.form.get("board_id", "1246796913")
            limit = request.form.get("limit", "100")

            logger.info(f"Form data extracted - Token: {len(api_token) if api_token else 0} chars, Board: {board_id}, Limit: {limit}")

            if not api_token:
                logger.warning("No API token provided")
                flash("API token is required", "error")
                return redirect(url_for("monday.update_ar_monday"))

            # Convert board_id and limit to integers
            try:
                board_id = int(board_id)
                limit = int(limit)
            except ValueError as e:
                logger.error(f"Invalid form data: {str(e)}")
                flash("Invalid board ID or limit", "error")
                return redirect(url_for("monday.update_ar_monday"))

            # Fetch data from Monday.com
            try:
                logger.info("Fetching Monday.com data...")
                monday_metadata = fetch_monday_assessments(api_token, board_id, limit)
                logger.info(f"Fetched {len(monday_metadata)} items from Monday.com")
            except Exception as e:
                logger.error(f"Error fetching Monday.com data: {str(e)}")
                flash(f"Error fetching Monday.com data: {str(e)}", "error")
                return redirect(url_for("monday.update_ar_monday"))

            if not monday_metadata:
                flash("No data found in Monday.com board", "warning")
                return redirect(url_for("monday.update_ar_monday"))

            # Check for duplicates
            try:
                logger.info("Checking for duplicates...")
                duplicate_check = check_duplicates(DB_PATH, monday_metadata)
                logger.info(f"Duplicate check complete: {duplicate_check['duplicate_count']} duplicates, {duplicate_check['new_count']} new records")
            except Exception as e:
                logger.error(f"Error checking duplicates: {str(e)}")
                flash(f"Error checking duplicates: {str(e)}", "error")
                return redirect(url_for("monday.update_ar_monday"))

            # Save new records to database
            if duplicate_check["new_records"]:
                try:
                    saved_count = save_metadata(DB_PATH, duplicate_check["new_records"])
                    logger.info(f"Saved {saved_count} new records to database")

                    message = f"Successfully processed {duplicate_check['total_fetched']} items from Monday.com. "
                    message += f"Found {duplicate_check['duplicate_count']} duplicates. "
                    message += f"Saved {saved_count} new records to database."

                    flash(message, "success")
                except Exception as e:
                    logger.error(f"Error saving records: {str(e)}")
                    flash(f"Error saving records: {str(e)}", "error")
                    return redirect(url_for("monday.update_ar_monday"))
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

            return redirect(url_for("monday.update_ar_monday"))

        else:
            logger.error(f"Unsupported method: {request.method}")
            flash("Method not allowed", "error")
            return redirect(url_for("monday.update_ar_monday"))

    except Exception as e:
        logger.error(f"Unexpected error in update_ar_monday: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f"Unexpected error: {str(e)}", "error")
        return jsonify({'error': 'Unexpected error occurred'}), 500

@monday.route('/monday/sync')
def sync_monday():
    """Placeholder for Monday.com sync functionality."""
    return jsonify({'message': 'Monday.com sync functionality coming soon'})