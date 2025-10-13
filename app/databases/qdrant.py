from typing import List, Optional, Dict, Any
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from qdrant_client.conversions.common_types import CollectionInfo
from app.configs.settings import settings
from app.utils import get_logger


logger = get_logger(__name__)


class QdrantDB:
    """Qdrant service using LangChain integration for vector operations."""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=False,
        )
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


    def get_vector_store(self, collection_name: str) -> QdrantVectorStore:
        """Get or create the LangChain QdrantVectorStore instance for a specific collection."""
        if self._embeddings is None:
            raise ValueError("Embeddings not set")
        return QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=self._embeddings,
        )

    def ensure_collection(self, collection_name: str, vector_size: int, distance: Distance = Distance.COSINE):
        """Ensure the collection exists with the correct configuration."""
        try:
            exists = self.client.collection_exists(collection_name)
            if exists:
                try:
                    info = self.client.get_collection(collection_name)
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
                            f"Qdrant collection '{collection_name}' has dim {current_size}, "
                            f"but we need {vector_size}. Recreating collection."
                        )
                        self.client.delete_collection(collection_name)
                        exists = False
                except Exception as e:
                    logger.warning(f"Failed to read collection info for '{collection_name}': {e}")

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
        collection_name: str,
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
                self.ensure_collection(collection_name, vector_size)

            # Add documents using LangChain
            doc_ids = self.get_vector_store(collection_name).add_documents(
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
        collection_name: str,
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
                self.ensure_collection(collection_name, vector_size)

            # Add texts using LangChain
            doc_ids = self.get_vector_store(collection_name).add_texts(
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
        filter: Optional[Filter] = None,
        collection_name: str = None
    ) -> List[Document]:
        """Perform similarity search using LangChain."""
        try:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            # Ensure collection exists
            sample_embedding = embeddings.embed_query("sample")
            vector_size = len(sample_embedding)
            self.ensure_collection(collection_name, vector_size)

            # Perform search using LangChain
            results = self.get_vector_store(collection_name).similarity_search(
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
        filter: Optional[Filter] = None,
        collection_name: str = None
    ) -> List[tuple[Document, float]]:
        """Perform similarity search with scores using LangChain."""
        try:
            if self._embeddings is None:
                raise ValueError("Embeddings not set")
            # Ensure collection exists
            sample_embedding = embeddings.embed_query("sample")
            vector_size = len(sample_embedding)
            self.ensure_collection(collection_name, vector_size)

            # Perform search with scores using LangChain
            results = self.get_vector_store(collection_name).similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"Found {len(results)} similar documents with scores for query")
            return results
        except Exception as e:
            logger.error(f"Failed to perform similarity search with score: {e}")
            raise

    def delete_documents(self, ids: List[str], collection_name: str = None) -> bool:
        """Delete documents by IDs."""
        try:
            # Use direct client for deletion as LangChain doesn't have delete method
            self.client.delete(
                collection_name=collection_name,
                points_selector=ids
            )
            logger.info(f"Deleted {len(ids)} documents from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False





    def create_collection(self, collection_name: str, vector_size: int = 384, distance: Distance = Distance.COSINE) -> bool:
        """Create a new collection with specified parameters."""
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            return True
        except Exception as e:
            logger.error(f"Qdrant: Failed to create collection '{collection_name}': {str(e)}")
            import traceback
            logger.error(f"Qdrant: Traceback: {traceback.format_exc()}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information."""
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "status": getattr(collection_info, "status", "unknown"),
                "vectors_count": getattr(collection_info, "vectors_count", 0),
                "indexed_vectors_count": getattr(collection_info, "indexed_vectors_count", 0),
                "points_count": getattr(collection_info, "points_count", 0),
                "segments_count": getattr(collection_info, "segments_count", 0),
                "config": getattr(collection_info, "config", None)
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    def scroll(self, collection_name: str, limit: int = 5, offset: Optional[str] = None) -> tuple[List[Any], Optional[str]]:
        """
        Scroll through points in a collection with pagination.
        Returns tuple of (points, next_scroll_id)
        """
        try:
            # Use the client's scroll method directly with correct parameters
            result = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )

            # Extract points and next scroll ID
            points = result[0] if result else []
            next_scroll_id = result[1] if len(result) > 1 else None

            return points, next_scroll_id

        except Exception as e:
            logger.error(f"Failed to scroll collection {collection_name}: {e}")
            return [], None




# Global instance
qdrant = QdrantDB()

