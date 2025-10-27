from langchain.tools import tool, ToolRuntime
from langchain.agents import AgentState
from app.agents.context import AgentContext

@tool
def run_sql_query(query: str, runtime: ToolRuntime[AgentContext, AgentState]):
  """Execute SQL query on user's datasets and return results."""
  try:
      context = runtime.context
      dataset_service = context.dataset_service
      # Get DuckDB connection directly
      duckdb_conn = dataset_service.duckdb

      # Add LIMIT if not present
      import sqlglot
      from sqlglot import exp

      parsed = sqlglot.parse_one(query)
      if not parsed.find(exp.Limit):
          query = f"{query} LIMIT 100"

      # Execute query directly
      result = duckdb_conn.execute(query).df()
      return result.to_string()
  except Exception as e:
      return str(e)

@tool
def get_list_table(runtime: ToolRuntime[AgentContext, AgentState]):
  """Get list of all datasets/tables for the user."""
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
