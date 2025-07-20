"""
FAISS Vector Database Manager for document embeddings
"""
import faiss
import numpy as np
import json
import os
import pickle
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class VectorDatabaseManager:
    """Manages FAISS vector database for document embeddings"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.dimension = config['dimension']
        self.index_path = config['index_path']
        self.metadata_path = config['metadata_path']
        
        # Create vector_db directory if it doesn't exist
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        # Initialize FAISS index
        self.index = None
        self.metadata = {}
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        try:
            if os.path.exists(self.index_path):
                # Load existing index
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
                
                # Load metadata
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
                else:
                    self.metadata = {}
            else:
                # Create new index - using IndexFlatIP for cosine similarity
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata = {}
                logger.info(f"Created new FAISS index with dimension {self.dimension}")
                
        except Exception as e:
            logger.error(f"Error loading/creating FAISS index: {e}")
            # Fallback to new index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = {}
    
    def add_embedding(self, document_id: int, chunk_index: int, text: str, embedding: List[float]) -> str:
        """Add embedding to the vector database"""
        try:
            # Convert embedding to numpy array and normalize for cosine similarity
            vector = np.array(embedding, dtype=np.float32).reshape(1, -1)
            faiss.normalize_L2(vector)
            
            # Generate unique ID for this embedding
            vector_id = f"doc_{document_id}_chunk_{chunk_index}_{int(datetime.now().timestamp())}"
            
            # Add to FAISS index
            current_id = self.index.ntotal
            self.index.add(vector)
            
            # Store metadata
            self.metadata[str(current_id)] = {
                'vector_id': vector_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'text': text,
                'created_date': datetime.now().isoformat()
            }
            
            # Save index and metadata
            self._save_index()
            
            logger.info(f"Added embedding {vector_id} to vector database")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error adding embedding: {e}")
            return None
    
    def search(self, query_text: str, top_k: int = 10) -> List[Dict]:
        """Search for similar embeddings using query text"""
        try:
            # Generate embedding for query (you'll need to implement this)
            query_embedding = self._generate_query_embedding(query_text)
            if not query_embedding:
                return []
            
            # Convert to numpy array and normalize
            query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            faiss.normalize_L2(query_vector)
            
            # Search in FAISS index
            scores, indices = self.index.search(query_vector, top_k)
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for empty results
                    continue
                    
                metadata = self.metadata.get(str(idx), {})
                results.append({
                    'rank': i + 1,
                    'score': float(score),
                    'vector_id': metadata.get('vector_id'),
                    'document_id': metadata.get('document_id'),
                    'chunk_index': metadata.get('chunk_index'),
                    'text': metadata.get('text', '')[:200],  # Truncate for display
                    'created_date': metadata.get('created_date')
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []
    
    def find_similar_documents(self, document_id: int, top_k: int = 5) -> List[Dict]:
        """Find documents similar to the given document"""
        try:
            # Get all embeddings for the document
            doc_embeddings = []
            for idx, meta in self.metadata.items():
                if meta.get('document_id') == document_id:
                    doc_embeddings.append(int(idx))
            
            if not doc_embeddings:
                return []
            
            # Use the first embedding as representative
            representative_idx = doc_embeddings[0]
            representative_vector = self.index.reconstruct(representative_idx).reshape(1, -1)
            
            # Search for similar vectors
            scores, indices = self.index.search(representative_vector, top_k + len(doc_embeddings))
            
            # Filter out embeddings from the same document
            results = []
            seen_docs = set()
            
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                    
                metadata = self.metadata.get(str(idx), {})
                other_doc_id = metadata.get('document_id')
                
                if other_doc_id != document_id and other_doc_id not in seen_docs:
                    seen_docs.add(other_doc_id)
                    results.append({
                        'document_id': other_doc_id,
                        'similarity_score': float(score),
                        'vector_id': metadata.get('vector_id'),
                        'text_preview': metadata.get('text', '')[:200]
                    })
                    
                    if len(results) >= top_k:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            return []
    
    def get_total_embeddings(self) -> int:
        """Get total number of embeddings in the database"""
        return self.index.ntotal if self.index else 0
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            faiss.write_index(self.index, self.index_path)
            
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def _generate_query_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for search query - implement based on your embedding model"""
        # TODO: Implement with your chosen embedding model (OpenAI, sentence-transformers, etc.)
        # For now, return None to indicate not implemented
        logger.warning("Query embedding generation not implemented yet")
        return None
    
    def delete_document_embeddings(self, document_id: int):
        """Delete all embeddings for a document (requires rebuilding index)"""
        try:
            # Find indices to remove
            indices_to_remove = []
            for idx, meta in self.metadata.items():
                if meta.get('document_id') == document_id:
                    indices_to_remove.append(int(idx))
            
            if not indices_to_remove:
                return True
            
            # FAISS doesn't support deletion, so we need to rebuild the index
            # Get all vectors except the ones to delete
            remaining_vectors = []
            remaining_metadata = {}
            new_idx = 0
            
            for old_idx in range(self.index.ntotal):
                if old_idx not in indices_to_remove:
                    vector = self.index.reconstruct(old_idx)
                    remaining_vectors.append(vector)
                    
                    # Update metadata with new index
                    old_meta = self.metadata.get(str(old_idx))
                    if old_meta:
                        remaining_metadata[str(new_idx)] = old_meta
                        new_idx += 1
            
            # Create new index
            if remaining_vectors:
                vectors_array = np.vstack(remaining_vectors)
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index.add(vectors_array)
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
            
            self.metadata = remaining_metadata
            self._save_index()
            
            logger.info(f"Removed {len(indices_to_remove)} embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document embeddings: {e}")
            return False