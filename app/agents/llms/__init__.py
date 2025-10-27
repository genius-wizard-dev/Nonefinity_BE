from langchain.chat_models import init_chat_model
from pydantic.dataclasses import dataclass
from app.schemas.credential import Credential
from langchain.chat_models.base import BaseChatModel
@dataclass
class LLMConfig:
  model: str
  provider: str
  api_key: str
  base_url: str | None = None

  def get_model(self) -> BaseChatModel:

    if self.provider == "google_genai":
      return init_chat_model(
        model=self.model,
        model_provider=self.provider,
        google_api_key=self.api_key,
      )
    else:
      return init_chat_model(
        model=self.model,
        model_provider=self.provider,
        api_key=self.api_key,
        base_url=self.base_url
      )



