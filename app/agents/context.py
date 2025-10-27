from pydantic.dataclasses import dataclass
from app.services.dataset_service import DatasetService

@dataclass(config={'arbitrary_types_allowed': True})
class AgentContext:
  user_id: str
  dataset_service: DatasetService


