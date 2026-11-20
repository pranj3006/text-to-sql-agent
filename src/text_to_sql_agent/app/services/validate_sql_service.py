
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient
import sqlglot
from sqlglot import exp
from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient

MAX_ROWS = 100

def validate_sql(
    sql: str,
    *,
    dialect: str = "postgres",
    allowed_tables: frozenset[str] | None = None,
    schema: str | None = None,
    catalog: str | None = None,
) -> str:
    """Parse, authorize, and normalize one read-only query.

    Raises ``ValueError`` when the SQL is malformed, changes data, calls a
    prohibited function, or references an object outside the supplied allowlist.
    """
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except sqlglot.errors.ParseError as exc:
        raise ValueError("The generated SQL could not be parsed.") from exc

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValueError("Only read-only SELECT queries are allowed.")

    blocked_functions = {
        "PG_SLEEP",
        "SET_CONFIG",
        "LO_IMPORT",
        "LO_EXPORT",
        "DBLINK",
        "DBLINK_EXEC",
    }
    # SQLGlot represents some dialect functions as anonymous function nodes,
    # so inspect both anonymous names and typed function names.
    for function in tree.find_all(exp.Func):
        function_name = (
            function.name if isinstance(function, exp.Anonymous) else function.sql_name()
        )
        if function_name.upper() in blocked_functions:
            raise ValueError("The query contains a prohibited function.")

    if allowed_tables is not None:
        if schema is None:
            raise ValueError("A target schema is required for table allowlisting.")
        common_table_expressions = {
            cte.alias_or_name for cte in tree.find_all(exp.CTE)
        }
        for table in tree.find_all(exp.Table):
            if (
                table.name in common_table_expressions
                and not table.db
                and not table.catalog
            ):
                continue
            if table.name not in allowed_tables:
                raise ValueError(
                    f"The query references an unavailable table or view: {table.name}."
                )
            if table.db and (schema is None or table.db != schema):
                raise ValueError("The query references an unavailable schema.")
            if table.catalog and (catalog is None or table.catalog != catalog):
                raise ValueError("The query references an unavailable database.")
            if not table.db:
                table.set("db", exp.to_identifier(schema, quoted=True))

    _apply_row_limit(tree)
    return tree.sql(dialect=dialect)

def _apply_row_limit(tree: exp.Expression) -> None:
    """Preserve a smaller row limit or append the configured maximum limit."""
    # Capping here provides a deterministic resource limit even if model output
    # is valid SQL but omits or exceeds the application's row budget.
    limit = tree.args.get("limit")
    if limit is not None:
        expression = limit.expression
        if (
            isinstance(expression, exp.Literal)
            and expression.is_number
            and expression.this.isdecimal()
            and int(expression.this) <= MAX_ROWS
        ):
            return
        return tree.set(
            "limit",
            exp.Limit(expression=exp.Literal.number(MAX_ROWS)),
        )
    tree.set("limit", exp.Limit(expression=exp.Literal.number(MAX_ROWS)))

async def validate_sql_tool_call(sql: str,
    client: MCPClient):

    validated_sql_result = await client.call_tool(
        "validate_sql_tool",
        {
            "sql": sql,            
        },
    )
    is_error = getattr(validated_sql_result, "isError", getattr(validated_sql_result, "is_error", False))
    if is_error:
        error = validated_sql_result.content[0].text
        return {
            "sql": sql,
            "isError": True,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }
    else:
        validation_result = validated_sql_result.structured_content  
        if not validation_result["valid"]:
            error = validation_result["error"]
            return {
            "sql": sql,
            "isError": True,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }

    validation_result = validated_sql_result.structured_content    
    
    validated_sql = validation_result["normalized_sql"]

    return {
            "isError": False,
            "sql": sql,
            "validated_sql": validated_sql,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }