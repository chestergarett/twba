"""
Tobacco chart builders for TWBA Dashboard.

Each function here is a pure helper that takes data + filter inputs and
returns a Plotly figure. Dash callbacks in app.py simply call these helpers.
"""

from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from charts.utils import filter_data, apply_dark_layout


def _filter_tobacco_items(df: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe to only include tobacco-related items."""
    if df.empty:
        return df
    df = df.copy()
    mask = (
        df["category"].str.contains("tobacco|cigarette", case=False, na=False)
        | df["brandName"].str.contains("marlboro|camel|chesterfield|fortune|winston|mighty", case=False, na=False)
    )
    return df[mask]


def build_tobacco_time_avgqty_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Tobacco Products Purchase Time x Average Quantity chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
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


def build_tobacco_day_avgqty_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Tobacco Products Purchase Day x Average Quantity chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
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


def build_tobacco_brands_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Tobacco Brands chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
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


def build_tobacco_brands_day_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Tobacco Brands x Day chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
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


def build_tobacco_gender_pie_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Tobacco Purchases by Gender pie chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = tob.dropna(subset=["gender_clean"]).groupby("gender_clean").agg(units=("quantity", "sum")).reset_index()
    fig = px.pie(summary, names="gender_clean", values="units", title="Tobacco Purchases by Gender", color_discrete_sequence=px.colors.sequential.Reds)
    apply_dark_layout(fig, "Tobacco Purchases by Gender", "", "", "", height=400)
    return fig


def build_tobacco_age_pie_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Tobacco Purchases by Age Group pie chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
    if tob.empty:
        return go.Figure().add_annotation(text="No tobacco data", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")

    summary = tob.dropna(subset=["age_bucket"]).groupby("age_bucket").agg(units=("quantity", "sum")).reset_index()
    fig = px.pie(summary, names="age_bucket", values="units", title="Tobacco Purchases by Age Group", color_discrete_sequence=px.colors.sequential.Reds)
    apply_dark_layout(fig, "Tobacco Purchases by Age Group", "", "", "", height=400)
    return fig


def build_tobacco_gender_brand_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Gender x Tobacco Brands Purchased chart."""
    tob = _filter_tobacco_items(filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend))
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


def build_tobacco_cluster_items_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Number of Items Purchased with Marlboro pie chart."""
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)
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


def build_tobacco_cluster_categories_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Categories Purchased with Marlboro chart."""
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)
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


def build_tobacco_cluster_brands_figure(
    items_df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    gender: Optional[List[str]],
    age: Optional[List[str]],
    payment: Optional[List[str]],
    month_year: Optional[List[str]],
    weekday_weekend: Optional[str],
) -> go.Figure:
    """Top 10 Brands Purchased with Marlboro chart."""
    items_filtered = filter_data(items_df, [start_date, end_date], gender, age, payment, month_year, weekday_weekend)
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

