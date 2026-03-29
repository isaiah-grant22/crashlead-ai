"""APScheduler-based background job that refreshes crash data periodically."""

import sys
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from data_fetcher import (
    get_all_opd_crashes,
    get_nhtsa_fatals,
    get_california_ccrs_crashes,
    get_florida_fdot_crashes,
    get_austin_tx_crashes,
)
from utils import simple_lead_score
from production.backend.models import SessionLocal, CrashLead

import pandas as pd


def refresh_crash_data():
    """Pull fresh crash data from all sources and upsert into Postgres."""
    print(f"[{datetime.now()}] Starting crash data refresh...")

    df_list = [
        get_all_opd_crashes(30),
        get_nhtsa_fatals(60),
        get_california_ccrs_crashes(30),
        get_florida_fdot_crashes(30),
        get_austin_tx_crashes(30),
    ]

    df = pd.concat(df_list, ignore_index=True)

    if df.empty:
        print("  No data returned from any source.")
        return

    df["lead_score"] = df.apply(simple_lead_score, axis=1)

    db = SessionLocal()
    inserted = 0
    try:
        for _, row in df.iterrows():
            lead = CrashLead(
                date=row.get("Date"),
                agency=str(row.get("Agency", ""))[:255],
                state=str(row.get("State", ""))[:10],
                nature=str(row.get("Nature", ""))[:500],
                injury=str(row.get("Injury", ""))[:500],
                latitude=row.get("Latitude"),
                longitude=row.get("Longitude"),
                lead_score=int(row.get("lead_score", 0)),
                source=str(row.get("Source", ""))[:100],
                created_at=datetime.now(),
            )
            db.add(lead)
            inserted += 1

        db.commit()
        print(f"  Inserted {inserted} leads into database.")
    except Exception as e:
        db.rollback()
        print(f"  Error: {e}")
    finally:
        db.close()


def start_scheduler():
    """Launch the background scheduler (runs refresh every 6 hours)."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_crash_data, "interval", hours=6, id="crash_refresh")
    # Also run once immediately on startup
    scheduler.add_job(refresh_crash_data, "date", id="crash_initial")
    scheduler.start()
    print("Scheduler started — crash data will refresh every 6 hours.")
    return scheduler
