from pydantic.dataclasses import dataclass
from app.services.dataset_service import DatasetService
from typing import List, Optional
from app.models.dataset import Dataset
from langchain.embeddings import Embeddings

@dataclass(config={'arbitrary_types_allowed': True})
class AgentContext:
  user_id: str
  session_id: str
  dataset_service: Optional[DatasetService] = None
  datasets: Optional[List[Dataset]] = None
  knowledge_store_collection_name: Optional[str] = None
  embedding_model: Optional[Embeddings] = None




