import sqlparse
import sqlglot
import re


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

def extract_limit_from_query(sql: str) -> int | None:
    """
    Extract LIMIT value from SQL query if it exists.

    Args:
        sql (str): The SQL statement.

    Returns:
        int | None: The LIMIT value if exists, None otherwise.
    """
    try:
        parser = sqlglot.parse_one(sql)
        limit_expr = parser.args.get("limit")
        if limit_expr:
            # Try different ways to get the limit value
            limit_value = None

            # Method 1: Direct value access
            if hasattr(limit_expr, 'this'):
                limit_value = limit_expr.this
            elif hasattr(limit_expr, 'expression'):
                limit_value = limit_expr.expression
            elif hasattr(limit_expr, 'value'):
                limit_value = limit_expr.value

            # If we have a value, try to convert to int
            if limit_value is not None:
                try:
                    # Convert to string first, then to int
                    value_str = str(limit_value).strip()
                    # Remove any quotes or parentheses
                    value_str = value_str.strip("'\"()")
                    return int(value_str)
                except (ValueError, TypeError, AttributeError):
                    pass

            # Method 2: Try to get SQL representation and parse
            try:
                limit_sql = limit_expr.sql()
                import re
                match = re.search(r'(\d+)', limit_sql)
                if match:
                    return int(match.group(1))
            except Exception:
                pass

        return None
    except Exception:
        # Fallback: try regex extraction
        import re
        match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, TypeError):
                return None
        return None


def add_limit_sql(sql: str, request_limit: int) -> str:
    """
    Add or update LIMIT clause in SQL query with smart limit handling:
    - If query has LIMIT < 1000: keep the query limit (user specified in query)
    - If query has LIMIT >= 1000: replace with 1000
    - If query has no LIMIT: use request_limit (capped at 1000)

    Logic:
    - If request_limit < 1000: use request_limit when no LIMIT in query
    - If request_limit >= 1000: use 1000 as default when no LIMIT in query
    - Always respect query LIMIT if it's < 1000

    Args:
        sql (str): The SQL statement to add or update the LIMIT clause.
        request_limit (int): The limit value from request.

    Returns:
        str: The SQL statement with the LIMIT clause applied.
    """
    try:
        # Cap request_limit at 1000
        max_limit = min(request_limit, 1000)

        # Parse the SQL statement
        parser = sqlglot.parse_one(sql)

        # Check if a LIMIT clause exists
        existing_limit = extract_limit_from_query(sql)

        if existing_limit is not None:
            # Query already has LIMIT
            if existing_limit < 1000:
                # Keep the query limit (user specified it in the query)
                final_limit = existing_limit
            else:
                # Query limit >= 1000, replace with 1000
                final_limit = 1000
        else:
            # No LIMIT in query, use request limit (capped at 1000)
            final_limit = max_limit

        # Apply the limit
        parser = parser.limit(final_limit)
        modified_sql = parser.sql()
        return modified_sql
    except Exception:
        # Fallback: if parsing fails, try simple regex replacement

        sql_upper = sql.upper()
        max_limit = min(request_limit, 1000)

        # Check if LIMIT exists
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit < 1000:
                # Keep existing limit
                return sql
            else:
                # Replace with 1000
                pattern = r'LIMIT\s+\d+'
                replacement = 'LIMIT 1000'
                return re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        else:
            # No LIMIT, add it
            final_limit = min(request_limit, 1000)
            return f"{sql.rstrip(';')} LIMIT {final_limit}"


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
