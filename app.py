"""
TWBA Analytics Dashboard
A Dash application for visualizing transaction and product analytics
with data sourced from Supabase.

Setup:
1. Install dependencies: pip install -r requirements.txt
2. Set environment variables in .env:
   - SUPABASE_URL=https://rlvvitxazrojipjacogn.supabase.co
   - SUPABASE_KEY=your_supabase_key
3. Run: python app.py
4. Open browser to http://localhost:8050
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import dash
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAI
from charts.documentation import create_documentation_tab

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rlvvitxazrojipjacogn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set. Ask AI tab will not work.")
    openai_client = None
else:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Database connection for query editor
# Get database connection string from environment or construct from Supabase URL
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
if not DB_CONNECTION_STRING:
    # Try to construct from individual components
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    # Only create connection string if all required fields are present
    if DB_HOST and DB_PORT and DB_NAME and DB_USER and DB_PASSWORD:
        DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
    else:
        DB_CONNECTION_STRING = None

# Create SQLAlchemy engine if connection string is available
db_engine = None
if DB_CONNECTION_STRING:
    try:
        db_engine = create_engine(DB_CONNECTION_STRING, pool_pre_ping=True, connect_args={"sslmode": "require"})
    except Exception as e:
        print(f"Warning: Could not create database engine: {e}")
        print("Query Editor will use Supabase REST API as fallback")

# Authentication credentials
AUTH_USERNAME = os.getenv("USERNAME", "twba-admin")
AUTH_PASSWORD = os.getenv("PASSWORD", "e1e87780-66e9-42f4-beb9-a7aa7f371983")

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Add custom CSS for dark mode and styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Dark Mode Base Styles - Material-ish */
            body {
                background-color: #0b0c0f !important;
                color: #e5e7eb !important;
                font-family: "Inter", -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                letter-spacing: 0.01em;
            }
            .container-fluid { background-color: #0b0c0f; }
            
            /* Headings */
            h1, h2, h3, h4, h5, h6 {
                color: #d4af37 !important;
                font-weight: 700;
                letter-spacing: 0.01em;
            }
            
            /* Global layout / spacing */
            .row { margin-bottom: 1.4rem !important; }
            .col, [class*="col-"] { margin-bottom: 1rem !important; max-height: none !important; overflow: visible !important; }
            .card-body { background: transparent !important; height: auto !important; overflow: visible !important; padding: 1rem 1rem 1.25rem 1rem !important; }
            
            /* Cards - sleek surfaces */
            .card, .dbc-card {
                background: #111417 !important;
                border: 1px solid #1e2126 !important;
                border-radius: 12px !important;
                box-shadow: 0 12px 28px rgba(0, 0, 0, 0.32) !important;
                color: #e5e7eb !important;
                margin-bottom: 1.6rem !important;
                margin-top: 0.6rem !important;
                padding: 0.8rem !important;
                transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, background-color 140ms ease;
            }
            .card:hover, .dbc-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 18px 32px rgba(0, 0, 0, 0.42) !important;
                border-color: #2a2f37 !important;
                background: #12171c !important;
            }
            
            /* Graph containers */
            .dash-graph { position: relative !important; height: auto !important; max-height: 600px !important; overflow: hidden !important; }
            .js-plotly-plot {
                background-color: #13171d !important;
                border-radius: 12px;
                padding: 10px;
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4) !important;
                border: 1px solid #1f242c;
                height: 100% !important;
                max-height: 100% !important;
            }
            .js-plotly-plot .plotly { height: 100% !important; max-height: 100% !important; }
            .js-plotly-plot .plotly .main-svg { max-height: 100% !important; }
            
            /* Tabs (dcc) */
            .tab { background-color: #1a1d22 !important; color: #e0e0e0 !important; border: 1px solid #2a2f37 !important; }
            .tab--selected { background-color: #161a1f !important; color: #d4af37 !important; border-bottom: 2px solid #d4af37 !important; }

            /* dbc Tabs in navbar */
            .twba-tabs .nav-link {
                color: #e0e0e0 !important;
                background-color: #0f1014 !important;
                border-color: #2a2f37 !important;
                border-radius: 10px 10px 0 0;
                transition: background-color 140ms ease, color 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
                box-shadow: inset 0 -1px 0 #2a2f37;
            }
            .twba-tabs .nav-link:hover {
                background-color: #14171d !important;
                color: #f2d57c !important;
            }
            .twba-tabs .nav-link.active {
                color: #d4af37 !important;
                background-color: #1a1e24 !important;
                border-color: #d4af37 #2a2f37 #1a1e24 !important;
                box-shadow: inset 0 -2px 0 #d4af37;
            }
            
            /* Buttons */
            .btn-primary {
                background: #d4af37 !important;
                border: 1px solid #d4af37 !important;
                color: #0a0a0a !important;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(212, 175, 55, 0.35) !important;
                border-radius: 10px !important;
            }
            .btn-primary:hover {
                background: #e0c26b !important;
                border-color: #e0c26b !important;
                box-shadow: 0 6px 16px rgba(224, 194, 107, 0.4) !important;
            }
            .btn-secondary {
                background: #1f232b !important;
                border: 1px solid #2f3540 !important;
                color: #e0e0e0 !important;
                border-radius: 10px !important;
            }
            .btn-secondary:hover {
                background: #2a303a !important;
                border-color: #3a4250 !important;
            }
            .btn-warning {
                background: #d4af37 !important;
                border: 1px solid #d4af37 !important;
                color: #0a0a0a !important;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(212, 175, 55, 0.35) !important;
                border-radius: 10px !important;
            }
            
            /* Inputs and Dropdowns */
            .form-control, .form-select, .DateInput_input, .DateInput_input_1 {
                background-color: #12151a !important;
                border: 1px solid #252a32 !important;
                color: #e0e0e0 !important;
                border-radius: 10px !important;
                transition: border-color 140ms ease, box-shadow 140ms ease;
            }
            .form-control:focus, .form-select:focus {
                background-color: #12151a !important;
                border-color: #d4af37 !important;
                color: #e0e0e0 !important;
                box-shadow: 0 0 0 0.2rem rgba(212, 175, 55, 0.2) !important;
            }
            
            /* Dropdown menus */
            .Select-menu-outer {
                background-color: #12151a !important;
                border: 1px solid #252a32 !important;
            }
            .Select-option {
                background-color: #12151a !important;
                color: #e0e0e0 !important;
            }
            .Select-option:hover { background-color: #1a1f26 !important; }
            .Select-option.is-selected { background-color: #d4af37 !important; color: #000 !important; }
            
            /* Labels */
            .filter-label, label {
                font-weight: 500;
                margin-bottom: 4px;
                color: #d4af37 !important;
            }
            
            /* Tables */
            table {
                background-color: #1a1a1a !important;
                color: #e0e0e0 !important;
            }
            
            .table {
                background-color: #1a1a1a !important;
            }
            
            .table thead th {
                background-color: #2a2a2a !important;
                color: #d4af37 !important;
                border-color: #3a3a3a !important;
            }
            
            .table tbody tr {
                border-color: #3a3a3a !important;
            }
            
            .table tbody tr:hover {
                background-color: #2a2a2a !important;
            }
            
            /* Alerts */
            .alert {
                border-radius: 8px;
                border: 1px solid;
            }
            
            .alert-danger {
                background-color: #2a1a1a !important;
                border-color: #8b0000 !important;
                color: #ff6b6b !important;
            }
            
            /* Login page specific */
            .login-card {
                background: linear-gradient(145deg, #1a1a1a, #0f0f0f) !important;
                border: 1px solid #2a2a2a !important;
                box-shadow: 
                    0 12px 24px rgba(0, 0, 0, 0.6),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
            }
            
            /* Ensure DatePickerRange and Dropdowns are full width */
            .DateInput_input, .DateInput_input_1 {
                width: 100% !important;
            }
            
            /* Consistent spacing for filter containers */
            .filter-container {
                margin-bottom: 4px;
            }
            
            /* Responsive adjustments */
            @media (max-width: 576px) {
                .filter-col {
                    margin-bottom: 1rem;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''
app.title = "Project Scout Analytics Dashboard"

# Helper function to load data from Supabase
def load_transactions() -> pd.DataFrame:
    """Load transaction data from Supabase."""
    response = supabase.table("twba_transactions").select("*").execute()
    df = pd.DataFrame(response.data)
    
    # Convert date columns
    if "TransactionDate" in df.columns:
        df["TransactionDate"] = pd.to_datetime(df["TransactionDate"])
    if "txn_date" in df.columns:
        df["txn_date"] = pd.to_datetime(df["txn_date"])
    if "txn_month" in df.columns:
        df["txn_month"] = pd.to_datetime(df["txn_month"])
    
    return df

def load_items() -> pd.DataFrame:
    """Load item-level data from Supabase."""
    response = supabase.table("twba_items").select("*").execute()
    df = pd.DataFrame(response.data)
    
    # Convert date columns
    if "TransactionDate" in df.columns:
        df["TransactionDate"] = pd.to_datetime(df["TransactionDate"])
    
    # Convert numeric columns
    for col in ["totalPrice", "unitPrice", "quantity", "Age"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df

# Load data once at startup
transactions_df = load_transactions()
items_df = load_items()

# Merge for convenience
items_df = items_df.merge(
    transactions_df[["InteractionID", "basket_total", "payment_method"]],
    on="InteractionID",
    how="left"
)

# Helper function to filter data
def filter_data(
    df: pd.DataFrame,
    date_range: Optional[list] = None,
    gender: Optional[list] = None,
    age_bucket: Optional[list] = None,
    payment_method: Optional[list] = None,
    month_year: Optional[list] = None,
    weekday_weekend: Optional[str] = None,
    category: Optional[list] = None,
) -> pd.DataFrame:
    """Apply filters to dataframe."""
    filtered = df.copy()
    
    # Handle date range filtering
    if date_range and len(date_range) == 2 and date_range[0] is not None and date_range[1] is not None:
        if "TransactionDate" in filtered.columns:
            try:
                start_date = pd.to_datetime(date_range[0])
                end_date = pd.to_datetime(date_range[1])
                # Ensure end_date includes the full day (end of day)
                end_date = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                
                # Normalize timezones if needed
                if filtered["TransactionDate"].dt.tz is not None:
                    # If TransactionDate is timezone-aware, make start/end timezone-aware too
                    if start_date.tz is None:
                        start_date = start_date.tz_localize('UTC')
                    if end_date.tz is None:
                        end_date = end_date.tz_localize('UTC')
                elif start_date.tz is not None:
                    # If TransactionDate is timezone-naive but dates are timezone-aware, remove timezone
                    start_date = start_date.tz_localize(None) if start_date.tz else start_date
                    end_date = end_date.tz_localize(None) if end_date.tz else end_date
                
                filtered = filtered[
                    (filtered["TransactionDate"] >= start_date) &
                    (filtered["TransactionDate"] <= end_date)
                ]
            except Exception as e:
                print(f"Error filtering dates: {e}")
                import traceback
                traceback.print_exc()
                # If date parsing fails, don't filter by date
    
    if gender:
        if "gender_clean" in filtered.columns:
            filtered = filtered[filtered["gender_clean"].isin(gender)]
    
    if age_bucket:
        if "age_bucket" in filtered.columns:
            filtered = filtered[filtered["age_bucket"].isin(age_bucket)]
    
    if payment_method:
        if "payment_method" in filtered.columns:
            filtered = filtered[filtered["payment_method"].isin(payment_method)]
    
    # Handle month/year filter
    if month_year and len(month_year) > 0:
        if "TransactionDate" in filtered.columns:
            filtered["year_month"] = filtered["TransactionDate"].dt.to_period("M")
            # Convert month_year values (format: "YYYY-MM") to Period objects
            month_year_periods = [pd.Period(f"{m}-01") if len(m) == 7 else pd.Period(m) for m in month_year]
            filtered = filtered[filtered["year_month"].isin(month_year_periods)]
            filtered = filtered.drop(columns=["year_month"], errors="ignore")
    
    # Handle weekday/weekend filter
    if weekday_weekend:
        if "TransactionDate" in filtered.columns:
            filtered["weekday_type"] = filtered["TransactionDate"].dt.dayofweek.apply(
                lambda x: "Weekend" if x >= 5 else "Weekday"
            )
            filtered = filtered[filtered["weekday_type"] == weekday_weekend]
            filtered = filtered.drop(columns=["weekday_type"], errors="ignore")
    
    # Handle category filter
    if category:
        if "category" in filtered.columns:
            # Direct category filter for items_df
            filtered = filtered[filtered["category"].isin(category)]
        elif "InteractionID" in filtered.columns:
            # For transactions_df, filter by category through items_df
            # Get InteractionIDs that have items in the selected categories
            category_interaction_ids = items_df[items_df["category"].isin(category)]["InteractionID"].unique()
            filtered = filtered[filtered["InteractionID"].isin(category_interaction_ids)]
    
    return filtered

# Chart layout helpers for dark mode
def apply_dark_layout(fig, title, xaxis_title="", yaxis_title="", yaxis2_title="", **kwargs):
    """Apply dark mode layout to a figure."""
    # Start with base dark mode settings
    dark_layout = dict(
        title=dict(text=title, font=dict(color="#d4af37", size=16)),
        paper_bgcolor="#1a1a1a",
        plot_bgcolor="#1a1a1a",
        font=dict(color="#e0e0e0", size=12),
        hovermode="x unified",
    )
    
    # Base axis settings
    base_xaxis = dict(
        gridcolor="#3a3a3a",
        linecolor="#4a4a4a",
        titlefont=dict(color="#d4af37"),
        tickfont=dict(color="#e0e0e0"),
    )
    if xaxis_title:
        base_xaxis["title"] = xaxis_title
    
    base_yaxis = dict(
        gridcolor="#3a3a3a",
        linecolor="#4a4a4a",
        titlefont=dict(color="#d4af37"),
        tickfont=dict(color="#e0e0e0"),
    )
    if yaxis_title:
        base_yaxis["title"] = yaxis_title
    
    # Merge axis settings from kwargs if provided
    if "xaxis" in kwargs:
        base_xaxis.update(kwargs.pop("xaxis"))
    dark_layout["xaxis"] = base_xaxis
    
    if "yaxis" in kwargs:
        base_yaxis.update(kwargs.pop("yaxis"))
    dark_layout["yaxis"] = base_yaxis
    
    if yaxis2_title or "yaxis2" in kwargs:
        base_yaxis2 = dict(
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        )
        if yaxis2_title:
            base_yaxis2["title"] = yaxis2_title
        if "yaxis2" in kwargs:
            base_yaxis2.update(kwargs.pop("yaxis2"))
        dark_layout["yaxis2"] = base_yaxis2
    
    # Base legend settings
    base_legend = dict(
        bgcolor="#1a1a1a",
        bordercolor="#3a3a3a",
        font=dict(color="#e0e0e0"),
    )
    if "legend" in kwargs:
        base_legend.update(kwargs.pop("legend"))
    dark_layout["legend"] = base_legend
    
    # Add any remaining kwargs
    dark_layout.update(kwargs)
    
    # Ensure height is always set to prevent infinite growth
    if "height" not in dark_layout:
        dark_layout["height"] = 50  # Default height (further reduced)
    
    # CRITICAL: Set autosize to False to prevent Plotly from auto-sizing
    dark_layout["autosize"] = False
    
    # Apply layout (this replaces the entire layout, not accumulates)
    fig.update_layout(**dark_layout)

# Login page component
def create_login_page(error_message=""):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1("Project Scout Analytics Dashboard", className="text-center mb-4"),
                    html.Hr(),
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Login", className="text-center mb-4"),
                            dbc.Input(
                                id="login-username",
                                type="text",
                                placeholder="Username",
                                className="mb-3"
                            ),
                            dbc.Input(
                                id="login-password",
                                type="password",
                                placeholder="Password",
                                className="mb-3"
                            ),
                            dbc.Button("Login", id="login-button", color="primary", className="w-100 mb-2"),
                            html.Div(id="login-message", children=[
                                dbc.Alert(error_message, color="danger", className="mb-0") if error_message else ""
                            ], className="text-center mt-3")
                        ])
                    ], className="shadow")
                ], style={"maxWidth": "400px", "margin": "0 auto", "paddingTop": "100px"})
                ])
            ])
        ], fluid=True)

# Store for authentication state - using session storage to persist across page refreshes
auth_store = dcc.Store(id="auth-store", data={"authenticated": False}, storage_type="session")

# Filters row below navbar
def build_filters_row():
    return dbc.Row([
        dbc.Col([
            html.Label("Date Range", className="mb-1", style={"fontWeight": "500"}),
            dcc.DatePickerRange(
                id="date-range",
                start_date=transactions_df["TransactionDate"].min() if not transactions_df.empty else datetime.now() - timedelta(days=90),
                end_date=transactions_df["TransactionDate"].max() if not transactions_df.empty else datetime.now(),
                display_format="YYYY-MM-DD",
                style={"width": "100%", "marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-date-range", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label("Month/Year", className="mb-1", style={"fontWeight": "500"}),
            dcc.Dropdown(
                id="month-year-filter",
                options=[
                    {"label": f"{dt.strftime('%B %Y')}", "value": f"{dt.year}-{dt.month:02d}"}
                    for dt in pd.date_range(
                        transactions_df["TransactionDate"].min() if not transactions_df.empty else datetime.now() - timedelta(days=365),
                        transactions_df["TransactionDate"].max() if not transactions_df.empty else datetime.now(),
                        freq="MS"
                    )
                ],
                value=None,
                multi=True,
                placeholder="All months",
                style={"marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-month-year", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label("Weekday/Weekend", className="mb-1", style={"fontWeight": "500"}),
            dcc.Dropdown(
                id="weekday-weekend-filter",
                options=[
                    {"label": "Weekday", "value": "Weekday"},
                    {"label": "Weekend", "value": "Weekend"},
                ],
                value=None,
                placeholder="All days",
                style={"marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-weekday-weekend", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label("Gender", className="mb-1", style={"fontWeight": "500"}),
            dcc.Dropdown(
                id="gender-filter",
                options=[{"label": g, "value": g} for g in transactions_df["gender_clean"].unique() if pd.notna(g)],
                value=None,
                multi=True,
                placeholder="All genders",
                style={"marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-gender", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label("Age Bucket", className="mb-1", style={"fontWeight": "500"}),
            dcc.Dropdown(
                id="age-filter",
                options=[{"label": a, "value": a} for a in sorted(transactions_df["age_bucket"].dropna().unique())],
                value=None,
                multi=True,
                placeholder="All ages",
                style={"marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-age", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label("Payment Method", className="mb-1", style={"fontWeight": "500"}),
            dcc.Dropdown(
                id="payment-filter",
                options=[{"label": p, "value": p} for p in transactions_df["payment_method"].unique() if pd.notna(p)],
                value=None,
                multi=True,
                placeholder="All methods",
                style={"marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-payment", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label("Category", className="mb-1", style={"fontWeight": "500"}),
            dcc.Dropdown(
                id="category-filter",
                options=[{"label": c, "value": c} for c in sorted(items_df["category"].dropna().unique())] if not items_df.empty and "category" in items_df.columns else [],
                value=None,
                multi=True,
                placeholder="All categories",
                style={"marginBottom": "4px"},
            ),
            dbc.Button("Reset", id="reset-category", color="secondary", size="sm", className="w-100"),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
        dbc.Col([
            html.Label(" ", className="mb-1"),
            dbc.Button("Reset All Filters", id="reset-all-filters", color="warning", className="w-100", style={"fontWeight": "600", "marginTop": "25px"}),
        ], xs=12, sm=6, md=4, lg=3, xl=3, className="mb-3"),
    ], className="mt-2")

# Main dashboard layout function
def create_dashboard_layout():
    return dbc.Container([
        # Sticky navbar
        dbc.Navbar(
            dbc.Container([
                html.Div([
                    html.Span("Project Scout Dashboard", className="navbar-brand mb-0 h4", style={"color": "#d4af37"}),
                ], style={"flex": "1"}),
                dbc.Tabs(
                    id="main-tabs",
                    active_tab="general",
                    children=[
                        dbc.Tab(label="Consumer Demographics", tab_id="general"),
                        dbc.Tab(label="Laundry", tab_id="laundry"),
                        dbc.Tab(label="Tobacco", tab_id="tobacco"),
                        dbc.Tab(label="Query Editor", tab_id="query-editor"),
                        dbc.Tab(label="Ask AI", tab_id="ask-ai"),
                        dbc.Tab(label="Documentation", tab_id="documentation"),
                    ],
                    className="flex-grow-1 twba-tabs"
                ),
                dbc.Button("Logout", id="logout-button", color="danger", size="sm", className="ms-3"),
            ], fluid=True),
            color="#0f0f0f",
            dark=True,
            fixed="top",
            className="mb-4",
            style={"boxShadow": "0 4px 8px rgba(0,0,0,0.4)"},
        ),

        html.Div(style={"height": "80px"}),  # spacer below navbar

        # Filters row
        build_filters_row(),

        # Charts/content row
        dbc.Row([
            dbc.Col([
                html.Div(id="tab-content"),
            ], xs=12)
        ], className="mt-2 mb-4"),
    ], fluid=True)

# Define app layout
app.layout = dbc.Container([
    auth_store,
    html.Div(id="page-content", children=create_login_page())
], fluid=True)

# General Analytics Tab
def create_general_tab():
    """Create content for General Analytics tab."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H3("Consumer Demographics", className="mt-4"),
            ]),
        ]),
        # Row 1: 2 charts - Gender and Age
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="gender-combined"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="age-bucket-combined"),
            ], md=6),
        ]),
        # Row 2: 1 chart - Gender MoM
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="gender-mom"),
            ]),
        ]),
        # Row 3: 2 charts - Payment and Day of Week
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="payment-combined"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="day-of-week"),
            ], md=6),
        ]),
        # Row 4: 2 charts - Weekday/Weekend and Time of Day
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="weekday-weekend"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="time-of-day"),
            ], md=6),
        ]),
        # Row 5: 1 chart - Gender Time Distribution
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="gender-time-distribution"),
            ]),
        ]),
        # Row 6: 1 chart - Daily Sales Payday
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="daily-sales-payday"),
            ]),
        ]),
        # Row 7: 1 chart - Basket Bands
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="basket-bands"),
            ]),
        ]),
        # Row 8: 1 chart - Category Performance
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="category-performance"),
            ]),
        ]),
        # Row 9: 1 chart - Category by Day
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="category-by-day"),
            ]),
        ]),
        # Row 10: 1 chart - Category by Price Tier
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="category-by-price-tier"),
            ]),
        ]),
        # Row 11: 1 chart - Category by Gender
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="category-by-gender"),
            ]),
        ]),
        # Row 12: 1 chart - Category by Age
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="category-by-age"),
            ]),
        ]),
        # Row 13: 1 chart - Category Ranking Table
        dbc.Row([
            dbc.Col([
                html.H4("Category Performance Ranking", className="mb-3"),
                html.Div(id="category-ranking-table"),
            ]),
        ]),
        # Row 12: 1 chart - Top Products Table
        dbc.Row([
            dbc.Col([
                html.H4("Top Products by Time of Day", className="mb-3"),
                html.Div(id="top-products-table"),
            ]),
        ]),
        # Row 14: 1 chart - Products Bought Together
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="products-bought-together"),
            ]),
        ]),
    ])

# Laundry Tab
def create_laundry_tab():
    """Create content for Laundry tab."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H3("Laundry Analytics", className="mt-4"),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="laundry-time-avgqty"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="laundry-day-avgqty"),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="laundry-brands"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="laundry-brands-day"),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="laundry-gender-pie"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="laundry-age-pie"),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="laundry-gender-brand"),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="laundry-cluster-items"),
            ], md=4),
            dbc.Col([
                dcc.Graph(id="laundry-cluster-categories"),
            ], md=4),
            dbc.Col([
                dcc.Graph(id="laundry-cluster-brands"),
            ], md=4),
        ]),
    ])

# Tobacco Tab
def create_tobacco_tab():
    """Create content for Tobacco tab."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H3("Tobacco Analytics", className="mt-4"),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="tobacco-time-avgqty"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="tobacco-day-avgqty"),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="tobacco-brands"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="tobacco-brands-day"),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="tobacco-gender-pie"),
            ], md=6),
            dbc.Col([
                dcc.Graph(id="tobacco-age-pie"),
            ], md=6),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="tobacco-gender-brand"),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="tobacco-cluster-items"),
            ], md=4),
            dbc.Col([
                dcc.Graph(id="tobacco-cluster-categories"),
            ], md=4),
            dbc.Col([
                dcc.Graph(id="tobacco-cluster-brands"),
            ], md=4),
        ]),
    ])

# Query Editor Tab
def create_query_editor_tab():
    """Create content for Query Editor tab."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H3("Query Editor", className="mt-4 mb-4"),
            ]),
        ]),
        # Table previews section
        dbc.Row([
            dbc.Col([
                html.H5("Table Previews", className="mb-3"),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("twba_transactions"),
                    dbc.CardBody([
                        html.Div(id="transactions-preview"),
                        dbc.Button("Load Preview", id="load-transactions-preview", color="primary", size="sm", className="mt-2"),
                    ]),
                ]),
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("twba_items"),
                    dbc.CardBody([
                        html.Div(id="items-preview"),
                        dbc.Button("Load Preview", id="load-items-preview", color="primary", size="sm", className="mt-2"),
                    ]),
                ]),
            ], md=6),
        ], className="mb-4"),
        # Query editor section
        dbc.Row([
            dbc.Col([
                html.H5("SQL Query Editor", className="mb-3"),
                dbc.Alert(
                    "Note: Only SELECT queries are allowed. For security, other SQL commands are blocked.",
                    color="info",
                    className="mb-3"
                ),
                dcc.Textarea(
                    id="sql-query-input",
                    placeholder="Enter your SELECT query here...\nExample: SELECT * FROM twba_transactions LIMIT 100",
                    style={"width": "100%", "height": "200px", "fontFamily": "monospace", "fontSize": "14px"},
                    value="SELECT * FROM twba_transactions LIMIT 100;"
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Execute Query", id="execute-query-btn", color="success", className="mt-3"),
                    ], md=6),
                    dbc.Col([
                        dbc.Button("Clear", id="clear-query-btn", color="secondary", className="mt-3"),
                    ], md=6),
                ]),
            ]),
        ]),
        # Results section
        dbc.Row([
            dbc.Col([
                html.Div(id="query-results", className="mt-4"),
            ]),
        ]),
    ])

# Ask AI Tab
def create_ask_ai_tab():
    """Create content for Ask AI tab."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H3("Ask AI - Natural Language to SQL", className="mt-4 mb-4"),
                dbc.Alert(
                    "Ask questions in natural language and get SQL query results. The AI understands your database schema and will generate appropriate queries.",
                    color="info",
                    className="mb-4"
                ),
            ]),
        ]),
        # Question input section
        dbc.Row([
            dbc.Col([
                html.Label("Ask a question about your data:", className="mb-2", style={"fontWeight": "500"}),
                dcc.Textarea(
                    id="ai-question-input",
                    placeholder="Example: What are the top 10 products by total quantity sold?",
                    style={"width": "100%", "height": "120px", "fontSize": "16px", "padding": "10px"},
                    value=""
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.Span(id="ask-ai-btn-text", children="Ask AI")],
                            id="ask-ai-btn",
                            color="primary",
                            size="lg",
                            className="mt-3",
                            disabled=False
                        ),
                    ], md=6),
                    dbc.Col([
                        dbc.Button("Clear", id="clear-ai-btn", color="secondary", size="lg", className="mt-3"),
                    ], md=6),
                ]),
            ]),
        ]),
        # Generated SQL and Results section
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="ai-loading",
                    type="default",
                    children=html.Div(id="ai-results", className="mt-4"),
                ),
            ]),
        ]),
    ])

# Helper function to get database schema
def get_database_schema() -> str:
    """Get the database schema information for OpenAI prompt."""
    schema = """
Database Schema:

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

# Helper function to execute SQL query directly (fallback when db_engine is not available)
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
                return pd.DataFrame(), f"Database connection not available. Missing environment variables: {', '.join(missing_fields)}. Please set these in your .env file."
            
            connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
            engine = create_engine(connection_string, pool_pre_ping=True, connect_args={"sslmode": "require"})
        
        # Execute the SQL query directly
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df, None
            
    except SQLAlchemyError as e:
        return pd.DataFrame(), f"Database error: {str(e)}"
    except Exception as e:
        return pd.DataFrame(), f"Error executing query: {str(e)}"

# Helper function to generate SQL from natural language
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
                {"role": "system", "content": "You are a SQL expert that generates PostgreSQL queries from natural language questions. Always wrap uppercase column names in double quotes (e.g., \"InteractionID\") and use LOWER() function for case-insensitive value comparisons in WHERE clauses (e.g., WHERE LOWER(column) = LOWER('value'))."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        sql_query = response.choices[0].message.content.strip()
        
        # Clean up the SQL query (remove markdown code blocks if present)
        sql_query = re.sub(r'```sql\s*', '', sql_query)
        sql_query = re.sub(r'```\s*', '', sql_query)
        sql_query = sql_query.strip()
        
        return sql_query, ""
    except Exception as e:
        return "", f"Error generating SQL: {str(e)}"

# Authentication callbacks
# Callback to check authentication state on page load
@callback(
    Output("page-content", "children"),
    Input("auth-store", "data"),
    prevent_initial_call=False,
)
def check_auth_on_load(auth_data):
    """Check authentication state on page load."""
    try:
        if auth_data and isinstance(auth_data, dict) and auth_data.get("authenticated"):
            return create_dashboard_layout()
        else:
            return create_login_page()
    except Exception as e:
        # If there's an error, show login page
        print(f"Error in check_auth_on_load: {e}")
        return create_login_page()

# Callback to handle login
@callback(
    Output("page-content", "children", allow_duplicate=True),
    Output("auth-store", "data", allow_duplicate=True),
    Input("login-button", "n_clicks"),
    State("auth-store", "data"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def handle_login(n_clicks, auth_data, username, password):
    """Handle login button click."""
    if n_clicks:
        # Validate credentials
        if username == AUTH_USERNAME and password == AUTH_PASSWORD:
            try:
                return create_dashboard_layout(), {"authenticated": True}
            except Exception as e:
                print(f"Error in handle_login: {e}")
                return create_login_page("Error loading dashboard. Please try again."), {"authenticated": False}
        else:
            # Show error message but stay on login page
            error_message = "Invalid username or password"
            return create_login_page(error_message), {"authenticated": False}
    
    return dash.no_update, dash.no_update

# Callback to handle logout
@callback(
    Output("page-content", "children", allow_duplicate=True),
    Output("auth-store", "data", allow_duplicate=True),
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True,
)
def handle_logout(n_clicks):
    """Handle logout button click."""
    if n_clicks:
        return create_login_page(), {"authenticated": False}
    return dash.no_update, dash.no_update

# Reset button callbacks
@callback(
    Output("date-range", "start_date", allow_duplicate=True),
    Output("date-range", "end_date", allow_duplicate=True),
    Input("reset-date-range", "n_clicks"),
    prevent_initial_call=True,
)
def reset_date_range(n_clicks):
    if n_clicks:
        return (
            transactions_df["TransactionDate"].min() if not transactions_df.empty else datetime.now() - timedelta(days=90),
            transactions_df["TransactionDate"].max() if not transactions_df.empty else datetime.now(),
        )
    return dash.no_update, dash.no_update

@callback(
    Output("month-year-filter", "value", allow_duplicate=True),
    Input("reset-month-year", "n_clicks"),
    prevent_initial_call=True,
)
def reset_month_year(n_clicks):
    return None if n_clicks else dash.no_update

@callback(
    Output("weekday-weekend-filter", "value", allow_duplicate=True),
    Input("reset-weekday-weekend", "n_clicks"),
    prevent_initial_call=True,
)
def reset_weekday_weekend(n_clicks):
    return None if n_clicks else dash.no_update

@callback(
    Output("gender-filter", "value", allow_duplicate=True),
    Input("reset-gender", "n_clicks"),
    prevent_initial_call=True,
)
def reset_gender(n_clicks):
    return None if n_clicks else dash.no_update

@callback(
    Output("age-filter", "value", allow_duplicate=True),
    Input("reset-age", "n_clicks"),
    prevent_initial_call=True,
)
def reset_age(n_clicks):
    return None if n_clicks else dash.no_update

@callback(
    Output("payment-filter", "value", allow_duplicate=True),
    Input("reset-payment", "n_clicks"),
    prevent_initial_call=True,
)
def reset_payment(n_clicks):
    return None if n_clicks else dash.no_update

@callback(
    Output("category-filter", "value", allow_duplicate=True),
    Input("reset-category", "n_clicks"),
    prevent_initial_call=True,
)
def reset_category(n_clicks):
    return None if n_clicks else dash.no_update

# Reset all filters callback
@callback(
    Output("date-range", "start_date", allow_duplicate=True),
    Output("date-range", "end_date", allow_duplicate=True),
    Output("month-year-filter", "value", allow_duplicate=True),
    Output("weekday-weekend-filter", "value", allow_duplicate=True),
    Output("gender-filter", "value", allow_duplicate=True),
    Output("age-filter", "value", allow_duplicate=True),
    Output("payment-filter", "value", allow_duplicate=True),
    Output("category-filter", "value", allow_duplicate=True),
    Input("reset-all-filters", "n_clicks"),
    prevent_initial_call=True,
)
def reset_all_filters(n_clicks):
    if n_clicks:
        return (
            transactions_df["TransactionDate"].min() if not transactions_df.empty else datetime.now() - timedelta(days=90),
            transactions_df["TransactionDate"].max() if not transactions_df.empty else datetime.now(),
            None,  # month-year
            None,  # weekday-weekend
            None,  # gender
            None,  # age
            None,  # payment
            None,  # category
        )
    return [dash.no_update] * 8

# Tab content callback
@callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab"),
)
def render_tab_content(tab):
    if tab == "general":
        return create_general_tab()
    elif tab == "laundry":
        return create_laundry_tab()
    elif tab == "tobacco":
        return create_tobacco_tab()
    elif tab == "query-editor":
        return create_query_editor_tab()
    elif tab == "ask-ai":
        return create_ask_ai_tab()
    elif tab == "documentation":
        return create_documentation_tab()
    return html.Div("Select a tab")

# General Analytics Callbacks
@callback(
    Output("gender-combined", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_gender_combined(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a dual-axis chart: bars for transactions, line for average spend."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    gender_summary = (
        filtered.groupby("gender_clean")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add bar chart for transactions (left y-axis)
    fig.add_trace(
        go.Bar(
            x=gender_summary["gender_clean"],
            y=gender_summary["total_transactions"],
            name="Total Transactions",
            marker_color="gold",
            text=gender_summary["total_transactions"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            yaxis="y",
        )
    )
    
    # Add line chart for average spend (right y-axis)
    fig.add_trace(
        go.Scatter(
            x=gender_summary["gender_clean"],
            y=gender_summary["avg_spend"],
            name="Average Spend",
            mode="lines+markers",
            marker=dict(size=10, color="blue"),
            line=dict(color="blue", width=3),
            text=gender_summary["avg_spend"].round(2),
            texttemplate="₱%{text:.2f}",
            textposition="top center",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Average Spend: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Update layout with dual y-axes and dark mode
    apply_dark_layout(
        fig,
        "Gender Demographics: Transactions & Average Spend",
        "Gender",
        "Total Transactions",
        "Average Spend (₱)",
        yaxis=dict(
            title="Total Transactions",
            side="left",
            showgrid=True,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis2=dict(
            title="Average Spend (₱)",
            side="right",
            overlaying="y",
            showgrid=False,
            tickformat=".2f",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        height=500,
    )
    
    return fig

@callback(
    Output("gender-mom", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_gender_mom(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    monthly_gender = (
        filtered.groupby(["txn_month", "gender_clean"])
        .agg(total_transactions=("InteractionID", "count"))
        .reset_index()
    )
    
    fig = px.line(
        monthly_gender,
        x="txn_month",
        y="total_transactions",
        color="gender_clean",
        markers=True,
        title="Month-on-Month Transactions by Gender",
        labels={"txn_month": "Month", "total_transactions": "Transactions"},
    )
    apply_dark_layout(fig, "Month-on-Month Transactions by Gender", "Month", "Transactions", "", height=500)
    return fig

@callback(
    Output("age-bucket-combined", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_age_bucket_combined(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a dual-axis chart: bars for transactions, line for average spend by age."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    age_summary = (
        filtered.dropna(subset=["age_bucket"])
        .groupby("age_bucket")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )
    
    # Sort by age bucket order
    age_order = ["<18", "18-24", "25-34", "35-44", "45-54", "55+"]
    age_summary["age_bucket"] = pd.Categorical(age_summary["age_bucket"], categories=age_order, ordered=True)
    age_summary = age_summary.sort_values("age_bucket")
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add bar chart for transactions (left y-axis)
    fig.add_trace(
        go.Bar(
            x=age_summary["age_bucket"],
            y=age_summary["total_transactions"],
            name="Transactions",
            marker_color="gold",
            text=age_summary["total_transactions"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            yaxis="y",
        )
    )
    
    # Add line chart for average spend (right y-axis)
    fig.add_trace(
        go.Scatter(
            x=age_summary["age_bucket"],
            y=age_summary["avg_spend"],
            name="Ave Total Spend",
            mode="lines+markers",
            marker=dict(size=10, color="blue"),
            line=dict(color="blue", width=3),
            text=age_summary["avg_spend"].round(2),
            texttemplate="₱%{text:.2f}",
            textposition="top center",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Ave Total Spend: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Update layout with dual y-axes
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Age Demographics: Transactions & Average Spend",
        "Age Bucket",
        "Transactions",
        "Ave Total Spend (₱)",
        yaxis=dict(
            title="Transactions",
            side="left",
            showgrid=True,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis2=dict(
            title="Ave Total Spend (₱)",
            side="right",
            overlaying="y",
            showgrid=False,
            tickformat=".2f",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        height=500,
    )
    
    return fig

@callback(
    Output("payment-combined", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_payment_combined(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a dual-axis chart: bars for transactions, line for average spend by payment method."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    tender_summary = (
        filtered.groupby("payment_method")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add bar chart for transactions (left y-axis)
    fig.add_trace(
        go.Bar(
            x=tender_summary["payment_method"],
            y=tender_summary["total_transactions"],
            name="Transactions",
            marker_color="gold",
            text=tender_summary["total_transactions"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            yaxis="y",
        )
    )
    
    # Add line chart for average spend (right y-axis)
    fig.add_trace(
        go.Scatter(
            x=tender_summary["payment_method"],
            y=tender_summary["avg_spend"],
            name="Average Spend",
            mode="lines+markers",
            marker=dict(size=10, color="blue"),
            line=dict(color="blue", width=3),
            text=tender_summary["avg_spend"].round(2),
            texttemplate="₱%{text:.2f}",
            textposition="top center",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Average Spend: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Payment Method: Transactions & Average Spend",
        "Payment Method",
        "Transactions",
        "Average Spend (₱)",
        yaxis=dict(
            title="Transactions",
            side="left",
            showgrid=True,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis2=dict(
            title="Average Spend (₱)",
            side="right",
            overlaying="y",
            showgrid=False,
            tickformat=".2f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        height=500,
    )
    
    return fig

@callback(
    Output("weekday-weekend", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_weekday_weekend(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a dual-axis chart: bars for transactions, line for average spend (Weekday vs Weekend)."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    filtered["weekday_type"] = filtered["TransactionDate"].dt.dayofweek.apply(
        lambda x: "Weekend" if x >= 5 else "Weekday"
    )
    
    week_summary = (
        filtered.groupby("weekday_type")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add bar chart for transactions (left y-axis)
    fig.add_trace(
        go.Bar(
            x=week_summary["weekday_type"],
            y=week_summary["total_transactions"],
            name="Transactions",
            marker_color="gold",
            text=week_summary["total_transactions"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            yaxis="y",
        )
    )
    
    # Add line chart for average spend (right y-axis)
    fig.add_trace(
        go.Scatter(
            x=week_summary["weekday_type"],
            y=week_summary["avg_spend"],
            name="Average Spend",
            mode="lines+markers",
            marker=dict(size=10, color="blue"),
            line=dict(color="blue", width=3),
            text=week_summary["avg_spend"].round(2),
            texttemplate="₱%{text:.2f}",
            textposition="top center",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Average Spend: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Update layout with dual y-axes
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Transactions & Average Spend: Weekday vs Weekend",
        "Weekday Type",
        "Transactions",
        "Average Spend (₱)",
        yaxis=dict(
            title="Transactions",
            side="left",
            showgrid=True,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis2=dict(
            title="Average Spend (₱)",
            side="right",
            overlaying="y",
            showgrid=False,
            tickformat=".2f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        height=500,
    )
    
    return fig

@callback(
    Output("time-of-day", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_time_of_day(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a dual-axis chart: bars for transactions, line for average spend by time of day."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    filtered["weekday_type"] = filtered["TransactionDate"].dt.dayofweek.apply(
        lambda x: "Weekend" if x >= 5 else "Weekday"
    )
    
    timeofday_summary = (
        filtered.dropna(subset=["timeofday_segment"])
        .groupby(["weekday_type", "timeofday_segment"])
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Get unique time segments and weekday types
    time_segments = sorted(timeofday_summary["timeofday_segment"].unique())
    weekday_types = ["Weekday", "Weekend"]
    
    # Add bars for transactions (grouped by weekday_type)
    for wd_type in weekday_types:
        data = timeofday_summary[timeofday_summary["weekday_type"] == wd_type]
        # Align data with time_segments order
        aligned_data = []
        for seg in time_segments:
            seg_data = data[data["timeofday_segment"] == seg]
            if not seg_data.empty:
                aligned_data.append(seg_data.iloc[0]["total_transactions"])
            else:
                aligned_data.append(0)
        
        fig.add_trace(
            go.Bar(
                x=time_segments,
                y=aligned_data,
                name=f"{wd_type} Transactions",
                marker_color="gold" if wd_type == "Weekday" else "orange",
                yaxis="y",
            )
        )
    
    # Calculate average spend across both weekday types for each time segment
    avg_spend_by_time = (
        filtered.dropna(subset=["timeofday_segment"])
        .groupby("timeofday_segment")
        .agg(avg_spend=("basket_total", "mean"))
        .reset_index()
    )
    avg_spend_by_time = avg_spend_by_time.sort_values("timeofday_segment")
    
    # Add line for average spend (right y-axis)
    fig.add_trace(
        go.Scatter(
            x=avg_spend_by_time["timeofday_segment"],
            y=avg_spend_by_time["avg_spend"],
            name="Average Spend",
            mode="lines+markers",
            marker=dict(size=10, color="blue"),
            line=dict(color="blue", width=3),
            text=avg_spend_by_time["avg_spend"].round(2),
            texttemplate="₱%{text:.2f}",
            textposition="top center",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Average Spend: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Apply dark mode layout with explicit height and autosize=False
    apply_dark_layout(
        fig,
        "Transactions & Average Spend by Time of Day (Weekday vs Weekend)",
        "Time of Day",
        "Transactions",
        "Average Spend (₱)",
        yaxis=dict(
            title="Transactions",
            side="left",
            showgrid=True,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis2=dict(
            title="Average Spend (₱)",
            side="right",
            overlaying="y",
            showgrid=False,
            tickformat=".2f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="group",
        legend=dict(x=0.02, y=0.98, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        height=500,
    )
    
    return fig

@callback(
    Output("day-of-week", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_day_of_week(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a dual-axis chart: bars for transactions, line for average spend by day of week."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Get day of week name
    filtered["day_of_week"] = filtered["TransactionDate"].dt.day_name()
    
    # Order days properly
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    filtered["day_of_week"] = pd.Categorical(
        filtered["day_of_week"], 
        categories=day_order, 
        ordered=True
    )
    
    day_summary = (
        filtered.dropna(subset=["day_of_week"])
        .groupby("day_of_week")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
        .sort_values("day_of_week")
    )
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add bar chart for transactions (left y-axis)
    fig.add_trace(
        go.Bar(
            x=day_summary["day_of_week"],
            y=day_summary["total_transactions"],
            name="Transactions",
            marker_color="gold",
            text=day_summary["total_transactions"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            yaxis="y",
        )
    )
    
    # Add line chart for average spend (right y-axis)
    fig.add_trace(
        go.Scatter(
            x=day_summary["day_of_week"],
            y=day_summary["avg_spend"],
            name="Average Spend",
            mode="lines+markers",
            marker=dict(size=10, color="blue"),
            line=dict(color="blue", width=3),
            text=day_summary["avg_spend"].round(2),
            texttemplate="₱%{text:.2f}",
            textposition="top center",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Average Spend: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Apply dark mode layout with dual y-axes
    apply_dark_layout(
        fig,
        "Transactions & Average Spend by Day of Week",
        "Day of Week",
        "Transactions",
        "Average Spend (₱)",
        yaxis=dict(
            title="Transactions",
            side="left",
            showgrid=True,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis2=dict(
            title="Average Spend (₱)",
            side="right",
            overlaying="y",
            showgrid=False,
            tickformat=".2f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        height=500,
    )
    
    return fig

@callback(
    Output("gender-time-distribution", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_gender_time_distribution(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a 100% stacked horizontal bar chart showing gender distribution by time of day."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Group by time of day segment and gender
    time_gender_summary = (
        filtered.dropna(subset=["timeofday_segment", "gender_clean"])
        .groupby(["timeofday_segment", "gender_clean"])
        .agg(total_transactions=("InteractionID", "count"))
        .reset_index()
    )
    
    # Calculate percentages for each time segment
    time_segments = sorted(time_gender_summary["timeofday_segment"].unique())
    genders = ["Female", "Male"]
    
    # Create data for stacked bars
    female_percentages = []
    male_percentages = []
    
    for segment in time_segments:
        segment_data = time_gender_summary[time_gender_summary["timeofday_segment"] == segment]
        total = segment_data["total_transactions"].sum()
        
        female_count = segment_data[segment_data["gender_clean"] == "Female"]["total_transactions"].sum() if not segment_data[segment_data["gender_clean"] == "Female"].empty else 0
        male_count = segment_data[segment_data["gender_clean"] == "Male"]["total_transactions"].sum() if not segment_data[segment_data["gender_clean"] == "Male"].empty else 0
        
        if total > 0:
            female_percentages.append((female_count / total) * 100)
            male_percentages.append((male_count / total) * 100)
        else:
            female_percentages.append(0)
            male_percentages.append(0)
    
    # Create figure with 100% stacked horizontal bars
    fig = go.Figure()
    
    # Add Female bars
    fig.add_trace(
        go.Bar(
            y=time_segments,
            x=female_percentages,
            name="Female",
            orientation="h",
            marker=dict(color="gold"),
            text=[f"{p:.1f}%" for p in female_percentages],
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Female: %{x:.1f}%<extra></extra>",
        )
    )
    
    # Add Male bars
    fig.add_trace(
        go.Bar(
            y=time_segments,
            x=male_percentages,
            name="Male",
            orientation="h",
            marker=dict(color="lightyellow"),
            text=[f"{p:.1f}%" for p in male_percentages],
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Male: %{x:.1f}%<extra></extra>",
        )
    )
    
    # Update layout for 100% stacked
    apply_dark_layout(
        fig,
        "Gender Distribution by Time of Day (100% Stacked)",
        "Percentage (%)",
        "Time of Day",
        "",
        xaxis=dict(
            title="Percentage (%)",
            range=[0, 100],
            tickformat=".0f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Time of Day",
            autorange="reversed",  # Reverse to show Morning at top
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="stack",
        height=400,
        legend=dict(x=0.7, y=0.95, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        hovermode="y unified",
    )
    
    return fig

@callback(
    Output("daily-sales-payday", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_daily_sales_payday(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a line chart showing average daily sales by day of month with payday windows and petsa de peligro zones."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Extract day of month
    filtered["day_of_month"] = filtered["TransactionDate"].dt.day
    
    # Calculate average sales by day of month
    daily_sales = (
        filtered.groupby("day_of_month")
        .agg(avg_sales=("basket_total", "mean"))
        .reset_index()
        .sort_values("day_of_month")
    )
    
    # Define payday windows (typically around 15th and 30th, ±2 days)
    # Also include end of month (days 29-31) and beginning (days 1-3) for monthly paydays
    payday_days = [15, 30]  # Main paydays
    
    # Payday windows: payday ±2 days
    payday_windows = set()
    for payday in payday_days:
        for day in range(payday - 2, payday + 3):
            if 1 <= day <= 31:
                payday_windows.add(day)
    # Also add end/beginning of month windows
    payday_windows.update([29, 30, 31, 1, 2, 3])
    
    # Define petsa de peligro zones (3 days before payday)
    petsa_zones = set()
    for payday in payday_days:
        for day in range(payday - 3, payday):
            if 1 <= day <= 31:
                petsa_zones.add(day)
    # Also add petsa before month-end payday (days 26-28)
    petsa_zones.update([26, 27, 28])
    # And petsa before mid-month payday (days 11-13)
    petsa_zones.update([11, 12, 13])
    
    # Find overlap zones (both payday window and petsa de peligro)
    overlap_zones = payday_windows.intersection(petsa_zones)
    
    # Create figure
    fig = go.Figure()
    
    # Get y-axis range for proper shading
    y_min = daily_sales["avg_sales"].min() * 0.9
    y_max = daily_sales["avg_sales"].max() * 1.1
    
    # Add shaded regions for payday windows (green) - only non-overlap days
    for day in payday_windows:
        if day not in overlap_zones:
            fig.add_shape(
                type="rect",
                x0=day - 0.5,
                x1=day + 0.5,
                y0=y_min,
                y1=y_max,
                fillcolor="green",
                opacity=0.15,
                layer="below",
                line_width=0,
            )
    
    # Add shaded regions for petsa de peligro (red) - only non-overlap days
    for day in petsa_zones:
        if day not in overlap_zones:
            fig.add_shape(
                type="rect",
                x0=day - 0.5,
                x1=day + 0.5,
                y0=y_min,
                y1=y_max,
                fillcolor="red",
                opacity=0.15,
                layer="below",
                line_width=0,
            )
    
    # Add shaded regions for overlap zones (brown)
    for day in overlap_zones:
        fig.add_shape(
            type="rect",
            x0=day - 0.5,
            x1=day + 0.5,
            y0=y_min,
            y1=y_max,
            fillcolor="brown",
            opacity=0.25,
            layer="below",
            line_width=0,
        )
    
    # Add line chart for average sales
    fig.add_trace(
        go.Scatter(
            x=daily_sales["day_of_month"],
            y=daily_sales["avg_sales"],
            mode="lines+markers",
            name="Average Sales",
            line=dict(color="orange", width=2),
            marker=dict(size=6, color="orange"),
            hovertemplate="<b>Day %{x}</b><br>Average Sales: ₱%{y:.2f}<extra></extra>",
        )
    )
    
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Average Daily Sales by Day of Month (Petsa de Peligro vs Payday Windows)",
        "Day of Month",
        "Average Sales (₱)",
        "",
        xaxis=dict(
            title="Day of Month",
            range=[0.5, 31.5],
            dtick=1,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Average Sales (₱)",
            tickformat=".0f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        height=500,
        hovermode="x unified",
        legend=dict(
            x=0.02,
            y=0.98,
            itemsizing="constant",
            bgcolor="#1a1a1a",
            bordercolor="#3a3a3a",
            font=dict(color="#e0e0e0"),
        ),
        annotations=[
            dict(
                x=0.98,
                y=0.02,
                xref="paper",
                yref="paper",
                text="<b>Legend:</b><br>🟢 Green: Payday Windows<br>🔴 Red: Petsa de Peligro<br>",
                showarrow=False,
                align="right",
                bgcolor="#2a2a2a",
                bordercolor="#4a4a4a",
                borderwidth=1,
                borderpad=5,
                font=dict(color="#e0e0e0"),
            )
        ],
    )
    
    return fig

@callback(
    Output("basket-bands", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_basket_bands(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    # Filter data but don't apply basket_total filter for this chart (we want all bands)
    filtered = transactions_df.copy()
    
    # Apply all filters except basket_total filter
    if start_date and end_date:
        if "TransactionDate" in filtered.columns:
            try:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                filtered = filtered[(filtered["TransactionDate"] >= start) & (filtered["TransactionDate"] <= end)]
            except:
                pass
    
    if gender and "gender_clean" in filtered.columns:
        filtered = filtered[filtered["gender_clean"].isin(gender)]
    if age and "age_bucket" in filtered.columns:
        filtered = filtered[filtered["age_bucket"].isin(age)]
    if payment and "payment_method" in filtered.columns:
        filtered = filtered[filtered["payment_method"].isin(payment)]
    if month_year and len(month_year) > 0 and "TransactionDate" in filtered.columns:
        filtered["year_month"] = filtered["TransactionDate"].dt.to_period("M")
        month_year_periods = [pd.Period(f"{m}-01") if len(m) == 7 else pd.Period(m) for m in month_year]
        filtered = filtered[filtered["year_month"].isin(month_year_periods)]
        filtered = filtered.drop(columns=["year_month"], errors="ignore")
    if weekday_weekend and "TransactionDate" in filtered.columns:
        filtered["weekday_type"] = filtered["TransactionDate"].dt.dayofweek.apply(
            lambda x: "Weekend" if x >= 5 else "Weekday"
        )
        filtered = filtered[filtered["weekday_type"] == weekday_weekend]
        filtered = filtered.drop(columns=["weekday_type"], errors="ignore")
    if category and "InteractionID" in filtered.columns:
        category_interaction_ids = items_df[items_df["category"].isin(category)]["InteractionID"].unique()
        filtered = filtered[filtered["InteractionID"].isin(category_interaction_ids)]
    
    # Guard: ensure basket_total column exists and data is present
    if "basket_total" not in filtered.columns or filtered.empty:
        return go.Figure().add_annotation(
            text="No basket data available",
            showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper"
        )
    
    # Ensure basket_total is numeric
    filtered = filtered.copy()
    filtered["basket_total"] = pd.to_numeric(filtered["basket_total"], errors="coerce")
    filtered = filtered.dropna(subset=["basket_total"])
    if filtered.empty:
        return go.Figure().add_annotation(
            text="No basket data available",
            showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper"
        )
    
    def basket_band(value):
        if pd.isna(value) or value <= 0:
            return None
        if value <= 10:
            return "₱0-10"
        elif value <= 20:
            return "₱11-20"
        elif value <= 50:
            return "₱21-50"
        elif value <= 100:
            return "₱51-100"
        elif value <= 200:
            return "₱101-200"
        else:
            return "₱200+"
    
    filtered["basket_band"] = filtered["basket_total"].apply(basket_band)
    
    basket_summary = (
        filtered.dropna(subset=["basket_band"])
        .groupby("basket_band")
        .agg(
            transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )
    
    # Guard: ensure we have data to plot
    if basket_summary.empty:
        return go.Figure().add_annotation(
            text="No basket data available for selected filters",
            showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper"
        )
    
    # Order bands
    band_order = ["₱0-10", "₱11-20", "₱21-50", "₱51-100", "₱101-200", "₱200+"]
    basket_summary["basket_band"] = pd.Categorical(basket_summary["basket_band"], categories=band_order, ordered=True)
    basket_summary = basket_summary.sort_values("basket_band")
    
    # Ensure transactions and avg_spend are numeric
    basket_summary["transactions"] = pd.to_numeric(basket_summary["transactions"], errors="coerce")
    basket_summary["avg_spend"] = pd.to_numeric(basket_summary["avg_spend"], errors="coerce")
    basket_summary = basket_summary.dropna(subset=["transactions", "avg_spend"])
    
    if basket_summary.empty:
        return go.Figure().add_annotation(
            text="No valid basket data to display",
            showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper"
        )
    
    fig = px.bar(
        basket_summary,
        x="basket_band",
        y="transactions",
        color="avg_spend",
        title="Basket Value Distribution",
        text="transactions",
        labels={"basket_band": "Basket Band", "transactions": "Transactions"},
        color_continuous_scale="Tealgrn",
    )
    fig.update_traces(textposition="outside", texttemplate="%{text:,.0f}")
    apply_dark_layout(fig, "Basket Value Distribution", "Basket Band", "Transactions", "", height=500)
    return fig

@callback(
    Output("category-performance", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_category_performance(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    try:
        filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
        
        # Ensure required columns and numeric values
        if "totalPrice" not in filtered_items.columns and "unitPrice" in filtered_items.columns and "quantity" in filtered_items.columns:
            filtered_items["totalPrice"] = filtered_items["unitPrice"] * filtered_items["quantity"]
        
        if filtered_items.empty or "category" not in filtered_items.columns:
            return go.Figure().add_annotation(
                text="No data available",
                showarrow=False,
                x=0.5, y=0.5, xref="paper", yref="paper"
            )
        
        # Coerce numeric columns early
        for col in ["quantity", "unitPrice", "totalPrice"]:
            if col in filtered_items.columns:
                filtered_items[col] = pd.to_numeric(filtered_items[col], errors="coerce")
        
        # Aggregations
        agg_dict = {}
        if "quantity" in filtered_items.columns:
            agg_dict["units"] = ("quantity", "sum")
        if "totalPrice" in filtered_items.columns:
            agg_dict["revenue"] = ("totalPrice", "sum")
        
        if not agg_dict:
            return go.Figure().add_annotation(
                text="No price or quantity data available",
                showarrow=False,
                x=0.5, y=0.5, xref="paper", yref="paper"
            )
        
        category_summary = (
            filtered_items.groupby("category")
            .agg(**agg_dict)
            .reset_index()
        )
        
        # Sort
        if "revenue" in category_summary.columns:
            category_summary = category_summary.sort_values("revenue", ascending=False)
        elif "units" in category_summary.columns:
            category_summary = category_summary.sort_values("units", ascending=False)
        
        if category_summary.empty:
            return go.Figure().add_annotation(
                text="No category data available",
                showarrow=False,
                x=0.5, y=0.5, xref="paper", yref="paper"
            )
        
        # Determine plot columns
        y_col = "revenue" if "revenue" in category_summary.columns else "units"
        text_col = "units" if "units" in category_summary.columns and y_col == "revenue" else None
        
        # Validate data
        if y_col not in category_summary.columns:
            return go.Figure().add_annotation(
                text="No data available for chart",
                showarrow=False,
                x=0.5, y=0.5, xref="paper", yref="paper"
            )
        
        # Coerce and clean
        category_summary[y_col] = pd.to_numeric(category_summary[y_col], errors="coerce")
        if text_col:
            category_summary[text_col] = pd.to_numeric(category_summary[text_col], errors="coerce")
        category_summary = category_summary.dropna(subset=[y_col, "category"])
        
        if category_summary.empty:
            return go.Figure().add_annotation(
                text="No valid data available",
                showarrow=False,
                x=0.5, y=0.5, xref="paper", yref="paper"
            )
        
        # Plot
        fig = px.bar(
            category_summary.head(15),
            x="category",
            y=y_col,
            text=text_col if text_col else None,
            title="Top Categories by Revenue" if y_col == "revenue" else "Top Categories by Units",
            labels={"category": "Category", "revenue": "Revenue (₱)", "units": "Units"},
        )
        if text_col:
            fig.update_traces(texttemplate="%{text:.0f} units", textposition="outside")
        
        apply_dark_layout(
            fig,
            "Top Categories by Revenue" if y_col == "revenue" else "Top Categories by Units",
            "Category",
            "Revenue (₱)" if y_col == "revenue" else "Units",
            "",
            xaxis_tickangle=45,
            height=450,
        )
        return fig
    except Exception as e:
        # Return a figure with the error to avoid callback failure
        return go.Figure().add_annotation(
            text=f"Error: {e}",
            showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper"
        )

@callback(
    Output("category-by-day", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_category_by_day(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a grouped bar chart showing category performance by day of week."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Get day of week name
    filtered_items["day_of_week"] = filtered_items["TransactionDate"].dt.day_name()
    
    # Order days properly
    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    filtered_items["day_of_week"] = pd.Categorical(
        filtered_items["day_of_week"], 
        categories=day_order, 
        ordered=True
    )
    
    # Group by category and day of week, sum quantities
    category_day_summary = (
        filtered_items.dropna(subset=["category", "day_of_week"])
        .groupby(["category", "day_of_week"])
        .agg(total_units=("quantity", "sum"))
        .reset_index()
        .sort_values(["category", "day_of_week"])
    )
    
    # Get all categories and sort them
    categories = sorted(category_day_summary["category"].unique())
    
    # Create figure with grouped bars
    fig = go.Figure()
    
    # Color palette for days (gold shades from darkest to lightest)
    day_colors = {
        "Sunday": "#B8860B",      # DarkGoldenrod
        "Monday": "#DAA520",       # Goldenrod
        "Tuesday": "#F4A460",      # SandyBrown
        "Wednesday": "#FFB347",    # LightGoldenrod
        "Thursday": "#FFD700",     # Gold
        "Friday": "#FFE4B5",       # Moccasin
        "Saturday": "#FFF8DC",     # Cornsilk (lightest)
    }
    
    # Add a bar for each day of week
    for day in day_order:
        day_data = category_day_summary[category_day_summary["day_of_week"] == day]
        
        # Align data with categories order
        aligned_values = []
        for cat in categories:
            cat_data = day_data[day_data["category"] == cat]
            if not cat_data.empty:
                aligned_values.append(cat_data.iloc[0]["total_units"])
            else:
                aligned_values.append(0)
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=aligned_values,
                name=day,
                marker_color=day_colors[day],
                hovertemplate=f"<b>%{{x}}</b><br>{day}: %{{y:.0f}} units<extra></extra>",
            )
        )
    
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Category Performance by Day of Week",
        "Category",
        "Units",
        "",
        xaxis=dict(
            title="Category",
            tickangle=45,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Units",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="group",
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            bgcolor="#1a1a1a",
            bordercolor="#3a3a3a",
            font=dict(color="#e0e0e0"),
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
    )
    
    return fig

@callback(
    Output("category-by-gender", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_category_by_gender(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a horizontal stacked bar chart showing gender distribution by category (100% stacked)."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Group by category and gender, count transactions (or sum quantities)
    category_gender_summary = (
        filtered_items.dropna(subset=["category", "gender_clean"])
        .groupby(["category", "gender_clean"])
        .agg(total_units=("quantity", "sum"))
        .reset_index()
    )
    
    # Get all categories
    categories = sorted(category_gender_summary["category"].unique())
    genders = ["Female", "Male"]
    
    # Calculate percentages for each category
    female_percentages = []
    male_percentages = []
    
    for cat in categories:
        cat_data = category_gender_summary[category_gender_summary["category"] == cat]
        total = cat_data["total_units"].sum()
        
        female_units = cat_data[cat_data["gender_clean"] == "Female"]["total_units"].sum() if not cat_data[cat_data["gender_clean"] == "Female"].empty else 0
        male_units = cat_data[cat_data["gender_clean"] == "Male"]["total_units"].sum() if not cat_data[cat_data["gender_clean"] == "Male"].empty else 0
        
        if total > 0:
            female_percentages.append((female_units / total) * 100)
            male_percentages.append((male_units / total) * 100)
        else:
            female_percentages.append(0)
            male_percentages.append(0)
    
    # Create figure with 100% stacked horizontal bars
    fig = go.Figure()
    
    # Add Female bars (darker yellow)
    fig.add_trace(
        go.Bar(
            y=categories,
            x=female_percentages,
            name="Female",
            orientation="h",
            marker=dict(color="gold"),
            text=[f"{p:.1f}%" for p in female_percentages],
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Female: %{x:.1f}%<extra></extra>",
        )
    )
    
    # Add Male bars (lighter yellow)
    fig.add_trace(
        go.Bar(
            y=categories,
            x=male_percentages,
            name="Male",
            orientation="h",
            marker=dict(color="lightyellow"),
            text=[f"{p:.1f}%" for p in male_percentages],
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Male: %{x:.1f}%<extra></extra>",
        )
    )
    
    # Apply dark mode layout for 100% stacked
    apply_dark_layout(
        fig,
        "Category Distribution by Gender (100% Stacked)",
        "Percentage (%)",
        "Category",
        "",
        xaxis=dict(
            title="Percentage (%)",
            range=[0, 100],
            tickformat=".0f",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Category",
            autorange="reversed",  # Reverse to show categories in order
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="stack",
        height=600,
        legend=dict(x=0.7, y=0.95, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
        hovermode="y unified",
    )
    
    return fig

@callback(
    Output("category-by-age", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_category_by_age(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a grouped bar chart showing age group distribution by category."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Group by category and age bucket, count transactions/units
    category_age_summary = (
        filtered_items.dropna(subset=["category", "age_bucket"])
        .groupby(["category", "age_bucket"])
        .agg(total_units=("quantity", "sum"))
        .reset_index()
    )
    
    # Get all categories
    categories = sorted(category_age_summary["category"].unique())
    
    # Age buckets (focusing on the main ones: 20-29, 30-39, 40-49)
    age_buckets = ["18-24", "25-34", "35-44", "45-54"]
    age_labels = {
        "18-24": "18-24",
        "25-34": "25-34",
        "35-44": "35-44",
        "45-54": "45-54",
    }
    
    # Create figure with grouped bars
    fig = go.Figure()
    
    # Color palette for age groups (gold shades)
    age_colors = {
        "18-24": "#B8860B",      # Darkest gold
        "25-34": "#DAA520",       # Goldenrod
        "35-44": "#FFD700",       # Gold
        "45-54": "#FFE4B5",       # Lighter gold
    }
    
    # Add a bar for each age bucket
    for age_bucket in age_buckets:
        age_data = category_age_summary[category_age_summary["age_bucket"] == age_bucket]
        
        # Align data with categories order
        aligned_values = []
        for cat in categories:
            cat_data = age_data[age_data["category"] == cat]
            if not cat_data.empty:
                aligned_values.append(cat_data.iloc[0]["total_units"])
            else:
                aligned_values.append(0)
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=aligned_values,
                name=age_labels[age_bucket],
                marker_color=age_colors[age_bucket],
                hovertemplate=f"<b>%{{x}}</b><br>{age_labels[age_bucket]}: %{{y:.0f}} units<extra></extra>",
            )
        )
    
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Category Distribution by Age Group",
        "Category",
        "Units",
        "",
        xaxis=dict(
            title="Category",
            tickangle=45,
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Units",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="group",
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="#1a1a1a",
            bordercolor="#3a3a3a",
            font=dict(color="#e0e0e0"),
        ),
        hovermode="x unified",
    )
    
    return fig

@callback(
    Output("category-by-price-tier", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_category_by_price_tier(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a stacked bar chart showing category composition by price tier."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)

    # Determine price per unit
    price_per_unit = None
    if "unitPrice" in filtered_items.columns:
        price_per_unit = filtered_items["unitPrice"]
    elif "totalPrice" in filtered_items.columns and "quantity" in filtered_items.columns:
        price_per_unit = filtered_items["totalPrice"] / filtered_items["quantity"]

    if price_per_unit is None:
        return go.Figure().add_annotation(
            text="No price data available to build price tiers.",
            showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper"
        )

    filtered_items = filtered_items.copy()
    filtered_items["price_per_unit"] = pd.to_numeric(price_per_unit, errors="coerce")
    filtered_items = filtered_items.dropna(subset=["price_per_unit", "quantity", "category"])

    # Define price tiers
    tiers = [
        ("₱0-10", 0, 10),
        ("₱11-20", 10, 20),
        ("₱21-30", 20, 30),
        ("₱31-50", 30, 50),
        ("₱51-70", 50, 70),
        ("₱71-100", 70, 100),
        ("₱100+", 100, float("inf")),
    ]

    def bucket_price(p):
        for label, low, high in tiers:
            if low < p <= high:
                return label
        return None

    filtered_items["price_tier"] = filtered_items["price_per_unit"].apply(bucket_price)
    filtered_items = filtered_items.dropna(subset=["price_tier"])

    # Aggregate units by category and price tier
    tier_summary = (
        filtered_items
        .groupby(["price_tier", "category"])
        .agg(units=("quantity", "sum"))
        .reset_index()
    )

    # Ensure tier order
    tier_order = [t[0] for t in tiers]
    tier_summary["price_tier"] = pd.Categorical(tier_summary["price_tier"], categories=tier_order, ordered=True)
    tier_summary = tier_summary.sort_values(["price_tier", "category"])

    # Build stacked bar
    fig = go.Figure()
    categories = sorted(tier_summary["category"].unique())

    for cat in categories:
        cat_data = tier_summary[tier_summary["category"] == cat]
        fig.add_trace(
            go.Bar(
                x=cat_data["price_tier"],
                y=cat_data["units"],
                name=cat,
                hovertemplate="<b>%{x}</b><br>%{y:.0f} units<br>Category: %{customdata}<extra></extra>",
                customdata=cat_data["category"],
            )
        )

    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Category Composition by Price Tier",
        "Price Tier",
        "Units Sold",
        "",
        xaxis=dict(
            title="Price Tier",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Units Sold",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="stack",
        height=600,
        hovermode="x unified",
        legend=dict(
            orientation="v",
            bgcolor="#1a1a1a",
            bordercolor="#3a3a3a",
            font=dict(color="#e0e0e0"),
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
    )

    return fig

@callback(
    Output("category-ranking-table", "children"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_category_ranking_table(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a ranked table showing category performance with strategic tiers."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Check available columns
    available_cols = filtered_items.columns.tolist()
    
    # Calculate category summary
    agg_dict = {}
    if "quantity" in available_cols:
        agg_dict["total_units"] = ("quantity", "sum")
    if "totalPrice" in available_cols:
        agg_dict["total_revenue"] = ("totalPrice", "sum")
    elif "unitPrice" in available_cols and "quantity" in available_cols:
        # Calculate revenue from unitPrice * quantity
        filtered_items["calculated_revenue"] = filtered_items["unitPrice"] * filtered_items["quantity"]
        agg_dict["total_revenue"] = ("calculated_revenue", "sum")
    
    if not agg_dict:
        return html.Div("No data available for ranking.")
    
    category_summary = (
        filtered_items.groupby("category")
        .agg(**agg_dict)
        .reset_index()
    )
    
    # Calculate total units for percentage
    total_units = category_summary["total_units"].sum() if "total_units" in category_summary.columns else 0
    
    if total_units > 0:
        category_summary["unit_percentage"] = (category_summary["total_units"] / total_units) * 100
    else:
        category_summary["unit_percentage"] = 0
    
    # Sort by total units and add rank
    category_summary = category_summary.sort_values("total_units", ascending=False).reset_index(drop=True)
    category_summary["rank"] = category_summary.index + 1
    
    # Assign strategic tiers based on rank and revenue
    def assign_strategic_tier(row):
        rank = row["rank"]
        revenue = row.get("total_revenue", 0)
        units = row["total_units"]
        pct = row["unit_percentage"]
        
        if rank <= 2:
            if pct > 20 or revenue > 100000:
                return "Core Traffic Driver"
            else:
                return "High-Frequency Impulse"
        elif rank <= 4:
            if revenue > 100000:
                return "High-Value Utility"
            else:
                return "Meal Prep Support"
        elif rank == 5:
            return "Impulse Buy"
        elif rank == 6:
            return "Hygiene/Sachet Staple"
        else:
            if pct > 3:
                return "Hygiene/Sachet Staple"
            else:
                return "Household Staple"
    
    category_summary["strategic_tier"] = category_summary.apply(assign_strategic_tier, axis=1)
    
    # Create table rows
    rows = []
    for idx, row in category_summary.iterrows():
        # Format revenue if available
        revenue_text = ""
        if "total_revenue" in row and pd.notna(row["total_revenue"]):
            revenue_text = f"₱{row['total_revenue']:,.2f}"
        else:
            revenue_text = "N/A"
        
        # Bold formatting for top performers
        units_style = {"fontWeight": "bold"} if row["rank"] <= 2 else {}
        revenue_style = {"fontWeight": "bold"} if row.get("total_revenue", 0) > 100000 else {}
        
        rows.append(
            html.Tr([
                html.Td(int(row["rank"]), style={"textAlign": "center", "fontWeight": "bold"}),
                html.Td(row["category"], style={"fontWeight": "bold"}),
                html.Td(f"{int(row['total_units']):,}", style=units_style),
                html.Td(revenue_text, style=revenue_style),
                html.Td(f"{row['unit_percentage']:.2f}%", style={"textAlign": "right"}),
                html.Td(row["strategic_tier"], style={"fontStyle": "italic"}),
            ])
        )
    
    # Create table
    table = dbc.Table(
        [
            html.Thead([
                html.Tr([
                    html.Th("Rank", style={"textAlign": "center"}),
                    html.Th("Category"),
                    html.Th("Total Units Sold", style={"textAlign": "right"}),
                    html.Th("Total Revenue (PHP)", style={"textAlign": "right"}),
                    html.Th("Unit Percentage", style={"textAlign": "right"}),
                    html.Th("Strategic Tier"),
                ])
            ]),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        className="mt-3"
    )
    
    return table

# ---------------------------
# Tobacco analytics callbacks
# ---------------------------

def _filter_tobacco_items(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    mask = (
        df["category"].str.contains("tobacco|cigarette", case=False, na=False)
        | df["brandName"].str.contains("marlboro|camel|chesterfield|fortune|winston|mighty", case=False, na=False)
    )
    return df[mask]


@callback(
    Output("tobacco-time-avgqty", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_time_avgqty(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = (
        tob.dropna(subset=["timeofday_segment"])
        .groupby("timeofday_segment")
        .agg(
            transactions=("InteractionID", "nunique"),
            avg_qty=("quantity", "mean"),
        )
        .reset_index()
    )
    summary = summary.sort_values("timeofday_segment")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["timeofday_segment"],
        y=summary["transactions"],
        name="Transactions",
        marker_color="#e65b4a",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=summary["timeofday_segment"],
        y=summary["avg_qty"],
        name="Average Quantity",
        mode="lines+markers",
        marker=dict(color="#f2a291"),
        line=dict(color="#f2a291", width=2),
        yaxis="y2",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Tobacco Products Purchase Time x Average Quantity",
        "Time of Day",
        "Transactions",
        "Average Quantity",
        yaxis2=dict(title="Average Quantity", overlaying="y", side="right", gridcolor="#3a3a3a", linecolor="#4a4a4a", titlefont=dict(color="#d4af37"), tickfont=dict(color="#e0e0e0")),
        barmode="group",
        height=400,
        legend=dict(orientation="h", x=0.3, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("tobacco-day-avgqty", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_day_avgqty(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    tob["txn_weekday"] = pd.Categorical(tob["txn_weekday"], categories=day_order, ordered=True)

    summary = (
        tob.dropna(subset=["txn_weekday"])
        .groupby("txn_weekday")
        .agg(
            transactions=("InteractionID", "nunique"),
            avg_qty=("quantity", "mean"),
        )
        .reset_index()
        .sort_values("txn_weekday")
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["txn_weekday"],
        y=summary["transactions"],
        name="Transactions",
        marker_color="#e65b4a",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=summary["txn_weekday"],
        y=summary["avg_qty"],
        name="Average Quantity",
        mode="lines+markers",
        marker=dict(color="#f2a291"),
        line=dict(color="#f2a291", width=2),
        yaxis="y2",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Tobacco Products Purchase Day x Average Quantity",
        "Day of Week",
        "Transactions",
        "Average Quantity",
        yaxis2=dict(title="Average Quantity", overlaying="y", side="right", gridcolor="#3a3a3a", linecolor="#4a4a4a", titlefont=dict(color="#d4af37"), tickfont=dict(color="#e0e0e0")),
        barmode="group",
        height=400,
        legend=dict(orientation="h", x=0.3, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("tobacco-brands", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_brands(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = (
        tob.dropna(subset=["brandName"])
        .groupby("brandName")
        .agg(
            transactions=("InteractionID", "nunique"),
            avg_qty=("quantity", "mean"),
        )
        .reset_index()
        .sort_values("transactions", ascending=False)
        .head(10)
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["brandName"],
        y=summary["transactions"],
        name="Transactions",
        marker_color="#e65b4a",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=summary["brandName"],
        y=summary["avg_qty"],
        name="Average Quantity",
        mode="lines+markers",
        marker=dict(color="#f2a291"),
        line=dict(color="#f2a291", width=2),
        yaxis="y2",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Tobacco Brands",
        "Brand",
        "Transactions",
        "Average Quantity",
        yaxis2=dict(title="Average Quantity", overlaying="y", side="right", gridcolor="#3a3a3a", linecolor="#4a4a4a", titlefont=dict(color="#d4af37"), tickfont=dict(color="#e0e0e0")),
        barmode="group",
        height=400,
        legend=dict(orientation="h", x=0.3, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("tobacco-brands-day", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_brands_day(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    tob["txn_weekday"] = pd.Categorical(tob["txn_weekday"], categories=day_order, ordered=True)

    summary = (
        tob.dropna(subset=["brandName", "txn_weekday"])
        .groupby(["brandName", "txn_weekday"])
        .agg(units=("quantity", "sum"))
        .reset_index()
    )
    brands = summary.groupby("brandName")["units"].sum().sort_values(ascending=False).head(8).index.tolist()
    summary = summary[summary["brandName"].isin(brands)]

    fig = go.Figure()
    for day in day_order:
        day_data = summary[summary["txn_weekday"] == day]
        fig.add_trace(go.Bar(
            x=day_data["brandName"],
            y=day_data["units"],
            name=day,
        ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Tobacco Brands x Day",
        "Brand",
        "Units",
        "",
        barmode="stack",
        height=400,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
            bgcolor="#1a1a1a",
            bordercolor="#3a3a3a",
            font=dict(color="#e0e0e0"),
        ),
    )
    return fig


@callback(
    Output("tobacco-gender-pie", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_gender_pie(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = tob.dropna(subset=["gender_clean"]).groupby("gender_clean").agg(units=("quantity", "sum")).reset_index()
    fig = px.pie(summary, names="gender_clean", values="units", title="Tobacco Purchases by Gender", color_discrete_sequence=px.colors.sequential.Reds)
    apply_dark_layout(fig, "Tobacco Purchases by Gender", "", "", "", height=400)
    return fig


@callback(
    Output("tobacco-age-pie", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_age_pie(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = tob.dropna(subset=["age_bucket"]).groupby("age_bucket").agg(units=("quantity", "sum")).reset_index()
    fig = px.pie(summary, names="age_bucket", values="units", title="Tobacco Purchases by Age Group", color_discrete_sequence=px.colors.sequential.Reds)
    apply_dark_layout(fig, "Tobacco Purchases by Age Group", "", "", "", height=400)
    return fig


@callback(
    Output("tobacco-gender-brand", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_gender_brand(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = (
        tob.dropna(subset=["brandName", "gender_clean"])
        .groupby(["brandName", "gender_clean"])
        .agg(units=("quantity", "sum"))
        .reset_index()
    )
    brands = summary.groupby("brandName")["units"].sum().sort_values(ascending=False).head(8).index.tolist()
    summary = summary[summary["brandName"].isin(brands)]

    female = []
    male = []
    ordered_brands = []
    for b in brands:
        bdata = summary[summary["brandName"] == b]
        total = bdata["units"].sum()
        f_units = bdata[bdata["gender_clean"] == "Female"]["units"].sum() if not bdata[bdata["gender_clean"] == "Female"].empty else 0
        m_units = bdata[bdata["gender_clean"] == "Male"]["units"].sum() if not bdata[bdata["gender_clean"] == "Male"].empty else 0
        if total > 0:
            female.append((f_units / total) * 100)
            male.append((m_units / total) * 100)
        else:
            female.append(0)
            male.append(0)
        ordered_brands.append(b)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=ordered_brands,
        x=female,
        name="Female",
        orientation="h",
        marker=dict(color="#e65b4a"),
        text=[f"{p:.1f}%" for p in female],
        textposition="inside",
    ))
    fig.add_trace(go.Bar(
        y=ordered_brands,
        x=male,
        name="Male",
        orientation="h",
        marker=dict(color="#f2a291"),
        text=[f"{p:.1f}%" for p in male],
        textposition="inside",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Gender x Tobacco Brands Purchased",
        "Percentage (%)",
        "Brand",
        "",
        xaxis=dict(
            title="Percentage (%)",
            range=[0, 100],
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Brand",
            autorange="reversed",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="stack",
        height=500,
        hovermode="y unified",
        legend=dict(orientation="h", x=0.4, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("tobacco-cluster-items", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_cluster_items(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    marlboro_txns = items_filtered[items_filtered["brandName"].str.contains("marlboro", case=False, na=False)]
    if marlboro_txns.empty:
        return go.Figure().add_annotation(text="No Marlboro data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    counts = (
        marlboro_txns.groupby("InteractionID")
        .agg(item_count=("productName", "count"))
        .reset_index()
    )
    summary = counts.groupby("item_count").agg(freq=("InteractionID", "count")).reset_index()
    fig = px.pie(summary, names="item_count", values="freq", title="Number of Items Purchased with Marlboro", color_discrete_sequence=px.colors.sequential.Reds)
    apply_dark_layout(fig, "Number of Items Purchased with Marlboro", "", "", "", height=400)
    return fig


@callback(
    Output("tobacco-cluster-categories", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_cluster_categories(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    marlboro_txns = items_filtered[items_filtered["brandName"].str.contains("marlboro", case=False, na=False)]
    if marlboro_txns.empty:
        return go.Figure().add_annotation(text="No Marlboro data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    txn_ids = marlboro_txns["InteractionID"].unique()
    companions = items_filtered[items_filtered["InteractionID"].isin(txn_ids)]
    summary = (
        companions.groupby("category")
        .agg(freq=("quantity", "sum"))
        .reset_index()
        .sort_values("freq", ascending=False)
        .head(12)
    )
    fig = px.bar(summary, x="freq", y="category", orientation="h", title="Categories Purchased with Marlboro", color_discrete_sequence=["#e65b4a"])
    # Apply dark mode layout with explicit height
    apply_dark_layout(
        fig,
        "Categories Purchased with Marlboro",
        "Frequency",
        "Category",
        "",
        yaxis=dict(autorange="reversed"),
        height=400,
    )
    return fig


@callback(
    Output("tobacco-cluster-brands", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_tobacco_cluster_brands(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    marlboro_txns = items_filtered[items_filtered["brandName"].str.contains("marlboro", case=False, na=False)]
    if marlboro_txns.empty:
        return go.Figure().add_annotation(text="No Marlboro data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    txn_ids = marlboro_txns["InteractionID"].unique()
    companions = items_filtered[(items_filtered["InteractionID"].isin(txn_ids))]
    companions = companions[~companions["brandName"].str.contains("marlboro", case=False, na=False)]

    summary = (
        companions.groupby("brandName")
        .agg(freq=("quantity", "sum"))
        .reset_index()
        .sort_values("freq", ascending=False)
        .head(10)
    )
    fig = px.bar(summary, x="freq", y="brandName", orientation="h", title="Top 10 Brands Purchased with Marlboro", color_discrete_sequence=["#e65b4a"])
    apply_dark_layout(
        fig,
        "Top 10 Brands Purchased with Marlboro",
        "Frequency",
        "Brand",
        "",
        yaxis=dict(autorange="reversed"),
        height=400,
    )
    return fig

# ---------------------------
# Laundry analytics callbacks (mirroring tobacco analytics)
# ---------------------------

def _filter_laundry_items(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    mask = (
        df["category"].str.contains("laundry|detergent|fabric|softener|conditioner", case=False, na=False)
        | df["brandName"].str.contains("surf|ariel|tide|downy|breeze|perla", case=False, na=False)
    )
    return df[mask]


@callback(
    Output("laundry-time-avgqty", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_time_avgqty(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = (
        lau.dropna(subset=["timeofday_segment"])
        .groupby("timeofday_segment")
        .agg(
            transactions=("InteractionID", "nunique"),
            avg_qty=("quantity", "mean"),
        )
        .reset_index()
    )
    summary = summary.sort_values("timeofday_segment")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["timeofday_segment"],
        y=summary["transactions"],
        name="Transactions",
        marker_color="#4a90e2",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=summary["timeofday_segment"],
        y=summary["avg_qty"],
        name="Average Quantity",
        mode="lines+markers",
        marker=dict(color="#a3c7f9"),
        line=dict(color="#a3c7f9", width=2),
        yaxis="y2",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Laundry Products Purchase Time x Average Quantity",
        "Time of Day",
        "Transactions",
        "Average Quantity",
        yaxis2=dict(title="Average Quantity", overlaying="y", side="right", gridcolor="#3a3a3a", linecolor="#4a4a4a", titlefont=dict(color="#d4af37"), tickfont=dict(color="#e0e0e0")),
        barmode="group",
        height=400,
        legend=dict(orientation="h", x=0.3, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("laundry-day-avgqty", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_day_avgqty(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    lau["txn_weekday"] = pd.Categorical(lau["txn_weekday"], categories=day_order, ordered=True)

    summary = (
        lau.dropna(subset=["txn_weekday"])
        .groupby("txn_weekday")
        .agg(
            transactions=("InteractionID", "nunique"),
            avg_qty=("quantity", "mean"),
        )
        .reset_index()
        .sort_values("txn_weekday")
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["txn_weekday"],
        y=summary["transactions"],
        name="Transactions",
        marker_color="#4a90e2",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=summary["txn_weekday"],
        y=summary["avg_qty"],
        name="Average Quantity",
        mode="lines+markers",
        marker=dict(color="#a3c7f9"),
        line=dict(color="#a3c7f9", width=2),
        yaxis="y2",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Laundry Products Purchase Day x Average Quantity",
        "Day of Week",
        "Transactions",
        "Average Quantity",
        yaxis2=dict(title="Average Quantity", overlaying="y", side="right", gridcolor="#3a3a3a", linecolor="#4a4a4a", titlefont=dict(color="#d4af37"), tickfont=dict(color="#e0e0e0")),
        barmode="group",
        height=400,
        legend=dict(orientation="h", x=0.3, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("laundry-brands", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_brands(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = (
        lau.dropna(subset=["brandName"])
        .groupby("brandName")
        .agg(
            transactions=("InteractionID", "nunique"),
            avg_qty=("quantity", "mean"),
        )
        .reset_index()
        .sort_values("transactions", ascending=False)
        .head(10)
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=summary["brandName"],
        y=summary["transactions"],
        name="Transactions",
        marker_color="#4a90e2",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=summary["brandName"],
        y=summary["avg_qty"],
        name="Average Quantity",
        mode="lines+markers",
        marker=dict(color="#a3c7f9"),
        line=dict(color="#a3c7f9", width=2),
        yaxis="y2",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Laundry Brands",
        "Brand",
        "Transactions",
        "Average Quantity",
        yaxis2=dict(title="Average Quantity", overlaying="y", side="right", gridcolor="#3a3a3a", linecolor="#4a4a4a", titlefont=dict(color="#d4af37"), tickfont=dict(color="#e0e0e0")),
        barmode="group",
        height=400,
        legend=dict(orientation="h", x=0.3, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("laundry-brands-day", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_brands_day(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    lau["txn_weekday"] = pd.Categorical(lau["txn_weekday"], categories=day_order, ordered=True)

    summary = (
        lau.dropna(subset=["brandName", "txn_weekday"])
        .groupby(["brandName", "txn_weekday"])
        .agg(units=("quantity", "sum"))
        .reset_index()
    )
    brands = summary.groupby("brandName")["units"].sum().sort_values(ascending=False).head(8).index.tolist()
    summary = summary[summary["brandName"].isin(brands)]

    fig = go.Figure()
    for day in day_order:
        day_data = summary[summary["txn_weekday"] == day]
        fig.add_trace(go.Bar(
            x=day_data["brandName"],
            y=day_data["units"],
            name=day,
        ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Laundry Brands x Day",
        "Brand",
        "Units",
        "",
        barmode="stack",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("laundry-gender-pie", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_gender_pie(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = lau.dropna(subset=["gender_clean"]).groupby("gender_clean").agg(units=("quantity", "sum")).reset_index()
    fig = px.pie(summary, names="gender_clean", values="units", title="Laundry Purchases by Gender", color_discrete_sequence=px.colors.sequential.Blues)
    apply_dark_layout(fig, "Laundry Purchases by Gender", "", "", "", height=400)
    return fig


@callback(
    Output("laundry-age-pie", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_age_pie(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = lau.dropna(subset=["age_bucket"]).groupby("age_bucket").agg(units=("quantity", "sum")).reset_index()
    fig = px.pie(summary, names="age_bucket", values="units", title="Laundry Purchases by Age Group", color_discrete_sequence=px.colors.sequential.Blues)
    apply_dark_layout(fig, "Laundry Purchases by Age Group", "", "", "", height=400)
    return fig


@callback(
    Output("laundry-gender-brand", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_gender_brand(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    lau = _filter_laundry_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category))
    if lau.empty:
        return go.Figure().add_annotation(text="No laundry data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = (
        lau.dropna(subset=["brandName", "gender_clean"])
        .groupby(["brandName", "gender_clean"])
        .agg(units=("quantity", "sum"))
        .reset_index()
    )
    brands = summary.groupby("brandName")["units"].sum().sort_values(ascending=False).head(8).index.tolist()
    summary = summary[summary["brandName"].isin(brands)]

    female = []
    male = []
    ordered_brands = []
    for b in brands:
        bdata = summary[summary["brandName"] == b]
        total = bdata["units"].sum()
        f_units = bdata[bdata["gender_clean"] == "Female"]["units"].sum() if not bdata[bdata["gender_clean"] == "Female"].empty else 0
        m_units = bdata[bdata["gender_clean"] == "Male"]["units"].sum() if not bdata[bdata["gender_clean"] == "Male"].empty else 0
        if total > 0:
            female.append((f_units / total) * 100)
            male.append((m_units / total) * 100)
        else:
            female.append(0)
            male.append(0)
        ordered_brands.append(b)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=ordered_brands,
        x=female,
        name="Female",
        orientation="h",
        marker=dict(color="#4a90e2"),
        text=[f"{p:.1f}%" for p in female],
        textposition="inside",
    ))
    fig.add_trace(go.Bar(
        y=ordered_brands,
        x=male,
        name="Male",
        orientation="h",
        marker=dict(color="#a3c7f9"),
        text=[f"{p:.1f}%" for p in male],
        textposition="inside",
    ))
    # Apply dark mode layout
    apply_dark_layout(
        fig,
        "Gender x Laundry Brands Purchased",
        "Percentage (%)",
        "Brand",
        "",
        xaxis=dict(
            title="Percentage (%)",
            range=[0, 100],
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        yaxis=dict(
            title="Brand",
            autorange="reversed",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        barmode="stack",
        height=500,
        hovermode="y unified",
        legend=dict(orientation="h", x=0.4, y=-0.2, bgcolor="#1a1a1a", bordercolor="#3a3a3a", font=dict(color="#e0e0e0")),
    )
    return fig


@callback(
    Output("laundry-cluster-items", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_cluster_items(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    anchor_txns = items_filtered[items_filtered["brandName"].str.contains("surf", case=False, na=False)]
    if anchor_txns.empty:
        return go.Figure().add_annotation(text="No Surf data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    counts = (
        anchor_txns.groupby("InteractionID")
        .agg(item_count=("productName", "count"))
        .reset_index()
    )
    summary = counts.groupby("item_count").agg(freq=("InteractionID", "count")).reset_index()
    fig = px.pie(summary, names="item_count", values="freq", title="Number of Items Purchased with Surf", color_discrete_sequence=px.colors.sequential.Blues)
    apply_dark_layout(fig, "Number of Items Purchased with Surf", "", "", "", height=400)
    return fig


@callback(
    Output("laundry-cluster-categories", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_cluster_categories(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    anchor_txns = items_filtered[items_filtered["brandName"].str.contains("surf", case=False, na=False)]
    if anchor_txns.empty:
        return go.Figure().add_annotation(text="No Surf data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    txn_ids = anchor_txns["InteractionID"].unique()
    companions = items_filtered[items_filtered["InteractionID"].isin(txn_ids)]
    summary = (
        companions.groupby("category")
        .agg(freq=("quantity", "sum"))
        .reset_index()
        .sort_values("freq", ascending=False)
        .head(12)
    )
    fig = px.bar(summary, x="freq", y="category", orientation="h", title="Categories Purchased with Surf", color_discrete_sequence=["#4a90e2"])
    # Apply dark mode layout with explicit height
    apply_dark_layout(
        fig,
        "Categories Purchased with Surf",
        "Frequency",
        "Category",
        "",
        yaxis=dict(autorange="reversed"),
        height=400,
    )
    return fig


@callback(
    Output("laundry-cluster-brands", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_laundry_cluster_brands(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    anchor_txns = items_filtered[items_filtered["brandName"].str.contains("surf", case=False, na=False)]
    if anchor_txns.empty:
        return go.Figure().add_annotation(text="No Surf data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    txn_ids = anchor_txns["InteractionID"].unique()
    companions = items_filtered[(items_filtered["InteractionID"].isin(txn_ids))]
    companions = companions[~companions["brandName"].str.contains("surf", case=False, na=False)]

    summary = (
        companions.groupby("brandName")
        .agg(freq=("quantity", "sum"))
        .reset_index()
        .sort_values("freq", ascending=False)
        .head(10)
    )
    fig = px.bar(summary, x="freq", y="brandName", orientation="h", title="Top Brands Purchased with Surf", color_discrete_sequence=["#4a90e2"])
    # Apply dark mode layout with explicit height
    apply_dark_layout(
        fig,
        "Top Brands Purchased with Surf",
        "Frequency",
        "Brand",
        "",
        yaxis=dict(autorange="reversed"),
        height=400,
    )
    return fig

@callback(
    Output("top-products-table", "children"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_top_products_table(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a table showing top products by time of day."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    # Time segment emojis and labels
    time_segment_info = {
        "Morning (5a-12p)": "🌅",
        "Afternoon (12p-6p)": "☀️",
        "Evening (6p-10p)": "🌙",
        "Late Night (10p-5a)": "🌃",
    }
    
    # Get top products for each time segment
    top_n = 5
    tables = []
    
    for time_segment, emoji in time_segment_info.items():
        segment_data = filtered_items[
            filtered_items["timeofday_segment"] == time_segment
        ]
        
        if not segment_data.empty:
            # Group by product name and sum quantities
            top_products = (
                segment_data.groupby("productName")
                .agg(total_units=("quantity", "sum"))
                .reset_index()
                .sort_values("total_units", ascending=False)
                .head(top_n)
            )
            
            # Create table rows
            rows = []
            for idx, row in top_products.iterrows():
                rows.append(
                    html.Tr([
                        html.Td(f"• {row['productName']}", style={"padding": "5px"}),
                        html.Td(f"({int(row['total_units'])} units)", style={"padding": "5px", "textAlign": "right"}),
                    ])
                )
            
            # Create table for this time segment
            tables.append(
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.Span(emoji, style={"marginRight": "10px"}),
                            html.Span(time_segment),
                        ], style={"margin": 0}),
                    ]),
                    dbc.CardBody([
                        dbc.Table(
                            [
                                html.Tbody(rows),
                            ],
                            bordered=False,
                            hover=True,
                            responsive=True,
                            striped=False
                        ),
                    ]),
                ], className="mb-3")
            )
    
    # Arrange in a grid
    return dbc.Row([
        dbc.Col(tables[0] if len(tables) > 0 else html.Div(), md=6),
        dbc.Col(tables[1] if len(tables) > 1 else html.Div(), md=6),
        dbc.Col(tables[2] if len(tables) > 2 else html.Div(), md=6),
        dbc.Col(tables[3] if len(tables) > 3 else html.Div(), md=6),
    ])


@callback(
    Output("products-bought-together", "figure"),
    [Input("date-range", "start_date"), Input("date-range", "end_date"),
     Input("gender-filter", "value"), Input("age-filter", "value"),
     Input("payment-filter", "value"),
     Input("month-year-filter", "value"), Input("weekday-weekend-filter", "value"),
     Input("category-filter", "value")],
)
def update_products_bought_together(start_date, end_date, gender, age, payment, month_year, weekday_weekend, category):
    """Create a horizontal bar chart showing products frequently bought together."""
    from itertools import combinations
    
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend, category)
    
    if filtered_items.empty or "InteractionID" not in filtered_items.columns or "productName" not in filtered_items.columns:
        return go.Figure().add_annotation(
            text="No data available for products bought together",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper"
        )
    
    # Group by transaction to get products bought together
    product_pairs = []
    for interaction_id, group in filtered_items.groupby("InteractionID"):
        # Get unique products in this transaction
        products = group["productName"].dropna().unique().tolist()
        
        # Only create pairs if there are at least 2 products
        if len(products) >= 2:
            # Create all pairs of products in this transaction
            for pair in combinations(sorted(products), 2):
                product_pairs.append(pair)
    
    if not product_pairs:
        return go.Figure().add_annotation(
            text="No product pairs found (transactions need at least 2 products)",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper"
        )
    
    # Count frequency of each pair
    pair_counts = {}
    for pair in product_pairs:
        pair_key = f"{pair[0]} & {pair[1]}"
        pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
    
    # Convert to DataFrame and sort by frequency
    pairs_df = pd.DataFrame([
        {"Product Pair": pair, "Frequency": count}
        for pair, count in pair_counts.items()
    ]).sort_values("Frequency", ascending=False).head(20)  # Top 20 pairs
    
    # Create horizontal bar chart
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            y=pairs_df["Product Pair"],
            x=pairs_df["Frequency"],
            orientation="h",
            marker_color="gold",
            text=pairs_df["Frequency"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Frequency: %{x}<extra></extra>",
        )
    )
    
    apply_dark_layout(
        fig,
        "Top 20 Products Bought Together",
        "Frequency (Number of Transactions)",
        "Product Pair",
        "",
        height=max(600, len(pairs_df) * 30),  # Dynamic height based on number of pairs
        yaxis=dict(
            title="Product Pair",
            autorange="reversed",  # Show highest frequency at top
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
        xaxis=dict(
            title="Frequency (Number of Transactions)",
            gridcolor="#3a3a3a",
            linecolor="#4a4a4a",
            titlefont=dict(color="#d4af37"),
            tickfont=dict(color="#e0e0e0"),
        ),
    )
    
    return fig
# Query Editor Callbacks

def validate_select_query(query: str) -> Tuple[bool, str]:
    """Validate that the query is a SELECT statement only."""
    # Remove comments and normalize whitespace
    query_clean = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    query_clean = ' '.join(query_clean.split())
    
    # Check if query starts with SELECT (case insensitive)
    if not query_clean.strip().upper().startswith('SELECT'):
        return False, "Only SELECT queries are allowed."
    
    # Block dangerous keywords
    dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
    query_upper = query_clean.upper()
    for keyword in dangerous_keywords:
        if f' {keyword} ' in query_upper or query_upper.startswith(keyword + ' '):
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
            className="table-sm"
        )
    except Exception as e:
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
            className="table-sm"
        )
    except Exception as e:
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
            if db_engine:
                with db_engine.connect() as conn:
                    result = conn.execute(text(query_text))
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
            else:
                # Fallback: Try to parse simple queries and use Supabase REST API
                query_lower = query_text.lower().strip()
                
                # Handle simple SELECT * FROM table LIMIT n queries
                if query_lower.startswith("select * from"):
                    # Extract table name
                    match = re.search(r'from\s+(\w+)', query_lower)
                    if match:
                        table_name = match.group(1)
                        # Extract LIMIT if present
                        limit_match = re.search(r'limit\s+(\d+)', query_lower)
                        limit = int(limit_match.group(1)) if limit_match else 1000
                        
                        response = supabase.table(table_name).select("*").limit(limit).execute()
                        df = pd.DataFrame(response.data)
                    else:
                        return dbc.Alert("Complex queries require database connection. Please set DB_CONNECTION_STRING in .env file.", color="warning"), dash.no_update
                else:
                    return dbc.Alert("Complex queries require database connection. Please set DB_CONNECTION_STRING in .env file.", color="warning"), dash.no_update
            
            if df.empty:
                return dbc.Alert("Query executed successfully but returned no results.", color="info"), dash.no_update
            
            # Create results table
            results_table = dbc.Table.from_dataframe(
                df,
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
                className="table-sm"
            )
            
            # Create summary
            summary = html.Div([
                dbc.Alert(f"Query executed successfully. Returned {len(df)} row(s) with {len(df.columns)} column(s).", color="success", className="mb-3"),
                results_table,
            ])
            
            return summary, dash.no_update
            
        except SQLAlchemyError as e:
            return dbc.Alert(f"Database error: {str(e)}", color="danger"), dash.no_update
        except Exception as e:
            return dbc.Alert(f"Error executing query: {str(e)}", color="danger"), dash.no_update
    
    return "", dash.no_update

# Ask AI Callbacks
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
        
        # Show loading state
        loading_alert = dbc.Alert([
            html.Div([
                html.Span([dbc.Spinner(size="sm")], className="me-2"),
                "Generating SQL query and fetching results..."
            ])
        ], color="info")
        
        # Generate SQL from question
        sql_query, error = generate_sql_from_question(question)
        
        if error:
            return dbc.Alert(f"Error: {error}", color="danger"), dash.no_update
        
        if not sql_query:
            return dbc.Alert("Failed to generate SQL query. Please try rephrasing your question.", color="warning"), dash.no_update
        
        # Validate the generated SQL
        is_valid, validation_error = validate_select_query(sql_query)
        if not is_valid:
            return dbc.Alert([
                html.H5("Generated SQL Query (Invalid):", className="mb-2"),
                html.Pre(sql_query, style={"backgroundColor": "#f8f9fa", "padding": "10px", "borderRadius": "5px", "overflow": "auto"}),
                html.P(f"Validation Error: {validation_error}", className="mt-2 text-danger"),
            ], color="danger"), dash.no_update
        
        # Execute the SQL query directly
        df, error_msg = execute_sql_directly(sql_query)
        if error_msg:
            return dbc.Alert([
                html.H5("Generated SQL Query:", className="mb-2"),
                html.Pre(sql_query, style={"backgroundColor": "#f8f9fa", "padding": "10px", "borderRadius": "5px", "overflow": "auto"}),
                html.P(f"Error: {error_msg}", className="mt-2 text-danger"),
            ], color="danger"), dash.no_update
        
        # Process and display results
        if df.empty:
            return html.Div([
                dbc.Alert("Query executed successfully but returned no results.", color="info", className="mb-3"),
                html.H5("Generated SQL Query:", className="mb-2"),
                html.Pre(sql_query, style={"backgroundColor": "#f8f9fa", "padding": "10px", "borderRadius": "5px", "overflow": "auto", "fontSize": "12px"}),
            ]), dash.no_update
        
        # Create results table
        results_table = dbc.Table.from_dataframe(
            df,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            className="table-sm"
        )
        
        # Create summary with SQL query and results
        summary = html.Div([
            dbc.Alert([
                html.H5("✓ Query executed successfully!", className="mb-2"),
                html.P(f"Returned {len(df)} row(s) with {len(df.columns)} column(s).", className="mb-0"),
            ], color="success", className="mb-3"),
            html.H5("Generated SQL Query:", className="mb-2"),
            html.Pre(sql_query, style={"backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px", "overflow": "auto", "fontSize": "13px", "border": "1px solid #dee2e6"}),
            html.H5("Results:", className="mb-2 mt-4"),
            results_table,
        ])
        
        return summary, dash.no_update
    
    return "", dash.no_update

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    debug = os.getenv("DEBUG")
    app.run_server(debug=debug, host="0.0.0.0", port=port)