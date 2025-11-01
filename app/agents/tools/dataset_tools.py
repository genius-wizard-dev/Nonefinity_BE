from langchain.tools import tool, ToolRuntime
from langchain.agents import AgentState
from app.agents.context import AgentContext
from app.utils.preprocess_sql import is_select_query
from langchain_core.messages.tool import ToolMessage

@tool
def run_sql_query(query: str, runtime: ToolRuntime[AgentContext, AgentState]):
  """Execute SQL query on user's datasets and return results.

  Args:
    query: The SQL query to execute
  Returns:
    The results of the query
  """
  try:
      context = runtime.context
      dataset_service = context.dataset_service
      # Get DuckDB connection directly
      duckdb_conn = dataset_service.duckdb

      if not is_select_query(query):
        return ToolMessage(content="Only SELECT queries are allowed", tool_call_id=runtime.tool_call_id, name="run_sql_query")

      # Execute query directly
      result = duckdb_conn.execute(query).df()
      return result.to_string()
  except Exception as e:
      return str(e)

@tool
def get_list_table(runtime: ToolRuntime[AgentContext, AgentState]):
  """Get list of all datasets/tables for the user.
  Returns:
    The list of tables
  """
  try:
      context = runtime.context
      dataset_service = context.dataset_service
      # Get DuckDB connection directly
      duckdb_conn = dataset_service.duckdb

      # Get all table names
      result = duckdb_conn.execute("SHOW TABLES").df()
      return result.to_dict(orient='records')
  except Exception as e:
      return str(e)

@tool
def describe_table(table_name: str, runtime: ToolRuntime[AgentContext, AgentState]):
  """Get detailed schema of a specific table.

  Args:
      table_name: Name of the table to describe
  """
  try:
      context = runtime.context
      dataset_service = context.dataset_service
      # Get DuckDB connection directly
      duckdb_conn = dataset_service.duckdb

      # Get table schema
      result = duckdb_conn.execute(f"DESCRIBE {table_name}").df()
      return result.to_dict(orient='records')
  except Exception as e:
      return str(e)

dataset_tools = [
  run_sql_query,
  get_list_table,
  describe_table
]
