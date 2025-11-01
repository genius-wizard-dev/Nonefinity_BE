from langchain.tools import tool, ToolRuntime
from langchain.agents import AgentState
from app.agents.context import AgentContext
from app.services.knowledge_store_service import knowledge_store_service

from app.utils import get_logger
logger = get_logger(__name__)
from langchain_core.documents import Document

@tool
def search_knowledge_base(query: str, runtime: ToolRuntime[AgentContext, AgentState]):
  """Search for information in the knowledge base.
  Args:
    query: The query to search for in the knowledge base
  Returns:
    The results of the search
  """

  knowledge_store = runtime.context.knowledge_store
  knowledge_store_collection_name = runtime.context.knowledge_store_collection_name
  embedding_model = runtime.context.embedding_model
  if embedding_model is None:
    raise ValueError("Embedding model is not set")

  knowledge_store.embeddings = embedding_model
  results =  knowledge_store.similarity_search(
    query=query,
    k=5,
    collection_name=knowledge_store_collection_name,
  )
  if len(results) == 0:
    return "No results found"
  return [{"text": result.page_content} for result in results]

knowledge_tools = [search_knowledge_base]
