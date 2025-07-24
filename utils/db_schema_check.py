import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def check_current_database_schema():
    """
    Check the current database schema and report what exists
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
    
    if not os.path.exists(db_path):
        print("❌ Database file does not exist!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 DATABASE SCHEMA ANALYSIS")
        print("=" * 60)
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
        
        print("\n📊 TABLE DETAILS:")
        print("-" * 60)
        
        for table in tables:
            try:
                # Get table info
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                print(f"\n🗂️  {table.upper()} ({count} records)")
                print(f"   Columns ({len(columns)}):")
                for col in columns:
                    col_id, name, data_type, not_null, default, pk = col
                    pk_indicator = " [PK]" if pk else ""
                    not_null_indicator = " NOT NULL" if not_null else ""
                    default_indicator = f" DEFAULT {default}" if default else ""
                    print(f"     {name}: {data_type}{pk_indicator}{not_null_indicator}{default_indicator}")
                
                # Check for indexes
                cursor.execute(f"PRAGMA index_list({table})")
                indexes = cursor.fetchall()
                if indexes:
                    print(f"   Indexes ({len(indexes)}):")
                    for idx in indexes:
                        print(f"     - {idx[1]}")
                
            except Exception as e:
                print(f"   ❌ Error reading {table}: {e}")
        
        # Check specific schema requirements
        print("\n🔧 SCHEMA REQUIREMENTS CHECK:")
        print("-" * 60)
        
        required_tables = {
            'assessments': 'Core assessment metadata',
            'document_downloads': 'PDF download tracking', 
            'document_registry': 'Document management',
            'document_content': 'Extracted text content',
            'document_embeddings': 'Vector embeddings',
            'content_metadata': 'Content analysis results',
            'admin_districts': 'Geographic tagging',
            'content_processing_jobs': 'Background jobs'
        }
        
        missing_tables = []
        for table, description in required_tables.items():
            if table in tables:
                print(f"✅ {table}: {description}")
            else:
                print(f"❌ {table}: {description} [MISSING]")
                missing_tables.append(table)
        
        # Check for recent schema additions
        print("\n📈 RECENT ADDITIONS CHECK:")
        print("-" * 60)
        
        # Check if assessments table has file_urls column
        cursor.execute("PRAGMA table_info(assessments)")
        assessment_columns = [col[1] for col in cursor.fetchall()]
        
        if 'file_urls' in assessment_columns:
            print("✅ file_urls column exists in assessments table")
        else:
            print("❌ file_urls column missing from assessments table")
        
        if 'platform_aggr' in assessment_columns:
            print("✅ platform_aggr column exists in assessments table")
        else:
            print("❌ platform_aggr column missing from assessments table")
        
        # Check content_metadata table structure
        if 'content_metadata' in tables:
            cursor.execute("PRAGMA table_info(content_metadata)")
            metadata_columns = [col[1] for col in cursor.fetchall()]
            
            expected_metadata_cols = [
                'document_id', 'assessment_id', 'language', 'word_count',
                'page_count', 'key_topics', 'named_entities', 'admin_districts'
            ]
            
            missing_cols = [col for col in expected_metadata_cols if col not in metadata_columns]
            if missing_cols:
                print(f"⚠️  content_metadata missing columns: {missing_cols}")
            else:
                print("✅ content_metadata has all expected columns")
        
        conn.close()
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total tables: {len(tables)}")
        print(f"   Missing tables: {len(missing_tables)}")
        if missing_tables:
            print(f"   Missing: {', '.join(missing_tables)}")
        
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"❌ Error checking database schema: {e}")
        return False

def get_database_size_info():
    """Get database size and usage information"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
    
    if not os.path.exists(db_path):
        return None
    
    try:
        # File size
        file_size = os.path.getsize(db_path)
        file_size_mb = file_size / (1024 * 1024)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Database page info
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA page_size") 
        page_size = cursor.fetchone()[0]
        
        # Table sizes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_sizes = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_sizes[table] = count
        
        conn.close()
        
        return {
            'file_size_mb': round(file_size_mb, 2),
            'page_count': page_count,
            'page_size': page_size,
            'table_sizes': table_sizes
        }
        
    except Exception as e:
        logger.error(f"Error getting database size info: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Checking current database schema...")
    schema_ok = check_current_database_schema()
    
    print("\n💾 Database Size Information:")
    size_info = get_database_size_info()
    if size_info:
        print(f"   File size: {size_info['file_size_mb']} MB")
        print(f"   Pages: {size_info['page_count']} x {size_info['page_size']} bytes")
        print(f"   Largest tables:")
        sorted_tables = sorted(size_info['table_sizes'].items(), key=lambda x: x[1], reverse=True)
        for table, count in sorted_tables[:5]:
            print(f"     {table}: {count:,} records")
    
    if schema_ok:
        print("\n✅ Database schema is complete and ready!")
    else:
        print("\n⚠️  Database schema needs updates. Run schema migration.")