"""
Ask AI module for TWBA Dashboard.
Encapsulates helpers and callback for the Ask AI tab.
"""

from typing import Tuple, Optional
import os
import re

import dash
from dash import Input, Output, State, callback, html
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# These will be injected from app.py
openai_client = None
db_engine = None


def init_ask_ai(openai_client_instance, db_engine_instance) -> None:
    """Initialize module-level clients used by Ask AI."""
    global openai_client, db_engine
    openai_client = openai_client_instance
    db_engine = db_engine_instance


def get_database_schema() -> str:
    """Get the database schema information for OpenAI prompt."""
    schema = """Database Schema:

Table: twba_transactions
Columns:
- InteractionID (text): Unique transaction identifier
- TransactionDate (timestamptz): Date and time of transaction
- txn_date (date): Date of transaction
- txn_month (timestamp): Month of transaction
- txn_weekday (text): Day of week (Monday, Tuesday, etc.)
- txn_hour (integer): Hour of transaction (0-23)
- timeofday_segment (text): Time segment (Morning, Afternoon, Evening, Late Night)
- Gender (text): Original gender value
- gender_clean (text): Cleaned gender value (Male, Female, Unknown)
- Age (integer): Customer age
- age_bucket (text): Age group (18-24, 25-34, 35-44, 45-54, 55+)
- payment_method (text): Payment method (cash, card, etc.)
- basket_total (numeric): Total transaction amount

Table: twba_items
Columns:
- InteractionID (text): Unique transaction identifier (links to twba_transactions)
- TransactionDate (timestamptz): Date and time of transaction
- gender_clean (text): Cleaned gender value
- age_bucket (text): Age group
- Age (integer): Customer age
- transactionContext_paymentMethod_voice (text): Payment method
- totals_totalAmount_voice (numeric): Total transaction amount
- totalPrice (numeric): Total price for this item
- unitPrice (numeric): Unit price of the item
- quantity (numeric): Quantity purchased
- category (text): Product category
- brandName (text): Brand name
- productName (text): Product name
- sku (text): SKU code
- timeofday_segment (text): Time segment
- txn_weekday (text): Day of week
- round_price_flag (text): Flag for rounded prices

Notes:
- Use JOIN on InteractionID to link twba_transactions and twba_items
- All monetary values are in numeric/decimal format
- Dates should be handled with proper PostgreSQL date functions
- Always use LIMIT for large result sets
"""
    return schema


def execute_sql_directly(sql_query: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Execute SQL query directly using database connection."""
    try:
        # Try to create a database connection if db_engine is not available
        engine = db_engine
        if not engine:
            # Try to construct connection string from environment variables
            DB_HOST = os.getenv("DB_HOST")
            DB_PORT = os.getenv("DB_PORT")
            DB_NAME = os.getenv("DB_NAME")
            DB_USER = os.getenv("DB_USER")
            DB_PASSWORD = os.getenv("DB_PASSWORD")

            # Validate all required fields are present
            missing_fields = []
            if not DB_HOST:
                missing_fields.append("DB_HOST")
            if not DB_PORT:
                missing_fields.append("DB_PORT")
            if not DB_NAME:
                missing_fields.append("DB_NAME")
            if not DB_USER:
                missing_fields.append("DB_USER")
            if not DB_PASSWORD:
                missing_fields.append("DB_PASSWORD")

            if missing_fields:
                return (
                    pd.DataFrame(),
                    "Database connection not available. Missing environment variables: "
                    + ", ".join(missing_fields)
                    + ". Please set these in your .env file.",
                )

            connection_string = (
                f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
            )
            engine = create_engine(
                connection_string, pool_pre_ping=True, connect_args={"sslmode": "require"}
            )

        # Execute the SQL query directly
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df, None

    except SQLAlchemyError as e:  # pragma: no cover - defensive
        return pd.DataFrame(), f"Database error: {str(e)}"
    except Exception as e:  # pragma: no cover - defensive
        return pd.DataFrame(), f"Error executing query: {str(e)}"


def generate_sql_from_question(question: str) -> Tuple[str, str]:
    """Generate SQL query from natural language question using OpenAI."""
    if not openai_client:
        return "", "OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file."

    schema = get_database_schema()

    prompt = f"""You are a SQL expert. Given a database schema and a natural language question, generate a PostgreSQL SELECT query.

{schema}

Question: {question}

Instructions:
1. Generate ONLY a valid PostgreSQL SELECT query
2. Do not include any explanations, markdown, or code blocks
3. Always include a reasonable LIMIT clause (e.g., LIMIT 100) unless the question specifically asks for all records
4. Use proper JOINs when querying multiple tables
5. Use appropriate aggregate functions (COUNT, SUM, AVG, etc.) when needed
6. Format dates properly using PostgreSQL date functions
7. IMPORTANT: For PostgreSQL column names that contain uppercase letters, wrap them in double quotes (e.g., "InteractionID", "brandName")
8. IMPORTANT: When filtering by specific values in WHERE clauses, always use LOWER() function for case-insensitive matching (e.g., WHERE LOWER(i."brandName") = LOWER('Surf'))
9. Return ONLY the SQL query, nothing else

SQL Query:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a SQL expert that generates PostgreSQL queries from natural language questions. "
                    "Always wrap uppercase column names in double quotes (e.g., \"InteractionID\") and use LOWER() "
                    "function for case-insensitive value comparisons in WHERE clauses (e.g., WHERE LOWER(column) = LOWER('value')).",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )

        sql_query = response.choices[0].message.content.strip()

        # Clean up the SQL query (remove markdown code blocks if present)
        sql_query = re.sub(r"```sql\s*", "", sql_query)
        sql_query = re.sub(r"```\s*", "", sql_query)
        sql_query = sql_query.strip()

        return sql_query, ""
    except Exception as e:  # pragma: no cover - defensive
        return "", f"Error generating SQL: {str(e)}"


# We import validate_select_query from the query_editor module to avoid duplication
from charts.query_editor import validate_select_query  # type: ignore  # circular import handled at runtime


@callback(
    Output("ai-results", "children"),
    Output("ai-question-input", "value", allow_duplicate=True),
    Input("ask-ai-btn", "n_clicks"),
    Input("clear-ai-btn", "n_clicks"),
    State("ai-question-input", "value"),
    prevent_initial_call=True,
)
def handle_ai_query(ask_clicks, clear_clicks, question):
    """Handle AI question and generate SQL query."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return "", dash.no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Handle clear button
    if trigger_id == "clear-ai-btn":
        return "", ""

    # Handle ask button
    if trigger_id == "ask-ai-btn":
        if not question or not question.strip():
            return dbc.Alert("Please enter a question.", color="warning"), dash.no_update

        # Show loading state (not strictly necessary as dbc.Alert is static, but kept for UX)
        loading_alert = dbc.Alert(
            [
                html.Div(
                    [
                        html.Span([dbc.Spinner(size="sm")], className="me-2"),
                        "Generating SQL query and fetching results...",
                    ]
                )
            ],
            color="info",
        )

        # Generate SQL from question
        sql_query, error = generate_sql_from_question(question)

        if error:
            return dbc.Alert(f"Error: {error}", color="danger"), dash.no_update

        if not sql_query:
            return (
                dbc.Alert("Failed to generate SQL query. Please try rephrasing your question.", color="warning"),
                dash.no_update,
            )

        # Validate the generated SQL
        is_valid, validation_error = validate_select_query(sql_query)
        if not is_valid:
            return (
                dbc.Alert(
                    [
                        html.H5("Generated SQL Query (Invalid):", className="mb-2"),
                        html.Pre(
                            sql_query,
                            style={
                                "backgroundColor": "#f8f9fa",
                                "padding": "10px",
                                "borderRadius": "5px",
                                "overflow": "auto",
                            },
                        ),
                        html.P(f"Validation Error: {validation_error}", className="mt-2 text-danger"),
                    ],
                    color="danger",
                ),
                dash.no_update,
            )

        # Execute the SQL query directly
        df, error_msg = execute_sql_directly(sql_query)
        if error_msg:
            return (
                dbc.Alert(
                    [
                        html.H5("Generated SQL Query:", className="mb-2"),
                        html.Pre(
                            sql_query,
                            style={
                                "backgroundColor": "#f8f9fa",
                                "padding": "10px",
                                "borderRadius": "5px",
                                "overflow": "auto",
                            },
                        ),
                        html.P(f"Error: {error_msg}", className="mt-2 text-danger"),
                    ],
                    color="danger",
                ),
                dash.no_update,
            )

        # Process and display results
        if df.empty:
            return (
                html.Div(
                    [
                        dbc.Alert(
                            "Query executed successfully but returned no results.",
                            color="info",
                            className="mb-3",
                        ),
                        html.H5("Generated SQL Query:", className="mb-2"),
                        html.Pre(
                            sql_query,
                            style={
                                "backgroundColor": "#f8f9fa",
                                "padding": "10px",
                                "borderRadius": "5px",
                                "overflow": "auto",
                                "fontSize": "12px",
                            },
                        ),
                    ]
                ),
                dash.no_update,
            )

        # Create results table
        results_table = dbc.Table.from_dataframe(
            df,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm",
        )

        # Create summary with SQL query and results
        summary = html.Div(
            [
                dbc.Alert(
                    [
                        html.H5("✓ Query executed successfully!", className="mb-2"),
                        html.P(
                            f"Returned {len(df)} row(s) with {len(df.columns)} column(s).",
                            className="mb-0",
                        ),
                    ],
                    color="success",
                    className="mb-3",
                ),
                html.H5("Generated SQL Query:", className="mb-2"),
                html.Pre(
                    sql_query,
                    style={
                        "backgroundColor": "#f8f9fa",
                        "padding": "15px",
                        "borderRadius": "5px",
                        "overflow": "auto",
                        "fontSize": "13px",
                        "border": "1px solid #dee2e6",
                    },
                ),
                html.H5("Results:", className="mb-2 mt-4"),
                results_table,
            ]
        )

        return summary, dash.no_update

    return "", dash.no_update
