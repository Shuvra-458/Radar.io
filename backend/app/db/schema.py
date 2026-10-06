from app.db.connection import get_conn

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    company     TEXT NOT NULL,
    task_id     TEXT NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    content     TEXT NOT NULL,
    query       TEXT,
    embedding   vector(768) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents USING hnsw (embedding vector_cosine_ops);
"""

CREATE_COMPANY_IDX = """
CREATE INDEX IF NOT EXISTS documents_company_idx ON documents (company);
"""

async def ensure_schema() -> None:
    """Idempotent - safe to call at every app start"""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(CREATE_TABLE)
            await cur.execute(CREATE_INDEX)
            await cur.execute(CREATE_COMPANY_IDX)