"""FastAPI app: morning brief API + static React UI. Human approval is the only way a draft leaves 'pending'."""
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .agents import run_morning
from .llm import mode
from .rules import fmt_slot, to_usd

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect()
    if not db.DB_PATH.stat().st_size or not conn.execute("SELECT name FROM sqlite_master WHERE name='deals'").fetchone():
        db.seed(conn)
        await run_morning(conn)
    conn.close()
    yield


app = FastAPI(title="Proactive CRM", lifespan=lifespan)


def _brief(conn) -> dict:
    items = []
    for r in conn.execute("""SELECT d.*, a.name_en acc_en, a.name_ar acc_ar, a.country, c.name_en con_en, c.name_ar con_ar, c.title_en, c.title_ar,
                                    s.idle_days, s.threshold, s.rule_score, s.llm_adjust, s.risk, s.level, s.reason_en, s.reason_ar, s.source score_src,
                                    dr.id draft_id, dr.language, dr.channel, dr.subject, dr.body, dr.slots, dr.status, dr.source draft_src
                             FROM assessments s JOIN deals d ON d.id=s.deal_id JOIN accounts a ON a.id=d.account_id JOIN contacts c ON c.id=d.contact_id
                             JOIN drafts dr ON dr.id=(SELECT MAX(id) FROM drafts WHERE deal_id=d.id)
                             ORDER BY s.risk DESC"""):
        x = dict(r)
        slots = [datetime.fromisoformat(s) for s in json.loads(x.pop("slots"))]
        x["slots"] = [{"iso": s.isoformat(), "en": fmt_slot(s, "en"), "ar": fmt_slot(s, "ar")} for s in slots]
        x["amount_usd"] = round(to_usd(x["amount"], x["currency"]))
        items.append(x)
    live = [i for i in items if i["status"] != "rejected"]
    return {
        "mode": mode(), "today": db.today().isoformat(),
        "stats": {
            "open_deals": conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0],
            "at_risk": len(items),
            "value_at_risk_usd": sum(i["amount_usd"] for i in items),
            "pending": sum(i["status"] == "pending" for i in live),
            "approved": sum(i["status"] == "approved" for i in live),
        },
        "items": items,
    }


@app.get("/api/brief")
async def brief():
    conn = db.connect()
    try:
        return _brief(conn)
    finally:
        conn.close()


@app.post("/api/run")
async def run():
    conn = db.connect()
    try:
        return await run_morning(conn)
    finally:
        conn.close()


@app.post("/api/reset")
async def reset():
    conn = db.connect()
    try:
        db.seed(conn)
        await run_morning(conn)
        return {"ok": True}
    finally:
        conn.close()


def _decide(draft_id: int, status: str):
    conn = db.connect()
    try:
        d = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not d or d["status"] != "pending":
            raise HTTPException(409, "draft is not pending")
        conn.execute("UPDATE drafts SET status=?, decided_at=? WHERE id=?", (status, db.now(), draft_id))
        db.audit(conn, "user", status, d["deal_id"], f"draft={draft_id}")
        if status == "approved":  # log back to the CRM; sending itself stays a manual step by the rep
            conn.execute("INSERT INTO activities(deal_id,type,date,note) VALUES(?,?,?,?)", (
                d["deal_id"], "agent_followup", db.today().isoformat(),
                f"Follow-up draft #{draft_id} ({d['channel']}, {d['language']}) approved by rep; ready to send."))
            db.audit(conn, "System", "crm_activity_logged", d["deal_id"], f"draft={draft_id}")
        conn.commit()
        return {"ok": True, "status": status}
    finally:
        conn.close()


@app.post("/api/drafts/{draft_id}/approve")
async def approve(draft_id: int):
    return _decide(draft_id, "approved")


@app.post("/api/drafts/{draft_id}/reject")
async def reject(draft_id: int):
    return _decide(draft_id, "rejected")


@app.get("/api/audit")
async def audit_log(limit: int = 200):
    conn = db.connect()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))]
    finally:
        conn.close()


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
