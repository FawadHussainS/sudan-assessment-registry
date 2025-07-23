import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import logging
from utils.db_utils import create_content_tables

logger = logging.getLogger(__name__)


def update_database_schema(db_path: str):
    """Update database schema to include all required columns for content extraction"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check and add platform_aggr column to assessments
        cursor.execute("PRAGMA table_info(assessments)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'platform_aggr' not in columns:
            print("Adding platform_aggr column to database")
            cursor.execute("ALTER TABLE assessments ADD COLUMN platform_aggr TEXT DEFAULT 'ReliefWeb'")
            cursor.execute("UPDATE assessments SET platform_aggr = 'ReliefWeb' WHERE platform_aggr IS NULL")
            conn.commit()
            print("Successfully added platform_aggr column")
        else:
            print("platform_aggr column already exists")

        # Add all missing columns to content_metadata
        cursor.execute("PRAGMA table_info(content_metadata)")
        meta_columns = [column[1] for column in cursor.fetchall()]
        
        required_columns = {
            'document_id': 'INTEGER',
            'assessment_id': 'INTEGER', 
            'language': 'TEXT',
            'word_count': 'INTEGER',
            'page_count': 'INTEGER',
            'key_topics': 'TEXT',
            'named_entities': 'TEXT',
            'admin_districts': 'TEXT',
            'sentiment_score': 'REAL',
            'readability_score': 'REAL',
            'extraction_confidence': 'REAL',
            'processing_status': 'TEXT DEFAULT "completed"',
            'vector_ids': 'TEXT'
        }
        
        for column_name, column_type in required_columns.items():
            if column_name not in meta_columns:
                print(f"Adding {column_name} column to content_metadata table")
                try:
                    cursor.execute(f"ALTER TABLE content_metadata ADD COLUMN {column_name} {column_type}")
                    conn.commit()
                    print(f"Successfully added {column_name} column to content_metadata")
                except Exception as e:
                    print(f"Error adding {column_name} column: {e}")
            else:
                print(f"{column_name} column already exists in content_metadata")

        # Print final schema
        cursor.execute("PRAGMA table_info(content_metadata)")
        meta_columns = [column[1] for column in cursor.fetchall()]
        print(f"Final content_metadata columns: {meta_columns}")

        conn.close()
        return True
    except Exception as e:
        print(f"Error updating database schema: {str(e)}")
        return False

def init_db():
    """Initialize database with all required tables"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        create_content_tables(cursor)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER UNIQUE,
            title TEXT,
            body TEXT,
            body_html TEXT,
            country TEXT,
            date_created TEXT,
            disaster TEXT,
            disaster_type TEXT,
            file_info TEXT,
            format TEXT,
            language TEXT,
            origin TEXT,
            primary_country TEXT,
            redirects TEXT,
            source TEXT,
            status TEXT,
            theme TEXT,
            url TEXT,
            url_alias TEXT,
            platform_aggr TEXT DEFAULT 'ReliefWeb',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def verify_schema():
    """Verify all required tables exist"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
        
        if not os.path.exists(db_path):
            logger.warning(f"Database file does not exist: {db_path}")
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        required_tables = [
            'assessments',
            'document_downloads', 
            'document_content',
            'content_metadata',
            'document_embeddings',
            'admin_districts'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            create_content_tables(cursor)
            conn.commit()
            logger.info("Created missing tables")
        
        conn.close()
        logger.info(f"Schema verification completed. Existing tables: {existing_tables}")
        return True
        
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False

def debug_database_structure():
    """Debug function to print database structure"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
        
        if not os.path.exists(db_path):
            print(f"❌ Database file does not exist: {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Database Structure Analysis:")
        print("=" * 50)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Tables found: {tables}")
        
        for table in tables:
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                print(f"\n🗂️  Table: {table} ({count} records)")
                print(f"   Columns: {[col[1] for col in columns]}")
                
            except Exception as e:
                print(f"   ❌ Error reading {table}: {e}")
        
        conn.close()
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Database debug failed: {e}")

if __name__ == "__main__":
    print("🚀 Initializing and debugging database...")
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
    init_db()
    debug_database_structure()
    verify_schema()
    print("\n🔧 Running schema update for migrations...")
    result = update_database_schema(db_path)
    if result:
        print("✅ Schema update completed.")
    else:
        print("❌ Schema update failed. Check logs for details.")