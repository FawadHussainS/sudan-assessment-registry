import sqlite3
import os
import logging

def add_headline_column():
    """Add the missing headline column to assessments table"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(assessments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'headline' not in columns:
            print("🔧 Adding headline column to assessments table...")
            cursor.execute("ALTER TABLE assessments ADD COLUMN headline TEXT DEFAULT ''")
            conn.commit()
            print("✅ headline column added successfully!")
        else:
            print("✅ headline column already exists")
        
        # Verify all expected columns exist
        cursor.execute("PRAGMA table_info(assessments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        expected_columns = [
            'id', 'report_id', 'title', 'body', 'body_html', 'country', 
            'date_created', 'disaster', 'disaster_type', 'file_info', 
            'format', 'language', 'origin', 'primary_country', 'redirects', 
            'source', 'status', 'theme', 'url', 'url_alias', 'created_at', 
            'updated_at', 'platform_aggr', 'file_urls', 'headline'
        ]
        
        missing_columns = [col for col in expected_columns if col not in columns]
        
        if missing_columns:
            print(f"⚠️  Still missing columns: {missing_columns}")
            for col in missing_columns:
                print(f"🔧 Adding {col} column...")
                cursor.execute(f"ALTER TABLE assessments ADD COLUMN {col} TEXT DEFAULT ''")
            conn.commit()
            print("✅ All missing columns added!")
        else:
            print("✅ All required columns present!")
        
        # Show final column count
        cursor.execute("PRAGMA table_info(assessments)")
        final_columns = cursor.fetchall()
        print(f"📊 Final schema: {len(final_columns)} columns")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding headline column: {e}")
        return False

def show_recent_assessment_ids():
    """Show the newest assessment IDs to verify what's being processed"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'humanitarian_assessments.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the newest records by report_id
        cursor.execute("""
            SELECT report_id, title, date_created, created_at 
            FROM assessments 
            ORDER BY CAST(report_id AS INTEGER) DESC 
            LIMIT 10
        """)
        
        recent_records = cursor.fetchall()
        
        print("\n📊 Most Recent Records in Database:")
        print("-" * 80)
        for record in recent_records:
            report_id, title, date_created, created_at = record
            title_short = title[:60] + "..." if len(title) > 60 else title
            print(f"ID: {report_id} | {date_created} | {title_short}")
        
        # Get count by date range
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN date_created >= '2025-07-17' THEN 1 END) as recent_week,
                COUNT(CASE WHEN date_created >= '2025-07-01' THEN 1 END) as this_month
            FROM assessments
        """)
        
        counts = cursor.fetchone()
        print(f"\n📈 Database Statistics:")
        print(f"   Total records: {counts[0]}")
        print(f"   This month (July 2025): {counts[2]}")
        print(f"   Last week (July 17-24): {counts[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing recent records: {e}")

if __name__ == "__main__":
    print("🚀 Fixing headline column...")
    success = add_headline_column()
    
    if success:
        print("\n✅ Database schema is now complete!")
        show_recent_assessment_ids()
        print("\n🎯 Ready for fresh ReliefWeb extraction!")
        print("💡 Try extracting with a very recent date range (e.g., last 3 days) to get new records.")
    else:
        print("\n❌ Failed to fix schema. Check error messages above.")