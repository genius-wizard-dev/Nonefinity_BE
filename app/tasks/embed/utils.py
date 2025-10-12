"""
Embedding utilities for text processing and vector generation
"""
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from app.utils import get_logger


logger = get_logger(__name__)



def hf_local_embed(batch_texts: List[str], model: str) -> List[List[float]]:
    """
    Create embeddings using HuggingFace SentenceTransformers locally

    Args:
        batch_texts: List of texts to embed
        model: Model name for SentenceTransformer

    Returns:
        List of embedding vectors
    """
    embedder = SentenceTransformer(model)
    vectors = embedder.encode(
        batch_texts, show_progress_bar=False, normalize_embeddings=False)
    return [v.tolist() for v in vectors]


def langchain_embed(provider: str, model: str, texts: List[str], credential: Dict[str, Any]) -> List[List[float]]:
    """
    Create embeddings using LangChain when credentials are provided

    Args:
        provider: Provider name (openai, google)
        model: Model name
        texts: List of texts to embed
        credential: Credentials dictionary

    Returns:
        List of embedding vectors

    Raises:
        ValueError: If LangChain modules are not available or embedding fails
    """
    try:
        p = provider.lower()
        if p == "google":
            embeddings = GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=credential.get("api_key")
            )
        else:
            embeddings = OpenAIEmbeddings(
                model=model,
                api_key=credential.get("api_key"),
                base_url=credential.get("base_url")
            )

        vectors = embeddings.embed_documents(texts)
        return vectors

    except ImportError as e:
        logger.error(f"Failed to import LangChain modules: {e}")
        raise ValueError(f"LangChain modules not available: {e}")
    except Exception as e:
        logger.error(f"Failed to create embeddings with LangChain: {e}")
        raise ValueError(f"LangChain embedding failed: {e}")


def create_embeddings(provider: str, model: str, texts: List[str], credential: Dict[str, Any]) -> List[List[float]]:
    """
    Create embeddings using either LangChain (if credentials provided) or local models

    Args:
        provider: Provider name (huggingface, openai, google, local)
        model: Model name
        texts: List of texts to embed
        credential: Credentials dictionary

    Returns:
        List of embedding vectors

    Raises:
        ValueError: If provider is not supported
    """
    p = (provider or "").lower()
    has_credentials = credential and any(credential.values())

    if has_credentials:
        if p in ("openai", "huggingface", "google"):
            return langchain_embed(provider, model, texts, credential)
        else:
            logger.warning(f"Provider {provider} not supported with LangChain, falling back to local")

    if p in ("huggingface", "hf", "local"):
        return hf_local_embed(texts, model=model)

    raise ValueError(f"Unsupported provider: {provider}. Use 'huggingface', 'local', or provide credentials for 'openai', 'google'")
