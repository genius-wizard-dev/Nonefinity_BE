
from langchain.chat_models import init_chat_model
from pydantic.dataclasses import dataclass
from langchain.chat_models.base import BaseChatModel
from langchain.embeddings import Embeddings, init_embeddings
from starlette.status import HTTP_404_NOT_FOUND
from app.core.exceptions import AppError
from app.crud import model_crud, credential_crud
from app.services import credential_service, provider_service


@dataclass
class LLMConfig:
  model: str
  provider: str
  api_key: str
  base_url: str | None = None

  def get_llm(self) -> BaseChatModel:
    if self.provider == "google_genai":
      return init_chat_model(model=self.model, model_provider=self.provider, google_api_key=self.api_key)
    else:
      return init_chat_model(model=self.model, model_provider=self.provider, api_key=self.api_key, base_url=self.base_url)

  @classmethod
  async def from_model_id(
    cls,
    owner_id: str,
    model_id: str,

  ) -> "LLMConfig":
    """Create LLMConfig from model ID by fetching from database"""
    model = await model_crud.get_by_id(id=model_id, owner_id=owner_id)
    if not model:
      raise AppError(
        message="Model not found",
        status_code=HTTP_404_NOT_FOUND
      )

    credential = await credential_crud.get_by_id(id=model.credential_id, owner_id=owner_id)
    if not credential:
      raise AppError(
        message="Credential not found",
        status_code=HTTP_404_NOT_FOUND
      )

    provider = await provider_service.get_provider_by_id(credential.provider_id)
    if not provider:
      raise AppError(
        message="Provider not found",
        status_code=HTTP_404_NOT_FOUND
      )

    api_key = credential_service._decrypt_api_key(credential.api_key)
    base_url = credential.base_url if credential.base_url else None

    return cls(
      model=model.model,
      provider=provider.provider,
      api_key=api_key,
      base_url=base_url
    )


@dataclass
class EmbeddingModelConfig:
  model: str
  provider: str
  api_key: str
  base_url: str | None = None

  def get_embedding_model(self) -> Embeddings:
    return init_embeddings(
      model=self.model,
      provider=self.provider,
      api_key=self.api_key,
      base_url=self.base_url
    )

  @classmethod
  async def from_model_id(
    cls,
    owner_id: str,
    embedding_model_id: str,
  ) -> "EmbeddingModelConfig":
    """Create EmbeddingModelConfig from model ID by fetching from database"""
    embedding_model = await model_crud.get_by_id(id=embedding_model_id, owner_id=owner_id)
    if not embedding_model:
      raise AppError(
        message="Embedding model not found",
        status_code=HTTP_404_NOT_FOUND
      )

    credential = await credential_crud.get_by_id(id=embedding_model.credential_id, owner_id=owner_id)
    if not credential:
      raise AppError(
        message="Credential not found",
        status_code=HTTP_404_NOT_FOUND
      )

    provider = await provider_service.get_provider_by_id(credential.provider_id)
    if not provider:
      raise AppError(
        message="Provider not found",
        status_code=HTTP_404_NOT_FOUND
      )

    api_key = credential_service._decrypt_api_key(credential.api_key)
    base_url = credential.base_url if credential.base_url else None

    return cls(
      model=embedding_model.model,
      provider=provider.provider,
      api_key=api_key,
      base_url=base_url
    )


