"""
Common utility functions for TWBA Dashboard charts.
"""
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from supabase import Client


def load_transactions(supabase: Client) -> pd.DataFrame:
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


def load_items(supabase: Client) -> pd.DataFrame:
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
    
    # Filter out outliers: drop rows where basket_total < 500
    if "basket_total" in filtered.columns:
        filtered = filtered[filtered["basket_total"] >= 500]
    
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
            filtered = filtered[filtered["category"].isin(category)]
    
    return filtered


def validate_plot_data(data, required_columns=None):
    """Validate data before plotting to prevent axis scaling errors."""
    if data is None or (hasattr(data, 'empty') and data.empty):
        return False, "Data is empty"
    
    if required_columns:
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            return False, f"Missing required columns: {missing_cols}"
    
    # Check for all NaN values in numeric columns
    if hasattr(data, 'select_dtypes'):
        numeric_cols = data.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if data[col].notna().sum() == 0:
                return False, f"Column {col} contains only NaN values"
    
    return True, "OK"


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
        type="linear",  # Explicitly set axis type
    )
    if xaxis_title:
        base_xaxis["title"] = xaxis_title
    
    base_yaxis = dict(
        gridcolor="#3a3a3a",
        linecolor="#4a4a4a",
        titlefont=dict(color="#d4af37"),
        tickfont=dict(color="#e0e0e0"),
        type="linear",  # Explicitly set axis type
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
            type="linear",  # Explicitly set axis type
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
        dark_layout["height"] = 300  # Default height
    
    # CRITICAL: Set autosize to False to prevent Plotly from auto-sizing
    dark_layout["autosize"] = False
    
    # Apply layout (this replaces the entire layout, not accumulates)
    try:
        fig.update_layout(**dark_layout)
    except Exception as e:
        # If layout update fails, try with minimal settings
        print(f"Warning: Layout update failed, using minimal layout: {e}")
        fig.update_layout(
            title=dict(text=title, font=dict(color="#d4af37", size=16)),
            paper_bgcolor="#1a1a1a",
            plot_bgcolor="#1a1a1a",
            font=dict(color="#e0e0e0", size=12),
            height=dark_layout.get("height", 300),
            autosize=False,
        )

