
from typing import Dict, Any, List
from io import BytesIO
from uuid import uuid4
import chardet
from langchain_community.document_loaders import PyPDFLoader


from app.tasks import celery_app
from app.services.minio_client_service import MinIOClientService
from app.databases import qdrant
from app.utils import get_logger
from .utils import create_embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
logger = get_logger(__name__)


@celery_app.task(name="tasks.embedding.run_embedding")
def run_embedding(user_id: str, object_name: str, provider: str, model_id: str, credential: Dict[str, Any], file_id: str) -> Dict[str, Any]:
    minio = MinIOClientService(access_key=user_id, secret_key=credential.get("secret_key"))
    data = minio.get_object_bytes(bucket_name=user_id, object_name=object_name)
    if not data:
        raise ValueError("Failed to download file from MinIO")

    loader = PyPDFLoader(BytesIO(data))
    docs = loader.load()

    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_text(docs)

    if not chunks:
        return {"message": "No content to embed", "total_chunks": 0}



    qdrant.ensure_collection(vector_size=len(vectors[0]))



    # Upsert to Qdrant
    qdrant.upsert_points(points)

    return {
        "user_id": user_id,
        "file_id": file_id,
        "provider": provider,
        "model_id": model_id,
        "total_chunks": len(chunks),
        "successful_chunks": len(points),
    }
