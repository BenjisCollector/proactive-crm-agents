"""SQLite schema + a fictional Gulf sample CRM. Dates are relative to 'today' so the demo never goes stale."""
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("CRM_DB", Path(__file__).resolve().parent.parent / "data" / "crm.db"))
FX_TO_USD = {"AED": 0.272, "SAR": 0.267, "QAR": 0.275, "KWD": 3.25, "BHD": 2.65, "OMR": 2.60, "USD": 1.0}
# days without customer contact before a deal in this stage counts as "going cold"
STALE_DAYS = {"Qualified": 14, "Discovery": 10, "Proposal": 7, "Negotiation": 5, "Contract": 4}
STAGES = list(STALE_DAYS)
# customer-facing touches; agent/system rows are excluded so our own follow-ups never hide a cold deal
TOUCH_TYPES = ("call", "email", "meeting", "whatsapp")

SCHEMA = """
CREATE TABLE accounts(id INTEGER PRIMARY KEY, name_en TEXT, name_ar TEXT, country TEXT, industry TEXT);
CREATE TABLE contacts(id INTEGER PRIMARY KEY, account_id INT, name_en TEXT, name_ar TEXT, title_en TEXT, title_ar TEXT,
  gender TEXT, language TEXT, channel TEXT, email TEXT, phone TEXT);
CREATE TABLE deals(id INTEGER PRIMARY KEY, account_id INT, contact_id INT, name_en TEXT, name_ar TEXT, stage TEXT,
  amount REAL, currency TEXT, close_date TEXT, owner TEXT);
CREATE TABLE activities(id INTEGER PRIMARY KEY, deal_id INT, type TEXT, date TEXT, note TEXT);
CREATE TABLE calendar(id INTEGER PRIMARY KEY, start TEXT, end TEXT, title TEXT);
CREATE TABLE assessments(deal_id INTEGER PRIMARY KEY, idle_days INT, threshold INT, rule_score INT, llm_adjust INT,
  risk INT, level TEXT, reason_en TEXT, reason_ar TEXT, source TEXT, created_at TEXT);
CREATE TABLE drafts(id INTEGER PRIMARY KEY, deal_id INT, language TEXT, channel TEXT, subject TEXT, body TEXT,
  slots TEXT, status TEXT, source TEXT, created_at TEXT, decided_at TEXT);
CREATE TABLE audit(id INTEGER PRIMARY KEY, ts TEXT, actor TEXT, action TEXT, deal_id INT, detail TEXT);
"""

# (en, ar, country, industry)
ACCOUNTS = [
    ("Wahat Logistics", "واحة للخدمات اللوجستية", "UAE", "Logistics"),
    ("Marjan Bay Hospitality", "مرجان باي للضيافة", "Bahrain", "Hospitality"),
    ("Sahara Steelworks", "الصحراء للصناعات الحديدية", "KSA", "Manufacturing"),
    ("Rimal Retail Group", "مجموعة رمال للتجزئة", "UAE", "Retail"),
    ("Falaj Water Solutions", "الفلج لحلول المياه", "Oman", "Utilities"),
    ("Safwa Medical Centers", "مراكز صفوة الطبية", "Kuwait", "Healthcare"),
    ("Tilal Property Developers", "تلال للتطوير العقاري", "Qatar", "Real estate"),
    ("Najd Agritech", "نجد للتقنيات الزراعية", "KSA", "Agriculture"),
    ("Hudhud Telecom Services", "الهدهد لخدمات الاتصالات", "UAE", "Telecom"),
    ("Mawj Marine Services", "موج للخدمات البحرية", "Qatar", "Maritime"),
    ("Qamar Education Group", "مجموعة قمر التعليمية", "KSA", "Education"),
    ("Sabah Foods Trading", "صباح لتجارة الأغذية", "Kuwait", "Food & beverage"),
]
GENDER = "mfmfmfmfmmfm"  # per contact, used for Arabic/English honorifics
# (account idx, name_en, name_ar, title_en, title_ar, language, channel)
CONTACTS = [
    (0, "Khalid Al-Mazrouei", "خالد المزروعي", "Head of Operations", "رئيس العمليات", "ar", "whatsapp"),
    (1, "Priya Menon", "بريا مينون", "IT Director", "مديرة تقنية المعلومات", "en", "email"),
    (2, "Faisal Al-Dossary", "فيصل الدوسري", "Procurement Manager", "مدير المشتريات", "ar", "email"),
    (3, "Mariam Al-Suwaidi", "مريم السويدي", "Chief Digital Officer", "الرئيسة التنفيذية للتحول الرقمي", "ar", "whatsapp"),
    (4, "Said Al-Balushi", "سعيد البلوشي", "Operations Director", "مدير العمليات", "ar", "email"),
    (5, "Dr. Hessa Al-Sabah", "د. حصة الصباح", "Medical Director", "المديرة الطبية", "en", "email"),
    (6, "Nasser Al-Thani", "ناصر آل ثاني", "Commercial Director", "المدير التجاري", "ar", "whatsapp"),
    (7, "Reem Al-Qahtani", "ريم القحطاني", "Innovation Lead", "قائدة الابتكار", "ar", "email"),
    (8, "James Whitfield", "جيمس ويتفيلد", "VP Customer Experience", "نائب الرئيس لتجربة العملاء", "en", "email"),
    (9, "Abdullah Al-Kuwari", "عبدالله الكواري", "Fleet Manager", "مدير الأسطول", "ar", "whatsapp"),
    (10, "Noura Al-Harbi", "نورة الحربي", "Head of Finance", "رئيسة المالية", "ar", "email"),
    (11, "Yousef Al-Rashidi", "يوسف الراشدي", "Supply Chain Manager", "مدير سلسلة الإمداد", "ar", "email"),
]
# (contact idx, name_en, name_ar, stage, amount, currency, close in N days, idle days, last note)
DEALS = [
    (0, "Fleet visibility rollout", "تطبيق منصة تتبع الأسطول", "Proposal", 420000, "AED", 24, 12, "Sent revised proposal; he asked for a Q3 go-live date."),
    (1, "Guest feedback analytics", "تحليلات آراء الضيوف", "Negotiation", 38000, "BHD", 14, 9, "Legal reviewing MSA; waiting on data-residency answer."),
    (2, "Plant maintenance AI", "الصيانة التنبؤية للمصنع", "Discovery", 900000, "SAR", 70, 15, "Site visit done; asked for a reference customer in KSA."),
    (3, "Loyalty personalisation", "تخصيص برنامج الولاء", "Contract", 650000, "AED", 9, 6, "Contract sent for signature; CFO still to approve."),
    (4, "Network leak detection", "اكتشاف تسرب الشبكات", "Proposal", 120000, "OMR", 35, 3, "Walkthrough of the pilot scope went well."),
    (5, "Patient no-show reduction", "تقليل غياب المرضى عن المواعيد", "Qualified", 85000, "KWD", 60, 19, "Intro call; interested but busy with accreditation."),
    (6, "Sales pipeline copilot", "مساعد ذكي لإدارة المبيعات", "Negotiation", 1400000, "QAR", 18, 8, "Discount discussion; wants three-year price lock."),
    (7, "Crop yield forecasting", "التنبؤ بإنتاجية المحاصيل", "Discovery", 540000, "SAR", 55, 4, "Shared sample dataset requirements."),
    (8, "Churn early warning", "نظام الإنذار المبكر لفقدان العملاء", "Proposal", 310000, "AED", 30, 10, "Asked for an Arabic-language demo for his regional team."),
    (9, "Vessel turnaround tracker", "متابعة زمن دوران السفن", "Contract", 760000, "QAR", 12, 2, "Signed order form expected this week."),
    (10, "Admissions assistant", "مساعد القبول والتسجيل", "Discovery", 270000, "SAR", 80, 14, "Requested a quote for 3 campuses; then went quiet."),
    (11, "Demand forecasting", "التنبؤ بالطلب", "Qualified", 150000, "KWD", 90, 5, "Booked a discovery workshop."),
    (0, "Warehouse robotics analytics", "تحليلات الروبوتات في المستودعات", "Qualified", 95000, "AED", 100, 16, "Early interest after the logistics summit."),
    (3, "Store traffic heatmaps", "الخرائط الحرارية لحركة المتاجر", "Negotiation", 210000, "AED", 20, 7, "Procurement asked for a revised payment schedule."),
]
# busy blocks for the rep's sample calendar: (days from today, start hour, minutes, title)
BUSY = [(1, 10, 60, "Quarterly forecast review"), (1, 14, 60, "Customer onboarding call"), (2, 11, 60, "Team stand-up"),
        (2, 15, 60, "Partner sync"), (3, 10, 60, "Pipeline review"), (3, 14, 30, "Internal demo prep"),
        (4, 11, 60, "Product roadmap session"), (5, 10, 90, "Training"), (7, 14, 60, "Customer QBR")]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def today() -> date:
    return date.fromisoformat(os.environ["CRM_TODAY"]) if os.environ.get("CRM_TODAY") else date.today()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def seed(conn: sqlite3.Connection) -> None:
    """Drop and recreate everything. Fictional data only; any resemblance to real companies is coincidental."""
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        conn.execute(f"DROP TABLE {t}")
    conn.executescript(SCHEMA)
    t = today()
    d = lambda n: (t + timedelta(days=n)).isoformat()
    for i, (en, ar, country, ind) in enumerate(ACCOUNTS, 1):
        conn.execute("INSERT INTO accounts VALUES(?,?,?,?,?)", (i, en, ar, country, ind))
    for i, (a, en, ar, ten, tar, lang, ch) in enumerate(CONTACTS, 1):
        slug = ACCOUNTS[a][0].lower().replace(" ", "-")
        conn.execute("INSERT INTO contacts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                     (i, a + 1, en, ar, ten, tar, GENDER[i - 1], lang, ch, f"{en.split()[-1].lower()}@{slug}.example", f"+971 50 000 {1000 + i}"))
    for i, (c, en, ar, stage, amt, cur, close, idle, note) in enumerate(DEALS, 1):
        acc = CONTACTS[c][0] + 1
        conn.execute("INSERT INTO deals VALUES(?,?,?,?,?,?,?,?,?,?)", (i, acc, c + 1, en, ar, stage, amt, cur, d(close), "Omar Haddad"))
        conn.execute("INSERT INTO activities(deal_id,type,date,note) VALUES(?,?,?,?)", (i, "meeting", d(-idle - 20), "Kick-off meeting."))
        conn.execute("INSERT INTO activities(deal_id,type,date,note) VALUES(?,?,?,?)", (i, "email", d(-idle), note))
    for day, hour, mins, title in BUSY:
        s = datetime.combine(t + timedelta(days=day), datetime.min.time()).replace(hour=hour)
        conn.execute("INSERT INTO calendar(start,end,title) VALUES(?,?,?)", (s.isoformat(), (s + timedelta(minutes=mins)).isoformat(), title))
    conn.commit()


def audit(conn: sqlite3.Connection, actor: str, action: str, deal_id: int | None, detail: str = "") -> None:
    conn.execute("INSERT INTO audit(ts,actor,action,deal_id,detail) VALUES(?,?,?,?,?)", (now(), actor, action, deal_id, detail))
    conn.commit()


def idle_days(conn: sqlite3.Connection, deal_id: int) -> int:
    q = ",".join("?" * len(TOUCH_TYPES))
    last = conn.execute(f"SELECT MAX(date) FROM activities WHERE deal_id=? AND type IN ({q})", (deal_id, *TOUCH_TYPES)).fetchone()[0]
    return (today() - date.fromisoformat(last)).days
