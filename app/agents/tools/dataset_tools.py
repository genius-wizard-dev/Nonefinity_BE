from langchain.tools import tool, ToolRuntime

from langchain.agents import AgentState
from app.agents.context import AgentContext


@tool
async def run_sql_query(query: str, runtime: ToolRuntime[AgentContext, AgentState]):
  """Execute SQL query on user's datasets and return results."""
  try:
      context = runtime.context
      dataset_service = context.dataset_service
      result = await dataset_service.query_dataset(context.user_id, query)
      return result
  except Exception as e:
      return e

@tool
async def get_list_table(runtime: ToolRuntime[AgentContext, AgentState]):
  """Get list of all datasets/tables for the user."""
  try:
      context = runtime.context
      dataset_service = context.dataset_service
      result = await dataset_service.get_list_dataset(context.user_id)
      return result
  except Exception as e:
      return e



dataset_tools = [
  run_sql_query,
  get_list_table
]
