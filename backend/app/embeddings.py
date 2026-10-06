from langchain_google_genai import GoogleGenerativeAIEmbeddings
import math
from app.config import EMBED_MODEL, EMBED_DIM

# Instance of model
_doc_emb = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, task_type="RETRIEVAL_DOCUMENT",)
_query_emb = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, task_type="RETRIEVAL_QUERY",)

def _truncate_normalize(vec: list[float], dim: int) -> list[float]:
    """
    Matryoshka truncation: keep the first `dim` components and renormalize
    to unit length. This is mathematically valid for MRL-trained models
    (which gemini-embedding-001 is) and gives near-native retrieval quality.
    """
    if len(vec) == dim:
        return vec
    if len(vec) < dim:
        raise ValueError(f"Embedding dim {len(vec)} < target {dim}")

    head = vec[:dim]
    norm = math.sqrt(sum(x*x for x in head))
    return head if norm == 0.0 else [x / norm for x in head]

async def embed_one(text: str) -> list[float]:
    """Embed a single string (query side)."""
    raw = await _query_emb.aembed_query(text)
    return _truncate_normalize(raw, EMBED_DIM)

async def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed a batch (document side)."""
    raw = await _doc_emb.aembed_documents(texts)
    return [_truncate_normalize(v, EMBED_DIM) for v in raw]

