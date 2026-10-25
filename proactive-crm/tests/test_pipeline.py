import asyncio
import os

os.environ["CRM_FORCE_DEMO"] = "1"
os.environ["CRM_TODAY"] = "2026-10-26"  # a Monday
os.environ["CRM_DB"] = "/tmp/proactive_crm_test.db"

from fastapi.testclient import TestClient  # noqa: E402

from proactive_crm import db  # noqa: E402
from proactive_crm.agents import run_morning  # noqa: E402
from proactive_crm.rules import free_slots, rule_score  # noqa: E402


def test_rules():
    assert rule_score("Proposal", 3, 100_000, 30) == (False, 17)
    flagged, score = rule_score("Contract", 6, 176_000, 9)
    assert flagged and score == 78


def test_slots_respect_weekends():
    conn = db.connect()
    db.seed(conn)
    for country in ("UAE", "KSA"):
        for s in free_slots(conn, country):
            assert s.weekday() <= (4 if country == "UAE" else 3)


def test_end_to_end_human_in_the_loop():
    from proactive_crm.server import app

    with TestClient(app) as c:
        c.post("/api/reset")
        b = c.get("/api/brief").json()
        assert b["mode"]["mode"] == "demo" and b["stats"]["at_risk"] == 10
        assert all(i["status"] == "pending" for i in b["items"])  # nothing is auto-approved or sent
        ar = next(i for i in b["items"] if i["language"] == "ar")
        assert "السلام عليكم" in ar["body"] and ar["slots"][0]["ar"] in ar["body"]
        en = next(i for i in b["items"] if i["language"] == "en")
        assert en["slots"][0]["en"] in en["body"]
        assert c.post(f"/api/drafts/{ar['draft_id']}/approve").status_code == 200
        assert c.post(f"/api/drafts/{ar['draft_id']}/approve").status_code == 409  # decided once
        actions = [a["action"] for a in c.get("/api/audit").json()]
        assert "approved" in actions and "crm_activity_logged" in actions and "drafted_followup" in actions
        # re-running the morning job does not duplicate drafts
        assert c.post("/api/run").json()["drafts_created"] == 0
