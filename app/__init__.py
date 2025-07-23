from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = "humanitarian-assessment-registry-2025"
    
    # Initialize database schema at startup
    try:
        from utils.db_schema_update import init_db, verify_schema
        db_initialized = init_db()
        schema_valid = verify_schema()
        
        if db_initialized and schema_valid:
            print("✓ Database schema initialized and verified")
        else:
            print("⚠ Database schema issues detected")
            
    except Exception as e:
        print(f"⚠ Database initialization warning: {e}")
    
    # Optional CORS - only import if available
    try:
        from flask_cors import CORS
        CORS(app)
        print("✓ CORS enabled")
    except ImportError:
        print("⚠ CORS not available")

    # Register blueprints with error handling
    try:
        from .main.routes import main
        app.register_blueprint(main)
        print("✓ Main blueprint registered")
    except ImportError as e:
        print(f"Error importing main blueprint: {e}")
    
    try:
        from .manage.routes import manage
        app.register_blueprint(manage)
        print("✓ Manage blueprint registered")
    except ImportError as e:
        print(f"Error importing manage blueprint: {e}")
    
    try:
        from .metadata.routes import metadata
        app.register_blueprint(metadata)
        print("✓ Metadata blueprint registered")
    except ImportError as e:
        print(f"Error importing metadata blueprint: {e}")
    
    try:
        from .monday.routes import monday
        app.register_blueprint(monday)
        print("✓ Monday blueprint registered")
    except ImportError as e:
        print(f"Error importing monday blueprint: {e}")
    
    try:
        from .api.routes import api_bp
        app.register_blueprint(api_bp)
        print("✓ API blueprint registered")
    except ImportError as e:
        print(f"Error importing API blueprint: {e}")
    
    # Register Download-RW blueprint
    try:
        from .download_rw.download_rw_bp import download_rw_bp
        app.register_blueprint(download_rw_bp)
        print("\u2713 Download-RW blueprint registered")
    except ImportError as e:
        print(f"Error importing Download-RW blueprint: {e}")
    
    # Register Document Registry blueprint
    try:
        from .document_registry.document_registry_bp import document_registry_bp
        app.register_blueprint(document_registry_bp)
        print("✓ Document Registry blueprint registered")
    except ImportError as e:
        print(f"Error importing Document Registry blueprint: {e}")
    
    # Register Content Extraction blueprint
    try:
        from .content_extraction.content_extraction_bp import content_extraction_bp
        app.register_blueprint(content_extraction_bp)
        print("✓ Content Extraction blueprint registered")
    except ImportError as e:
        print(f"Error importing Content Extraction blueprint: {e}")

    return app