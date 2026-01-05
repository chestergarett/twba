"""
Query Editor module for TWBA Dashboard.
Contains validation and callbacks for the SQL query editor tab.
"""

from typing import Tuple
import re

import dash
from dash import Input, Output, State, callback, html
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from supabase import Client

# These will be injected from app.py
supabase: Client | None = None
db_engine = None


def init_query_editor(supabase_client: Client, db_engine_instance) -> None:
    """Initialize module-level clients used by query editor callbacks."""
    global supabase, db_engine
    supabase = supabase_client
    db_engine = db_engine_instance


def validate_select_query(query: str) -> Tuple[bool, str]:
    """Validate that the query is a SELECT statement only."""
    # Remove comments and normalize whitespace
    query_clean = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)
    query_clean = re.sub(r"/\*.*?\*/", "", query_clean, flags=re.DOTALL)
    query_clean = " ".join(query_clean.split())

    # Check if query starts with SELECT (case insensitive)
    if not query_clean.strip().upper().startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    # Block dangerous keywords
    dangerous_keywords = [
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
    ]
    query_upper = query_clean.upper()
    for keyword in dangerous_keywords:
        if f" {keyword} " in query_upper or query_upper.startswith(keyword + " "):
            return False, f"Query contains forbidden keyword: {keyword}"

    return True, ""


@callback(
    Output("transactions-preview", "children"),
    Input("load-transactions-preview", "n_clicks"),
    prevent_initial_call=True,
)
def load_transactions_preview(n_clicks):
    """Load preview of twba_transactions table."""
    if not n_clicks:
        return ""

    try:
        # Load first 100 rows
        assert supabase is not None, "Supabase client is not initialized"
        response = supabase.table("twba_transactions").select("*").limit(100).execute()
        df = pd.DataFrame(response.data)

        if df.empty:
            return html.Div("No data available", className="text-muted")

        # Create table
        return dbc.Table.from_dataframe(
            df.head(5),  # Show first 5 rows in preview
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm",
        )
    except Exception as e:  # pragma: no cover - defensive
        return dbc.Alert(f"Error loading preview: {str(e)}", color="danger")


@callback(
    Output("items-preview", "children"),
    Input("load-items-preview", "n_clicks"),
    prevent_initial_call=True,
)
def load_items_preview(n_clicks):
    """Load preview of twba_items table."""
    if not n_clicks:
        return ""

    try:
        # Load first 100 rows
        assert supabase is not None, "Supabase client is not initialized"
        response = supabase.table("twba_items").select("*").limit(100).execute()
        df = pd.DataFrame(response.data)

        if df.empty:
            return html.Div("No data available", className="text-muted")

        # Create table
        return dbc.Table.from_dataframe(
            df.head(5),  # Show first 5 rows in preview
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm",
        )
    except Exception as e:  # pragma: no cover - defensive
        return dbc.Alert(f"Error loading preview: {str(e)}", color="danger")


@callback(
    Output("query-results", "children"),
    Output("sql-query-input", "value", allow_duplicate=True),
    Input("execute-query-btn", "n_clicks"),
    Input("clear-query-btn", "n_clicks"),
    State("sql-query-input", "value"),
    prevent_initial_call=True,
)
def execute_query(execute_clicks, clear_clicks, query_text):
    """Execute SQL query and display results."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return "", dash.no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Handle clear button
    if trigger_id == "clear-query-btn":
        return "", ""

    # Handle execute button
    if trigger_id == "execute-query-btn":
        if not query_text or not query_text.strip():
            return dbc.Alert("Please enter a query.", color="warning"), dash.no_update

        # Validate query
        is_valid, error_msg = validate_select_query(query_text)
        if not is_valid:
            return dbc.Alert(error_msg, color="danger"), dash.no_update

        try:
            # Try to execute using database engine if available
            if db_engine is not None:
                with db_engine.connect() as conn:
                    result = conn.execute(text(query_text))
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
            else:
                # Fallback: Try to parse simple queries and use Supabase REST API
                query_lower = query_text.lower().strip()

                # Handle simple SELECT * FROM table LIMIT n queries
                if query_lower.startswith("select * from"):
                    # Extract table name
                    match = re.search(r"from\s+(\w+)", query_lower)
                    if match:
                        table_name = match.group(1)
                        # Extract LIMIT if present
                        limit_match = re.search(r"limit\s+(\d+)", query_lower)
                        limit = int(limit_match.group(1)) if limit_match else 1000

                        assert supabase is not None, "Supabase client is not initialized"
                        response = supabase.table(table_name).select("*").limit(limit).execute()
                        df = pd.DataFrame(response.data)
                    else:
                        return (
                            dbc.Alert(
                                "Complex queries require database connection. Please set DB_CONNECTION_STRING in .env file.",
                                color="warning",
                            ),
                            dash.no_update,
                        )
                else:
                    return (
                        dbc.Alert(
                            "Complex queries require database connection. Please set DB_CONNECTION_STRING in .env file.",
                            color="warning",
                        ),
                        dash.no_update,
                    )

            if df.empty:
                return dbc.Alert("Query executed successfully but returned no results.", color="info"), dash.no_update

            # Create results table
            results_table = dbc.Table.from_dataframe(
                df,
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
                className="table-sm",
            )

            # Create summary
            summary = html.Div(
                [
                    dbc.Alert(
                        f"Query executed successfully. Returned {len(df)} row(s) with {len(df.columns)} column(s).",
                        color="success",
                        className="mb-3",
                    ),
                    results_table,
                ]
            )

            return summary, dash.no_update

        except SQLAlchemyError as e:  # pragma: no cover - defensive
            return dbc.Alert(f"Database error: {str(e)}", color="danger"), dash.no_update
        except Exception as e:  # pragma: no cover - defensive
            return dbc.Alert(f"Error executing query: {str(e)}", color="danger"), dash.no_update

    return "", dash.no_update
