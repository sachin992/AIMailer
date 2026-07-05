"""
FAQ Manager module for AIMailer
Handles FAQ database, vector embeddings, and similarity search
"""
import os
import pandas as pd
import faiss
import numpy as np
from typing import List, Tuple, Optional
from openai import OpenAI

from config import Config
from logger import get_logger
from utils import retry_with_backoff, FAQValidator, QueryValidator

logger = get_logger("faq_manager")


class FAQManagerError(Exception):
    """Custom exception for FAQ manager errors"""
    pass


class FAQManager:
    """Manages FAQ database and similarity search"""
    
    def __init__(self):
        """Initialize FAQ manager"""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.df: Optional[pd.DataFrame] = None
        self.index: Optional[faiss.Index] = None
        self.load_faq_database()
    
    def load_faq_database(self):
        """Load FAQ Excel file and vector index"""
        try:
            # Check if FAQ file exists
            if not os.path.exists(Config.FAQ_EXCEL_FILE):
                raise FAQManagerError(
                    f"FAQ file not found: {Config.FAQ_EXCEL_FILE}"
                )
            
            # Load FAQ Excel
            logger.info(f"Loading FAQ from {Config.FAQ_EXCEL_FILE}")
            self.df = pd.read_excel(Config.FAQ_EXCEL_FILE)
            
            # Validate FAQ data
            validation_errors = FAQValidator.validate_faq_dataframe(self.df)
            if validation_errors:
                logger.warning(f"FAQ validation errors: {validation_errors}")
                logger.info("Cleaning FAQ data...")
                self.df = FAQValidator.clean_faq_dataframe(self.df)
                logger.info(f"FAQ data cleaned. Rows: {len(self.df)}")
            
            logger.info(f"Loaded {len(self.df)} FAQ entries")
            
            # Load or build vector index
            if os.path.exists(Config.VECTOR_STORE_FILE):
                self._load_vector_index()
            else:
                self._build_vector_index()
        
        except Exception as e:
            logger.error(f"Error loading FAQ database: {e}")
            raise FAQManagerError(f"Failed to load FAQ database: {e}")
    
    def _load_vector_index(self):
        """Load existing FAISS vector index"""
        try:
            logger.info(f"Loading vector index from {Config.VECTOR_STORE_FILE}")
            self.index = faiss.read_index(Config.VECTOR_STORE_FILE)
            
            # Verify index size matches FAQ data
            if self.index.ntotal != len(self.df):
                logger.warning(
                    f"Index size ({self.index.ntotal}) doesn't match FAQ size ({len(self.df)}). "
                    "Rebuilding index..."
                )
                self._build_vector_index()
            else:
                logger.info(f"Loaded vector index with {self.index.ntotal} vectors")
        
        except Exception as e:
            logger.error(f"Error loading vector index: {e}. Rebuilding...")
            self._build_vector_index()
    
    @retry_with_backoff(max_retries=Config.MAX_RETRIES)
    def _build_vector_index(self):
        """Build FAISS vector index from FAQ questions"""
        try:
            logger.info("Building vector index from FAQ questions...")
            
            questions = self.df["Question"].tolist()
            
            # Get embeddings from OpenAI
            logger.info(f"Getting embeddings for {len(questions)} questions...")
            embeddings_response = self.client.embeddings.create(
                model=Config.OPENAI_EMBEDDING_MODEL,
                input=questions
            )
            
            # Convert to numpy array
            vectors = np.array(
                [e.embedding for e in embeddings_response.data]
            ).astype("float32")
            
            logger.info(f"Got embeddings with shape: {vectors.shape}")
            
            # Create FAISS index
            dimension = vectors.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(vectors)
            
            # Save index
            faiss.write_index(self.index, Config.VECTOR_STORE_FILE)
            
            logger.info(
                f"Built and saved vector index with {self.index.ntotal} vectors to "
                f"{Config.VECTOR_STORE_FILE}"
            )
        
        except Exception as e:
            logger.error(f"Error building vector index: {e}")
            raise FAQManagerError(f"Failed to build vector index: {e}")
    
    @retry_with_backoff(max_retries=Config.MAX_RETRIES)
    def search_similar_faq(
        self,
        query: str,
        threshold: Optional[float] = None,
        top_k: Optional[int] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Search for similar FAQ entries
        
        Args:
            query: User query text
            threshold: Maximum distance threshold (lower = more similar)
            top_k: Number of results to return
            
        Returns:
            List of (question, answer, distance) tuples
        """
        if not self.df is not None or self.index is None:
            raise FAQManagerError("FAQ database not loaded")
        
        # Use config defaults if not provided
        threshold = threshold if threshold is not None else Config.FAQ_SIMILARITY_THRESHOLD
        top_k = top_k if top_k is not None else Config.FAQ_TOP_K_RESULTS
        
        # Validate and sanitize query
        if not QueryValidator.is_valid_query(query):
            logger.warning(f"Invalid query: {query}")
            return []
        
        query = QueryValidator.sanitize_query(query)
        
        try:
            # Get query embedding
            logger.debug(f"Getting embedding for query: {query[:100]}...")
            embedding_response = self.client.embeddings.create(
                model=Config.OPENAI_EMBEDDING_MODEL,
                input=query
            )
            
            vector = np.array([embedding_response.data[0].embedding]).astype("float32")
            
            # Search in FAISS index
            distances, indices = self.index.search(vector, top_k)
            
            indices = indices[0]
            distances = distances[0]
            
            logger.debug(f"FAISS search results - Indices: {indices}, Distances: {distances}")
            
            # Filter by threshold and collect results
            results = []
            for idx, dist in zip(indices, distances):
                if idx < 0:
                    continue
                
                # FAISS IndexFlatL2 returns squared Euclidean distance
                # Lower distance = more similar
                if dist > threshold:
                    logger.debug(f"Skipping result with distance {dist} (threshold: {threshold})")
                    continue
                
                question = self.df.loc[idx, "Question"]
                answer = self.df.loc[idx, "Answer"]
                
                results.append((question, answer, float(dist)))
                logger.debug(f"Match: {question[:50]}... (distance: {dist:.4f})")
            
            logger.info(f"Found {len(results)} FAQ matches for query")
            return results
        
        except Exception as e:
            logger.error(f"Error searching FAQ: {e}")
            raise FAQManagerError(f"FAQ search failed: {e}")
    
    def get_confidence_score(self, distance: float) -> float:
        """
        Convert distance to confidence score (0-1)
        
        Args:
            distance: FAISS distance (lower = more similar)
            
        Returns:
            Confidence score between 0 and 1
        """
        # Transform distance to confidence score
        # Using exponential decay: confidence = e^(-distance)
        # This gives ~0.135 confidence at threshold=2.0
        import math
        confidence = math.exp(-distance)
        return min(1.0, max(0.0, confidence))
    
    def rebuild_index(self):
        """Force rebuild of vector index"""
        logger.info("Force rebuilding vector index...")
        if os.path.exists(Config.VECTOR_STORE_FILE):
            os.remove(Config.VECTOR_STORE_FILE)
        self._build_vector_index()
    
    def reload_faq(self):
        """Reload FAQ database and rebuild index"""
        logger.info("Reloading FAQ database...")
        self.load_faq_database()
    
    def get_faq_stats(self) -> dict:
        """Get FAQ database statistics"""
        if self.df is None:
            return {}
        
        return {
            "total_faqs": len(self.df),
            "index_size": self.index.ntotal if self.index else 0,
            "faq_file": Config.FAQ_EXCEL_FILE,
            "vector_store": Config.VECTOR_STORE_FILE,
            "similarity_threshold": Config.FAQ_SIMILARITY_THRESHOLD,
            "top_k_results": Config.FAQ_TOP_K_RESULTS
        }
