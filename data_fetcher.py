"""
CrashLead AI — Data Fetcher v3.2
Pulls crash data from working public APIs + includes demo data as fallback.
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import random
import streamlit as st


# ── Austin TX (Socrata API — reliable, well-structured) ─────────────────────
def get_austin_tx_crashes(days_back: int = 30) -> pd.DataFrame:
    """Fetch Austin TX crashes from the city's Socrata open data API."""
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    url = "https://data.austintexas.gov/resource/y2wy-tber.json"
    params = {
        "$where": f"crash_date > '{start}'",
        "$limit": 500,
        "$order": "crash_date DESC",
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Map columns to our standard schema
        df["Agency"] = "Austin Police / TxDOT"
        df["State"] = "TX"
        df["Source"] = "Austin Open Data"

        if "crash_date" in df.columns:
            df["Date"] = pd.to_datetime(df["crash_date"], errors="coerce")

        if "latitude" in df.columns:
            df["Latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        if "longitude" in df.columns:
            df["Longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

        # Build Nature from available fields
        nature_cols = [c for c in df.columns if any(
            k in c.lower() for k in ["severity", "type", "manner", "crash_sev"]
        )]
        if nature_cols:
            df["Nature"] = df[nature_cols[0]].astype(str)
        else:
            df["Nature"] = "Traffic Crash"

        # Build Injury field
        injury_cols = [c for c in df.columns if "injur" in c.lower() or "fatal" in c.lower()]
        if injury_cols:
            df["Injury"] = df[injury_cols[0]].astype(str)
        else:
            df["Injury"] = "Unknown"

        return df

    except Exception as e:
        st.warning(f"Austin TX source: {e}")
        return pd.DataFrame()


# ── NHTSA FARS (Fatal crashes — all 50 states) ──────────────────────────────
def get_nhtsa_fatals(days_back: int = 365) -> pd.DataFrame:
    """Fetch fatal crash data from the NHTSA FARS API."""
    year = datetime.now().year - 1  # FARS data lags ~1 year
    df_list = []

    # Pull multiple states for broader coverage
    for state_code in [6, 12, 17, 18, 36, 48]:  # CA, FL, IL, IN, NY, TX
        url = "https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCaseList"
        params = {
            "states": str(state_code),
            "fromYear": year,
            "toYear": year,
            "format": "json",
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "Results" in data and data["Results"]:
                results = data["Results"][0] if isinstance(data["Results"], list) else data["Results"]
                if isinstance(results, list) and results:
                    df = pd.DataFrame(results)
                    state_names = {6: "CA", 12: "FL", 17: "IL", 18: "IN", 36: "NY", 48: "TX"}
                    df["Agency"] = "NHTSA FARS (Fatal)"
                    df["State"] = state_names.get(state_code, "US")
                    df["Source"] = "NHTSA"
                    df["Nature"] = "FATAL CRASH"
                    df["Injury"] = "Fatal"

                    # FARS uses LATITUDEDD / LONGITUDEDD
                    for lat_col in ["LATITUDEDD", "LATITUDE"]:
                        if lat_col in df.columns:
                            df["Latitude"] = pd.to_numeric(df[lat_col], errors="coerce")
                            break
                    for lon_col in ["LONGITUD", "LONGITUDEDD", "LONGITUDE"]:
                        if lon_col in df.columns:
                            df["Longitude"] = pd.to_numeric(df[lon_col], errors="coerce")
                            break

                    df_list.append(df)
        except Exception:
            continue

    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()


# ── Demo / Sample Data (always available) ────────────────────────────────────
def get_demo_crashes() -> pd.DataFrame:
    """Generate realistic demo crash data so the app always has something to show."""
    now = datetime.now()
    random.seed(42)

    crash_types = [
        ("Rear-End Collision — Injury", "Suspected Serious Injury", 75),
        ("Head-On Collision — Fatal", "Fatal", 95),
        ("T-Bone at Intersection — Injury", "Suspected Minor Injury", 60),
        ("DUI / Alcohol-Related Crash", "Suspected Serious Injury", 85),
        ("Semi Truck Rear-End", "Suspected Serious Injury", 90),
        ("Pedestrian Struck — Injury", "Suspected Serious Injury", 80),
        ("Multi-Vehicle Pileup", "Suspected Minor Injury", 65),
        ("Motorcycle Crash — Injury", "Suspected Serious Injury", 70),
        ("Run Off Road — Rollover", "Possible Injury", 50),
        ("Sideswipe — Minor", "No Injury", 20),
    ]

    agencies = [
        ("Indiana State Police", "IN", 41.16, -85.49),
        ("Fort Wayne PD", "IN", 41.08, -85.14),
        ("Indianapolis Metro PD", "IN", 39.77, -86.16),
        ("Chicago PD", "IL", 41.88, -87.63),
        ("Austin PD", "TX", 30.27, -97.74),
        ("Los Angeles PD", "CA", 34.05, -118.24),
        ("Miami-Dade PD", "FL", 25.76, -80.19),
        ("NYPD", "NY", 40.71, -74.01),
        ("Houston PD", "TX", 29.76, -95.37),
        ("Columbus PD", "IN", 39.20, -85.92),
    ]

    rows = []
    for i in range(80):
        crash = random.choice(crash_types)
        agency = random.choice(agencies)
        days_ago = random.randint(1, 60)

        rows.append({
            "Date": now - timedelta(days=days_ago),
            "Agency": agency[0],
            "State": agency[1],
            "Nature": crash[0],
            "Injury": crash[1],
            "Latitude": agency[2] + random.uniform(-0.3, 0.3),
            "Longitude": agency[3] + random.uniform(-0.3, 0.3),
            "Source": "Demo Data",
        })

    return pd.DataFrame(rows)


# ── Main entry point ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_crashes(days_back: int = 30, include_austin: bool = True) -> pd.DataFrame:
    """Fetch from all sources. Falls back to demo data if live sources return nothing."""
    df_list = []
    source_status = {}

    # Try live sources
    with st.spinner("Pulling Austin TX crashes..."):
        if include_austin:
            austin = get_austin_tx_crashes(days_back)
            df_list.append(austin)
            source_status["Austin TX"] = len(austin)

    with st.spinner("Pulling NHTSA fatal crashes..."):
        nhtsa = get_nhtsa_fatals()
        df_list.append(nhtsa)
        source_status["NHTSA FARS"] = len(nhtsa)

    live_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    live_count = len(live_df) if not live_df.empty else 0

    # Always include demo data as supplement
    demo = get_demo_crashes()
    source_status["Demo Data"] = len(demo)

    if live_count > 0:
        combined = pd.concat([live_df, demo], ignore_index=True)
    else:
        combined = demo

    # Show source breakdown in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Data Sources**")
    for src, count in source_status.items():
        icon = "✅" if count > 0 else "❌"
        st.sidebar.markdown(f"{icon} {src}: **{count}** records")

    return combined
