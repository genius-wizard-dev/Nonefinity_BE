from typing import List, Optional, Dict, Any
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)


class QdrantDB:
    """Qdrant service using LangChain integration for vector operations."""

    def __init__(self):
        """Initialize the Qdrant service with LangChain integration."""
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=False,
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self._embeddings = None
        self._vector_store = None

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            raise ValueError("Embeddings not set")
        return self._embeddings

    @embeddings.setter
    def embeddings(self, embeddings: Embeddings):
        self._embeddings = embeddings


    @property
    def vector_store(self) -> QdrantVectorStore:
        """Get or create the LangChain QdrantVectorStore instance."""
        if self._vector_store is None:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            self._vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embedding=self._embeddings,
            )
        return self._vector_store

    def ensure_collection(self, vector_size: int, distance: Distance = Distance.COSINE):
        """Ensure the collection exists with the correct configuration."""
        try:
            exists = self.client.collection_exists(self.collection_name)
            if exists:
                try:
                    info = self.client.get_collection(self.collection_name)
                    current_cfg = getattr(info, "config", None)
                    current_params = None
                    if current_cfg and getattr(current_cfg, "params", None):
                        current_params = current_cfg.params
                    if current_params is None and getattr(info, "vectors_config", None):
                        current_params = info.vectors_config

                    current_size = None
                    if current_params:
                        if isinstance(current_params, VectorParams):
                            current_size = current_params.size
                        elif isinstance(current_params, dict):
                            first = next(iter(current_params.values()))
                            if isinstance(first, VectorParams):
                                current_size = first.size

                    if current_size is not None and current_size != vector_size:
                        logger.warning(
                            f"Qdrant collection '{self.collection_name}' has dim {current_size}, "
                            f"but we need {vector_size}. Recreating collection."
                        )
                        self.client.delete_collection(self.collection_name)
                        exists = False
                except Exception as e:
                    logger.warning(f"Failed to read collection info for '{self.collection_name}': {e}")

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=distance
                    ),
                )
                logger.info(f"Created Qdrant collection '{self.collection_name}' with size {vector_size}")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            raise

    def add_documents(
        self,
        documents: List[Document],
        embeddings: Embeddings,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to the vector store using LangChain."""
        try:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            # Ensure collection exists with correct vector size
            if documents:
                # Get embedding dimension from first document
                sample_embedding = embeddings.embed_query("sample")
                vector_size = len(sample_embedding)
                self.ensure_collection(vector_size)

            # Add documents using LangChain
            doc_ids = self.vector_store.add_documents(
                documents=documents,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to Qdrant")
            return doc_ids
        except Exception as e:
            logger.error(f"Failed to add documents to Qdrant: {e}")
            raise

    def add_texts(
        self,
        texts: List[str],
        embeddings: Embeddings,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add texts to the vector store using LangChain."""
        try:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            # Ensure collection exists with correct vector size
            if texts:
                sample_embedding = embeddings.embed_query("sample")
                vector_size = len(sample_embedding)
                self.ensure_collection(vector_size)

            # Add texts using LangChain
            doc_ids = self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(texts)} texts to Qdrant")
            return doc_ids
        except Exception as e:
            logger.error(f"Failed to add texts to Qdrant: {e}")
            raise

    def similarity_search(
        self,
        query: str,
        embeddings: Embeddings,
        k: int = 5,
        filter: Optional[Filter] = None
    ) -> List[Document]:
        """Perform similarity search using LangChain."""
        try:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            # Ensure collection exists
            sample_embedding = embeddings.embed_query("sample")
            vector_size = len(sample_embedding)
            self.ensure_collection(vector_size)

            # Perform search using LangChain
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"Found {len(results)} similar documents for query")
            return results
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            raise

    def similarity_search_with_score(
        self,
        query: str,
        embeddings: Embeddings,
        k: int = 5,
        filter: Optional[Filter] = None
    ) -> List[tuple[Document, float]]:
        """Perform similarity search with scores using LangChain."""
        try:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            # Ensure collection exists
            sample_embedding = embeddings.embed_query("sample")
            vector_size = len(sample_embedding)
            self.ensure_collection(vector_size)

            # Perform search with scores using LangChain
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"Found {len(results)} similar documents with scores for query")
            return results
        except Exception as e:
            logger.error(f"Failed to perform similarity search with score: {e}")
            raise

    def delete_documents(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        try:
            # Use direct client for deletion as LangChain doesn't have delete method
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            logger.info(f"Deleted {len(ids)} documents from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": getattr(info, "vectors_count", 0),
                "status": getattr(info, "status", "unknown"),
                "config": getattr(info, "config", None)
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}

    def clear_collection(self) -> bool:
        """Clear all documents from the collection."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Cleared collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False


# Global instance
qdrant = QdrantDB()

