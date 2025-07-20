"""
Content processing utilities for text cleaning, chunking, and metadata extraction
"""

import re
import logging
import spacy
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
from textstat import flesch_reading_ease, gunning_fog
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentProcessor:
    """Main content processor for text cleaning, chunking, and metadata extraction"""
    
    def __init__(self):
        self.nlp = None
        self.embedding_model = None
        self._load_models()
    
    def _load_models(self):
        """Load spaCy and embedding models"""
        try:
            # Load spaCy model (download if needed)
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found. Installing...")
                spacy.cli.download("en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
            
            # Load sentence transformer for embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Content processing models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            # Fallback to basic processing
            self.nlp = None
            self.embedding_model = None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text or not text.strip():
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        
        # Remove multiple dots
        text = re.sub(r'\.{3,}', '...', text)
        
        # Remove page numbers and headers/footers patterns
        text = re.sub(r'\b\d{1,3}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^Page\s+\d+', '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def chunk_text(self, text: str, method: str = 'semantic', max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
        """Split text into chunks using different strategies"""
        
        if not text or not text.strip():
            return []
        
        chunks = []
        
        if method == 'semantic' and self.nlp:
            chunks = self._semantic_chunking(text, max_chunk_size, overlap)
        elif method == 'sentence':
            chunks = self._sentence_chunking(text, max_chunk_size, overlap)
        else:
            chunks = self._fixed_chunking(text, max_chunk_size, overlap)
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk.update({
                'chunk_id': i,
                'method': method,
                'char_count': len(chunk['text']),
                'word_count': len(chunk['text'].split())
            })
        
        return chunks
    
    def _semantic_chunking(self, text: str, max_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Chunk text based on semantic boundaries using spaCy"""
        doc = self.nlp(text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_length = len(sent_text)
            
            if current_length + sent_length > max_size and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'start_pos': len(' '.join(chunks)) if chunks else 0
                })
                
                # Handle overlap
                if overlap > 0 and len(current_chunk) > 1:
                    overlap_sents = []
                    overlap_length = 0
                    for sent in reversed(current_chunk):
                        if overlap_length + len(sent) <= overlap:
                            overlap_sents.insert(0, sent)
                            overlap_length += len(sent)
                        else:
                            break
                    current_chunk = overlap_sents
                    current_length = overlap_length
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sent_text)
            current_length += sent_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'start_pos': len(' '.join([c['text'] for c in chunks])) if chunks else 0
            })
        
        return chunks
    
    def _sentence_chunking(self, text: str, max_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Chunk text by sentences using basic sentence splitting"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > max_size and current_chunk:
                chunk_text = '. '.join(current_chunk) + '.'
                chunks.append({
                    'text': chunk_text,
                    'start_pos': len('. '.join([c['text'] for c in chunks])) if chunks else 0
                })
                
                # Handle overlap
                if overlap > 0 and len(current_chunk) > 1:
                    overlap_count = min(2, len(current_chunk))
                    current_chunk = current_chunk[-overlap_count:]
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = '. '.join(current_chunk) + '.'
            chunks.append({
                'text': chunk_text,
                'start_pos': len('. '.join([c['text'] for c in chunks])) if chunks else 0
            })
        
        return chunks
    
    def _fixed_chunking(self, text: str, max_size: int, overlap: int) -> List[Dict[str, Any]]:
        """Fixed-size chunking with word boundaries"""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = []
            chunk_length = 0
            
            # Build chunk up to max_size
            while i < len(words) and chunk_length + len(words[i]) + 1 <= max_size:
                chunk_words.append(words[i])
                chunk_length += len(words[i]) + 1
                i += 1
            
            if chunk_words:
                chunk_text = ' '.join(chunk_words)
                chunks.append({
                    'text': chunk_text,
                    'start_pos': len(' '.join([c['text'] for c in chunks])) if chunks else 0
                })
                
                # Handle overlap
                if overlap > 0 and i < len(words):
                    overlap_words = min(overlap // 10, len(chunk_words) // 2)
                    i -= overlap_words
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for list of texts"""
        if not self.embedding_model:
            logger.error("Embedding model not available")
            return np.array([])
        
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return np.array([])
    
    def extract_content_metadata(self, text: str, chunks: List[Dict]) -> Dict[str, Any]:
        """Extract comprehensive metadata from content"""
        if not text or not text.strip():
            return {}
        
        metadata = {
            'content_stats': self._calculate_content_stats(text),
            'readability': self._calculate_readability(text),
            'key_terms': self._extract_key_terms(text),
            'chunk_stats': self._calculate_chunk_stats(chunks)
        }
        
        if self.nlp:
            metadata['entities'] = self._extract_entities(text)
            metadata['language_features'] = self._analyze_language_features(text)
        
        return metadata
    
    def _calculate_content_stats(self, text: str) -> Dict[str, Any]:
        """Calculate basic content statistics"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return {
            'char_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_words_per_sentence': len(words) / max(1, len(sentences)),
            'avg_chars_per_word': len(text) / max(1, len(words))
        }
    
    def _calculate_readability(self, text: str) -> Dict[str, float]:
        """Calculate readability scores"""
        try:
            return {
                'flesch_reading_ease': flesch_reading_ease(text),
                'gunning_fog': gunning_fog(text)
            }
        except Exception as e:
            logger.warning(f"Error calculating readability: {e}")
            return {'flesch_reading_ease': 0.0, 'gunning_fog': 0.0}
    
    def _extract_key_terms(self, text: str, max_terms: int = 20) -> List[Dict[str, Any]]:
        """Extract key terms using TF-IDF"""
        try:
            # Clean text for TF-IDF
            clean_text = self.clean_text(text)
            
            vectorizer = TfidfVectorizer(
                max_features=max_terms,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )
            
            tfidf_matrix = vectorizer.fit_transform([clean_text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Create term-score pairs
            terms = []
            for term, score in zip(feature_names, tfidf_scores):
                if score > 0:
                    terms.append({'term': term, 'score': float(score)})
            
            # Sort by score
            terms.sort(key=lambda x: x['score'], reverse=True)
            return terms[:max_terms]
            
        except Exception as e:
            logger.warning(f"Error extracting key terms: {e}")
            return []
    
    def _calculate_chunk_stats(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics about chunks"""
        if not chunks:
            return {}
        
        chunk_lengths = [len(chunk['text']) for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_length': sum(chunk_lengths) / len(chunks),
            'min_chunk_length': min(chunk_lengths),
            'max_chunk_length': max(chunk_lengths)
        }
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities using spaCy"""
        try:
            doc = self.nlp(text)
            entities = {}
            
            for ent in doc.ents:
                if ent.label_ not in entities:
                    entities[ent.label_] = []
                if ent.text not in entities[ent.label_]:
                    entities[ent.label_].append(ent.text)
            
            return entities
            
        except Exception as e:
            logger.warning(f"Error extracting entities: {e}")
            return {}
    
    def _analyze_language_features(self, text: str) -> Dict[str, Any]:
        """Analyze language features using spaCy"""
        try:
            doc = self.nlp(text)
            
            pos_counts = Counter([token.pos_ for token in doc])
            
            return {
                'pos_distribution': dict(pos_counts),
                'num_tokens': len(doc),
                'num_unique_tokens': len(set([token.text.lower() for token in doc]))
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing language features: {e}")
            return {}

# Global content processor instance
content_processor = ContentProcessor()

def process_content_pipeline(text: str, max_chunk_size: int = 1000, chunk_method: str = 'semantic') -> Dict[str, Any]:
    """Complete content processing pipeline"""
    
    # Step 1: Clean text
    cleaned_text = content_processor.clean_text(text)
    
    # Step 2: Chunk text
    chunks = content_processor.chunk_text(cleaned_text, method=chunk_method, max_chunk_size=max_chunk_size)
    
    # Step 3: Generate embeddings
    chunk_texts = [chunk['text'] for chunk in chunks]
    embeddings = content_processor.generate_embeddings(chunk_texts) if chunk_texts else np.array([])
    
    # Step 4: Extract metadata
    metadata = content_processor.extract_content_metadata(cleaned_text, chunks)
    
    return {
        'cleaned_text': cleaned_text,
        'chunks': chunks,
        'embeddings': embeddings.tolist() if embeddings.size > 0 else [],
        'metadata': metadata
    }
