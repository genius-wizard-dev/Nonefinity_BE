import sqlparse
import sqlglot


def check_sql_syntax(sql: str) -> bool:
    """Check if the SQL syntax is correct"""
    try:
        sqlparse.parse(sql)
        return True
    except Exception:
        return False


def is_select_query(sql: str) -> bool:
    """
    Check if the given SQL statement is a SELECT query.

    Args:
        sql (str): The SQL statement to check.

    Returns:
        bool: True if the statement is a SELECT query, False otherwise.
    """
    try:
        statements = sqlparse.parse(sql)
        if not statements or len(statements) == 0:
            return False
        stmt = statements[0]
        return stmt.get_type() == "SELECT"
    except Exception:
        return False

def add_limit_sql(sql: str, limit: int) -> str:
    """
    Add a LIMIT clause to the given SQL statement. If a LIMIT clause already exists, it will be replaced.

    Args:
        sql (str): The SQL statement to add or update the LIMIT clause.
        limit (int): The limit value to set.

    Returns:
        str: The SQL statement with the LIMIT clause applied.
    """
    try:
        # Parse the SQL statement
        parser = sqlglot.parse_one(sql)
        # Check if a LIMIT clause exists
        check = parser.args.get("limit")
        if not check:
            parser = parser.limit(limit)
        modified_sql = parser.sql()
        return modified_sql
    except Exception:
        return sql
