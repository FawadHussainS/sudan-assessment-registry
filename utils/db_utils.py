import sqlite3
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def init_db(db_path):
    """Initialize SQLite database with proper schema"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create index for faster queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_report_id ON assessments(report_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_date_created ON assessments(date_created)")
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {db_path}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def save_metadata(db_path, metadata):
    """Save metadata to database with deduplication"""
    if not metadata:
        logger.warning("No metadata to save")
        return 0
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        saved_count = 0
        for meta in metadata:
            try:
                # Check if report already exists
                c.execute("SELECT id FROM assessments WHERE report_id = ?", (meta.get("report_id"),))
                if c.fetchone():
                    logger.info(f"Report {meta.get('report_id')} already exists, skipping")
                    continue
                
                # Process file_urls: convert to JSON string if it's a list
                file_urls = meta.get('file_urls', [])
                if isinstance(file_urls, list):
                    file_urls = json.dumps(file_urls)
                
                # Insert new record
                c.execute("""
                INSERT INTO assessments (
                    report_id, title, body, body_html, country, date_created,
                    disaster, disaster_type, file_info, format, language, origin,
                    primary_country, redirects, source, status, theme, url, url_alias
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meta.get("report_id"), meta.get("title"), meta.get("body"),
                    meta.get("body_html"), meta.get("country"), meta.get("date_created"),
                    meta.get("disaster"), meta.get("disaster_type"), meta.get("file_info"),
                    meta.get("format"), meta.get("language"), meta.get("origin"),
                    meta.get("primary_country"), meta.get("redirects"), meta.get("source"),
                    meta.get("status"), meta.get("theme"), meta.get("url"), meta.get("url_alias")
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Failed to save record {meta.get('report_id')}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {saved_count} new records to database")
        return saved_count
        
    except Exception as e:
        logger.error(f"Database save operation failed: {str(e)}")
        raise

def get_all_metadata(db_path):
    """Retrieve all metadata from database"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        c = conn.cursor()
        
        c.execute("SELECT * FROM assessments ORDER BY date_created DESC")
        rows = c.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to retrieve metadata: {str(e)}")
        return []

def get_table_columns(db_path, table_name):
    """Get column names for a table"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in c.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        logger.error(f"Failed to get table columns: {str(e)}")
        return []

def get_database_stats(db_path):
    """Get comprehensive database statistics for dashboard"""
    try:
        conn = sqlite3.connect(db_path)
        conn.text_factory = str
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        stats = {}
        
        # Total records
        c.execute("SELECT COUNT(*) as count FROM assessments")
        stats['total_records'] = c.fetchone()['count']
        
        # Unique countries (from both primary_country and country fields)
        c.execute("""
            SELECT COUNT(DISTINCT country_name) as count FROM (
                SELECT primary_country as country_name FROM assessments 
                WHERE primary_country IS NOT NULL AND primary_country != ''
                UNION
                SELECT TRIM(country_name) as country_name FROM (
                    SELECT SUBSTR(country || ',', 1, INSTR(country || ',', ',') - 1) as country_name FROM assessments
                    WHERE country IS NOT NULL AND country != ''
                    UNION ALL
                    SELECT TRIM(SUBSTR(country || ',', INSTR(country || ',', ',') + 1)) as country_name FROM assessments
                    WHERE country IS NOT NULL AND country != '' AND INSTR(country, ',') > 0
                ) WHERE country_name != ''
            ) WHERE country_name IS NOT NULL AND country_name != ''
        """)
        unique_countries_result = c.fetchone()
        stats['unique_countries'] = unique_countries_result['count'] if unique_countries_result else 0
        
        # Unique sources
        c.execute("SELECT COUNT(DISTINCT source) as count FROM assessments WHERE source IS NOT NULL AND source != ''")
        stats['unique_sources'] = c.fetchone()['count']
        
        # Records in last 7 days - check both created_at and date_created
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        c.execute("""
            SELECT COUNT(*) as count FROM assessments 
            WHERE (created_at >= ? OR date_created >= ?)
        """, (seven_days_ago, seven_days_ago))
        stats['records_last_7_days'] = c.fetchone()['count']
        
        # Top 10 countries by frequency - include both primary and secondary countries
        c.execute("""
            WITH country_list AS (
                SELECT primary_country as country_name FROM assessments 
                WHERE primary_country IS NOT NULL AND primary_country != ''
                UNION ALL
                SELECT TRIM(country_part) as country_name FROM (
                    SELECT 
                        CASE 
                            WHEN INSTR(country, ';') > 0 THEN 
                                SUBSTR(country, 1, INSTR(country, ';') - 1)
                            WHEN INSTR(country, ',') > 0 THEN 
                                SUBSTR(country, 1, INSTR(country, ',') - 1)
                            ELSE country
                        END as country_part
                    FROM assessments WHERE country IS NOT NULL AND country != ''
                    UNION ALL
                    SELECT 
                        TRIM(SUBSTR(country, INSTR(country, ';') + 1)) as country_part
                    FROM assessments 
                    WHERE country IS NOT NULL AND country != '' AND INSTR(country, ';') > 0
                    UNION ALL
                    SELECT 
                        TRIM(SUBSTR(country, INSTR(country, ',') + 1)) as country_part
                    FROM assessments 
                    WHERE country IS NOT NULL AND country != '' AND INSTR(country, ',') > 0 AND INSTR(country, ';') = 0
                )
                WHERE country_part IS NOT NULL AND country_part != ''
            )
            SELECT country_name, COUNT(*) as count 
            FROM country_list 
            WHERE country_name IS NOT NULL AND country_name != ''
            GROUP BY country_name 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_countries = c.fetchall()
        stats['top_countries'] = [(row['country_name'], row['count']) for row in top_countries]
        
        # Top 10 sources by frequency
        c.execute("""
            SELECT source, COUNT(*) as count 
            FROM assessments 
            WHERE source IS NOT NULL AND source != '' 
            GROUP BY source 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_sources = c.fetchall()
        stats['top_sources'] = [(row['source'], row['count']) for row in top_sources]
        
        # Recent records (last 5)
        c.execute("""
            SELECT id, title, country, primary_country, source, format, date_created, created_at
            FROM assessments 
            ORDER BY COALESCE(created_at, date_created) DESC 
            LIMIT 5
        """)
        stats['recent_records'] = [dict(row) for row in c.fetchall()]
        
        # Format recent dates for better display
        for record in stats['recent_records']:
            if record['created_at']:
                try:
                    dt = datetime.fromisoformat(record['created_at'])
                    record['date_created'] = dt.strftime('%Y-%m-%d')
                except:
                    pass
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database statistics: {str(e)}")
        return {
            'total_records': 0,
            'unique_countries': 0,
            'unique_sources': 0,
            'records_last_7_days': 0,
            'top_countries': [],
            'top_sources': [],
            'recent_records': []
        }

def delete_records(db_path, filters):
    """Delete records based on filters (enhanced version)"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Build WHERE clause from filters
        where_conditions = []
        params = []
        
        for field, value in filters.items():
            if field == "id":
                # Exact match for ID
                where_conditions.append("id = ?")
                params.append(value)
            elif field == "date_from":
                where_conditions.append("date_created >= ?")
                params.append(value)
            elif field == "date_to":
                where_conditions.append("date_created <= ?")
                params.append(value)
            elif field in ["country", "primary_country", "source", "format", "theme"]:
                # Use LIKE for text fields
                where_conditions.append(f"{field} LIKE ?")
                params.append(f"%{value}%")
            else:
                # Exact match for other fields
                where_conditions.append(f"{field} = ?")
                params.append(value)
        
        if not where_conditions:
            logger.warning("No valid filter conditions provided for deletion")
            return 0
        
        where_clause = " AND ".join(where_conditions)
        
        # Count records to be deleted
        count_query = f"SELECT COUNT(*) FROM assessments WHERE {where_clause}"
        c.execute(count_query, params)
        count = c.fetchone()[0]
        
        if count == 0:
            logger.info("No records found matching deletion criteria")
            return 0
        
        # Delete records
        delete_query = f"DELETE FROM assessments WHERE {where_clause}"
        c.execute(delete_query, params)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted {count} records with filters: {filters}")
        return count
        
    except Exception as e:
        logger.error(f"Failed to delete records: {str(e)}")
        raise

def get_record_by_id(db_path, record_id):
    """Get a single record by ID"""
    try:
        conn = sqlite3.connect(db_path)
        conn.text_factory = str
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM assessments WHERE id = ?", (record_id,))
        row = c.fetchone()
        
        conn.close()
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Failed to get record by ID: {str(e)}")
        return None

def get_filtered_metadata(db_path, filters):
    """Get metadata with filters applied"""
    try:
        conn = sqlite3.connect(db_path)
        conn.text_factory = str
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        for field, value in filters.items():
            if value:
                if field in ["date_from"]:
                    where_conditions.append("date_created >= ?")
                    params.append(value)
                elif field in ["date_to"]:
                    where_conditions.append("date_created <= ?")
                    params.append(value)
                else:
                    where_conditions.append(f"{field} LIKE ?")
                    params.append(f"%{value}%")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"SELECT * FROM assessments WHERE {where_clause} ORDER BY date_created DESC"
        c.execute(query, params)
        rows = c.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get filtered metadata: {str(e)}")
        return []