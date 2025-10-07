from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.configs.settings import settings
from app.utils import get_logger


logger = get_logger(__name__)


class QdrantService:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=False,
        )
        self.collection = settings.QDRANT_COLLECTION

    def ensure_collection(self, vector_size: int, distance: qm.Distance = qm.Distance.COSINE):
        try:
            exists = self.client.collection_exists(self.collection)
            if exists:
                try:
                    info = self.client.get_collection(self.collection)
                    # info.vectors_count, info.config, etc. For single vector, vectors is VectorParams
                    current_cfg = getattr(info, "config", None)
                    current_params = None
                    if current_cfg and getattr(current_cfg, "params", None):
                        current_params = current_cfg.params
                    # Fallback: some client versions expose vectors_config
                    if current_params is None and getattr(info, "vectors_config", None):
                        current_params = info.vectors_config
                    current_size = None
                    if current_params:
                        # Single-vector setup
                        if isinstance(current_params, qm.VectorParams):
                            current_size = current_params.size
                        # Named vectors dict case
                        elif isinstance(current_params, dict):
                            # Pick first
                            first = next(iter(current_params.values()))
                            if isinstance(first, qm.VectorParams):
                                current_size = first.size
                    if current_size is not None and current_size != vector_size:
                        logger.warning(
                            f"Qdrant collection '{self.collection}' has dim {current_size}, "
                            f"but we need {vector_size}. Recreating collection.")
                        self.client.delete_collection(self.collection)
                        exists = False
                except Exception as e:
                    logger.warning(f"Failed to read collection info for '{self.collection}': {e}")
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=qm.VectorParams(
                        size=vector_size, distance=distance),
                )
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            raise

    def upsert_points(self, points: List[qm.PointStruct]):
        try:
            self.client.upsert(collection_name=self.collection, points=points)
        except Exception as e:
            msg = str(e)
            logger.error(f"Failed to upsert points to Qdrant: {e}")
            # Auto-recover on vector dimension mismatch by recreating collection
            if "Vector dimension error" in msg and points:
                try:
                    expected_size = len(points[0].vector)
                    logger.warning(
                        f"Detected dimension mismatch. Recreating collection '{self.collection}' with size={expected_size}.")
                    # Recreate with correct size
                    self.client.delete_collection(self.collection)
                    self.client.create_collection(
                        collection_name=self.collection,
                        vectors_config=qm.VectorParams(size=expected_size, distance=qm.Distance.COSINE),
                    )
                    # Retry once
                    self.client.upsert(collection_name=self.collection, points=points)
                    return
                except Exception as re:
                    logger.error(f"Auto-recreate-and-retry failed: {re}")
                    raise
            raise

    def search(self, vector: List[float], limit: int = 5, filter_: Optional[qm.Filter] = None):
        return self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit,
            query_filter=filter_,
        )
