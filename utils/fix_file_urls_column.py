import sqlite3
import os
import logging

def add_file_urls_column():
    """Add the missing file_urls column to assessments table"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(assessments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'file_urls' not in columns:
            print("🔧 Adding file_urls column to assessments table...")
            cursor.execute("ALTER TABLE assessments ADD COLUMN file_urls TEXT DEFAULT ''")
            
            # Update existing records with file URLs from document_downloads
            cursor.execute('''
                UPDATE assessments 
                SET file_urls = (
                    SELECT GROUP_CONCAT(original_url, ', ')
                    FROM document_downloads 
                    WHERE document_downloads.assessment_id = assessments.id
                )
                WHERE id IN (
                    SELECT DISTINCT assessment_id 
                    FROM document_downloads
                )
            ''')
            
            conn.commit()
            print("✅ file_urls column added and populated successfully!")
            
            # Show updated count
            cursor.execute("SELECT COUNT(*) FROM assessments WHERE file_urls IS NOT NULL AND file_urls != ''")
            updated_count = cursor.fetchone()[0]
            print(f"📊 Updated {updated_count} records with file URLs")
            
        else:
            print("✅ file_urls column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding file_urls column: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Fixing file_urls column...")
    success = add_file_urls_column()
    
    if success:
        print("\n✅ Database schema is now complete!")
        print("🎯 Ready for full-scale ReliefWeb extraction!")
    else:
        print("\n❌ Failed to fix schema. Check error messages above.")