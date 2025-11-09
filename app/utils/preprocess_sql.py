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


def is_schema_modifying_query(sql: str) -> bool:
    """
    Check if the SQL query modifies table schema (ALTER TABLE, RENAME, etc.)

    Args:
        sql (str): The SQL statement to check.

    Returns:
        bool: True if the statement modifies schema, False otherwise.
    """
    try:
        sql_upper = sql.upper().strip()
        # Check for schema-modifying keywords
        schema_modifying_keywords = [
            "ALTER TABLE",
            "RENAME COLUMN",
            "RENAME TO",
            "ADD COLUMN",
            "DROP COLUMN",
            "MODIFY COLUMN",
            "CHANGE COLUMN",
            "CREATE TABLE",
            "DROP TABLE",
            "TRUNCATE TABLE"
        ]

        # Check if query contains any schema-modifying keywords
        for keyword in schema_modifying_keywords:
            if keyword in sql_upper:
                return True

        return False
    except Exception:
        return False


def extract_table_names_from_query(sql: str) -> list:
    """
    Extract table names from SQL query (for SELECT, INSERT, UPDATE, DELETE, ALTER, etc.)

    Args:
        sql (str): The SQL statement.

    Returns:
        list: List of table names mentioned in the query.
    """
    try:
        table_names = []
        sql_upper = sql.upper()

        # Try to parse with sqlglot for better table extraction
        try:
            parsed = sqlglot.parse_one(sql)
            for table in parsed.find_all(sqlglot.expressions.Table):
                table_name = table.name
                if table_name:
                    table_names.append(table_name)
        except Exception:
            # Fallback: simple regex-based extraction
            import re
            # Match FROM, JOIN, INTO, UPDATE, ALTER TABLE patterns
            patterns = [
                r'FROM\s+["\']?(\w+)["\']?',
                r'JOIN\s+["\']?(\w+)["\']?',
                r'INTO\s+["\']?(\w+)["\']?',
                r'UPDATE\s+["\']?(\w+)["\']?',
                r'ALTER\s+TABLE\s+["\']?(\w+)["\']?',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, sql_upper, re.IGNORECASE)
                table_names.extend(matches)

        # Remove duplicates and return
        return list(set(table_names))
    except Exception:
        return []
