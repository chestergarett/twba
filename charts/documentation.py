"""
Documentation for all charts in the TWBA Dashboard.

This module provides metadata about each chart including:
- Chart name
- X-axis column(s) (raw column names)
- Y-axis column(s) (raw column names)
- Aggregation method (how metrics are calculated)
- Data source (transactions_df or items_df)
"""

from typing import Dict, List
from dash import html
import dash_bootstrap_components as dbc


# Chart documentation organized by category
CHART_DOCUMENTATION = {
    "consumer_demographics": [
        {
            "name": "Gender Demographics: Transactions & Average Spend",
            "x_axis": "gender_clean",
            "y_axis": "total_transactions (left), avg_spend (right)",
            "aggregation": "groupby gender_clean: InteractionID count, basket_total mean",
            "data_source": "transactions_df",
            "description": "Bar chart showing total transactions by gender with line overlay for average spend",
        },
        {
            "name": "Month-on-Month Transactions by Gender",
            "x_axis": "txn_month",
            "y_axis": "total_transactions",
            "aggregation": "groupby [txn_month, gender_clean]: InteractionID count",
            "data_source": "transactions_df",
            "description": "Line chart showing transaction trends over time by gender",
        },
        {
            "name": "Age Demographics: Transactions & Average Spend",
            "x_axis": "age_bucket",
            "y_axis": "total_transactions (left), avg_spend (right)",
            "aggregation": "groupby age_bucket: InteractionID count, basket_total mean",
            "data_source": "transactions_df",
            "description": "Bar chart showing total transactions by age group with line overlay for average spend",
        },
        {
            "name": "Payment Method: Transactions & Average Spend",
            "x_axis": "payment_method",
            "y_axis": "total_transactions (left), avg_spend (right)",
            "aggregation": "groupby payment_method: InteractionID count, basket_total mean",
            "data_source": "transactions_df",
            "description": "Bar chart showing total transactions by payment method with line overlay for average spend",
        },
        {
            "name": "Transactions & Average Spend: Weekday vs Weekend",
            "x_axis": "weekday_type",
            "y_axis": "total_transactions (left), avg_spend (right)",
            "aggregation": "groupby weekday_type: InteractionID count, basket_total mean",
            "data_source": "transactions_df",
            "description": "Bar chart comparing weekday vs weekend transactions and average spend",
        },
        {
            "name": "Transactions & Average Spend by Time of Day (Weekday vs Weekend)",
            "x_axis": "timeofday_segment",
            "y_axis": "total_transactions (left), avg_spend (right)",
            "aggregation": "groupby [weekday_type, timeofday_segment]: InteractionID count, basket_total mean",
            "data_source": "transactions_df",
            "description": "Grouped bar chart showing transactions by time of day segmented by weekday/weekend, with average spend line",
        },
        {
            "name": "Transactions & Average Spend by Day of Week",
            "x_axis": "day_of_week",
            "y_axis": "total_transactions (left), avg_spend (right)",
            "aggregation": "groupby day_of_week: InteractionID count, basket_total mean",
            "data_source": "transactions_df",
            "description": "Bar chart showing transactions by day of week with average spend line",
        },
        {
            "name": "Gender Distribution by Time of Day (100% Stacked)",
            "x_axis": "timeofday_segment",
            "y_axis": "Percentage (%)",
            "aggregation": "groupby [timeofday_segment, gender_clean]: InteractionID count, then calculate percentage",
            "data_source": "transactions_df",
            "description": "Horizontal stacked bar chart showing gender distribution percentages by time of day",
        },
        {
            "name": "Average Daily Sales by Day of Month (Petsa de Peligro vs Payday Windows)",
            "x_axis": "day_of_month",
            "y_axis": "avg_sales",
            "aggregation": "groupby day_of_month: basket_total mean",
            "data_source": "transactions_df",
            "description": "Line chart showing average sales by day of month with shaded regions for payday windows and petsa de peligro",
        },
        {
            "name": "Basket Value Distribution",
            "x_axis": "basket_band",
            "y_axis": "transactions",
            "aggregation": "groupby basket_band: InteractionID count",
            "data_source": "transactions_df",
            "description": "Bar chart showing transaction count by basket value bands (₱0-10, ₱11-20, etc.)",
        },
        {
            "name": "Top Categories by Revenue",
            "x_axis": "category",
            "y_axis": "revenue or units",
            "aggregation": "groupby category: totalPrice sum (revenue) or quantity sum (units)",
            "data_source": "items_df",
            "description": "Bar chart showing top 15 categories by revenue or units sold",
        },
        {
            "name": "Category Performance by Day of Week",
            "x_axis": "category",
            "y_axis": "total_units",
            "aggregation": "groupby [category, day_of_week]: quantity sum",
            "data_source": "items_df",
            "description": "Grouped bar chart showing units sold by category for each day of week",
        },
        {
            "name": "Category Distribution by Gender (100% Stacked)",
            "x_axis": "category",
            "y_axis": "Percentage (%)",
            "aggregation": "groupby [category, gender_clean]: quantity sum, then calculate percentage",
            "data_source": "items_df",
            "description": "Horizontal stacked bar chart showing gender distribution percentages by category",
        },
        {
            "name": "Category Distribution by Age Group",
            "x_axis": "category",
            "y_axis": "total_units",
            "aggregation": "groupby [category, age_bucket]: quantity sum",
            "data_source": "items_df",
            "description": "Grouped bar chart showing units sold by category for each age group",
        },
        {
            "name": "Category Composition by Price Tier",
            "x_axis": "price_tier",
            "y_axis": "units",
            "aggregation": "groupby [price_tier, category]: quantity sum",
            "data_source": "items_df",
            "description": "Stacked bar chart showing units sold by price tier, grouped by category",
        },
        {
            "name": "Category Ranking Table",
            "x_axis": "N/A (Table)",
            "y_axis": "N/A (Table)",
            "aggregation": "groupby category: quantity sum, totalPrice sum, then calculate percentages and tiers",
            "data_source": "items_df",
            "description": "Ranked table showing category performance with total units, revenue, percentage, and strategic tier",
        },
        {
            "name": "Top Products Table",
            "x_axis": "N/A (Table)",
            "y_axis": "N/A (Table)",
            "aggregation": "groupby [timeofday_segment, productName]: quantity sum",
            "data_source": "items_df",
            "description": "Table showing top 5 products by time of day segment",
        },
    ],
    "laundry": [
        {
            "name": "Laundry Products Purchase Time x Average Quantity",
            "x_axis": "timeofday_segment",
            "y_axis": "transactions (left), avg_qty (right)",
            "aggregation": "groupby timeofday_segment: InteractionID nunique, quantity mean",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Bar chart showing transactions by time of day with line overlay for average quantity",
        },
        {
            "name": "Laundry Products Purchase Day x Average Quantity",
            "x_axis": "txn_weekday",
            "y_axis": "transactions (left), avg_qty (right)",
            "aggregation": "groupby txn_weekday: InteractionID nunique, quantity mean",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Bar chart showing transactions by day of week with line overlay for average quantity",
        },
        {
            "name": "Laundry Brands",
            "x_axis": "brandName",
            "y_axis": "transactions (left), avg_qty (right)",
            "aggregation": "groupby brandName: InteractionID nunique, quantity mean",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Bar chart showing top 10 laundry brands by transactions with average quantity line",
        },
        {
            "name": "Laundry Brands x Day",
            "x_axis": "brandName",
            "y_axis": "units",
            "aggregation": "groupby [brandName, txn_weekday]: quantity sum",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Stacked bar chart showing units sold by top 8 laundry brands for each day of week",
        },
        {
            "name": "Laundry Purchases by Gender",
            "x_axis": "N/A (Pie Chart)",
            "y_axis": "units",
            "aggregation": "groupby gender_clean: quantity sum",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Pie chart showing laundry purchase distribution by gender",
        },
        {
            "name": "Laundry Purchases by Age Group",
            "x_axis": "N/A (Pie Chart)",
            "y_axis": "units",
            "aggregation": "groupby age_bucket: quantity sum",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Pie chart showing laundry purchase distribution by age group",
        },
        {
            "name": "Gender x Laundry Brands Purchased",
            "x_axis": "brandName",
            "y_axis": "Percentage (%)",
            "aggregation": "groupby [brandName, gender_clean]: quantity sum, then calculate percentage",
            "data_source": "items_df (filtered: laundry category/brands)",
            "description": "Horizontal stacked bar chart showing gender distribution percentages by top 8 laundry brands",
        },
        {
            "name": "Number of Items Purchased with Surf",
            "x_axis": "item_count",
            "y_axis": "freq",
            "aggregation": "Filter items with Surf brand, groupby InteractionID: productName count, then groupby item_count: InteractionID count",
            "data_source": "items_df",
            "description": "Pie chart showing distribution of item counts in transactions containing Surf products",
        },
        {
            "name": "Categories Purchased with Surf",
            "x_axis": "category",
            "y_axis": "freq",
            "aggregation": "Filter transactions with Surf, get all items in those transactions, groupby category: quantity sum",
            "data_source": "items_df",
            "description": "Horizontal bar chart showing top 12 categories purchased in transactions containing Surf",
        },
        {
            "name": "Top Brands Purchased with Surf",
            "x_axis": "brandName",
            "y_axis": "freq",
            "aggregation": "Filter transactions with Surf, get all items in those transactions (excluding Surf), groupby brandName: quantity sum",
            "data_source": "items_df",
            "description": "Horizontal bar chart showing top 10 brands purchased in transactions containing Surf",
        },
    ],
    "tobacco": [
        {
            "name": "Tobacco Products Purchase Time x Average Quantity",
            "x_axis": "timeofday_segment",
            "y_axis": "transactions (left), avg_qty (right)",
            "aggregation": "groupby timeofday_segment: InteractionID nunique, quantity mean",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Bar chart showing transactions by time of day with line overlay for average quantity",
        },
        {
            "name": "Tobacco Products Purchase Day x Average Quantity",
            "x_axis": "txn_weekday",
            "y_axis": "transactions (left), avg_qty (right)",
            "aggregation": "groupby txn_weekday: InteractionID nunique, quantity mean",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Bar chart showing transactions by day of week with line overlay for average quantity",
        },
        {
            "name": "Tobacco Brands",
            "x_axis": "brandName",
            "y_axis": "transactions (left), avg_qty (right)",
            "aggregation": "groupby brandName: InteractionID nunique, quantity mean",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Bar chart showing top 10 tobacco brands by transactions with average quantity line",
        },
        {
            "name": "Tobacco Brands x Day",
            "x_axis": "brandName",
            "y_axis": "units",
            "aggregation": "groupby [brandName, txn_weekday]: quantity sum",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Stacked bar chart showing units sold by top 8 tobacco brands for each day of week",
        },
        {
            "name": "Tobacco Purchases by Gender",
            "x_axis": "N/A (Pie Chart)",
            "y_axis": "units",
            "aggregation": "groupby gender_clean: quantity sum",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Pie chart showing tobacco purchase distribution by gender",
        },
        {
            "name": "Tobacco Purchases by Age Group",
            "x_axis": "N/A (Pie Chart)",
            "y_axis": "units",
            "aggregation": "groupby age_bucket: quantity sum",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Pie chart showing tobacco purchase distribution by age group",
        },
        {
            "name": "Gender x Tobacco Brands Purchased",
            "x_axis": "brandName",
            "y_axis": "Percentage (%)",
            "aggregation": "groupby [brandName, gender_clean]: quantity sum, then calculate percentage",
            "data_source": "items_df (filtered: tobacco category/brands)",
            "description": "Horizontal stacked bar chart showing gender distribution percentages by top 8 tobacco brands",
        },
        {
            "name": "Number of Items Purchased with Marlboro",
            "x_axis": "item_count",
            "y_axis": "freq",
            "aggregation": "Filter items with Marlboro brand, groupby InteractionID: productName count, then groupby item_count: InteractionID count",
            "data_source": "items_df",
            "description": "Pie chart showing distribution of item counts in transactions containing Marlboro products",
        },
        {
            "name": "Categories Purchased with Marlboro",
            "x_axis": "category",
            "y_axis": "freq",
            "aggregation": "Filter transactions with Marlboro, get all items in those transactions, groupby category: quantity sum",
            "data_source": "items_df",
            "description": "Horizontal bar chart showing top 12 categories purchased in transactions containing Marlboro",
        },
        {
            "name": "Top 10 Brands Purchased with Marlboro",
            "x_axis": "brandName",
            "y_axis": "freq",
            "aggregation": "Filter transactions with Marlboro, get all items in those transactions (excluding Marlboro), groupby brandName: quantity sum",
            "data_source": "items_df",
            "description": "Horizontal bar chart showing top 10 brands purchased in transactions containing Marlboro",
        },
    ],
}


def create_documentation_tab() -> html.Div:
    """Create the documentation tab content."""
    sections = []

    # Consumer Demographics Section
    sections.append(
        html.Div([
            html.H3("Consumer Demographics Charts", className="mt-4 mb-3", style={"color": "#d4af37"}),
            dbc.Table(
                [
                    html.Thead([
                        html.Tr([
                            html.Th("Chart Name", style={"width": "25%"}),
                            html.Th("X-Axis Column(s)", style={"width": "15%"}),
                            html.Th("Y-Axis Column(s)", style={"width": "15%"}),
                            html.Th("Aggregation Method", style={"width": "25%"}),
                            html.Th("Data Source", style={"width": "10%"}),
                            html.Th("Description", style={"width": "10%"}),
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td(chart["name"], style={"fontWeight": "500"}),
                            html.Td(chart["x_axis"]),
                            html.Td(chart["y_axis"]),
                            html.Td(chart["aggregation"], style={"fontSize": "0.85em"}),
                            html.Td(chart["data_source"]),
                            html.Td(chart["description"], style={"fontSize": "0.9em"}),
                        ])
                        for chart in CHART_DOCUMENTATION["consumer_demographics"]
                    ]),
                ],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                className="mb-4",
            ),
        ])
    )

    # Laundry Section
    sections.append(
        html.Div([
            html.H3("Laundry Charts", className="mt-4 mb-3", style={"color": "#4a90e2"}),
            dbc.Table(
                [
                    html.Thead([
                        html.Tr([
                            html.Th("Chart Name", style={"width": "25%"}),
                            html.Th("X-Axis Column(s)", style={"width": "15%"}),
                            html.Th("Y-Axis Column(s)", style={"width": "15%"}),
                            html.Th("Aggregation Method", style={"width": "25%"}),
                            html.Th("Data Source", style={"width": "10%"}),
                            html.Th("Description", style={"width": "10%"}),
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td(chart["name"], style={"fontWeight": "500"}),
                            html.Td(chart["x_axis"]),
                            html.Td(chart["y_axis"]),
                            html.Td(chart["aggregation"], style={"fontSize": "0.85em"}),
                            html.Td(chart["data_source"]),
                            html.Td(chart["description"], style={"fontSize": "0.9em"}),
                        ])
                        for chart in CHART_DOCUMENTATION["laundry"]
                    ]),
                ],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                className="mb-4",
            ),
        ])
    )

    # Tobacco Section
    sections.append(
        html.Div([
            html.H3("Tobacco Charts", className="mt-4 mb-3", style={"color": "#e65b4a"}),
            dbc.Table(
                [
                    html.Thead([
                        html.Tr([
                            html.Th("Chart Name", style={"width": "25%"}),
                            html.Th("X-Axis Column(s)", style={"width": "15%"}),
                            html.Th("Y-Axis Column(s)", style={"width": "15%"}),
                            html.Th("Aggregation Method", style={"width": "25%"}),
                            html.Th("Data Source", style={"width": "10%"}),
                            html.Th("Description", style={"width": "10%"}),
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td(chart["name"], style={"fontWeight": "500"}),
                            html.Td(chart["x_axis"]),
                            html.Td(chart["y_axis"]),
                            html.Td(chart["aggregation"], style={"fontSize": "0.85em"}),
                            html.Td(chart["data_source"]),
                            html.Td(chart["description"], style={"fontSize": "0.9em"}),
                        ])
                        for chart in CHART_DOCUMENTATION["tobacco"]
                    ]),
                ],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                className="mb-4",
            ),
        ])
    )

    return html.Div([
        html.Div([
            html.H2("Chart Documentation", className="mb-4", style={"color": "#d4af37"}),
            html.P(
                "This documentation provides details about the columns used for X-axis and Y-axis in each chart, "
                "along with the aggregation methods used to calculate metrics. "
                "All charts respect the filters applied in the dashboard (date range, gender, age, payment method, etc.).",
                className="mb-4",
                style={"color": "#e0e0e0"},
            ),
        ]),
        *sections,
    ])
