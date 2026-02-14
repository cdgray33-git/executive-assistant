"""
Conversation Memory Manager for JARVIS
Stores and retrieves conversations with semantic search using pgvector
"""
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import text, desc
import numpy as np

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation storage and retrieval with semantic search"""
    
    def __init__(self):
        from server.database.connection import get_db_session
        self.get_db_session = get_db_session
        self._embedding_model = None
    
    def _get_embedding_model(self):
        """Lazy load embedding model (uses Ollama)"""
        if self._embedding_model is None:
            from server.llm.ollama_adapter import OllamaAdapter
            self._embedding_model = OllamaAdapter()
        return self._embedding_model
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text using Ollama"""
        try:
            model = self._get_embedding_model()
            # Use Ollama's embedding endpoint
            import requests
            response = requests.post(
                "http://127.0.0.1:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30
            )
            if response.status_code == 200:
                embedding = response.json()["embedding"]
                # Pad or truncate to 384 dimensions
                if len(embedding) > 384:
                    return embedding[:384]
                elif len(embedding) < 384:
                    return embedding + [0.0] * (384 - len(embedding))
                return embedding
            else:
                logger.warning(f"Embedding generation failed, using zero vector")
                return [0.0] * 384
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 384
    
    def store_conversation(
        self,
        user_id: str,
        session_id: str,
        role: str,
        message_text: str,
        function_calls: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Store a conversation message with embedding
        
        Args:
            user_id: User identifier (for multi-user isolation)
            session_id: Session UUID
            role: 'user' or 'assistant' or 'system'
            message_text: The actual message
            function_calls: JSON of function calls made (if any)
            metadata: Additional metadata
            
        Returns:
            conversation_id (int)
        """
        try:
            # Generate embedding
            embedding = self._generate_embedding(message_text)
            
            with self.get_db_session() as session:
                result = session.execute(
                    text("""
                        INSERT INTO conversations 
                        (user_id, session_id, role, message_text, embedding, function_calls, metadata)
                        VALUES (:user_id, :session_id, :role, :message_text, :embedding, :function_calls, :metadata)
                        RETURNING id
                    """),
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": role,
                        "message_text": message_text,
                        "embedding": str(embedding),  # pgvector format
                        "function_calls": function_calls,
                        "metadata": metadata
                    }
                )
                conv_id = result.scalar()
                logger.info(f"Stored conversation {conv_id} for user {user_id}")
                return conv_id
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            raise
    
    def recall(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for similar past conversations
        
        Args:
            user_id: User to search for (isolated)
            query: Search query text
            limit: Max results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching conversations with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            with self.get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT 
                            id, role, message_text, timestamp,
                            function_calls, metadata,
                            1 - (embedding <=> :query_embedding::vector) as similarity
                        FROM conversations
                        WHERE user_id = :user_id
                          AND embedding IS NOT NULL
                          AND (1 - (embedding <=> :query_embedding::vector)) > :threshold
                        ORDER BY similarity DESC
                        LIMIT :limit
                    """),
                    {
                        "user_id": user_id,
                        "query_embedding": str(query_embedding),
                        "threshold": similarity_threshold,
                        "limit": limit
                    }
                )
                
                conversations = []
                for row in results:
                    conversations.append({
                        "id": row.id,
                        "role": row.role,
                        "message": row.message_text,
                        "timestamp": row.timestamp.isoformat(),
                        "function_calls": row.function_calls,
                        "metadata": row.metadata,
                        "similarity": float(row.similarity)
                    })
                
                logger.info(f"Found {len(conversations)} similar conversations for query: {query[:50]}...")
                return conversations
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def get_session_history(
        self,
        user_id: str,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all messages from a specific session"""
        try:
            with self.get_db_session() as session:
                query = """
                    SELECT id, role, message_text, timestamp, function_calls, metadata
                    FROM conversations
                    WHERE user_id = :user_id AND session_id = :session_id
                    ORDER BY timestamp ASC
                """
                if limit:
                    query += f" LIMIT {limit}"
                
                results = session.execute(
                    text(query),
                    {"user_id": user_id, "session_id": session_id}
                )
                
                history = []
                for row in results:
                    history.append({
                        "id": row.id,
                        "role": row.role,
                        "message": row.message_text,
                        "timestamp": row.timestamp.isoformat(),
                        "function_calls": row.function_calls,
                        "metadata": row.metadata
                    })
                
                return history
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return []
    
    def get_recent_conversations(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent conversations for a user"""
        try:
            with self.get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT id, session_id, role, message_text, timestamp, function_calls
                        FROM conversations
                        WHERE user_id = :user_id
                          AND timestamp > NOW() - INTERVAL ':days days'
                        ORDER BY timestamp DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "days": days, "limit": limit}
                )
                
                conversations = []
                for row in results:
                    conversations.append({
                        "id": row.id,
                        "session_id": str(row.session_id),
                        "role": row.role,
                        "message": row.message_text,
                        "timestamp": row.timestamp.isoformat(),
                        "function_calls": row.function_calls
                    })
                
                return conversations
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []
    
    def search_by_keyword(
        self,
        user_id: str,
        keyword: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Full-text search by keyword"""
        try:
            with self.get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT id, role, message_text, timestamp, function_calls
                        FROM conversations
                        WHERE user_id = :user_id
                          AND message_text ILIKE :keyword
                        ORDER BY timestamp DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "keyword": f"%{keyword}%", "limit": limit}
                )
                
                conversations = []
                for row in results:
                    conversations.append({
                        "id": row.id,
                        "role": row.role,
                        "message": row.message_text,
                        "timestamp": row.timestamp.isoformat(),
                        "function_calls": row.function_calls
                    })
                
                return conversations
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a user"""
        try:
            with self.get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_messages,
                            COUNT(DISTINCT session_id) as total_sessions,
                            MIN(timestamp) as first_conversation,
                            MAX(timestamp) as last_conversation
                        FROM conversations
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                )
                row = result.fetchone()
                
                return {
                    "total_messages": row.total_messages,
                    "total_sessions": row.total_sessions,
                    "first_conversation": row.first_conversation.isoformat() if row.first_conversation else None,
                    "last_conversation": row.last_conversation.isoformat() if row.last_conversation else None
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
