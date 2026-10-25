"""Deterministic stand-in for the LLM, used in demo mode (no keys, no network). Same JSON contract as the real prompts."""
import json
from datetime import datetime

ASK_AR = {
    "Qualified": "وددت أن أطمئن على أولوياتكم الحالية وأن أرى كيف نستطيع دعمكم في الفترة القادمة.",
    "Discovery": "ونرغب في استكمال ما بدأناه في جلسة الاستكشاف وتزويدكم بكل ما طلبتموه.",
    "Proposal": "وأودّ الاطمئنان على رأيكم في العرض المقدّم والإجابة عن أي استفسار لديكم.",
    "Negotiation": "ونرغب في حسم النقاط المتبقية في الاتفاق حتى نتمكن من المضي قدماً في الموعد المخطط له.",
    "Contract": "ونأمل إتمام إجراءات توقيع العقد في أقرب وقت، وأنا جاهز لتسهيل أي ملاحظات متبقية.",
}
ASK_EN = {
    "Qualified": "I wanted to check in on your current priorities and see how we can best support you in the coming weeks.",
    "Discovery": "I would like to pick up where our discovery session left off and share everything you asked for.",
    "Proposal": "I would value your thoughts on the proposal we shared, and I am glad to answer any questions you may have.",
    "Negotiation": "I would like to close out the remaining points so that we can keep to the timeline we planned together.",
    "Contract": "I hope we can complete the contract signature soon, and I am ready to help with any remaining comments.",
}


def _honorific_ar(p: dict) -> str:
    name = p["contact_ar"]
    if name.startswith("د."):
        return ("الدكتورة " if p["gender"] == "f" else "الدكتور ") + name[2:].strip()
    return ("الأستاذة " if p["gender"] == "f" else "الأستاذ ") + name


def _short_ar(p: dict) -> str:
    name = p["contact_ar"]
    if name.startswith("د."):
        return ("دكتورة " if p["gender"] == "f" else "دكتور ") + name[2:].split()[0]
    return ("أستاذة " if p["gender"] == "f" else "أستاذ ") + name.split()[0]


def _honorific_en(p: dict) -> str:
    n = p["contact_en"]
    return n if n.startswith("Dr.") else ("Ms. " if p["gender"] == "f" else "Mr. ") + n.split(" ", 1)[1]


def watcher(p: dict) -> dict:
    note, idle, thr = p["last_note"].lower(), p["idle_days"], p["threshold"]
    adjust = 8 if "quiet" in note else 4 if "busy" in note else -3 if any(k in note for k in ("legal", "signature", "cfo", "waiting")) else 0
    why_en = f"No customer contact for {idle} days (limit for {p['stage']} is {thr}); about {p['amount_usd']:,.0f} USD, closing in {p['close_in_days']} days."
    why_ar = f"لا يوجد تواصل مع العميل منذ {idle} يوماً (الحد في مرحلة {p['stage_ar']} هو {thr})، بقيمة تقارب {p['amount_usd']:,.0f} دولار وإغلاق متوقع بعد {p['close_in_days']} يوماً."
    if adjust > 0:
        why_en += " The last note suggests the customer is drifting away."
        why_ar += " آخر ملاحظة تشير إلى أن العميل يبتعد."
    elif adjust < 0:
        why_en += " The last note points to a customer-side process, so risk is eased a little."
        why_ar += " آخر ملاحظة تشير إلى إجراء داخلي لدى العميل، لذلك خُفّفت درجة الخطر قليلاً."
    return {"adjust": adjust, "reason_en": why_en, "reason_ar": why_ar}


def scheduler(p: dict) -> dict:
    c = [datetime.fromisoformat(x) for x in p["candidates"]]
    first = c[0]
    second = next((x for x in c if x.date() > first.date() and x.hour != first.hour), c[-1])
    return {"slots": [first.isoformat(), second.isoformat()], "rationale": "Earliest free slots on different days, inside both sides' working hours."}


def writer(p: dict) -> dict:
    s1, s2 = p["slot_labels"][:2]
    rep, vendor, stage = p["rep"], p["vendor"], p["stage"]
    first_rep = rep.split()[0]
    if p["language"] == "ar":
        who = _honorific_ar(p)
        ask = ASK_AR[stage]
        rep, vendor = p["rep_ar"], p["vendor_ar"]
        subject = f"متابعة بخصوص {p['deal_ar']}"
        if p["channel"] == "whatsapp":
            body = (f"السلام عليكم {_short_ar(p)}، أتمنى أنكم بخير.\n{ask}\n"
                    f"يناسبكم نتكلم {s1} أو {s2}؟\nوإذا في وقت ثاني أنسب لكم أنا حاضر.\nتحياتي، {rep.split()[0]} من {vendor}")
        else:
            body = (f"السلام عليكم ورحمة الله وبركاته،\n\n{who} المحترم{'ة' if p['gender'] == 'f' else ''}،\n\n"
                    f"أتمنى أن تكونوا بخير. أتواصل معكم بخصوص «{p['deal_ar']}» مع {p['company_ar']}؛ {ask}\n\n"
                    f"يسعدني أن نخصص مكالمة قصيرة لمناقشة الخطوات القادمة، وأقترح أحد الموعدين التاليين:\n• {s1}\n• {s2}\n\n"
                    f"وإن كان هناك وقت آخر أنسب لكم فيسعدني التنسيق معكم.\n\nمع خالص التقدير،\n{rep}\n{vendor}")
    else:
        who = _honorific_en(p)
        ask = ASK_EN[stage]
        subject = f"Following up: {p['deal_en']}"
        if p["channel"] == "whatsapp":
            body = (f"Hello {who}, I hope you are well. {ask} Would {s1} or {s2} suit you for a quick call? "
                    f"Happy to adjust if another time is better.\nBest regards, {first_rep} ({vendor})")
        else:
            body = (f"Dear {who},\n\nI hope you and the team at {p['company_en']} are doing well. I am writing about \"{p['deal_en']}\". {ask}\n\n"
                    f"Could we set aside a short call to agree the next steps? I would suggest either of these times:\n- {s1}\n- {s2}\n\n"
                    f"If another time suits you better, I will gladly work around your schedule.\n\nKind regards,\n{rep}\n{vendor}")
    return {"subject": subject, "body": body}


TASKS = {"watcher": watcher, "scheduler": scheduler, "writer": writer}


def answer(prompt: str) -> str:
    task, payload = prompt.split("PAYLOAD:", 1)
    return json.dumps(TASKS[task.replace("TASK:", "").strip()](json.loads(payload)), ensure_ascii=False)
