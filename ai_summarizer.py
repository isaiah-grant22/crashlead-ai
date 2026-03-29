import os
import httpx
from dotenv import load_dotenv

load_dotenv()


async def grok_crash_summary(crash_row: dict) -> str:
    """Generate a crash summary. Uses Grok AI if a key is set, otherwise
    returns a basic rule-based summary so the app works without any API key."""

    api_key = os.getenv("GROK_API_KEY", "")

    # ---- Fallback: no API key → simple local summary ----
    if not api_key or api_key.startswith("xai-XXX"):
        nature = str(crash_row.get("Nature", "Unknown"))
        injury = str(crash_row.get("Injury", "Unknown"))
        agency = str(crash_row.get("Agency", "Unknown"))
        state = str(crash_row.get("State", ""))
        return (
            f"Crash reported by {agency} ({state}). "
            f"Nature: {nature}. Injury: {injury}. "
            f"Review the full report for liability and insurance details. "
            f"(Add a GROK_API_KEY to .env for AI-powered summaries.)"
        )

    # ---- Grok AI summary ----
    prompt = f"""
    You are an Indiana personal-injury attorney. Summarize this crash report
    in 2-3 sentences for a lawyer. Focus on injury severity, possible liability,
    insurance angles, and why this is a strong lead.
    Crash data: {crash_row}
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.grok.xai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "grok-beta",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 400,
                },
                timeout=30,
            )
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI summary unavailable: {str(e)}"
