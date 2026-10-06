from app.db.connection import get_conn
from app.embeddings import embed_one, embed_many
from app.state import SourceDoc

async def insert_docs(company: str, docs: list[SourceDoc]) -> int:
    """
    Embed every doc in one batch, then insert in one statement.
    Returns the number of rows inserted.
    """
    if not docs:
        return 0

    # One embedding call for N docs
    vectors = await embed_many([d.content for d in docs])

    rows = [
        (company, d.task_id, d.url, d.title, d.content, d.query, vec)
        for d, vec in zip(docs, vectors)
    ]

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO documents
                    (company, task_id, url, title, content, query, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
    return len(rows)

async def search_docs(
    query: str,
    company: str,
    k: int = 5,
) -> list[dict]:
    """
    Return the top-k most similar docs for `query`, restricted to one company.
    """
    qvec = await embed_one(query)

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT url, title, content,
                    embedding <=> %s::vector AS distance
                FROM documents
                WHERE company = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec, company, qvec, k),
            )
            rows = await cur.fetchall()

    return [
        {"url": r[0], "title": r[1], "content": r[2], "distance": float(r[3])}
        for r in rows
    ]