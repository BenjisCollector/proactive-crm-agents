const { useState, useEffect, useMemo, createElement: h } = React;
const html = htm.bind(h);

const T = {
  en: { title: "Proactive CRM", sub: "Morning brief", openDeals: "Open deals", atRisk: "Going cold", valueAtRisk: "Value at risk", pending: "Awaiting approval", approved: "Approved",
    guard: "Nothing is ever sent automatically. Every draft needs your approval and is logged below.", run: "Run morning scan", reset: "Reset demo", brief: "Brief", audit: "Audit log",
    pend: "Awaiting", appr: "Approved", all: "All", why: "Why it is flagged", risk: "Risk", rules: "rules", llm: "agent", draft: "Draft follow-up", slots: "Proposed meeting slots",
    approve: "Approve draft", reject: "Reject", idle: "days silent", to: "To", empty: "No deals here.", demo: "Demo mode: canned outputs", live: "Live model",
    time: "Time", actor: "Actor", action: "Action", deal: "Deal", detail: "Detail", lang: "Customer language", approvedMsg: "Approved and logged to the CRM. The rep sends it.", rejectedMsg: "Rejected." },
  ar: { title: "CRM الاستباقي", sub: "الملخص الصباحي", openDeals: "الصفقات المفتوحة", atRisk: "صفقات تبرد", valueAtRisk: "القيمة المعرّضة للخطر", pending: "بانتظار الموافقة", approved: "تمت الموافقة",
    guard: "لا يُرسَل شيء تلقائياً. كل مسودة تحتاج موافقتك ويُسجَّل ذلك في سجل التدقيق.", run: "تشغيل الفحص الصباحي", reset: "إعادة ضبط العرض", brief: "الملخص", audit: "سجل التدقيق",
    pend: "بانتظار", appr: "موافق عليها", all: "الكل", why: "سبب التنبيه", risk: "الخطر", rules: "القواعد", llm: "الوكيل", draft: "مسودة المتابعة", slots: "المواعيد المقترحة",
    approve: "الموافقة على المسودة", reject: "رفض", idle: "يوماً بلا تواصل", to: "إلى", empty: "لا توجد صفقات.", demo: "وضع العرض: مخرجات جاهزة", live: "نموذج حي",
    time: "الوقت", actor: "المنفّذ", action: "الإجراء", deal: "الصفقة", detail: "التفاصيل", lang: "لغة العميل", approvedMsg: "تمت الموافقة وسُجّلت في النظام. المندوب هو من يرسلها.", rejectedMsg: "تم الرفض." },
};
const STAGE_AR = { Qualified: "مؤهَّل", Discovery: "الاستكشاف", Proposal: "العرض", Negotiation: "التفاوض", Contract: "التعاقد" };
const ACTIONS = { scored_risk: ["Scored risk", "تقييم الخطر"], proposed_slots: ["Proposed slots", "اقتراح مواعيد"], drafted_followup: ["Drafted follow-up", "صياغة مسودة"],
  approved: ["Approved", "موافقة"], rejected: ["Rejected", "رفض"], crm_activity_logged: ["Logged to CRM", "تسجيل في النظام"], morning_run_started: ["Morning run started", "بدء الفحص الصباحي"],
  morning_run_finished: ["Morning run finished", "انتهاء الفحص الصباحي"] };

function App() {
  const [lang, setLang] = useState(() => { try { return localStorage.getItem("lang") || "en"; } catch { return "en"; } });
  const [data, setData] = useState(null);
  const [audit, setAudit] = useState([]);
  const [view, setView] = useState("brief");
  const [filter, setFilter] = useState("pending");
  const [sel, setSel] = useState(null);
  const [busy, setBusy] = useState(false);
  const t = T[lang];
  const nf = useMemo(() => new Intl.NumberFormat(lang === "ar" ? "ar-AE-u-nu-latn" : "en-US"), [lang]);

  const load = async () => {
    const [b, a] = await Promise.all([fetch("/api/brief").then(r => r.json()), fetch("/api/audit").then(r => r.json())]);
    setData(b); setAudit(a);
    setSel(s => (s && b.items.some(i => i.id === s)) ? s : (b.items.find(i => i.status === "pending") || b.items[0] || {}).id);
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    document.documentElement.lang = lang; document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    try { localStorage.setItem("lang", lang); } catch {}
  }, [lang]);

  if (!data) return html`<div class="app"><div class="empty">…</div></div>`;
  const nm = (i, k) => (lang === "ar" ? i[k + "_ar"] : i[k + "_en"]);
  const items = data.items.filter(i => filter === "all" || i.status === (filter === "pending" ? "pending" : "approved"));
  const cur = data.items.find(i => i.id === sel);
  const post = async (url) => { setBusy(true); await fetch(url, { method: "POST" }); await load(); setBusy(false); };
  const decide = async (kind) => {
    await post(`/api/drafts/${cur.draft_id}/${kind}`);
  };
  const s = data.stats;
  const stat = (v, l, warn) => html`<div class=${"stat" + (warn ? " warn" : "")}><b>${v}</b><span>${l}</span></div>`;

  return html`<div class="app">
    <header>
      <h1>${t.title}</h1><span class="sub">${t.sub} · ${data.today}</span>
      <span class=${"badge " + data.mode.mode}>${data.mode.mode === "demo" ? t.demo : `${t.live}: ${data.mode.model}`}</span>
      <span class="sp"></span>
      <div class="seg"><button class=${view === "brief" ? "on" : ""} onClick=${() => setView("brief")}>${t.brief}</button>
        <button class=${view === "audit" ? "on" : ""} onClick=${() => setView("audit")}>${t.audit}</button></div>
      <button disabled=${busy} onClick=${() => post("/api/run")}>${t.run}</button>
      <button disabled=${busy} onClick=${() => post("/api/reset")}>${t.reset}</button>
      <div class="seg"><button class=${lang === "en" ? "on" : ""} onClick=${() => setLang("en")}>EN</button>
        <button class=${lang === "ar" ? "on" : ""} onClick=${() => setLang("ar")}>العربية</button></div>
    </header>
    <div class="stats">
      ${stat(nf.format(s.open_deals), t.openDeals)}${stat(nf.format(s.at_risk), t.atRisk, true)}${stat("$" + nf.format(s.value_at_risk_usd), t.valueAtRisk, true)}
      ${stat(nf.format(s.pending), t.pending)}${stat(nf.format(s.approved), t.approved)}
    </div>
    <div class="guard">${t.guard}</div>
    ${view === "audit" ? html`<div class="panel"><table><thead><tr><th>${t.time}</th><th>${t.actor}</th><th>${t.action}</th><th>${t.deal}</th><th>${t.detail}</th></tr></thead><tbody>
      ${audit.map(a => { const d = data.items.find(i => i.id === a.deal_id); return html`<tr key=${a.id}><td class="d">${a.ts.replace("T", " ")}</td><td>${a.actor}</td>
        <td>${(ACTIONS[a.action] || [a.action, a.action])[lang === "ar" ? 1 : 0]}</td><td>${d ? nm(d, "name") : ""}</td><td class="d" dir="ltr">${a.detail}</td></tr>`; })}</tbody></table></div>` :
    html`<main>
      <section class="panel list">
        <div class="tabs">${[["pending", t.pend], ["approved", t.appr], ["all", t.all]].map(([k, l]) => html`<div key=${k} class="seg"><button class=${filter === k ? "on" : ""} onClick=${() => setFilter(k)}>${l}</button></div>`)}</div>
        ${items.length === 0 ? html`<div class="empty">${t.empty}</div>` : items.map(i => html`<button key=${i.id} class=${"row" + (i.id === sel ? " sel" : "")} onClick=${() => setSel(i.id)}>
          <span class=${"risk " + i.level}>${i.risk}</span>
          <span class="t"><b>${nm(i, "acc")}</b><small>${nm(i, "name")} · ${nf.format(i.idle_days)} ${t.idle}</small></span>
          <span class=${"chip " + i.status}>${i.status === "pending" ? t.pend : i.status === "approved" ? t.appr : t.reject}</span></button>`)}
      </section>
      <section class="panel detail">${!cur ? html`<div class="empty">${t.empty}</div>` : html`
        <div><h2>${nm(cur, "acc")} · ${nm(cur, "name")}</h2>
          <div class="meta"><bdi>${nf.format(cur.amount)} ${cur.currency} (≈ $${nf.format(cur.amount_usd)})</bdi> · ${lang === "ar" ? STAGE_AR[cur.stage] : cur.stage} · ${t.to}: ${nm(cur, "con")}, ${lang === "ar" ? cur.title_ar : cur.title_en}</div></div>
        <div class="why"><div class="lbl">${t.why}</div>${lang === "ar" ? cur.reason_ar : cur.reason_en}
          <div class="score">${t.risk} ${cur.risk} = ${t.rules} ${cur.rule_score} ${cur.llm_adjust >= 0 ? "+" : "−"} ${t.llm} ${Math.abs(cur.llm_adjust)}</div></div>
        <div><div class="lbl">${t.slots}</div><div class="slots">${cur.slots.map(x => html`<span class="slot" key=${x.iso} dir=${cur.language === "ar" ? "rtl" : "ltr"}>${x[cur.language]}</span>`)}</div></div>
        <div><div class="lbl">${t.draft} · ${cur.channel} · ${t.lang}: ${cur.language === "ar" ? "العربية" : "English"}</div>
          <div class="draft" dir=${cur.language === "ar" ? "rtl" : "ltr"}>${cur.subject && cur.channel === "email" ? html`<div class="subj">${cur.subject}</div>` : null}${cur.body}</div></div>
        ${cur.status === "pending" ? html`<div class="actions"><button class="primary" disabled=${busy} onClick=${() => decide("approve")}>${t.approve}</button>
          <button class="danger" disabled=${busy} onClick=${() => decide("reject")}>${t.reject}</button></div>` :
          html`<div class="actions"><span class=${"chip " + cur.status}>${cur.status === "approved" ? t.approvedMsg : t.rejectedMsg}</span></div>`}`}
      </section></main>`}
  </div>`;
}
ReactDOM.createRoot(document.getElementById("root")).render(h(App));
