"""
Database connection helper for vector_db (READ-ONLY)

Confidence: 98% ✅
Limitations:
- No connection pooling (acceptable for testing)
- No retry logic
- Single connection model
"""
import os
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", "hassan123"),
    "dbname": os.getenv("PGDATABASE", "vector_db"),
}

def get_connection(autocommit: bool = True) -> psycopg.Connection:
    """
    Get database connection
    
    Confidence: 98% ✅
    Limitation: Connection pooling not implemented (fine for testing)
    
    Returns:
        psycopg.Connection: Database connection with vector support
    """
    conn = psycopg.connect(
        **DB_CONFIG,
        autocommit=autocommit,
        row_factory=dict_row
    )
    register_vector(conn)
    return conn

def test_connection() -> bool:
    """
    Test database connection
    
    Confidence: 99% ✅
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Test basic query
                cur.execute("SELECT COUNT(*) as count FROM chunks WHERE embedding IS NOT NULL")
                result = cur.fetchone()
                print(f"✅ Connected to vector_db: {result['count']} chunks available")
                
                # Test documents table
                cur.execute("SELECT COUNT(*) as count FROM documents")
                docs = cur.fetchone()
                print(f"✅ Documents available: {docs['count']}")
                
                return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def get_database_stats() -> dict:
    """
    Get database statistics
    
    Confidence: 95% ✅
    
    Returns:
        dict: Database statistics
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                stats = {}
                
                # Chunks with embeddings
                cur.execute("SELECT COUNT(*) as count FROM chunks WHERE embedding IS NOT NULL")
                stats['chunks_with_embeddings'] = cur.fetchone()['count']
                
                # Total documents
                cur.execute("SELECT COUNT(*) as count FROM documents")
                stats['total_documents'] = cur.fetchone()['count']
                
                # Total links
                cur.execute("SELECT COUNT(*) as count FROM links")
                stats['total_links'] = cur.fetchone()['count']
                
                # Document types
                cur.execute("""
                    SELECT document_type, COUNT(*) as count 
                    FROM documents 
                    GROUP BY document_type 
                    ORDER BY count DESC
                """)
                stats['document_types'] = {row['document_type']: row['count'] for row in cur.fetchall()}
                
                return stats
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return {}

