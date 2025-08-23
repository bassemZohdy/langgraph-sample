"""
Embedding service for document processing and vector similarity search.
Supports multiple embedding providers and document formats.
"""

import os
import io
import logging
import hashlib
from typing import List, Dict, Any, Optional, Union
import requests
from .models import model_manager

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing document embeddings."""
    
    def __init__(self):
        self.chunk_size = int(os.getenv("EMBEDDING_CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", "200"))
    
    def generate_embedding(self, text: str, provider: Optional[str] = None) -> List[float]:
        """
        Generate embedding for the given text using available AI providers.
        
        Args:
            text: The text to embed
            provider: Optional specific provider to use
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Use OpenAI for embeddings if available
            if not provider:
                # Check providers in order of preference for embeddings
                if "OPENAI_API_KEY" in os.environ:
                    provider = "openai"
                elif "ANTHROPIC_API_KEY" in os.environ:
                    # Anthropic doesn't have embedding endpoint, fallback
                    return self._generate_simple_embedding(text)
                else:
                    return self._generate_simple_embedding(text)
            
            if provider == "openai":
                return self._generate_openai_embedding(text)
            else:
                return self._generate_simple_embedding(text)
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Fallback to simple embedding
            return self._generate_simple_embedding(text)
    
    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
        
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        payload = {
            "input": text,
            "model": model
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{base_url}/embeddings",
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        if "data" in result and len(result["data"]) > 0:
            return result["data"][0]["embedding"]
        else:
            raise ValueError("Invalid embedding response from OpenAI")
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """
        Generate a simple hash-based embedding as fallback.
        This is not as good as proper embeddings but allows the system to work.
        """
        # Create a deterministic embedding based on text content
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert hex to list of floats (1536 dimensions to match OpenAI)
        embedding = []
        for i in range(0, len(text_hash), 2):
            hex_pair = text_hash[i:i+2]
            # Convert hex to float between -1 and 1
            val = (int(hex_pair, 16) - 127.5) / 127.5
            embedding.append(val)
        
        # Pad or truncate to 1536 dimensions
        target_size = 1536
        if len(embedding) < target_size:
            # Repeat pattern to reach target size
            while len(embedding) < target_size:
                embedding.extend(embedding[:min(32, target_size - len(embedding))])
        
        return embedding[:target_size]
    
    def extract_text_content(self, file_content: bytes, content_type: str) -> str:
        """
        Extract text content from various file formats.
        
        Args:
            file_content: Raw file bytes
            content_type: MIME type of the file
            
        Returns:
            Extracted text content
        """
        try:
            if content_type.startswith('text/'):
                # Plain text files
                return file_content.decode('utf-8', errors='ignore')
            
            elif content_type == 'application/pdf':
                # PDF files - would need PyPDF2 or similar
                # For now, return a placeholder
                logger.warning("PDF text extraction not implemented, using placeholder")
                return f"[PDF Document - {len(file_content)} bytes]"
            
            elif content_type in ['application/msword', 
                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # Word documents - would need python-docx
                logger.warning("Word document text extraction not implemented, using placeholder")
                return f"[Word Document - {len(file_content)} bytes]"
            
            else:
                # Try to decode as text for other types
                try:
                    return file_content.decode('utf-8', errors='ignore')
                except:
                    return f"[Binary File - {content_type} - {len(file_content)} bytes]"
                    
        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            return f"[Error extracting content from {content_type}]"
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into smaller chunks for embedding.
        
        Args:
            text: The text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundary
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - self.chunk_overlap)
        
        return chunks
    
    def process_document(
        self, 
        document_id: str, 
        filename: str, 
        file_content: bytes, 
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a document: extract text, create chunks, generate embeddings.
        
        Args:
            document_id: Unique identifier for the document
            filename: Original filename
            file_content: Raw file bytes
            content_type: MIME type
            metadata: Additional metadata
            
        Returns:
            List of processed chunks with embeddings
        """
        try:
            # Extract text content
            text_content = self.extract_text_content(file_content, content_type)
            logger.info(f"Extracted {len(text_content)} characters from {filename}")
            
            # Split into chunks
            chunks = self.chunk_text(text_content)
            logger.info(f"Created {len(chunks)} chunks from {filename}")
            
            # Generate embeddings for each chunk
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = self.generate_embedding(chunk)
                    
                    chunk_data = {
                        'document_id': f"{document_id}_chunk_{i}",
                        'parent_document_id': document_id,
                        'filename': filename,
                        'content_type': content_type,
                        'content': chunk,
                        'embedding': embedding,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'metadata': {
                            **(metadata or {}),
                            'file_size': len(file_content),
                            'chunk_size': len(chunk),
                            'processing_method': 'basic_chunking'
                        }
                    }
                    
                    processed_chunks.append(chunk_data)
                    logger.info(f"Processed chunk {i+1}/{len(chunks)} for {filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to process chunk {i} of {filename}: {e}")
                    continue
            
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Failed to process document {filename}: {e}")
            return []
    
    def search_similar_content(
        self, 
        query: str, 
        limit: int = 5, 
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for content similar to the query.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar document chunks with similarity scores
        """
        try:
            from .database import search_similar_documents
            
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)
            
            # Search in database
            results = search_similar_documents(
                query_embedding, 
                limit=limit, 
                similarity_threshold=similarity_threshold
            )
            
            logger.info(f"Found {len(results)} similar documents for query: {query[:100]}...")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            return []


# Global embedding service instance
embedding_service = EmbeddingService()