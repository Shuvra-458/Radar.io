from contextlib import asynccontextmanager
import psycopg
from pgvector.psycopg import register_vector_async

from app.config import DATABASE_URL

@asynccontextmanager
async def get_conn():
    """
    Async context manager yielding a connection with the pgvector type
    registered.
    """
    conn = await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)
    try:
        await register_vector_async(conn)
        yield conn
    finally:
        await conn.close()
        