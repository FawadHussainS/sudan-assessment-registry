import sqlite3
import logging
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def create_content_tables(cursor):
    """Create tables for content extraction and vector database"""
    
    # Document content table for storing extracted text
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        assessment_id INTEGER,
        original_text TEXT,
        cleaned_text TEXT,
        extraction_method TEXT,
        extraction_confidence REAL,
        page_count INTEGER,
        word_count INTEGER,
        char_count INTEGER,
        processing_time REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES document_downloads (id),
        FOREIGN KEY (assessment_id) REFERENCES assessments (id)
    )
    """)
    
    # Document embeddings table for vector storage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER,
        chunk_id INTEGER,
        chunk_text TEXT,
        chunk_start_pos INTEGER,
        chunk_end_pos INTEGER,
        embedding_vector TEXT,
        embedding_dimension INTEGER,
        embedding_model TEXT,
        similarity_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (content_id) REFERENCES document_content (id)
    )
    """)
    
    # Content metadata table for semantic analysis
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS content_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER,
        key_terms TEXT,
        named_entities TEXT,
        readability_scores TEXT,
        language_features TEXT,
        content_statistics TEXT,
        chunk_statistics TEXT,
        confidence_score REAL,
        extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (content_id) REFERENCES document_content (id)
    )
    """)
    
    # Admin districts table for geographic tagging
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_districts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER,
        country_iso2 TEXT,
        country_iso3 TEXT,
        country_name TEXT,
        admin_level INTEGER,
        admin_name TEXT,
        parent_admin TEXT,
        confidence REAL,
        extraction_method TEXT,
        coordinates TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (content_id) REFERENCES document_content (id)
    )
    """)
    
    # Content processing jobs table for tracking extraction pipeline
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS content_processing_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        job_type TEXT,
        status TEXT DEFAULT 'pending',
        processing_options TEXT,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        processing_time REAL,
        error_message TEXT,
        results_summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES document_downloads (id)
    )
    """)
    
    # Create indexes for content extraction tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_document ON document_content(document_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_assessment ON document_content(assessment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_content ON document_embeddings(content_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON document_embeddings(chunk_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_content ON content_metadata(content_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_districts_content ON admin_districts(content_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_districts_country ON admin_districts(country_iso2)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_document ON content_processing_jobs(document_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON content_processing_jobs(status)")

def parse_datetime(date_str):
    """Parse datetime string from database into datetime object"""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    try:
        # Try multiple datetime formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    except (ValueError, TypeError):
        return None

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
        
        # Create document downloads tracking table
        c.execute("""
        CREATE TABLE IF NOT EXISTS document_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id INTEGER,
            filename TEXT,
            original_url TEXT,
            file_size INTEGER,
            download_status TEXT DEFAULT 'completed',
            download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT,
            mime_type TEXT,
            checksum TEXT,
            FOREIGN KEY (assessment_id) REFERENCES assessments (id)
        )
        """)
        
        # Create document registry table for tracking and future AI features
        c.execute("""
        CREATE TABLE IF NOT EXISTS document_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id INTEGER,
            download_id INTEGER,
            document_type TEXT,
            processing_status TEXT DEFAULT 'pending',
            ai_summary TEXT,
            ai_embeddings TEXT,
            ai_keywords TEXT,
            ai_processed_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assessment_id) REFERENCES assessments (id),
            FOREIGN KEY (download_id) REFERENCES document_downloads (id)
        )
        """)
        
        # Enhanced Content Extraction Tables
        create_content_tables(c)

        # Create indexes for faster queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_report_id ON assessments(report_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_date_created ON assessments(date_created)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_download_assessment ON document_downloads(assessment_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_registry_assessment ON document_registry(assessment_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_registry_download ON document_registry(download_id)")
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {db_path}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def save_metadata(db_path, assessments):
    """Save assessment metadata to database
    
    Args:
        db_path (str): Path to database file
        assessments (list): List of assessment metadata dictionaries
        
    Returns:
        int: Number of new records saved
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        saved_count = 0
        
        # Handle both single dict and list of dicts
        if isinstance(assessments, dict):
            assessments = [assessments]
        elif not isinstance(assessments, list):
            logger.error(f"Invalid assessments data type: {type(assessments)}")
            return 0
        
        for meta in assessments:
            try:
                # Validate that meta is a dictionary
                if not isinstance(meta, dict):
                    logger.error(f"Invalid metadata item type: {type(meta)}, expected dict")
                    continue
                
                # Check if record already exists
                report_id = meta.get("report_id")
                if not report_id:
                    logger.warning(f"Skipping record without report_id: {meta.get('title', 'Unknown')}")
                    continue
                
                c.execute("SELECT id FROM assessments WHERE report_id = ?", (report_id,))
                existing = c.fetchone()
                
                if existing:
                    logger.debug(f"Record {report_id} already exists, skipping")
                    continue
                
                # Prepare data for insertion
                insert_data = {
                    'report_id': report_id,
                    'title': meta.get('title', ''),
                    'date_created': meta.get('date_created', ''),
                    'source': ', '.join(meta.get('source', [])) if isinstance(meta.get('source'), list) else str(meta.get('source', '')),
                    'format': ', '.join(meta.get('format', [])) if isinstance(meta.get('format'), list) else str(meta.get('format', '')),
                    'theme': ', '.join(meta.get('theme', [])) if isinstance(meta.get('theme'), list) else str(meta.get('theme', '')),
                    'country': ', '.join(meta.get('country', [])) if isinstance(meta.get('country'), list) else str(meta.get('country', '')),
                    'primary_country': meta.get('primary_country', ''),
                    'language': ', '.join(meta.get('language', [])) if isinstance(meta.get('language'), list) else str(meta.get('language', '')),
                    'status': meta.get('status', ''),
                    'url': meta.get('url', ''),
                    'url_alias': meta.get('url_alias', ''),
                    'body': meta.get('body', ''),
                    'body_html': meta.get('body_html', ''),
                    'file_urls': ', '.join([f.get('url', '') for f in meta.get('file', []) if isinstance(f, dict)]) if meta.get('file') else '',
                    'headline': meta.get('headline', ''),
                    'created_at': datetime.now().isoformat()
                }
                
                # Insert the record
                c.execute('''
                    INSERT INTO assessments (
                        report_id, title, date_created, source, format, theme, country, 
                        primary_country, language, status, url, url_alias, body, body_html, 
                        file_urls, headline, created_at
                    ) VALUES (
                        :report_id, :title, :date_created, :source, :format, :theme, :country,
                        :primary_country, :language, :status, :url, :url_alias, :body, :body_html,
                        :file_urls, :headline, :created_at
                    )
                ''', insert_data)
                
                saved_count += 1
                logger.debug(f"✅ Saved record: {report_id}")
                
            except Exception as e:
                logger.error(f"Failed to save record {meta.get('report_id', 'Unknown') if isinstance(meta, dict) else 'Invalid'}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully saved {saved_count} new assessment records")
        return saved_count
        
    except Exception as e:
        logger.error(f"Database save operation failed: {str(e)}")
        return 0

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
        
        # Top 10 countries by frequency - Python-based approach for proper splitting
        c.execute("SELECT primary_country, country FROM assessments")
        all_records = c.fetchall()
        
        country_counts = {}
        
        for record in all_records:
            # Get all countries mentioned in this record (avoid double counting)
            countries_in_record = set()
            
            # Process primary country
            primary_country = record['primary_country']
            if primary_country and primary_country.strip():
                country_name = primary_country.strip().title()
                countries_in_record.add(country_name)
            
            # Process secondary countries (split properly on both ; and ,)
            country_field = record['country']
            if country_field and country_field.strip():
                # Replace semicolons with commas and split
                countries_str = country_field.replace(';', ',')
                countries = [c.strip().title() for c in countries_str.split(',') if c.strip()]
                
                # Add all countries to the set (set will handle duplicates)
                for country in countries:
                    if country:
                        countries_in_record.add(country)
            
            # Count each unique country once per record
            for country in countries_in_record:
                country_counts[country] = country_counts.get(country, 0) + 1
        
        # Get top 10 countries
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats['top_countries'] = sorted_countries
        
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

def get_assessment_by_id(db_path, assessment_id):
    """Get assessment record by ID"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM assessments 
            WHERE id = ?
        ''', (assessment_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Error getting assessment by ID {assessment_id}: {e}")
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

def record_document_download(db_path, assessment_id, filename, original_url, file_path, file_size=None, mime_type=None, checksum=None):
    """Record a document download in the database"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO document_downloads 
            (assessment_id, filename, original_url, file_path, file_size, mime_type, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (assessment_id, filename, original_url, file_path, file_size, mime_type, checksum))
        
        download_id = c.lastrowid
        
        # Also create registry entry for future AI processing
        c.execute("""
            INSERT INTO document_registry 
            (assessment_id, download_id, document_type, processing_status)
            VALUES (?, ?, ?, 'pending')
        """, (assessment_id, download_id, 'pdf' if filename.endswith('.pdf') else 'other'))
        
        conn.commit()
        conn.close()
        logger.info(f"Recorded download: {filename} for assessment {assessment_id}")
        return download_id
        
    except Exception as e:
        logger.error(f"Failed to record document download: {str(e)}")
        return None

def get_document_downloads(db_path, assessment_id=None):
    """Get document downloads with integration status flags"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if assessment_id:
            c.execute("""
                SELECT d.*, a.title, a.country, a.source,
                       CASE WHEN dc.document_id IS NOT NULL THEN 1 ELSE 0 END as is_extracted,
                       CASE WHEN dr.download_id IS NOT NULL THEN 1 ELSE 0 END as is_managed
                FROM document_downloads d
                JOIN assessments a ON d.assessment_id = a.id
                LEFT JOIN document_content dc ON d.id = dc.document_id
                LEFT JOIN document_registry dr ON d.id = dr.download_id
                WHERE d.assessment_id = ?
                ORDER BY d.download_date DESC
            """, (assessment_id,))
        else:
            c.execute("""
                SELECT d.*, a.title, a.country, a.source,
                       CASE WHEN dc.document_id IS NOT NULL THEN 1 ELSE 0 END as is_extracted,
                       CASE WHEN dr.download_id IS NOT NULL THEN 1 ELSE 0 END as is_managed
                FROM document_downloads d
                JOIN assessments a ON d.assessment_id = a.id
                LEFT JOIN document_content dc ON d.id = dc.document_id
                LEFT JOIN document_registry dr ON d.id = dr.download_id
                ORDER BY d.download_date DESC
            """)
        
        rows = c.fetchall()
        conn.close()
        
        # Parse datetime fields and convert flags to boolean
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict['download_date'] = parse_datetime(row_dict.get('download_date'))
            row_dict['is_extracted'] = bool(row_dict.get('is_extracted', 0))
            row_dict['has_metadata'] = False  # Set to False since assessment_metadata table doesn't exist
            row_dict['is_managed'] = bool(row_dict.get('is_managed', 0))
            result.append(row_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get document downloads: {str(e)}")
        return []

def get_document_registry_status(db_path, assessment_id=None):
    """Get document registry with processing status"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if assessment_id:
            c.execute("""
                SELECT r.*, d.filename, d.original_url, d.file_path, d.download_date,
                       a.title, a.country, a.source
                FROM document_registry r
                JOIN document_downloads d ON r.download_id = d.id
                JOIN assessments a ON r.assessment_id = a.id
                WHERE r.assessment_id = ?
                ORDER BY r.created_at DESC
            """, (assessment_id,))
        else:
            c.execute("""
                SELECT r.*, d.filename, d.original_url, d.file_path, d.download_date,
                       a.title, a.country, a.source
                FROM document_registry r
                JOIN document_downloads d ON r.download_id = d.id
                JOIN assessments a ON r.assessment_id = a.id
                ORDER BY r.created_at DESC
            """)
        
        rows = c.fetchall()
        conn.close()
        
        # Parse datetime fields
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict['download_date'] = parse_datetime(row_dict.get('download_date'))
            row_dict['ai_processed_date'] = parse_datetime(row_dict.get('ai_processed_date'))
            row_dict['created_at'] = parse_datetime(row_dict.get('created_at'))
            row_dict['updated_at'] = parse_datetime(row_dict.get('updated_at'))
            result.append(row_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get document registry status: {str(e)}")
        return []

def get_assessment_with_downloads(db_path, limit=None):
    """Get assessments with their download status"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = """
            SELECT a.*, 
                   COUNT(d.id) as download_count,
                   GROUP_CONCAT(d.filename) as downloaded_files
            FROM assessments a
            LEFT JOIN document_downloads d ON a.id = d.assessment_id
            GROUP BY a.id
            ORDER BY a.date_created DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get assessments with downloads: {str(e)}")
        return []

# ===== CONTENT EXTRACTION DATABASE FUNCTIONS =====

def update_content_processing_status(db_path, document_id, status, error_message=None):
    """Update content processing status for a document"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if error_message:
            cursor.execute('''
                UPDATE content_metadata 
                SET processing_status = ?, updated_date = CURRENT_TIMESTAMP
                WHERE document_id = ?
            ''', (status, document_id))
        else:
            cursor.execute('''
                UPDATE content_metadata 
                SET processing_status = ?, updated_date = CURRENT_TIMESTAMP
                WHERE document_id = ?
            ''', (status, document_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating content processing status: {e}")
        return False

def record_content_extraction(db_path, content_metadata):
    """Record content extraction results"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, insert into document_content table (actual schema columns)
        cursor.execute('''
            INSERT INTO document_content (
                document_id, assessment_id, original_text, cleaned_text,
                extraction_method, extraction_confidence, page_count, word_count,
                char_count, processing_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            content_metadata['document_id'],
            content_metadata.get('assessment_id'),
            content_metadata.get('content_text', ''),  # Map content_text to original_text
            content_metadata.get('content_text', ''),  # Also use as cleaned_text for now
            content_metadata.get('extraction_method', 'automated'),
            content_metadata.get('extraction_confidence', 0.95),
            content_metadata.get('page_count', 1),
            content_metadata.get('word_count', 0),
            len(content_metadata.get('content_text', '')),  # char_count
            content_metadata.get('processing_time', 0.0)
        ))
        
        # Get the content_id from the insert
        content_id = cursor.lastrowid
        
        # Insert into content_metadata table (if it has the required columns)
        try:
            cursor.execute('''
                INSERT INTO content_metadata (
                    content_id, key_terms, named_entities, readability_scores,
                    language_features, content_statistics, chunk_statistics,
                    confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id,
                content_metadata.get('key_topics', ''),
                content_metadata.get('named_entities', ''),
                content_metadata.get('readability_score', ''),
                content_metadata.get('language', ''),
                json.dumps({'word_count': content_metadata.get('word_count', 0)}),
                '{}',  # Empty chunk statistics for now
                content_metadata.get('extraction_confidence', 0.95)
            ))
        except sqlite3.OperationalError as e:
            # If content_metadata table structure is different, skip this insert
            logger.warning(f"Could not insert into content_metadata: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Content extraction recorded for document {content_metadata['document_id']}")
        return content_id
        
    except Exception as e:
        logger.error(f"Error recording content extraction: {e}")
        return False

def get_content_metadata(db_path, document_id=None, limit=None):
    """Get content metadata with optional filtering"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT dc.*, dd.filename, dd.assessment_id, a.title, a.country,
                   COUNT(de.id) as chunk_count,
                   COUNT(ad.id) as admin_district_count
            FROM document_content dc
            LEFT JOIN document_downloads dd ON dc.document_id = dd.id
            LEFT JOIN assessments a ON dc.assessment_id = a.id
            LEFT JOIN document_embeddings de ON de.content_id = dc.id
            LEFT JOIN admin_districts ad ON ad.content_id = dc.id
        '''
        params = []
        
        if document_id:
            query += ' WHERE dc.document_id = ?'
            params.append(document_id)
        
        query += ' GROUP BY dc.id ORDER BY dc.created_at DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error getting content metadata: {e}")
        return []

def get_extracted_content_simple(db_path, limit=None):
    """Get simple extracted content list for dashboard (fallback method)"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to get from document_content table first
        try:
            query = '''
                SELECT dc.document_id, dc.assessment_id, dd.filename, 
                       dc.created_at as extracted_date, 'completed' as status
                FROM document_content dc
                LEFT JOIN document_downloads dd ON dc.document_id = dd.id
                ORDER BY dc.created_at DESC
            '''
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            
        except Exception:
            # Fallback: return empty list if table doesn't exist
            results = []
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error getting extracted content: {e}")
        return []