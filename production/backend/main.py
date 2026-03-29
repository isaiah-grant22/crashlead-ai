"""FastAPI production backend for CrashLead AI v3.2."""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

load_dotenv()

from production.backend.models import init_db, get_db, CrashLead, Subscriber
from production.backend.scheduler import start_scheduler
from ai_summarizer import grok_crash_summary
from stripe_service import create_checkout_session


# ---------------------------------------------------------------------------
# Lifespan — init DB + scheduler on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="CrashLead AI",
    version="3.2.0",
    description="Nationwide attorney lead generator from public crash reports",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "version": "3.2.0", "timestamp": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Leads endpoints
# ---------------------------------------------------------------------------
@app.get("/api/leads")
def get_leads(
    state: Optional[str] = None,
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return crash leads, optionally filtered by state and minimum score."""
    q = db.query(CrashLead).filter(CrashLead.lead_score >= min_score)
    if state:
        q = q.filter(CrashLead.state == state.upper())
    q = q.order_by(CrashLead.lead_score.desc())
    total = q.count()
    leads = q.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "leads": [
            {
                "id": l.id,
                "date": l.date.isoformat() if l.date else None,
                "agency": l.agency,
                "state": l.state,
                "nature": l.nature,
                "injury": l.injury,
                "latitude": l.latitude,
                "longitude": l.longitude,
                "lead_score": l.lead_score,
                "source": l.source,
                "ai_summary": l.ai_summary,
            }
            for l in leads
        ],
    }


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(CrashLead).filter(CrashLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {
        "id": lead.id,
        "date": lead.date.isoformat() if lead.date else None,
        "agency": lead.agency,
        "state": lead.state,
        "nature": lead.nature,
        "injury": lead.injury,
        "latitude": lead.latitude,
        "longitude": lead.longitude,
        "lead_score": lead.lead_score,
        "source": lead.source,
        "ai_summary": lead.ai_summary,
    }


@app.post("/api/leads/{lead_id}/summarize")
async def summarize_lead(lead_id: int, db: Session = Depends(get_db)):
    """Generate an AI summary for a specific lead using Grok."""
    lead = db.query(CrashLead).filter(CrashLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    crash_data = {
        "agency": lead.agency,
        "state": lead.state,
        "nature": lead.nature,
        "injury": lead.injury,
        "date": lead.date.isoformat() if lead.date else "unknown",
    }
    summary = await grok_crash_summary(crash_data)
    lead.ai_summary = summary
    db.commit()
    return {"lead_id": lead_id, "summary": summary}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(CrashLead).count()
    high_value = db.query(CrashLead).filter(CrashLead.lead_score >= 50).count()
    states = (
        db.query(CrashLead.state)
        .distinct()
        .all()
    )
    return {
        "total_leads": total,
        "high_value_leads": high_value,
        "states_covered": [s[0] for s in states if s[0]],
    }


# ---------------------------------------------------------------------------
# Stripe / Subscriptions
# ---------------------------------------------------------------------------
@app.post("/api/subscribe")
async def subscribe(email: str, tier: str = "pro"):
    url = await create_checkout_session(email, tier)
    return {"checkout_url": url}


@app.post("/api/webhooks/stripe")
async def stripe_webhook():
    """Handle Stripe webhook events (subscription created/canceled/etc.).

    TODO: Implement full webhook signature verification and event handling.
    See https://stripe.com/docs/webhooks for details.
    """
    return {"status": "received"}
