"""Three cooperating agents built on Microsoft Agent Framework: Pipeline Watcher -> Scheduler -> Follow-up Writer.
Nothing is ever sent: the pipeline only produces drafts that wait for a human click."""
import asyncio
import json
import re
from datetime import date, datetime

from agent_framework import Agent

from . import canned
from .db import STALE_DAYS, audit, idle_days, now, today
from .llm import make_client, mode
from .rules import fmt_slot, free_slots, level, rule_score, to_usd

VENDOR = "Nawa Solutions"  # fictional seller
STAGE_AR = {"Qualified": "مؤهَّل", "Discovery": "الاستكشاف", "Proposal": "العرض", "Negotiation": "التفاوض", "Contract": "التعاقد"}

WATCHER = ("You are the Pipeline Watcher of a B2B sales team in the Gulf. A rule engine already flagged a deal as going cold. "
           "Read the facts and last note. Reply with ONLY JSON: {\"adjust\": integer -15..15 (positive = riskier), "
           "\"reason_en\": one sentence, \"reason_ar\": the same sentence in Modern Standard Arabic}.")
SCHEDULER = ("You are the Scheduler. From the candidate slots (ISO, Dubai time, already free and inside working hours) pick the best two, "
             "on different days. Reply with ONLY JSON: {\"slots\": [iso, iso], \"rationale\": short}. Never invent a slot that is not a candidate.")
WRITER = ("You are the Follow-up Writer for a Gulf B2B sales rep. Write in the customer's language (language=ar: polished Modern Standard Arabic "
          "with a warm Gulf business tone, greeting 'السلام عليكم ورحمة الله وبركاته'; language=en: courteous professional English). "
          "Respect the channel (whatsapp: 3 to 4 short lines, email: subject + short body). Be specific to the deal, not pushy, never invent facts, "
          "offer exactly the two given meeting slots using the given labels verbatim, sign with the rep and company. "
          "Reply with ONLY JSON: {\"subject\": str, \"body\": str}.")


class Crew:
    def __init__(self, client=None):
        c = client or make_client()
        self.watcher = Agent(client=c, name="PipelineWatcher", instructions=WATCHER)
        self.scheduler = Agent(client=c, name="Scheduler", instructions=SCHEDULER)
        self.writer = Agent(client=c, name="FollowUpWriter", instructions=WRITER)

    async def ask(self, agent: Agent, task: str, payload: dict, valid) -> tuple[dict, str]:
        """Run one agent; on any LLM failure or invalid output fall back to the deterministic template (and say so)."""
        prompt = f"TASK: {task}\nPAYLOAD: {json.dumps(payload, ensure_ascii=False)}"
        try:
            text = (await agent.run(prompt)).text or ""
            out = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            if valid(out):
                return out, mode()["mode"]
        except Exception:  # noqa: BLE001 - any provider/parse error must not break the morning run
            pass
        return json.loads(canned.answer(prompt)), "fallback"


def _arabic_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum("؀" <= c <= "ۿ" for c in letters) / max(1, len(letters))


async def process_deal(conn, crew: Crew, deal) -> bool:
    """Run the three agents for one deal. Returns False when the deal is healthy (not flagged)."""
    did = deal["id"]
    idle = idle_days(conn, did)
    close_in = (date.fromisoformat(deal["close_date"]) - today()).days
    usd = to_usd(deal["amount"], deal["currency"])
    flagged, base = rule_score(deal["stage"], idle, usd, close_in)
    if not flagged:
        return False
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (deal["account_id"],)).fetchone()
    con = conn.execute("SELECT * FROM contacts WHERE id=?", (deal["contact_id"],)).fetchone()
    note = conn.execute("SELECT note FROM activities WHERE deal_id=? ORDER BY date DESC, id DESC LIMIT 1", (did,)).fetchone()[0]

    # 1) Pipeline Watcher: rules gave the base score, the LLM nudges it from the last note
    w, src = await crew.ask(crew.watcher, "watcher", dict(
        deal=deal["name_en"], stage=deal["stage"], stage_ar=STAGE_AR[deal["stage"]], idle_days=idle, threshold=STALE_DAYS[deal["stage"]],
        amount_usd=usd, close_in_days=close_in, rule_score=base, last_note=note),
        lambda o: isinstance(o.get("adjust"), int) and o.get("reason_en") and o.get("reason_ar"))
    adjust = max(-15, min(15, w["adjust"]))
    risk = max(50, min(100, base + adjust))
    conn.execute("INSERT OR REPLACE INTO assessments VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                 (did, idle, STALE_DAYS[deal["stage"]], base, adjust, risk, level(risk), w["reason_en"], w["reason_ar"], src, now()))
    audit(conn, "PipelineWatcher", "scored_risk", did, f"rules={base} llm_adjust={adjust} risk={risk} source={src}")

    # 2) Scheduler: propose two slots from the sample calendar
    cands = free_slots(conn, acc["country"])
    s, src = await crew.ask(crew.scheduler, "scheduler", {"candidates": [c.isoformat() for c in cands], "country": acc["country"]},
                            lambda o: len(o.get("slots", [])) == 2 and all(x in {c.isoformat() for c in cands} for x in o["slots"]))
    slots = [datetime.fromisoformat(x) for x in s["slots"]]
    audit(conn, "Scheduler", "proposed_slots", did, f"{[x.isoformat() for x in slots]} source={src}")

    # 3) Follow-up Writer: bilingual draft in the customer's language, containing the proposed slots
    lang = con["language"]
    labels = [fmt_slot(x, lang) for x in slots]
    payload = dict(language=lang, channel=con["channel"], stage=deal["stage"], gender=con["gender"], contact_en=con["name_en"], contact_ar=con["name_ar"],
                   company_en=acc["name_en"], company_ar=acc["name_ar"], deal_en=deal["name_en"], deal_ar=deal["name_ar"], idle_days=idle,
                   last_note=note, rep=deal["owner"], rep_ar="عمر حداد", vendor=VENDOR, vendor_ar="نوى للحلول", slot_labels=labels)
    d, src = await crew.ask(crew.writer, "writer", payload, lambda o: bool(o.get("body")) and (lang != "ar" or _arabic_ratio(o["body"]) > 0.4))
    cur = conn.execute("INSERT INTO drafts(deal_id,language,channel,subject,body,slots,status,source,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       (did, lang, con["channel"], d.get("subject", ""), d["body"], json.dumps([x.isoformat() for x in slots]), "pending", src, now()))
    audit(conn, "FollowUpWriter", "drafted_followup", did, f"draft={cur.lastrowid} lang={lang} channel={con['channel']} source={src}")
    conn.commit()
    return True


async def run_morning(conn, crew: Crew | None = None) -> dict:
    """The daily job: scan open deals, create drafts for newly flagged ones. Deals that already have a live draft are skipped."""
    crew = crew or Crew()
    audit(conn, "System", "morning_run_started", None, f"mode={mode()['mode']}")
    busy = {r[0] for r in conn.execute("SELECT deal_id FROM drafts WHERE status IN ('pending','approved') AND created_at >= datetime('now','localtime','-3 days')")}
    deals = [d for d in conn.execute("SELECT * FROM deals ORDER BY id") if d["id"] not in busy]
    sem = asyncio.Semaphore(4)

    async def one(d):
        async with sem:
            return await process_deal(conn, crew, d)

    flags = await asyncio.gather(*(one(d) for d in deals))
    n = sum(flags)
    audit(conn, "System", "morning_run_finished", None, f"scanned={len(deals)} drafts_created={n}")
    return {"scanned": len(deals), "drafts_created": n}
