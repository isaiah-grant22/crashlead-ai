import openpolicedata as opd
import pandas as pd
import requests
from datetime import datetime, timedelta


def get_all_opd_crashes(days_back: int = 30) -> pd.DataFrame:
    """Fetch crash data from all available OpenPoliceData agencies."""
    datasets = opd.datasets.query(table_type="CRASHES")
    df_list = []
    start_date = datetime.now() - timedelta(days=days_back)

    for _, row in datasets.iterrows():
        try:
            dataset = opd.Dataset(row["SourceName"], row["TableName"])
            df = dataset.load(date_range=(start_date, datetime.now()))
            if not df.empty:
                df["Agency"] = row["Agency"]
                df["State"] = row["State"]
                df["Source"] = "OpenPoliceData"
                df_list.append(df)
        except Exception:
            continue

    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()


def get_nhtsa_fatals(days_back: int = 60) -> pd.DataFrame:
    """Fetch fatal crash data from NHTSA FARS API."""
    df_list = []
    url = "https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCaseList"
    params = {
        "states": "18",  # start with IN; expand later if needed
        "fromYear": datetime.now().year - 1,
        "toYear": datetime.now().year,
        "format": "json",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if "Results" in data and data["Results"]:
            crashes = (
                data["Results"][0]
                if isinstance(data["Results"], list)
                else data["Results"]
            )
            df = pd.DataFrame(crashes)
            df["Agency"] = "NHTSA FARS (Fatal)"
            df["Source"] = "NHTSA"
            df["Nature"] = "FATAL CRASH"
            df_list.append(df)
    except Exception:
        pass

    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()


def get_california_ccrs_crashes(days_back: int = 30) -> pd.DataFrame:
    """Fetch California crash data from CCRS open data."""
    url = (
        "https://data.ca.gov/dataset/80c6a49d-c6b3-40ba-86d8-379c9741b4be/"
        "resource/b8ce0ca4-b4e9-490d-b4d1-1f4ec48cbefb/download/"
        "hq1d-p-app52dopendataexport2026crashes.csv"
    )
    try:
        df = pd.read_csv(url, low_memory=False)
        df["Agency"] = "California Highway Patrol (CCRS)"
        df["State"] = "CA"
        df["Source"] = "CCRS"
        df["Date"] = pd.to_datetime(
            df.get("COLLISION_DATE", df.get("CRASH_DATE")), errors="coerce"
        )
        start_date = datetime.now() - timedelta(days=days_back)
        return df[df["Date"] >= start_date].copy()
    except Exception:
        return pd.DataFrame()


def get_florida_fdot_crashes(days_back: int = 30) -> pd.DataFrame:
    """Fetch Florida crash data from FDOT open data."""
    url = (
        "https://gis-fdot.opendata.arcgis.com/datasets/"
        "630f22996b88425a94781c597be7bc01_0.csv"
    )
    try:
        df = pd.read_csv(url, low_memory=False)
        df["Agency"] = "Florida FDOT"
        df["State"] = "FL"
        df["Source"] = "FDOT"
        date_col = next(
            (
                col
                for col in df.columns
                if "DATE" in col.upper() or "CRASH" in col.upper()
            ),
            None,
        )
        if date_col:
            df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
            start = datetime.now() - timedelta(days=days_back)
            df = df[df["Date"] >= start].copy()
        return df
    except Exception:
        return pd.DataFrame()


def get_austin_tx_crashes(days_back: int = 30) -> pd.DataFrame:
    """Fetch Austin TX crash data from city open data portal."""
    url = "https://data.austintexas.gov/api/views/3q5c-2n9m/rows.csv?accessType=DOWNLOAD"
    try:
        df = pd.read_csv(url, low_memory=False)
        df["Agency"] = "Austin Police / TxDOT"
        df["State"] = "TX"
        df["Source"] = "Austin Open Data"
        date_col = next(
            (
                col
                for col in df.columns
                if any(x in col.upper() for x in ["DATE", "CRASH", "OCCURRED"])
            ),
            None,
        )
        if date_col:
            df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
            start = datetime.now() - timedelta(days=days_back)
            df = df[df["Date"] >= start].copy()
        return df
    except Exception:
        return pd.DataFrame()
