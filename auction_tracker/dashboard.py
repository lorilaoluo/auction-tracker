"""Streamlit dashboard for auction results."""
import streamlit as st
import pandas as pd
from auction_tracker.database import Database

st.set_page_config(page_title="CHCH Auction Tracker", layout="wide")
st.title("Christchurch Auction Results")

db = Database()


def overview_tab():
    st.header("Overview")
    stats = db.get_stats()

    passed_in = stats["total"] - stats["with_price"]

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Results", stats["total"])
    with col2:
        st.metric("Sold", stats["with_price"])
    with col3:
        st.metric("Passed In", passed_in)
    with col4:
        median = f"${stats['median_price']:,.0f}" if stats["median_price"] else "N/A"
        st.metric("Median Price", median)
    with col5:
        avg = f"${stats['avg_price']:,.0f}" if stats["avg_price"] else "N/A"
        st.metric("Average Price", avg)

    st.subheader("Last Scrape per Agency")
    last = db.get_last_scrape_per_agency()
    if last:
        df_last = pd.DataFrame(
            [{"Agency": k, "Last Scraped": v} for k, v in last.items()]
        )
        st.dataframe(df_last, use_container_width=True)
    else:
        st.write("No data yet. Run `auction-tracker scrape` to collect results.")


def trends_tab():
    st.header("Price Trends")

    monthly = db.get_monthly_medians()
    if not monthly:
        st.write("Not enough data for trends yet.")
        return

    df = pd.DataFrame(monthly)
    df["month"] = pd.to_datetime(df["month"])

    st.subheader("Average Sale Price Over Time")
    st.line_chart(df.set_index("month")["avg_price"])

    st.subheader("Results Over Time")
    chart_df = df.set_index("month")[["sold", "passed_in"]]
    chart_df.columns = ["Sold", "Passed In"]
    st.bar_chart(chart_df)

    st.subheader("Filter by Suburb")
    suburbs = db.get_all_suburbs()
    if suburbs:
        selected = st.selectbox("Suburb", ["All"] + suburbs)
        if selected != "All":
            rows = db.get_by_suburb(selected)
            suburb_df = pd.DataFrame(rows)
            if not suburb_df.empty and "sale_price" in suburb_df.columns:
                st.line_chart(
                    suburb_df.set_index("sale_date")["sale_price"]
                )


def explore_tab():
    st.header("Explore Results")

    suburbs = ["All"] + db.get_all_suburbs()
    selected_suburb = st.selectbox("Suburb", suburbs, key="explore_suburb")

    min_price = st.number_input("Min Price", value=0, step=50_000)
    max_price = st.number_input("Max Price", value=5_000_000, step=50_000)

    rows = db.get_all()
    df = pd.DataFrame(rows)

    if df.empty:
        st.write("No results yet.")
        return

    if selected_suburb != "All":
        df = df[df["suburb"] == selected_suburb]
    if "sale_price" in df.columns:
        df = df[
            (df["sale_price"].isna())
            | ((df["sale_price"] >= min_price) & (df["sale_price"] <= max_price))
        ]

    df["status"] = df["sale_price"].apply(
        lambda p: "Sold" if p is not None and p > 0 else "Passed In"
    )
    st.dataframe(
        df[["address", "suburb", "status", "sale_price", "sale_date", "agency", "bedrooms", "bathrooms"]],
        use_container_width=True,
    )

    st.subheader("Median Price by Suburb")
    if "sale_price" in df.columns and "suburb" in df.columns:
        by_suburb = (
            df[df["sale_price"].notna()]
            .groupby("suburb")["sale_price"]
            .median()
            .sort_values(ascending=False)
            .head(15)
        )
        st.bar_chart(by_suburb)


tab1, tab2, tab3 = st.tabs(["Overview", "Trends", "Explore"])
with tab1:
    overview_tab()
with tab2:
    trends_tab()
with tab3:
    explore_tab()

db.close()
