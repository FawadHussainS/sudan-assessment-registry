import sqlite3
import logging

logger = logging.getLogger(__name__)

def update_database_schema(db_path: str):
    """Update database schema to include platform_aggr field"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if platform_aggr column exists
        cursor.execute("PRAGMA table_info(assessments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'platform_aggr' not in columns:
            logger.info("Adding platform_aggr column to database")
            cursor.execute("ALTER TABLE assessments ADD COLUMN platform_aggr TEXT DEFAULT 'ReliefWeb'")
            
            # Update existing records to have ReliefWeb as platform_aggr
            cursor.execute("UPDATE assessments SET platform_aggr = 'ReliefWeb' WHERE platform_aggr IS NULL")
            
            conn.commit()
            logger.info("Successfully added platform_aggr column")
        else:
            logger.info("platform_aggr column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False