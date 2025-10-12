"""
Text embedding tasks for processing direct text input and creating vector embeddings
"""
from typing import Dict, Any, List
from uuid import uuid4

from qdrant_client.http import models as qm

from app.tasks import celery_app
from app.services.qdrant_service import qdrant
from app.utils import get_logger
from .utils import simple_text_split, create_embeddings

logger = get_logger(__name__)


@celery_app.task(name="tasks.embedding.run_text_embedding")
def run_text_embedding(user_id: str, text: str, provider: str, model_id: str, credential: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create embeddings for direct text input using LangChain or local models

    Args:
        user_id: User identifier
        text: Input text to embed
        provider: Embedding provider (huggingface, openai, google, local)
        model_id: Model identifier
        credential: Provider credentials

    Returns:
        Dictionary with embedding results
    """
    logger.info(f"Run text embedding for user={user_id} provider={provider} model={model_id}")

    if not text or not text.strip():
        return {"message": "No text provided", "total_chunks": 0}

    # Split text into chunks
    chunks = simple_text_split(text.strip())

    if not chunks:
        return {"message": "No content to embed", "total_chunks": 0}

    # Create embeddings
    try:
        vectors = create_embeddings(
            provider=provider,
            model=model_id,
            texts=chunks,
            credential=credential or {}
        )
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        return {
            "success": False,
            "error": f"Embedding creation failed: {str(e)}",
            "total_chunks": 0
        }

    # Ensure collection exists
    qdrant.ensure_collection(vector_size=len(vectors[0]))

    # Create points for Qdrant
    points: List[qm.PointStruct] = []
    for idx, vec in enumerate(vectors):
        point = qm.PointStruct(
            id=str(uuid4()),
            vector=vec,
            payload={
                "user_id": user_id,
                "file_id": None,
                "chunk_index": idx,
                "text": chunks[idx],
            },
        )
        points.append(point)

    # Upsert to Qdrant
    qdrant.upsert_points(points)

    return {
        "user_id": user_id,
        "file_id": None,
        "provider": provider,
        "model_id": model_id,
        "total_chunks": len(chunks),
        "successful_chunks": len(points),
        "success": True
    }
