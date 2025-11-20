from langchain.tools import tool, ToolRuntime
from langchain.agents import AgentState
from app.agents.types import AgentContext
from app.databases.qdrant import qdrant
from app.utils import get_logger
logger = get_logger(__name__)

@tool("find_from_knowledge_base")
def search_knowledge_base(query: str, runtime: ToolRuntime[AgentContext, AgentState]):
  """Search for information in the knowledge base.
  Args:
    query: The query to search for in the knowledge base
  Returns:
    The results of the search
  """

  knowledge_store_collection_name = runtime.context.knowledge_store_collection_name
  embedding_model = runtime.context.embedding_model
  if embedding_model is None:
    raise ValueError("Embedding model is not set")

  qdrant.embeddings = embedding_model
  results =  qdrant.similarity_search(
    query=query,
    k=5,
    collection_name=knowledge_store_collection_name,
  )
  if len(results) == 0:
    return "No results found"
  return [{"text": result.page_content} for result in results]

knowledge_tools = [search_knowledge_base]
