#!/usr/bin/env python3
"""
Vector Database module for Telegram Agent Bot
Handles knowledge storage and retrieval using FAISS and sentence-transformers
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pickle

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    import openai
except ImportError as e:
    logging.error(f"Required packages not installed: {e}")
    raise

logger = logging.getLogger(__name__)

class VectorKnowledgeBase:
    """Handles vector-based knowledge storage and retrieval"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', index_path: str = "faiss_index"):
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.knowledge_path = Path("knowledge.json")
        
        # Initialize sentence transformer model
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded sentence transformer model: {model_name}")
            logger.info(f"Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {e}")
            raise
        
        # Initialize FAISS index
        self.index = None
        self.knowledge_texts = []
        self.knowledge_metadata = []
        
        # Load or create index
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        try:
            if self.index_path.exists():
                # Load existing index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load knowledge texts and metadata
                metadata_path = self.index_path.with_suffix('.metadata')
                if metadata_path.exists():
                    with open(metadata_path, 'rb') as f:
                        data = pickle.load(f)
                        self.knowledge_texts = data['texts']
                        self.knowledge_metadata = data['metadata']
                
                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index
                self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
                logger.info(f"Created new FAISS index with dimension {self.embedding_dim}")
                
        except Exception as e:
            logger.error(f"Error loading/creating FAISS index: {e}")
            # Create new index as fallback
            self.index = faiss.IndexFlatIP(self.embedding_dim)
    
    def add_knowledge(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> bool:
        """
        Add knowledge texts to the vector database
        
        Args:
            texts: List of text documents to add
            metadata: Optional metadata for each text
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not texts:
                logger.warning("No texts provided to add_knowledge")
                return False
            
            # Generate embeddings
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store texts and metadata
            self.knowledge_texts.extend(texts)
            if metadata:
                self.knowledge_metadata.extend(metadata)
            else:
                # Add default metadata
                self.knowledge_metadata.extend([{}] * len(texts))
            
            logger.info(f"Added {len(texts)} knowledge items to vector database")
            logger.info(f"Total items in database: {self.index.ntotal}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding knowledge to vector database: {e}")
            return False
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for relevant knowledge based on query
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of tuples: (text, score, metadata)
        """
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector database is empty")
                return []
            
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            
            # Search in FAISS index
            scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
            
            # Prepare results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.knowledge_texts):  # Valid index
                    text = self.knowledge_texts[idx]
                    metadata = self.knowledge_metadata[idx] if idx < len(self.knowledge_metadata) else {}
                    results.append((text, float(score), metadata))
            
            logger.debug(f"Search query '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []
    
    def save_index(self) -> bool:
        """Save FAISS index and metadata to disk"""
        try:
            # Create directory if it doesn't exist
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_path))
            
            # Save metadata
            metadata_path = self.index_path.with_suffix('.metadata')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'texts': self.knowledge_texts,
                    'metadata': self.knowledge_metadata
                }, f)
            
            logger.info(f"Saved FAISS index to {self.index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            return False
    
    def load_knowledge_from_json(self, json_path: str = None) -> bool:
        """
        Load knowledge from JSON file
        
        Args:
            json_path: Path to JSON file with knowledge
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if json_path is None:
                json_path = self.knowledge_path
            
            json_path = Path(json_path)
            if not json_path.exists():
                logger.warning(f"Knowledge JSON file not found: {json_path}")
                return False
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # List of strings
                texts = data
                metadata = [{}] * len(texts)
            elif isinstance(data, dict) and 'knowledge' in data:
                # Structured format
                knowledge_items = data['knowledge']
                texts = [item.get('text', '') for item in knowledge_items]
                metadata = [item.get('metadata', {}) for item in knowledge_items]
            else:
                logger.error("Invalid JSON format for knowledge")
                return False
            
            # Filter out empty texts
            valid_items = [(text, meta) for text, meta in zip(texts, metadata) if text.strip()]
            if not valid_items:
                logger.warning("No valid knowledge items found in JSON")
                return False
            
            texts, metadata = zip(*valid_items)
            
            # Add to vector database
            success = self.add_knowledge(list(texts), list(metadata))
            
            if success:
                logger.info(f"Loaded {len(texts)} knowledge items from {json_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error loading knowledge from JSON: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        return {
            'total_items': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name,
            'index_path': str(self.index_path),
            'knowledge_path': str(self.knowledge_path)
        }
    
    def clear(self) -> bool:
        """Clear all knowledge from the database"""
        try:
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.knowledge_texts = []
            self.knowledge_metadata = []
            logger.info("Cleared vector knowledge database")
            return True
        except Exception as e:
            logger.error(f"Error clearing vector database: {e}")
            return False


# Global vector database instance
vector_db = VectorKnowledgeBase()


def add_knowledge(texts: List[str], metadata: List[Dict[str, Any]] = None) -> bool:
    """Convenience function to add knowledge"""
    return vector_db.add_knowledge(texts, metadata)


def search_knowledge(query: str, top_k: int = 3) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Convenience function to search knowledge"""
    return vector_db.search(query, top_k)


def load_knowledge_from_json(json_path: str = None) -> bool:
    """Convenience function to load knowledge from JSON"""
    return vector_db.load_knowledge_from_json(json_path)


def get_vector_db_stats() -> Dict[str, Any]:
    """Convenience function to get vector database stats"""
    return vector_db.get_stats()


def save_vector_db() -> bool:
    """Convenience function to save vector database"""
    return vector_db.save_index()
