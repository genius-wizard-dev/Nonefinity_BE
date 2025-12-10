"""
Embedding utilities for text processing and vector generation
"""
from typing import List, Dict, Any
from app.utils import get_logger


logger = get_logger(__name__)


def simple_text_split(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter

    Args:
        text: Input text to split
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = text_splitter.split_text(text.strip())
    return [chunk for chunk in chunks if chunk.strip()]


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
        if p == "google_genai" or p == "google":
            from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
            embeddings = GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=credential.get("api_key")
            )
        else:
            from langchain_openai.embeddings import OpenAIEmbeddings
            # Use OpenAI-compatible API for all other providers
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
    Create embeddings using LangChain with configured AI models

    Args:
        provider: Provider name (openai, google, etc.)
        model: Model name
        texts: List of texts to embed
        credential: Credentials dictionary

    Returns:
        List of embedding vectors

    Raises:
        ValueError: If provider is not supported or credentials are missing
    """
    if not credential or not any(credential.values()):
        raise ValueError("Credentials are required for AI model embedding. Please configure your model credentials.")

    p = (provider or "").lower()

    if p in ("openai", "google", "google_genai", "nvidia", "togetherai", "groq"):
        return langchain_embed(provider, model, texts, credential)

    raise ValueError(f"Unsupported provider: {provider}. Supported providers: openai, google, nvidia, togetherai, groq")
