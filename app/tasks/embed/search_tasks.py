
from typing import Dict, Any, List, Optional

from qdrant_client.http import models as qm

from app.tasks import celery_app
from app.utils import get_logger
from .utils import create_embeddings

logger = get_logger(__name__)


@celery_app.task(name="tasks.embedding.search_similar")
def search_similar(
    query_text: str,
    provider: str,
    model_id: str,
    credential: Dict[str, Any],
    user_id: Optional[str] = None,
    file_id: Optional[str] = None,
    limit: int = 5,
    collection_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for similar vectors based on query text

    Args:
        query_text: Text to search for
        provider: Embedding provider
        model_id: Model identifier
        credential: Provider credentials
        user_id: Optional user filter
        file_id: Optional file filter
        limit: Maximum number of results to return

    Returns:
        List of search results with scores and payloads
    """
    logger.info(f"Searching for similar vectors: query='{query_text[:50]}...' user_id={user_id} file_id={file_id}")

    # Create embedding for query text
    vectors = create_embeddings(
        provider=provider,
        model=model_id,
        texts=[query_text],
        credential=credential
    )
    query_vec = vectors[0]

    # Build filter conditions
    flt = None
    if user_id or file_id:
        must: List[qm.FieldCondition] = []
        if user_id:
            must.append(qm.FieldCondition(
                key="user_id",
                match=qm.MatchValue(value=user_id)
            ))
        if file_id:
            must.append(qm.FieldCondition(
                key="file_id",
                match=qm.MatchValue(value=file_id)
            ))
        flt = qm.Filter(must=must)

    # Determine collection name
    target_collection = collection_name or f"user_{user_id}_embeddings" if user_id else "default_embeddings"

    from app.databases.qdrant import qdrant
    # Search in Qdrant
    results = qdrant.search(vector=query_vec, collection_name=target_collection, limit=limit, filter_=flt)

    return [
        {
            "id": r.id,
            "score": r.score,
            "payload": r.payload,
        }
        for r in results
    ]
