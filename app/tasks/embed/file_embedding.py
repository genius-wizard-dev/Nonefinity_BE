
from typing import Dict, Any, List
from uuid import uuid4
import tempfile
import os
from langchain_classic.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    CSVLoader,
    UnstructuredExcelLoader,
)
from qdrant_client.http import models as qm

from app.tasks import celery_app
from app.services.minio_client_service import MinIOClientService
from app.databases.qdrant import qdrant
from app.utils import get_logger
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import init_embeddings
logger = get_logger(__name__)


@celery_app.task(name="tasks.embedding.run_embedding")
def run_embedding(
    user_id: str,
    object_name: str,
    provider: str,
    model_id: str,
    credential: Dict[str, Any],
    file_id: str,
    knowledge_store_id: str = None,
    collection_name: str = None,
) -> Dict[str, Any]:
    minio = MinIOClientService(access_key=user_id, secret_key=credential.get("secret_key"))
    data = minio.get_object_bytes(bucket_name=user_id, object_name=object_name)
    if not data:
        raise ValueError("Failed to download file from MinIO")

    # Detect file type from object name
    file_extension = os.path.splitext(object_name)[1].lower()

    # Save to temporary file since document loaders require a file path
    temp_file_path = None
    try:
        # Create temporary file with appropriate extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, mode='wb') as temp_file:
            temp_file.write(data)
            temp_file_path = temp_file.name

        # Load document based on file type
        try:
            if file_extension == '.pdf':
                loader = PyPDFLoader(temp_file_path)
            elif file_extension in ['.txt', '.md', '.markdown']:
                loader = TextLoader(temp_file_path)
            elif file_extension in ['.doc', '.docx']:
                loader = UnstructuredWordDocumentLoader(temp_file_path)
            elif file_extension == '.csv':
                loader = CSVLoader(temp_file_path)
            elif file_extension in ['.xls', '.xlsx']:
                loader = UnstructuredExcelLoader(temp_file_path)
            else:
                # Try to read as plain text for unknown types
                logger.warning(f"Unknown file type: {file_extension}, attempting to read as text")
                loader = TextLoader(temp_file_path, encoding='utf-8')

            docs = loader.load()
        except Exception as e:
            logger.error(f"Failed to load file with extension {file_extension}: {e}")
            return {
                "success": False,
                "error": f"Unsupported or corrupted file type {file_extension}: {str(e)}",
                "total_chunks": 0
            }

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(docs)

        if not chunks:
            return {"message": "No content to embed", "total_chunks": 0}

        # Create embeddings

            # Use OpenAI-compatible API for all other providers
        embeddings = init_embeddings(
            provider=provider,
            model=model_id,
            api_key=credential.get("api_key"),
            base_url=credential.get("base_url")
        )
        qdrant.embeddings = embeddings
        uuids = [str(uuid4()) for _ in range(len(chunks))]
        qdrant.add_documents(documents=chunks, collection_name=collection_name, ids=uuids)
        return {
            "user_id": user_id,
            "file_id": file_id,
            "knowledge_store_id": knowledge_store_id,
            "provider": provider,
            "model_id": model_id,
            "total_chunks": len(chunks),
            "successful_chunks": len(chunks),
            "collection_name": collection_name,
            "success": True
        }
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
