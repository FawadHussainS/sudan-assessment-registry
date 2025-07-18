import logging
import traceback
from flask import request, flash, redirect, url_for, render_template, session

logger = logging.getLogger(__name__)

def debug_monday_route(db_path: str):
    """Debug version of Monday.com route with extensive logging"""
    
    logger.info(f"=== DEBUG: update_ar_monday route called ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request endpoint: {request.endpoint}")
    logger.info(f"Request URL: {request.url}")
    
    if request.method == "GET":
        logger.info("GET request - rendering template")
        try:
            return render_template("update_ar_monday.html", results=None)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            logger.error(traceback.format_exc())
            flash("Template rendering error", "error")
            return redirect(url_for("index"))
    
    elif request.method == "POST":
        logger.info("POST request - processing form data")
        
        try:
            # Log form data
            logger.info(f"Form data: {dict(request.form)}")
            
            # Get form data
            api_token = request.form.get("api_token", "").strip()
            board_id = request.form.get("board_id", "1246796913")
            limit = request.form.get("limit", "100")
            
            logger.info(f"API token length: {len(api_token) if api_token else 0}")
            logger.info(f"Board ID: {board_id}")
            logger.info(f"Limit: {limit}")
            
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
            
            # Mock successful processing for now
            flash("Debug: Form processed successfully", "success")
            logger.info("POST processing completed successfully")
            
            return redirect(url_for("update_ar_monday"))
            
        except Exception as e:
            logger.error(f"Error processing POST request: {str(e)}")
            logger.error(traceback.format_exc())
            flash(f"Error processing request: {str(e)}", "error")
            return redirect(url_for("update_ar_monday"))
    
    else:
        logger.error(f"Unsupported method: {request.method}")
        flash("Method not allowed", "error")
        return redirect(url_for("index"))