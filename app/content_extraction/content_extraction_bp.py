"""
Content Extraction Blueprint: Extract, embed, and analyze document content
"""
import os
import sys
import logging
import json
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

content_extraction_bp = Blueprint('content_extraction', __name__, url_prefix='/content_extraction')
logger = logging.getLogger(__name__)

# Enable debug logging for this module
logging.basicConfig(level=logging.DEBUG)

@content_extraction_bp.route('/')
def extraction():
    """Content extraction dashboard"""
    logger.debug("🔍 Loading content extraction dashboard...")
    
    try:
        # Import here to avoid circular imports
        from utils.db_utils import get_document_downloads, get_extracted_content_simple
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        logger.debug(f"📍 Database path: {db_path}")
        logger.debug(f"📁 DB exists: {os.path.exists(db_path)}")
        
        # Get documents available for extraction
        downloads = []
        try:
            downloads = get_document_downloads(db_path)
            logger.debug(f"📥 Downloads found: {len(downloads)}")
            
            # Debug first few downloads
            for i, download in enumerate(downloads[:3]):
                logger.debug(f"   📄 Download {i+1}: ID={download.get('id')}, "
                           f"File={download.get('filename')}, "
                           f"Assessment={download.get('assessment_id')}")
                           
        except Exception as e:
            logger.error(f"❌ Could not get downloads: {e}")
            logger.debug(f"📍 Error details: ", exc_info=True)
        
        # Get extracted content using fallback method
        extracted_content = []
        try:
            extracted_content = get_extracted_content_simple(db_path, limit=50)
            logger.debug(f"📊 Extracted content found: {len(extracted_content)}")
            
            # Debug first few extracted items
            for i, content in enumerate(extracted_content[:3]):
                logger.debug(f"   📝 Content {i+1}: Doc_ID={content.get('document_id')}, "
                           f"Status={content.get('status')}")
                           
        except Exception as e:
            logger.error(f"❌ Could not get extracted content: {e}")
            logger.debug(f"📍 Error details: ", exc_info=True)
        
        # Calculate statistics
        stats = {
            'total_documents': len(downloads),
            'extracted': len(extracted_content),
            'pending': len(downloads) - len(extracted_content),
            'failed': 0,
            'vector_embeddings': 0  # Placeholder for future
        }
        
        logger.debug(f"📊 Dashboard stats: {stats}")
        
        return render_template('content_extraction.html', 
                             stats=stats, 
                             downloads=downloads[:20] if downloads else [],
                             extracted_docs=extracted_content[:10] if extracted_content else [])
                             
    except Exception as e:
        logger.error(f"❌ Error loading content extraction dashboard: {e}")
        logger.debug(f"📍 Full error details: ", exc_info=True)
        flash(f"Error loading dashboard: {e}", "error")
        return redirect(url_for('main.index'))

@content_extraction_bp.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        from utils.db_utils import get_document_downloads, get_content_metadata
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        downloads = get_document_downloads(db_path)
        extracted_content = get_content_metadata(db_path, limit=1000)
        
        stats = {
            'total_documents': len(downloads),
            'extracted': len(extracted_content),
            'pending': len(downloads) - len(extracted_content),
            'total_embeddings': sum(content.get('chunk_count', 0) for content in extracted_content)
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@content_extraction_bp.route('/process_document/<int:document_id>', methods=['POST'])
def process_document(document_id):
    """Extract content synchronously (no Celery, no Redis)"""
    try:
        from utils.db_utils import get_document_downloads, record_content_extraction
        from utils.content_extractors import ContentExtractorFactory
        import os

        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        downloads = get_document_downloads(db_path)
        document = next((d for d in downloads if d['id'] == document_id), None)
        
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'})
        
        file_path = document.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found'})
        
        extractor = ContentExtractorFactory.get_extractor(file_path)
        if not extractor:
            return jsonify({'success': False, 'error': 'No extractor for file type'})
        
        # Extract content
        extracted_content = extractor.extract(file_path)
        
        if not extracted_content.text.strip():
            return jsonify({'success': False, 'error': 'No text content extracted'})
        
        # Prepare simplified metadata (matching database schema)
        content_metadata = {
            'document_id': document_id,
            'assessment_id': document.get('assessment_id'),
            'language': 'Unknown',  # Basic placeholder
            'word_count': len(extracted_content.text.split()),
            'page_count': extracted_content.page_count or 1,
            'key_topics': '',  # Placeholder for future AI processing
            'named_entities': '',  # Placeholder for future AI processing
            'admin_districts': '',  # Placeholder for future geo processing
            'sentiment_score': 0.0,  # Placeholder
            'readability_score': 0.0,  # Placeholder
            'extraction_confidence': extracted_content.confidence or 0.95,
            'processing_status': 'completed',
            'vector_ids': ''  # Placeholder for future vector processing
        }
        
        # Record extraction
        success = record_content_extraction(db_path, content_metadata)
        
        if success:
            return jsonify({'success': True, 'message': f'Successfully extracted {content_metadata["word_count"]} words from document'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save extraction results'})
            
    except Exception as e:
        logger.error(f"Error extracting document: {e}")
        return jsonify({'success': False, 'error': str(e)})


@content_extraction_bp.route('/bulk_process', methods=['POST'])
def bulk_process():
    """Process multiple documents for content extraction"""
    logger.debug("🚀 Starting bulk document processing")
    
    try:
        data = request.get_json()
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return jsonify({'success': False, 'error': 'No documents selected'}), 400
        
        logger.debug(f"📥 Processing {len(document_ids)} documents: {document_ids}")
        
        from utils.db_utils import get_document_downloads, record_content_extraction
        from utils.content_extractors import ContentExtractorFactory
        import os
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        # Get all downloads
        downloads = get_document_downloads(db_path)
        downloads_dict = {d['id']: d for d in downloads}
        
        results = []
        successful = 0
        failed = 0
        
        for doc_id in document_ids:
            try:
                document = downloads_dict.get(doc_id)
                if not document:
                    results.append({
                        'document_id': doc_id,
                        'status': 'error',
                        'error': 'Document not found'
                    })
                    failed += 1
                    continue
                
                file_path = document.get('file_path')
                if not file_path or not os.path.exists(file_path):
                    results.append({
                        'document_id': doc_id,
                        'status': 'error',
                        'error': 'File not found on disk'
                    })
                    failed += 1
                    continue
                
                # Extract content
                extractor = ContentExtractorFactory.get_extractor(file_path)
                if not extractor:
                    results.append({
                        'document_id': doc_id,
                        'status': 'error',
                        'error': 'Unsupported file format'
                    })
                    failed += 1
                    continue
                
                extracted_content = extractor.extract(file_path)
                if not extracted_content or not extracted_content.text:
                    results.append({
                        'document_id': doc_id,
                        'status': 'error',
                        'error': 'No text content found'
                    })
                    failed += 1
                    continue
                
                # Record extraction
                content_metadata = {
                    'document_id': doc_id,
                    'assessment_id': document.get('assessment_id'),
                    'content_text': extracted_content.text,
                    'word_count': len(extracted_content.text.split()),
                    'page_count': extracted_content.page_count or 1,
                    'extraction_method': 'bulk_extraction',
                    'processing_status': 'completed',
                    'extraction_confidence': extracted_content.confidence or 0.95
                }
                
                success = record_content_extraction(db_path, content_metadata)
                
                if success:
                    results.append({
                        'document_id': doc_id,
                        'status': 'success',
                        'message': f'Extracted {len(extracted_content.text.split())} words'
                    })
                    successful += 1
                else:
                    results.append({
                        'document_id': doc_id,
                        'status': 'error',
                        'error': 'Failed to save extraction results'
                    })
                    failed += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing document {doc_id}: {e}")
                results.append({
                    'document_id': doc_id,
                    'status': 'error',
                    'error': str(e)
                })
                failed += 1
        
        return jsonify({
            'success': True,
            'message': f'Bulk processing completed: {successful} successful, {failed} failed',
            'results': results,
            'summary': {
                'total': len(document_ids),
                'successful': successful,
                'failed': failed
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Bulk processing error: {e}")
        logger.debug(f"📍 Full error details: ", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@content_extraction_bp.route('/api/detailed_stats')
def get_detailed_stats():
    """Get detailed content extraction statistics"""
    try:
        from utils.db_utils import get_document_downloads, get_content_metadata
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        downloads = get_document_downloads(db_path)
        extracted_content = get_content_metadata(db_path, limit=None)
        
        stats = {
            'total_documents': len(downloads),
            'extracted': len(extracted_content),
            'pending': len(downloads) - len(extracted_content),
            'failed': 0,  # TODO: Implement failed tracking
            'total_chunks': sum(content.get('chunk_count', 0) for content in extracted_content),
            'total_embeddings': sum(1 for content in extracted_content if content.get('chunk_count', 0) > 0)
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@content_extraction_bp.route('/semantic_search', methods=['POST'])
def semantic_search():
    """Perform semantic search across extracted content"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # TODO: Implement semantic search using vector database
        # For now, return placeholder results
        results = {
            'query': query,
            'results': [],
            'total_results': 0,
            'message': 'Semantic search feature coming soon'
        }
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return jsonify({'error': str(e)}), 500

@content_extraction_bp.route('/view_content/<int:document_id>')
def view_content(document_id):
    """View extracted content for a document"""
    try:
        from utils.db_utils import get_content_metadata
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        # Get content metadata
        content_data = get_content_metadata(db_path, document_id=document_id)
        
        if not content_data:
            flash('Content not found for this document', 'error')
            return redirect(url_for('content_extraction.extraction'))
        
        content = content_data[0] if content_data else {}
        
        return render_template('content_extraction/view_content.html', content=content)
        
    except Exception as e:
        logger.error(f"❌ Error viewing content for document {document_id}: {e}")
        flash(f'Error loading content: {e}', 'error')
        return redirect(url_for('content_extraction.extraction'))

def process_single_document_internal(document_id):
    """Internal function for processing a single document (used by bulk processing)"""
    try:
        from utils.db_utils import get_document_downloads, record_content_extraction
        from utils.content_extractors import ContentExtractorFactory
        from utils.content_processing import process_content_pipeline
        from utils.admin_geo_utils import extract_admin_geo_from_content
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        # Get document info
        downloads = get_document_downloads(db_path)
        document = next((d for d in downloads if d['id'] == document_id), None)
        
        if not document:
            return {'success': False, 'error': 'Document not found'}
        
        file_path = document.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return {'success': False, 'error': 'Document file not found'}
        
        # Extract and process content
        extractor = ContentExtractorFactory.get_extractor(file_path)
        if not extractor:
            return {'success': False, 'error': 'No suitable extractor'}
        
        extracted_content = extractor.extract(file_path)
        if not extracted_content.text.strip():
            return {'success': False, 'error': 'No text content extracted'}
        
        processing_result = process_content_pipeline(extracted_content.text)
        geo_info = extract_admin_geo_from_content(processing_result['cleaned_text'])
        
        # Prepare and save metadata
        content_metadata = {
            'document_id': document_id,
            'assessment_id': document.get('assessment_id'),
            'original_text': extracted_content.text,
            'cleaned_text': processing_result['cleaned_text'],
            'extraction_method': extracted_content.metadata.get('extraction_method', 'unknown'),
            'extraction_confidence': extracted_content.confidence,
            'page_count': extracted_content.page_count,
            'word_count': len(processing_result['cleaned_text'].split()),
            'char_count': len(processing_result['cleaned_text']),
            'chunks': processing_result['chunks'],
            'metadata': processing_result['metadata'],
            'admin_districts': geo_info.get('admin_districts', []),
            'primary_country': geo_info.get('primary_country'),
            'embeddings': processing_result.get('embeddings', [])
        }
        
        extraction_id = record_content_extraction(db_path, content_metadata)
        
        return {
            'success': True,
            'extraction_id': extraction_id,
            'message': f'Successfully processed {document["filename"]}'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@content_extraction_bp.route('/debug/info')
def debug_info():
    """Debug endpoint to check system status"""
    try:
        from utils.db_utils import get_document_downloads, get_extracted_content_simple
        
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'humanitarian_assessments.db')
        
        debug_data = {
            'database': {
                'path': db_path,
                'exists': os.path.exists(db_path),
                'size': os.path.getsize(db_path) if os.path.exists(db_path) else 0
            },
            'downloads': {},
            'extracted_content': {},
            'system': {
                'python_path': sys.path[:3],  # First 3 paths
                'working_directory': os.getcwd()
            }
        }
        
        # Test downloads
        try:
            downloads = get_document_downloads(db_path)
            debug_data['downloads'] = {
                'count': len(downloads),
                'sample': downloads[:2] if downloads else [],
                'error': None
            }
        except Exception as e:
            debug_data['downloads'] = {
                'count': 0,
                'sample': [],
                'error': str(e)
            }
        
        # Test extracted content
        try:
            extracted = get_extracted_content_simple(db_path, limit=5)
            debug_data['extracted_content'] = {
                'count': len(extracted),
                'sample': extracted[:2] if extracted else [],
                'error': None
            }
        except Exception as e:
            debug_data['extracted_content'] = {
                'count': 0,
                'sample': [],
                'error': str(e)
            }
        
        return jsonify(debug_data)
        
    except Exception as e:
        return jsonify({'error': str(e), 'debug': 'Failed to generate debug info'}), 500