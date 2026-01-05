"""
Consumer demographics chart builders for TWBA Dashboard.

Each function here is a pure helper that takes data + filter inputs and
returns a Plotly figure or Dash children. Dash callbacks in app.py simply
call these helpers, so app.py stays thin.
"""

from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html
import dash_bootstrap_components as dbc

from charts.utils import filter_data, apply_dark_layout


# NOTE: All functions below expect either transactions_df or items_df
# to be passed from app.py. They do NOT access globals.


def build_gender_combined_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create Gender Demographics: Transactions & Average Spend chart."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    gender_summary = (
        filtered.groupby("gender_clean")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )

    fig = go.Figure()

    # Bars for transactions
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

    # Line for average spend
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
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="#1a1a1a",
            bordercolor="#3a3a3a",
            font=dict(color="#e0e0e0"),
        ),
        height=500,
    )
    return fig


def build_gender_mom_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Month-on-Month Transactions by Gender."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

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


def build_age_bucket_combined_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Age Demographics: Transactions & Average Spend."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    age_summary = (
        filtered.dropna(subset=["age_bucket"])
        .groupby("age_bucket")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )

    age_order = ["<18", "18-24", "25-34", "35-44", "45-54", "55+"]
    age_summary["age_bucket"] = pd.Categorical(age_summary["age_bucket"], categories=age_order, ordered=True)
    age_summary = age_summary.sort_values("age_bucket")

    fig = go.Figure()

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


def build_payment_combined_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Payment Method: Transactions & Average Spend."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    tender_summary = (
        filtered.groupby("payment_method")
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )

    fig = go.Figure()

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


def build_weekday_weekend_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a dual-axis chart: bars for transactions, line for average spend (Weekday vs Weekend)."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    filtered["weekday_type"] = filtered["TransactionDate"].dt.dayofweek.apply(
        lambda x: "Weekend" if x >= 5 else "Weekday"
    )

    week_summary = (
        filtered.groupby("weekday_type")
        .agg(
            total_transactions=("InteractionID", "count",
    ),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )

    fig = go.Figure()

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


def build_time_of_day_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a dual-axis chart: bars for transactions, line for average spend by time of day."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    filtered["weekday_type"] = filtered["TransactionDate"].dt.dayofweek.apply(
        lambda x: "Weekend" if x >= 5 else "Weekday"
    )

    timeofday_summary = (
        filtered.dropna(subset=["timeofday_segment"])
        .groupby(["weekday_type", "timeofday_segment"],
    )
        .agg(
            total_transactions=("InteractionID", "count"),
            avg_spend=("basket_total", "mean"),
        )
        .reset_index()
    )

    fig = go.Figure()

    time_segments = sorted(timeofday_summary["timeofday_segment"].unique())
    for wd_type in ["Weekday", "Weekend"]:
        data = timeofday_summary[timeofday_summary["weekday_type"] == wd_type]
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

    avg_spend_by_time = (
        filtered.dropna(subset=["timeofday_segment"])
        .groupby("timeofday_segment")
        .agg(avg_spend=("basket_total", "mean"))
        .reset_index()
    )
    avg_spend_by_time = avg_spend_by_time.sort_values("timeofday_segment")

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


def build_day_of_week_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a dual-axis chart: bars for transactions, line for average spend by day of week."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    filtered["day_of_week"] = filtered["TransactionDate"].dt.day_name()

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    filtered["day_of_week"] = pd.Categorical(filtered["day_of_week"], categories=day_order, ordered=True)

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

    fig = go.Figure()

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


def build_gender_time_distribution_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a 100% stacked horizontal bar chart showing gender distribution by time of day."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    time_gender_summary = (
        filtered.dropna(subset=["timeofday_segment", "gender_clean"])
        .groupby(["timeofday_segment", "gender_clean"])
        .agg(total_transactions=("InteractionID", "count"))
        .reset_index()
    )

    time_segments = sorted(time_gender_summary["timeofday_segment"].unique())
    genders = ["Female", "Male"]

    female_percentages = []
    male_percentages = []

    for segment in time_segments:
        segment_data = time_gender_summary[time_gender_summary["timeofday_segment"] == segment]
        total = segment_data["total_transactions"].sum()

        female_count = (
            segment_data[segment_data["gender_clean"] == "Female"]["total_transactions"].sum()
            if not segment_data[segment_data["gender_clean"] == "Female"].empty
            else 0
        )
        male_count = (
            segment_data[segment_data["gender_clean"] == "Male"]["total_transactions"].sum()
            if not segment_data[segment_data["gender_clean"] == "Male"].empty
            else 0
        )

        if total > 0:
            female_percentages.append((female_count / total) * 100)
            male_percentages.append((male_count / total) * 100)
        else:
            female_percentages.append(0)
            male_percentages.append(0)

    fig = go.Figure()

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
            autorange="reversed",
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


def build_daily_sales_payday_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a line chart showing average daily sales by day of month with payday windows and petsa de peligro zones."""
    filtered = filter_data(
        transactions_df,
        [start_date, end_date],
        gender,
        age,
        payment,
        month_year,
        weekday_weekend,
    )

    filtered["day_of_month"] = filtered["TransactionDate"].dt.day

    daily_sales = (
        filtered.groupby("day_of_month")
        .agg(avg_sales=("basket_total", "mean",
    ))
        .reset_index()
        .sort_values("day_of_month")
    )

    payday_days = [15, 30]

    payday_windows = set()
    for payday in payday_days:
        for day in range(payday - 2, payday + 3):
            if 1 <= day <= 31:
                payday_windows.add(day)

    petsa_de_peligro = set(range(1, 6))  # Days 1-5

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=daily_sales["day_of_month"],
            y=daily_sales["avg_sales"],
            mode="lines+markers",
            name="Average Sales",
            line=dict(color="orange", width=2),
            marker=dict(size=6, color="orange"),
            hovertemplate="<b>Day %{x}</b><br>Average Sales: ₱%{y:,.2f}<extra></extra>",
        )
    )

    for day in payday_windows:
        if day in daily_sales["day_of_month"].values:
            fig.add_vline(
                x=day,
                line_width=2,
                line_dash="dash",
                line_color="green",
                annotation_text="Payday",
                annotation_position="top",
                showlegend=False,
            )

    for day in petsa_de_peligro:
        if day in daily_sales["day_of_month"].values:
            fig.add_vline(
                x=day,
                line_width=1,
                line_dash="dot",
                line_color="red",
                annotation_text="Petsa de Peligro",
                annotation_position="bottom",
                showlegend=False,
            )

    apply_dark_layout(
        fig,
        "Average Daily Sales by Day of Month (Petsa de Peligro vs Payday Windows)",
        "Day of Month",
        "Average Sales (₱)",
        "",
        height=500,
    )
    # Hide any unwanted legend entries (like "Brown: overlap" from vlines)
    fig.update_layout(
        legend=dict(
            itemsizing="constant",
        )
    )
    # Ensure only the main trace shows in legend
    for trace in fig.data:
        if trace.name != "Average Sales":
            trace.showlegend = False
    return fig


def build_basket_bands_figure(
    transactions_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Basket Value Distribution chart."""
    filtered = filter_data(transactions_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    if "basket_total" not in filtered.columns or filtered.empty:
        return go.Figure().add_annotation(
            text="No basket data available", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
        )

    filtered = filtered.copy()
    filtered["basket_total"] = pd.to_numeric(filtered["basket_total"], errors="coerce")
    filtered = filtered.dropna(subset=["basket_total"])
    if filtered.empty:
        return go.Figure().add_annotation(
            text="No basket data available", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
        )

    def basket_band(value):
        if pd.isna(value):
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

    if basket_summary.empty:
        return go.Figure().add_annotation(
            text="No basket data available for selected filters",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
        )

    band_order = ["₱0-10", "₱11-20", "₱21-50", "₱51-100", "₱101-200", "₱200+"]
    basket_summary["basket_band"] = pd.Categorical(basket_summary["basket_band"], categories=band_order, ordered=True)
    basket_summary = basket_summary.sort_values("basket_band")

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
    fig.update_traces(textposition="outside")
    apply_dark_layout(fig, "Basket Value Distribution", "Basket Band", "Transactions", "", height=500)
    return fig


def build_category_performance_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Top Categories by Revenue or Units chart."""
    try:
        filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

        if "totalPrice" not in filtered_items.columns and "unitPrice" in filtered_items.columns and "quantity" in filtered_items.columns:
            filtered_items["totalPrice"] = filtered_items["unitPrice"] * filtered_items["quantity"]

        if filtered_items.empty or "category" not in filtered_items.columns:
            return go.Figure().add_annotation(
                text="No data available", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
            )

        category_summary = filtered_items.groupby("category").agg(
            revenue=("totalPrice", "sum") if "totalPrice" in filtered_items.columns else ("unitPrice", "sum"),
            units=("quantity", "sum"),
        ).reset_index()

        category_summary = category_summary.sort_values("units", ascending=False)

        y_col = "revenue" if "revenue" in category_summary.columns else "units"
        text_col = "units" if "units" in category_summary.columns and y_col == "revenue" else None

        if y_col not in category_summary.columns:
            return go.Figure().add_annotation(
                text="No data available for chart", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
            )

        category_summary[y_col] = pd.to_numeric(category_summary[y_col], errors="coerce")
        if text_col:
            category_summary[text_col] = pd.to_numeric(category_summary[text_col], errors="coerce")
        category_summary = category_summary.dropna(subset=[y_col, "category"])

        if category_summary.empty:
            return go.Figure().add_annotation(
                text="No valid data available", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
            )

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
        return go.Figure().add_annotation(
            text=f"Error: {e}", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
        )


def build_category_by_day_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a grouped bar chart showing category performance by day of week."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    filtered_items["day_of_week"] = filtered_items["TransactionDate"].dt.day_name()

    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    filtered_items["day_of_week"] = pd.Categorical(filtered_items["day_of_week"], categories=day_order, ordered=True,
    )

    category_day_summary = (
        filtered_items.dropna(subset=["category", "day_of_week"])
        .groupby(["category", "day_of_week"])
        .agg(total_units=("quantity", "sum"))
        .reset_index()
        .sort_values(["category", "day_of_week"])
    )

    categories = sorted(category_day_summary["category"].unique())

    fig = go.Figure()

    day_colors = {
        "Sunday": "#B8860B",
        "Monday": "#DAA520",
        "Tuesday": "#F4A460",
        "Wednesday": "#FFB347",
        "Thursday": "#FFD700",
        "Friday": "#FFE4B5",
        "Saturday": "#FFF8DC",
    }

    for day in day_order:
        day_data = category_day_summary[category_day_summary["day_of_week"] == day]

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


def build_category_by_gender_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a horizontal stacked bar chart showing gender distribution by category (100% stacked)."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    category_gender_summary = (
        filtered_items.dropna(subset=["category", "gender_clean"],
    )
        .groupby(["category", "gender_clean"])
        .agg(total_units=("quantity", "sum"))
        .reset_index()
    )

    categories = sorted(category_gender_summary["category"].unique())
    genders = ["Female", "Male"]

    female_percentages = []
    male_percentages = []

    for cat in categories:
        cat_data = category_gender_summary[category_gender_summary["category"] == cat]
        total = cat_data["total_units"].sum()

        female_units = (
            cat_data[cat_data["gender_clean"] == "Female"]["total_units"].sum()
            if not cat_data[cat_data["gender_clean"] == "Female"].empty
            else 0
        )
        male_units = (
            cat_data[cat_data["gender_clean"] == "Male"]["total_units"].sum()
            if not cat_data[cat_data["gender_clean"] == "Male"].empty
            else 0
        )

        if total > 0:
            female_percentages.append((female_units / total) * 100)
            male_percentages.append((male_units / total) * 100)
        else:
            female_percentages.append(0)
            male_percentages.append(0)

    fig = go.Figure()

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
            autorange="reversed",
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


def build_category_by_age_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a grouped bar chart showing age group distribution by category."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    category_age_summary = (
        filtered_items.dropna(subset=["category", "age_bucket"],
    )
        .groupby(["category", "age_bucket"])
        .agg(total_units=("quantity", "sum"))
        .reset_index()
    )

    categories = sorted(category_age_summary["category"].unique())

    age_buckets = ["18-24", "25-34", "35-44", "45-54"]
    age_labels = {
        "18-24": "18-24",
        "25-34": "25-34",
        "35-44": "35-44",
        "45-54": "45-54",
    }

    fig = go.Figure()

    age_colors = {
        "18-24": "#B8860B",
        "25-34": "#DAA520",
        "35-44": "#FFD700",
        "45-54": "#FFE4B5",
    }

    for age_bucket in age_buckets:
        age_data = category_age_summary[category_age_summary["age_bucket"] == age_bucket]

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


def build_category_by_price_tier_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Create a stacked bar chart showing category composition by price tier."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    price_per_unit = None
    if "unitPrice" in filtered_items.columns:
        price_per_unit = filtered_items["unitPrice"]
    elif "totalPrice" in filtered_items.columns and "quantity" in filtered_items.columns:
        price_per_unit = filtered_items["totalPrice"] / filtered_items["quantity"]

    if price_per_unit is None:
        return go.Figure().add_annotation(
            text="No price data available to build price tiers.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
    )

    filtered_items = filtered_items.copy()
    filtered_items["price_per_unit"] = pd.to_numeric(price_per_unit, errors="coerce")
    filtered_items = filtered_items.dropna(subset=["price_per_unit", "quantity", "category"])

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

    tier_summary = (
        filtered_items.groupby(["price_tier", "category"]).agg(units=("quantity", "sum")).reset_index()
    )

    tier_order = [t[0] for t in tiers]
    tier_summary["price_tier"] = pd.Categorical(tier_summary["price_tier"], categories=tier_order, ordered=True)
    tier_summary = tier_summary.sort_values(["price_tier", "category"])

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


def build_category_ranking_table(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> dbc.Table:
    """Create a ranked table showing category performance with strategic tiers."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    available_cols = filtered_items.columns.tolist()

    agg_dict = {}
    if "quantity" in available_cols:
        agg_dict["total_units"] = ("quantity", "sum",
    )
    if "totalPrice" in available_cols:
        agg_dict["total_revenue"] = ("totalPrice", "sum")
    elif "unitPrice" in available_cols and "quantity" in available_cols:
        filtered_items["calculated_revenue"] = filtered_items["unitPrice"] * filtered_items["quantity"]
        agg_dict["total_revenue"] = ("calculated_revenue", "sum")

    if not agg_dict:
        return html.Div("No data available for ranking.")

    category_summary = filtered_items.groupby("category").agg(**agg_dict).reset_index()

    total_units = category_summary["total_units"].sum() if "total_units" in category_summary.columns else 0

    if total_units > 0:
        category_summary["unit_percentage"] = (category_summary["total_units"] / total_units) * 100
    else:
        category_summary["unit_percentage"] = 0

    category_summary = category_summary.sort_values("total_units", ascending=False).reset_index(drop=True)
    category_summary["rank"] = category_summary.index + 1

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

    rows = []
    for idx, row in category_summary.iterrows():
        revenue_text = ""
        if "total_revenue" in row and pd.notna(row["total_revenue"]):
            revenue_text = f"₱{row['total_revenue']:,.2f}"
        else:
            revenue_text = "N/A"

        units_style = {"fontWeight": "bold"} if row["rank"] <= 2 else {}
        revenue_style = {"fontWeight": "bold"} if row.get("total_revenue", 0) > 100000 else {}

        rows.append(
            html.Tr(
                [
                    html.Td(int(row["rank"]), style={"textAlign": "center", "fontWeight": "bold"}),
                    html.Td(row["category"], style={"fontWeight": "bold"}),
                    html.Td(f"{int(row['total_units']):,}", style=units_style),
                    html.Td(revenue_text, style=revenue_style),
                    html.Td(f"{row['unit_percentage']:.2f}%", style={"textAlign": "right"}),
                    html.Td(row["strategic_tier"], style={"fontStyle": "italic"}),
                ]
            )
        )

    table = dbc.Table(
        [
            html.Thead(
                [
                    html.Tr(
                        [
                            html.Th("Rank", style={"textAlign": "center"}),
                            html.Th("Category"),
                            html.Th("Total Units Sold", style={"textAlign": "right"}),
                            html.Th("Total Revenue (PHP)", style={"textAlign": "right"}),
                            html.Th("Unit Percentage", style={"textAlign": "right"}),
                            html.Th("Strategic Tier"),
                        ]
                    )
                ]
            ),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        className="mt-3",
    )

    return table


def build_top_products_table(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> html.Div:
    """Create a table showing top products by time of day."""
    filtered_items = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)

    time_segment_info = {
        "Morning (5a-12p)": "🌅",
        "Afternoon (12p-6p)": "☀️",
        "Evening (6p-10p)": "🌙",
        "Late Night (10p-5a)": "🌃",
    }

    top_n = 5
    tables = []

    for time_segment, emoji in time_segment_info.items():
        segment_data = filtered_items[filtered_items["timeofday_segment"] == time_segment]

        if not segment_data.empty:
            top_products = (
                segment_data.groupby("productName")
                .agg(total_units=("quantity", "sum"))
                .reset_index()
                .sort_values("total_units", ascending=False)
                .head(top_n)
            )

            rows = []
            for idx, row in top_products.iterrows():
                rows.append(
                    html.Tr(
                        [
                            html.Td(f"• {row['productName']}", style={"padding": "5px"}),
                            html.Td(f"({int(row['total_units'])} units)", style={"padding": "5px", "textAlign": "right"}),
                        ]
                    )
                )

            tables.append(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            [
                                html.H5(
                                    [
                                        html.Span(emoji, style={"marginRight": "10px"}),
                                        html.Span(time_segment),
                                    ],
                                    style={"margin": 0},
                                ),
                            ]
                        ),
                        dbc.CardBody(
                            [
                                dbc.Table(
                                    [html.Tbody(rows)],
                                    bordered=False,
                                    hover=True,
                                    responsive=True,
                                    striped=False,
                                ),
                            ]
                        ),
                    ],
                    className="mb-3",
                )
            )

    return dbc.Row(
        [
            dbc.Col(tables[0] if len(tables) > 0 else html.Div(), md=6),
            dbc.Col(tables[1] if len(tables) > 1 else html.Div(), md=6),
            dbc.Col(tables[2] if len(tables) > 2 else html.Div(), md=6),
            dbc.Col(tables[3] if len(tables) > 3 else html.Div(), md=6),
        ]
    )
