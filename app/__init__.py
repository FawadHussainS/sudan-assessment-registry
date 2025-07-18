from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = "humanitarian-assessment-registry-2025"
    
    # Optional CORS - only import if available
    try:
        from flask_cors import CORS
        CORS(app)
    except ImportError:
        print("Warning: flask-cors not installed. CORS not enabled.")
        pass

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
    
    return app