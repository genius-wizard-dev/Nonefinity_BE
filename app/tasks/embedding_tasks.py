from typing import List, Dict, Any

from celery import Celery
from celery.signals import task_prerun, task_success, task_failure, task_revoked
from qdrant_client.http import models as qm
from app.configs.settings import settings
from app.crud.file import FileCRUD
from app.services.minio_client_service import MinIOClientService
from app.services.qdrant_service import QdrantService
from app.utils import get_logger
from app.databases.mongodb import mongodb
from app.models import DOCUMENT_MODELS
import asyncio
from app.crud.task import TaskCRUD
from sentence_transformers import SentenceTransformer
from app.crud.user import UserCRUD
logger = get_logger(__name__)


celery_app = Celery(
    "ai_tasks_system",
    broker=(f"redis://:{settings.redis_password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
            if settings.redis_password else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"),
    backend=(f"redis://:{settings.redis_password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
             if settings.redis_password else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"),
)


_mongo_inited = False


def _ensure_mongo_initialized() -> None:
    global _mongo_inited
    if _mongo_inited:
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(mongodb.connect(document_models=DOCUMENT_MODELS))
    _mongo_inited = True


def _update_task(task_id: str, update: Dict[str, Any]) -> None:
    _ensure_mongo_initialized()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    crud = TaskCRUD()
    doc = loop.run_until_complete(crud.get_by_task_id(task_id))
    if doc:
        loop.run_until_complete(crud.update(doc, update))


@task_prerun.connect
def _on_task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **extras):
    try:
        logger.info(f"Task prerun signal: {task_id}")
        _update_task(task_id, {"status": "STARTED"})
    except Exception as e:
        logger.error(f"Failed to update task prerun: {e}")


@task_success.connect
def _on_task_success(sender=None, result=None, task_id=None, **kwargs):
    try:
        logger.info(f"Task success signal: {task_id}")
        payload: Dict[str, Any] = {"status": "SUCCESS"}
        if isinstance(result, dict):
            payload["metadata"] = result
        _update_task(task_id, payload)
    except Exception as e:
        logger.error(f"Failed to update task success: {e}")


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extras):
    try:
        logger.info(f"Task failure signal: {task_id}")
        _update_task(task_id, {"status": "FAILURE", "error": str(exception) if exception else None})
    except Exception as e:
        logger.error(f"Failed to update task failure: {e}")


@task_revoked.connect
def _on_task_revoked(sender=None, request=None, terminated=None, signum=None, expired=None, **kwargs):
    try:
        if request and getattr(request, "id", None):
            logger.info(f"Task revoked signal: {request.id}")
            _update_task(request.id, {"status": "REVOKED"})
    except Exception as e:
        logger.error(f"Failed to update task revoked: {e}")


def _simple_text_split(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(end - chunk_overlap, 0)
    return chunks


def _hf_local_embed(batch_texts: List[str], model: str) -> List[List[float]]:


    embedder = SentenceTransformer(model)
    vectors = embedder.encode(
        batch_texts, show_progress_bar=False, normalize_embeddings=False)
    return [v.tolist() for v in vectors]


def _langchain_embed(provider: str, model: str, texts: List[str], credential: Dict[str, Any]) -> List[List[float]]:
    """Create embeddings using LangChain when credentials are provided"""
    try:
        # Import LangChain modules dynamically
        p = provider.lower()
        if p == "openai" or p == "openrouter" or p == "huggingface":
            # Default to OpenAIEmbeddings for openai, opnerouter, huggingface (if base_url is provided)
            from langchain_openai.embeddings import OpenAIEmbeddings
            embeddings = OpenAIEmbeddings(
                model=model,
                api_key=credential.get("api_key"),
                base_url=credential.get("base_url")
            )
        elif p == "google":
            from langchain_google_vertexai.embeddings import VertexAIEmbeddings
            embeddings = VertexAIEmbeddings(
                model=model,
                project=credential.get("project"),
                location=credential.get("location")
            )
        else:
            # Default to OpenAIEmbeddings for any other provider
            from langchain_openai.embeddings import OpenAIEmbeddings
            embeddings = OpenAIEmbeddings(
                model=model,
                api_key=credential.get("api_key"),
                base_url=credential.get("base_url")
            )

        # Generate embeddings
        vectors = embeddings.embed_documents(texts)
        return vectors

    except ImportError as e:
        logger.error(f"Failed to import LangChain modules: {e}")
        raise ValueError(f"LangChain modules not available: {e}")
    except Exception as e:
        logger.error(f"Failed to create embeddings with LangChain: {e}")
        raise ValueError(f"LangChain embedding failed: {e}")


def _embed(provider: str, model: str, texts: List[str], credential: Dict[str, Any]) -> List[List[float]]:
    """Create embeddings using either LangChain (if credentials provided) or local models"""
    p = (provider or "").lower()

    # Check if credentials are provided and not empty
    has_credentials = credential and any(credential.values())

    if has_credentials:
        # Use LangChain for external providers when credentials are available
        if p in ("openai", "huggingface", "google"):
            return _langchain_embed(provider, model, texts, credential)
        else:
            logger.warning(f"Provider {provider} not supported with LangChain, falling back to local")

    # Fallback to local models (HuggingFace sentence-transformers)
    if p in ("huggingface", "hf", "local"):
        return _hf_local_embed(texts, model=model)

    raise ValueError(f"Unsupported provider: {provider}. Use 'huggingface', 'local', or provide credentials for 'openai', 'google'")


@celery_app.task(name="tasks.embedding.run_embedding")
def run_embedding(user_id: str, file_id: str, provider: str, model_id: str, credential: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_mongo_initialized()
    logger.info(
        f"Run embedding for user={user_id} file={file_id} provider={provider} model={model_id}")

    file_crud = FileCRUD()
    qdrant = QdrantService()

    # 1) Load file metadata
    file = asyncio.get_event_loop().run_until_complete(file_crud.get_by_id(file_id))
    if not file:
        raise ValueError("File not found")

    # 2) Download bytes from MinIO using user's secret key

    user_crud = UserCRUD()
    user = asyncio.get_event_loop().run_until_complete(user_crud.get_by_id(user_id))
    secret_key = getattr(user, "minio_secret_key", None) if user else None
    if not secret_key:
        raise ValueError("User MinIO secret key not found")

    minio = MinIOClientService(access_key=user_id, secret_key=secret_key)
    data = minio.get_object_bytes(
        bucket_name=user_id, object_name=file.file_path)
    if not data:
        raise ValueError("Failed to download file from MinIO")

    # Extract text for PDF or text files
    text = ""
    try:
        import chardet
        enc = chardet.detect(data).get("encoding") or "utf-8"
        text = data.decode(enc, errors="ignore")
    except Exception:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    if (file.file_ext or "").lower() == ".pdf" or (file.file_type or "").lower() == "application/pdf":
        try:
            from io import BytesIO
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            texts: List[str] = []
            for page in reader.pages:
                texts.append(page.extract_text() or "")
            text = "\n".join(texts)
        except Exception:
            pass

    chunks = _simple_text_split(text)

    if not chunks:
        return {"message": "No content to embed", "total_chunks": 0}

    # 3) Embed (supports huggingface/local via SentenceTransformers only)
    vectors = _embed(provider=provider, model=model_id,
                     texts=chunks, credential=credential or {})

    # Ensure collection created
    qdrant.ensure_collection(vector_size=len(vectors[0]))

    # 4) Upsert to Qdrant
    points: List[qm.PointStruct] = []
    from uuid import uuid4
    for idx, vec in enumerate(vectors):
        point = qm.PointStruct(
            id=str(uuid4()),
            vector=vec,
            payload={
                "user_id": user_id,
                "file_id": file_id,
                "chunk_index": idx,
                "text": chunks[idx],
            },
        )
        points.append(point)

    qdrant.upsert_points(points)

    return {
        "user_id": user_id,
        "file_id": file_id,
        "provider": provider,
        "model_id": model_id,
        "total_chunks": len(chunks),
        "successful_chunks": len(points),
    }


@celery_app.task(name="ai.embeddings.tasks.search_similar")
def search_similar(query_text: str, provider: str, model_id: str, credential: Dict[str, Any], user_id: str | None = None, file_id: str | None = None, limit: int = 5):
    _ensure_mongo_initialized()
    vectors = _embed(provider=provider, model=model_id, texts=[
                     query_text], credential=credential or {})
    query_vec = vectors[0]

    qdrant = QdrantService()

    flt = None
    if user_id or file_id:
        must: List[qm.FieldCondition] = []
        if user_id:
            must.append(qm.FieldCondition(key="user_id",
                        match=qm.MatchValue(value=user_id)))
        if file_id:
            must.append(qm.FieldCondition(key="file_id",
                        match=qm.MatchValue(value=file_id)))
        flt = qm.Filter(must=must)

    results = qdrant.search(vector=query_vec, limit=limit, filter_=flt)
    return [
        {
            "id": r.id,
            "score": r.score,
            "payload": r.payload,
        }
        for r in results
    ]


@celery_app.task(name="tasks.embedding.run_text_embedding")
def run_text_embedding(user_id: str, text: str, provider: str, model_id: str, credential: Dict[str, Any]) -> Dict[str, Any]:
    """Create embeddings for direct text input using LangChain or local models"""
    _ensure_mongo_initialized()
    logger.info(f"Run text embedding for user={user_id} provider={provider} model={model_id}")

    qdrant = QdrantService()

    if not text or not text.strip():
        return {"message": "No text provided", "total_chunks": 0}

    # Split text into chunks
    chunks = _simple_text_split(text.strip())

    if not chunks:
        return {"message": "No content to embed", "total_chunks": 0}

    # Create embeddings using LangChain or local models
    try:
        vectors = _embed(provider=provider, model=model_id, texts=chunks, credential=credential or {})
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        return {
            "success": False,
            "error": f"Embedding creation failed: {str(e)}",
            "total_chunks": 0
        }

    # Ensure collection created
    qdrant.ensure_collection(vector_size=len(vectors[0]))

    # Upsert to Qdrant
    points: List[qm.PointStruct] = []
    from uuid import uuid4
    for idx, vec in enumerate(vectors):
        point = qm.PointStruct(
            id=str(uuid4()),
            vector=vec,
            payload={
                "user_id": user_id,
                "file_id": None,  # Direct text embedding
                "chunk_index": idx,
                "text": chunks[idx],
            },
        )
        points.append(point)

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
