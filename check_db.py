import sqlite3
import os

# Check both database locations
db_paths = ['data/assessments.db', 'database/humanitarian_assessments.db']

for db_path in db_paths:
    if os.path.exists(db_path):
        print(f'\n=== Checking {db_path} ===')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f'Tables found: {table_names}')
        
        # Check if document_downloads exists and has data
        if 'document_downloads' in table_names:
            cursor.execute('SELECT COUNT(*) FROM document_downloads')
            count = cursor.fetchone()[0]
            print(f'document_downloads records: {count}')
            
            if count > 0:
                cursor.execute('SELECT id, assessment_id, filename FROM document_downloads LIMIT 5')
                samples = cursor.fetchall()
                print(f'Sample records: {samples}')
                
                # Check if there are any content extractions
                if 'document_content' in table_names:
                    cursor.execute('SELECT COUNT(*) FROM document_content')
                    content_count = cursor.fetchone()[0]
                    print(f'document_content records: {content_count}')
                
                # Check document_registry table
                if 'document_registry' in table_names:
                    cursor.execute('SELECT COUNT(*) FROM document_registry')
                    registry_count = cursor.fetchone()[0]
                    print(f'document_registry records: {registry_count}')
                    
                    # Check registry schema
                    cursor.execute("PRAGMA table_info(document_registry)")
                    registry_schema = cursor.fetchall()
                    print(f'document_registry schema: {registry_schema}')
        
        conn.close()
    else:
        print(f'{db_path} does not exist')
