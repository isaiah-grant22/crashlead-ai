import streamlit as st
import pandas as pd
import asyncio
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
from datetime import datetime

from data_fetcher import (
    get_all_opd_crashes,
    get_nhtsa_fatals,
    get_california_ccrs_crashes,
    get_florida_fdot_crashes,
    get_austin_tx_crashes,
)
from utils import filter_by_radius, simple_lead_score
from ai_summarizer import grok_crash_summary
from stripe_service import create_checkout_session

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="CrashLead AI v3.2", layout="wide")
st.title("🚨 CrashLead AI v3.2 — Nationwide Attorney Leads")

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("🌎 Coverage")

if st.sidebar.button("🚀 MAXIMUM COVERAGE (All States + CA + FL + Austin TX)"):
    include_ca = include_fl = include_tx = True
else:
    include_ca = st.sidebar.checkbox("California CCRS", value=True)
    include_fl = st.sidebar.checkbox("Florida FDOT", value=True)
    include_tx = st.sidebar.checkbox("Austin TX", value=True)

days = st.sidebar.slider("Days back", 7, 90, 30)
radius_km = st.sidebar.slider("Radius (miles)", 20, 500, 80)
center_lat = st.sidebar.number_input("Center Latitude", value=41.1589)
center_lon = st.sidebar.number_input("Center Longitude", value=-85.4883)
min_score = st.sidebar.slider("Min lead score", 0, 100, 50)

# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------
with st.spinner("Fetching nationwide crashes..."):
    df_list = [get_all_opd_crashes(days), get_nhtsa_fatals()]
    if include_ca:
        df_list.append(get_california_ccrs_crashes(days))
    if include_fl:
        df_list.append(get_florida_fdot_crashes(days))
    if include_tx:
        df_list.append(get_austin_tx_crashes(days))
    df = pd.concat(df_list, ignore_index=True)

# ---------------------------------------------------------------------------
# Filter & score
# ---------------------------------------------------------------------------
center_point = Point(center_lon, center_lat)
df = filter_by_radius(df, center=center_point, radius_km=radius_km)
df["lead_score"] = df.apply(simple_lead_score, axis=1)
df = df[df["lead_score"] >= min_score].sort_values("lead_score", ascending=False)

st.success(f"✅ Found **{len(df)} high-value leads** across the US")

# ---------------------------------------------------------------------------
# Interactive Folium map
# ---------------------------------------------------------------------------
st.subheader("🗺️ Crash Map")

has_coords = (
    not df.empty
    and "Latitude" in df.columns
    and "Longitude" in df.columns
)

if has_coords:
    map_df = df.dropna(subset=["Latitude", "Longitude"])
else:
    map_df = pd.DataFrame()

m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

# Center marker
folium.Marker(
    [center_lat, center_lon],
    popup="📍 Search Center",
    icon=folium.Icon(color="blue", icon="home", prefix="fa"),
).add_to(m)

# Color based on lead score
def _marker_color(score: int) -> str:
    if score >= 80:
        return "red"
    elif score >= 50:
        return "orange"
    return "green"

for _, row in map_df.iterrows():
    try:
        lat = float(row["Latitude"])
        lon = float(row["Longitude"])
    except (ValueError, TypeError):
        continue

    popup_html = (
        f"<b>Agency:</b> {row.get('Agency', 'N/A')}<br>"
        f"<b>State:</b> {row.get('State', 'N/A')}<br>"
        f"<b>Nature:</b> {row.get('Nature', 'N/A')}<br>"
        f"<b>Score:</b> {row.get('lead_score', 0)}<br>"
        f"<b>Source:</b> {row.get('Source', 'N/A')}"
    )
    folium.CircleMarker(
        [lat, lon],
        radius=6,
        color=_marker_color(row.get("lead_score", 0)),
        fill=True,
        fill_opacity=0.7,
        popup=folium.Popup(popup_html, max_width=300),
    ).add_to(m)

st_folium(m, width=1100, height=550)

# ---------------------------------------------------------------------------
# Lead table
# ---------------------------------------------------------------------------
st.subheader("📋 Lead Table")

display_cols = [
    col
    for col in ["Date", "Agency", "State", "Nature", "Injury", "Source", "lead_score"]
    if col in df.columns
]
if display_cols:
    st.dataframe(
        df[display_cols].head(200),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No displayable columns found — raw data shown below.")
    st.dataframe(df.head(50))

# ---------------------------------------------------------------------------
# Lead detail expanders with AI summaries & BuyCrash links
# ---------------------------------------------------------------------------
st.subheader("🔍 Lead Details")

top_leads = df.head(25)

for idx, (_, row) in enumerate(top_leads.iterrows()):
    label = (
        f"🏷️ Score {row.get('lead_score', 0)} | "
        f"{row.get('Agency', 'Unknown')} — "
        f"{row.get('Nature', 'Crash')} "
        f"({row.get('State', '')})"
    )
    with st.expander(label):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Agency:** {row.get('Agency', 'N/A')}")
            st.markdown(f"**State:** {row.get('State', 'N/A')}")
            st.markdown(f"**Nature:** {row.get('Nature', 'N/A')}")
            st.markdown(f"**Injury:** {row.get('Injury', 'N/A')}")
            st.markdown(f"**Source:** {row.get('Source', 'N/A')}")
            if "Date" in row and pd.notna(row.get("Date")):
                st.markdown(f"**Date:** {row['Date']}")
            if "Latitude" in row and pd.notna(row.get("Latitude")):
                st.markdown(
                    f"**Location:** {row.get('Latitude', '')}, {row.get('Longitude', '')}"
                )

        with col2:
            st.metric("Lead Score", row.get("lead_score", 0))

            # BuyCrash link
            buycrash_url = (
                f"https://www.buycrash.com/search?"
                f"state={row.get('State', '')}"
                f"&date={row.get('Date', '')}"
            )
            st.markdown(f"[🛒 View on BuyCrash]({buycrash_url})")

        # AI summary button
        if st.button(f"🤖 Get AI Summary", key=f"ai_{idx}"):
            with st.spinner("Generating AI summary..."):
                summary = asyncio.run(grok_crash_summary(row.to_dict()))
                st.info(summary)

# ---------------------------------------------------------------------------
# CSV download
# ---------------------------------------------------------------------------
st.divider()
if not df.empty:
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Download All Leads (CSV)",
        csv,
        "crashlead_leads.csv",
        "text/csv",
    )

# ---------------------------------------------------------------------------
# Stripe upgrade section
# ---------------------------------------------------------------------------
st.divider()
st.subheader("💰 Upgrade to Pro")
st.markdown(
    "Get unlimited leads, priority AI summaries, and real-time alerts for **$149/mo**."
)

email = st.text_input("Law-firm email")
if st.button("Upgrade to Pro — $149/mo"):
    if email:
        url = asyncio.run(create_checkout_session(email))
        st.markdown(f"[✅ Open Stripe Checkout]({url})")
    else:
        st.warning("Please enter your email first.")
