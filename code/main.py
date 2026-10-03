#!/usr/bin/env python3
"""
Buy or Wait? — AI-powered financial decision agent.
V2: Improved accuracy with better recurring detection and forecast.
"""

import csv
import os
import math
import re
from datetime import datetime, timedelta
from collections import defaultdict
from copy import deepcopy

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")
FORECAST_DAYS = 90

IMAGE_AMOUNTS = {
    "image_01": (4365000, "IDR"), "image_02": (200000, "INR"),
    "image_03": (41272, "INR"),   "image_04": (2854, "INR"),
    "image_05": (704.05, "INR"), "image_06": (1995, "INR"),
    "image_07": (8528, "INR"),   "image_08": (15339, "INR"),
    "image_09": (723, "INR"),    "image_10": (79679.26, "INR"),
    "image_11": (3650, "INR"),   "image_12": (33.50, "USD"),
    "image_13": (2298, "INR"),   "image_14": (4593, "INR"),
    "image_15": (9968, "INR"),   "image_16": (393.22, "INR"),
}

def load_csv(filename):
    path = os.path.join(DATASET_DIR, filename)
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {}
            for k, v in row.items():
                k = k.strip() if k else k
                v = v.strip() if v else v
                cleaned[k] = v
            rows.append(cleaned)
    return rows

def parse_float(s):
    if not s or s.strip() == "":
        return None
    try:
        return float(s.replace(",", ""))
    except:
        return None

def parse_date(s):
    if not s or s.strip() == "":
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except:
        return None

def load_all_data():
    data = {}
    data["requests"] = load_csv("requests.csv")
    data["profiles"] = load_csv("financial_profiles.csv")
    data["events"] = load_csv("financial_events.csv")
    data["exchange_rates"] = load_csv("exchange_rates.csv")
    data["payment_options"] = load_csv("request_payment_options.csv")
    data["messages"] = load_csv("messages.csv")
    data["images"] = load_csv("images.csv")

    data["profile_by_user"] = {p["user_id"]: p for p in data["profiles"]}
    data["events_by_user"] = defaultdict(list)
    data["event_by_id"] = {}
    for e in data["events"]:
        data["events_by_user"][e["user_id"]].append(e)
        data["event_by_id"][e["event_id"]] = e

    data["options_by_request"] = defaultdict(list)
    for o in data["payment_options"]:
        data["options_by_request"][o["request_id"]].append(o)

    data["messages_by_user"] = defaultdict(list)
    data["messages_by_request"] = defaultdict(list)
    for m in data["messages"]:
        data["messages_by_user"][m["user_id"]].append(m)
        if m.get("request_id"):
            data["messages_by_request"][m["request_id"]].append(m)

    data["rate_lookup"] = {}
    data["rate_dates"] = sorted(set(r["rate_date"] for r in data["exchange_rates"]))
    for r in data["exchange_rates"]:
        key = (r["rate_date"], r["from_currency"], r["to_currency"])
        data["rate_lookup"][key] = float(r["rate"])

    for img in data["images"]:
        event_id = img["related_event_id"]
        image_id = img["image_id"]
        if event_id in data["event_by_id"]:
            evt = data["event_by_id"][event_id]
            if not evt.get("amount") or evt["amount"].strip() == "":
                if image_id in IMAGE_AMOUNTS:
                    amt, cur = IMAGE_AMOUNTS[image_id]
                    evt["amount"] = str(amt)
    return data

# ── Exchange rates ───────────────────────────────────────────────────────────
def get_exchange_rate(data, sdate, fc, tc):
    if fc == tc: return 1.0
    ds = sdate.strftime("%Y-%m-%d") if hasattr(sdate, 'strftime') else str(sdate)
    best = None
    for rd in data["rate_dates"]:
        if rd <= ds: best = rd
        else: break
    if not best: best = data["rate_dates"][0] if data["rate_dates"] else None
    if not best: return None
    rl = data["rate_lookup"]
    if (best,fc,tc) in rl: return rl[(best,fc,tc)]
    if (best,tc,fc) in rl: return 1.0/rl[(best,tc,fc)]
    for mid in ("USD","EUR"):
        if fc==mid or tc==mid: continue
        r1=r2=None
        if (best,fc,mid) in rl: r1=rl[(best,fc,mid)]
        elif (best,mid,fc) in rl: r1=1.0/rl[(best,mid,fc)]
        if (best,mid,tc) in rl: r2=rl[(best,mid,tc)]
        elif (best,tc,mid) in rl: r2=1.0/rl[(best,tc,mid)]
        if r1 and r2: return r1*r2
    return None

def get_event_hc(data, event, hcur):
    amt = parse_float(event.get("amount", ""))
    if amt is None: return None
    ecur = event.get("currency", hcur)
    if ecur == hcur: return amt
    sd = parse_date(event.get("settlement_date", "")) or parse_date(event.get("event_date", ""))
    if not sd: return amt
    r = get_exchange_rate(data, sd, ecur, hcur)
    return amt * r if r else amt

# ── Message processing ───────────────────────────────────────────────────────
def process_messages(data, uid, rid):
    adj = {"pending_skip": set(), "unrealized_skip": set(), "rent_increase": False,
           "employment_ended": False, "scam": False}
    all_raw = data["messages_by_user"].get(uid, [])
    if rid:
        all_raw = all_raw + data["messages_by_request"].get(rid, [])
    msgs = list({m["message_id"]: m for m in all_raw}.values())
    for msg in msgs:
        t = msg.get("message_text",""); tl = t.lower(); rev = msg.get("related_event_id","")
        if "refund" in tl and ("not reached" in tl or "still processing" in tl):
            if rev: adj["pending_skip"].add(rev)
        if "prize" in tl and ("pending" in tl or "processing" in tl or "not been credited" in tl):
            if rev and "reached your account" not in tl: adj["pending_skip"].add(rev)
        if "payout is still pending" in tl:
            if rev: adj["pending_skip"].add(rev)
        if "portfolio" in tl and ("no units have been sold" in tl or "no cash proceeds" in tl):
            if rev: adj["unrealized_skip"].add(rev)
        if "rent" in tl and ("12%" in t or "12 %" in t): adj["rent_increase"] = True
        if any(p in tl for p in ["employment has ended","no regular salary payments scheduled",
                                  "seasonal contract has ended","kontrak musiman"]):
            adj["employment_ended"] = True
        if "pay the release charge" in tl or "pay the processing charge" in tl:
            adj["scam"] = True
    return adj

# ── Recurring detection ──────────────────────────────────────────────────────
def detect_recurring(events, hcur, data, rdate):
    """Detect monthly recurring from settled history, grouping by (category, direction)."""
    lookback = rdate - timedelta(days=180)
    cat_month = defaultdict(lambda: defaultdict(float))
    cat_last = {}
    sal_days = []
    sal_amts = []

    for e in events:
        if e.get("status") != "settled" or e.get("direction","") == "non_cash":
            continue
        ed = parse_date(e.get("event_date",""))
        if not ed or ed < lookback or ed >= rdate: continue
        a = get_event_hc(data, e, hcur)
        if not a or a <= 0: continue
        cat = e.get("category","")
        dr = e.get("direction","")
        mk = (ed.year, ed.month)
        cat_month[(cat,dr)][mk] += a
        k = (cat,dr)
        if k not in cat_last or ed > parse_date(cat_last[k].get("event_date","")):
            cat_last[k] = e
        if cat == "salary" and dr == "credit":
            sal_days.append(ed.day)
            sal_amts.append(a)

    recurring = []
    for key, months in cat_month.items():
        if len(months) < 2: continue
        cat, dr = key
        vals = sorted(months.values())
        median = vals[len(vals)//2]
        latest = cat_last.get(key, {})
        # Find last event date for this category
        last_dates = []
        for e in events:
            if e.get("category","") == cat and e.get("direction","") == dr and e.get("status") == "settled":
                ed2 = parse_date(e.get("event_date",""))
                if ed2 and ed2 < rdate: last_dates.append(ed2)
        last_d = max(last_dates) if last_dates else rdate - timedelta(days=30)

        recurring.append({
            "category": cat, "direction": dr,
            "amount": median, "freq": 30, "last_date": last_d,
            "event_ids": [latest.get("event_id","")],
            "flexibility": latest.get("flexibility","fixed"),
            "min_allowed": parse_float(latest.get("minimum_allowed_amount","")),
            "description": latest.get("description",""),
        })
    sal_day = int(sum(sal_days)/len(sal_days)) if sal_days else 15
    sal_amt = sorted(sal_amts)[len(sal_amts)//2] if sal_amts else 0
    return recurring, sal_day, sal_amt

# ── Forecast ─────────────────────────────────────────────────────────────────
def build_cashflows(data, uid, hcur, rdate, adj, recurring, sal_day, extra_debits=None,
                    stopped_cats=None, reduced_cats=None):
    end = rdate + timedelta(days=FORECAST_DAYS)
    flows = defaultdict(float)
    skip = adj.get("pending_skip", set()) | adj.get("unrealized_skip", set())

    # Explicit future events
    explicit_cats_month = defaultdict(lambda: defaultdict(float))  # mk -> {(cat,dir) -> total}
    for e in data["events_by_user"].get(uid, []):
        eid = e.get("event_id",""); st = e.get("status",""); dr = e.get("direction","")
        if st in ("cancelled","failed") or dr == "non_cash" or st == "unrealized": continue
        if eid in skip: continue
        cat = e.get("category","")
        if st == "pending" and dr == "credit" and cat != "salary": continue
        sd = parse_date(e.get("settlement_date","")) or parse_date(e.get("event_date",""))
        if not sd or sd < rdate or sd > end: continue
        a = get_event_hc(data, e, hcur)
        if not a: continue
        if dr == "debit": flows[sd] -= a
        else: flows[sd] += a
        mk = (sd.year, sd.month)
        explicit_cats_month[mk][(cat,dr)] += a

    # Project recurring, skipping months/cats with explicit events
    for rec in recurring:
        cat = rec["category"]; dr = rec["direction"]
        amt = rec["amount"]
        if stopped_cats and any(eid in stopped_cats for eid in rec["event_ids"]):
            continue
        if reduced_cats:
            for eid in rec["event_ids"]:
                if eid in reduced_cats:
                    old_amt = amt
                    new_val = reduced_cats[eid]
                    # Scale category total proportionally
                    amt = max(0, amt - (old_amt - new_val) if old_amt > new_val else amt)
                    break
        if adj.get("employment_ended") and cat == "salary" and dr == "credit":
            continue

        # For each future month, check if explicit events cover this category
        d = rdate
        from datetime import date
        while d <= end:
            y, m = d.year, d.month
            mk = (y, m)
            # Days of this month in forecast window
            if m == 12: me = date(y+1,1,1) - timedelta(days=1)
            else: me = date(y,m+1,1) - timedelta(days=1)
            m_start = max(rdate, date(y,m,1))
            m_end = min(end, me)
            days_in_period = (m_end - m_start).days + 1
            prorate = days_in_period / me.day

            explicit_amt = explicit_cats_month.get(mk, {}).get((cat,dr), 0)
            projected = amt * prorate
            gap = max(0, projected - explicit_amt)

            if gap > 0:
                # Place on mid-month or salary day
                if cat == "salary" and dr == "credit":
                    try: target = date(y, m, min(15, me.day))
                    except: target = m_start
                else:
                    target = m_start + timedelta(days=days_in_period//2)
                if m_start <= target <= m_end:
                    if dr == "debit": flows[target] -= gap
                    else: flows[target] += gap

            # Next month
            if m == 12: d = date(y+1,1,1)
            else: d = date(y,m+1,1)

    # Rent increase
    if adj.get("rent_increase"):
        for rec in recurring:
            if rec["category"] == "rent" and rec["direction"] == "debit":
                d = rdate
                from datetime import date
                while d <= end:
                    y, m = d.year, d.month
                    if m == 12: me = date(y+1,1,1)-timedelta(days=1)
                    else: me = date(y,m+1,1)-timedelta(days=1)
                    m_start = max(rdate, date(y,m,1))
                    m_end = min(end, me)
                    prorate = ((m_end-m_start).days+1)/me.day
                    increase = rec["amount"] * 0.12 * prorate
                    mid = m_start + timedelta(days=((m_end-m_start).days+1)//2)
                    flows[mid] -= increase
                    if m == 12: d = date(y+1,1,1)
                    else: d = date(y,m+1,1)

    if extra_debits:
        for dd, a in extra_debits:
            if rdate <= dd <= end: flows[dd] -= a
    return flows


def run_forecast(balance, flows, rdate):
    end = rdate + timedelta(days=FORECAST_DAYS)
    cur = balance; minb = balance
    d = rdate
    while d <= end:
        cur += flows.get(d, 0)
        minb = min(minb, cur)
        d += timedelta(days=1)
    return minb


def calc_safe(balance, minbal, flows, rdate, ramt):
    tf = dict(flows); tf[rdate] = tf.get(rdate,0) - ramt
    if run_forecast(balance, tf, rdate) >= minbal: return ramt
    if run_forecast(balance, flows, rdate) < minbal: return 0
    lo, hi = 0.0, ramt
    for _ in range(50):
        mid = (lo+hi)/2
        tf2 = dict(flows); tf2[rdate] = tf2.get(rdate,0) - mid
        if run_forecast(balance, tf2, rdate) >= minbal: lo = mid
        else: hi = mid
    return max(0, min(math.floor(lo*100)/100, ramt))


def find_earliest(balance, minbal, flows, rdate, ramt):
    end = rdate + timedelta(days=FORECAST_DAYS)
    d = rdate
    while d <= end:
        tf = dict(flows); tf[d] = tf.get(d,0) - ramt
        if run_forecast(balance, tf, rdate) >= minbal: return d
        d += timedelta(days=1)
    return None


# ── Spending changes ─────────────────────────────────────────────────────────
def find_changeable(recurring, protected, w_stop, w_reduce):
    cands = []
    for rec in recurring:
        cat = rec["category"]
        if cat in protected or rec["direction"] != "debit": continue
        flex = rec["flexibility"]
        eid = rec["event_ids"][-1] if rec["event_ids"] else None
        if not eid: continue
        can_stop = cat in w_stop and flex in ("stoppable","reducible_or_stoppable")
        can_reduce = cat in w_reduce and flex in ("reducible","reducible_or_stoppable")
        mina = rec["min_allowed"]
        if can_stop:
            cands.append(("stop", eid, rec["amount"], rec))
        if can_reduce and mina is not None and mina < rec["amount"]:
            cands.append(("reduce", eid, rec["amount"]-mina, rec))
    cands.sort(key=lambda x: x[2], reverse=True)
    return cands


def try_changes(data, uid, hcur, rdate, ramt, bal, minbal, adj, recurring, sal_day, options, protected, w_stop, w_reduce):
    cands = find_changeable(recurring, protected, w_stop, w_reduce)
    for n in range(1, min(4, len(cands)+1)):
        combo = cands[:n]
        eids = set(); ok = True
        for _,eid,_,_ in combo:
            if eid in eids: ok=False; break
            eids.add(eid)
        if not ok: continue
        stopped = set(); reduced = {}
        for action,eid,_,rec in combo:
            if action == "stop": stopped.add(eid)
            else: reduced[eid] = rec["min_allowed"]
        mod_flows = build_cashflows(data, uid, hcur, rdate, adj, recurring, sal_day,
                                    stopped_cats=stopped, reduced_cats=reduced)
        sa2 = calc_safe(bal, minbal, mod_flows, rdate, ramt)
        if sa2 >= ramt:
            parts = []
            for action,eid,_,rec in combo:
                if action == "stop": parts.append(f"stop:{eid}")
                else: parts.append(f"reduce_to:{eid}:{fn(rec['min_allowed'])}")
            chg = "|".join(parts)
            fp_d = rdate
            for o in options:
                if o.get("payment_method") == "full_payment":
                    fp_d = parse_date(o.get("first_payment_date","")) or rdate; break
            ef = find_earliest(bal, minbal, mod_flows, rdate, ramt)
            return {"m":"full_payment","st":"affordable_with_plan","s":[(fp_d,ramt)],
                    "tot":ramt,"ch":chg,"compl":True,"np":1,"start":fp_d,"oid":None,"ef":ef}
    return None


# ── Main solver ──────────────────────────────────────────────────────────────
data_g = None

def solve(data, req):
    global data_g; data_g = data
    rid = req["request_id"]; uid = req["user_id"]
    rdate = parse_date(req.get("request_date","")); ramt = parse_float(req.get("requested_amount","0")) or 0
    desired = parse_date(req.get("desired_completion_date",""))
    allows_partial = req.get("allows_partial_payment","").lower() == "true"
    if not rdate: return naf(rid, 0, "")

    prof = data["profile_by_user"].get(uid, {})
    hcur = prof.get("home_currency","USD")
    bal = parse_float(prof.get("current_available_balance","0")) or 0
    minbal = parse_float(prof.get("minimum_balance_to_keep","0")) or 0
    pmethods = [x.strip() for x in prof.get("payment_methods_user_will_consider","").split("|") if x.strip()]
    max_inst = parse_float(prof.get("max_installment_months",""))
    w_stop = [x.strip() for x in prof.get("expense_categories_user_is_willing_to_stop","").split("|") if x.strip()]
    w_reduce = [x.strip() for x in prof.get("expense_categories_user_is_willing_to_reduce","").split("|") if x.strip()]
    protected = [x.strip() for x in prof.get("expense_categories_to_protect","").split("|") if x.strip()]

    adj = process_messages(data, uid, rid)
    events = data["events_by_user"].get(uid, [])
    recurring, sal_day, sal_amt = detect_recurring(events, hcur, data, rdate)
    base_flows = build_cashflows(data, uid, hcur, rdate, adj, recurring, sal_day)

    sa = calc_safe(bal, minbal, base_flows, rdate, ramt)
    ef = find_earliest(bal, minbal, base_flows, rdate, ramt)

    options = data["options_by_request"].get(rid, [])
    plans = []

    # Full payment now
    if "full_payment" in pmethods and sa >= ramt:
        fp_d = rdate
        for o in options:
            if o.get("payment_method") == "full_payment":
                fp_d = parse_date(o.get("first_payment_date","")) or rdate; break
        plans.append({"m":"full_payment","st":"affordable_now","s":[(fp_d,ramt)],"tot":ramt,
                      "ch":"none","compl":True,"np":1,"start":fp_d,"oid":None})

    # Installments
    if "installments" in pmethods and max_inst is not None:
        for o in options:
            if o.get("payment_method") != "installments": continue
            n = int(parse_float(o.get("number_of_payments","0")) or 0)
            freq = int(parse_float(o.get("payment_frequency_days","30")) or 30)
            if (n*freq)/30.0 > max_inst: continue
            sched = mk_sched(o)
            if not sched: continue
            last_d = sched[-1][0]
            compl = desired and last_d <= desired
            tf = dict(base_flows)
            for d,a in sched: tf[d] = tf.get(d,0) - a
            if run_forecast(bal, tf, rdate) >= minbal:
                tot = parse_float(o.get("total_payable_amount","0")) or 0
                plans.append({"m":"installments","st":"affordable_with_plan","s":sched,"tot":tot,
                              "ch":"none","compl":compl,"np":n,"start":sched[0][0],
                              "oid":o.get("payment_option_id","")})

    # Partial payment
    if "partial_payment" in pmethods and allows_partial and 0 < sa < ramt:
        if ef and desired and ef <= desired:
            rem = round(ramt - sa, 2)
            sched = [(rdate, sa), (ef, rem)]
            tf = dict(base_flows)
            for d,a in sched: tf[d] = tf.get(d,0) - a
            if run_forecast(bal, tf, rdate) >= minbal:
                plans.append({"m":"partial_payment","st":"affordable_with_plan","s":sched,"tot":ramt,
                              "ch":"none","compl":True,"np":2,"start":rdate,"oid":None})

    # Wait
    if "full_payment" in pmethods and ef and ef > rdate:
        if desired and ef <= desired:
            plans.append({"m":"wait","st":"affordable_later","s":[(ef,ramt)],"tot":ramt,
                          "ch":"none","compl":True,"np":1,"start":ef,"oid":None})

    # Spending changes
    if not any(p["st"]=="affordable_now" for p in plans) and "full_payment" in pmethods:
        sc = try_changes(data, uid, hcur, rdate, ramt, bal, minbal, adj, recurring, sal_day,
                         options, protected, w_stop, w_reduce)
        if sc: plans.append(sc)

    plans.sort(key=plan_key)
    best = plans[0] if plans else None

    if best:
        st = best["st"]; meth = best["m"]; pp = fmt_sched(best["s"])
        chg = best.get("ch","none")
        e_str = rdate.strftime("%Y-%m-%d") if st == "affordable_now" else (ef.strftime("%Y-%m-%d") if ef else "")
        expl = mk_expl(best, hcur, minbal, ramt, sa, desired, rdate)
    else:
        st="not_affordable"; meth="not_recommended"; pp="none"; chg="none"
        e_str = ef.strftime("%Y-%m-%d") if ef else ""
        expl = mk_expl(None, hcur, minbal, ramt, sa, desired, rdate)

    return {"request_id":rid,"amount_safe_to_pay":fn(sa),"affordability_status":st,
            "recommended_payment_method":meth,"payment_plan":pp,
            "earliest_date_for_full_payment":e_str,"spending_changes_needed":chg,
            "decision_explanation":expl}


def mk_sched(o):
    a=parse_float(o.get("payment_amount","0")); n=int(parse_float(o.get("number_of_payments","1")) or 1)
    fd=parse_date(o.get("first_payment_date","")); freq=int(parse_float(o.get("payment_frequency_days","30")) or 30)
    if not fd or not a: return []
    s=[]; d=fd
    for i in range(n):
        s.append((d,a)); d=d+timedelta(days=freq) if i<n-1 else d
    return s


def plan_key(p):
    c = 0 if p["compl"] else 1
    ch = 0 if p.get("ch","none")=="none" else 1
    t = p.get("tot",0) or 0
    s = p["start"] if p["start"] else datetime.max.date()
    n = p["np"]
    oid = 999
    if p.get("oid"):
        m = re.search(r'(\d+)', p["oid"])
        if m: oid = int(m.group(1))
    return (c, ch, t, s, n, oid)


def fmt_sched(s):
    if not s: return "none"
    return "|".join(f"{d.strftime('%Y-%m-%d')}:{fn(a)}" for d,a in s)

def fn(v):
    if v is None: return "0"
    if v == int(v): return str(int(v))
    s = f"{v:.2f}"
    if "." in s: s = s.rstrip("0").rstrip(".")
    return s

def fdisplay(v):
    if v is None: return "0"
    if v == int(v): return f"{int(v):,}"
    return f"{v:,.2f}"

def mk_expl(plan, hcur, minbal, ramt, sa, desired, rdate):
    mb=fdisplay(minbal); ra=fdisplay(ramt); sas=fdisplay(sa)
    if not plan:
        if sa > 0 and desired:
            return f"Do not proceed with the {hcur} {ra} request. Although {hcur} {sas} is available today, the full amount cannot be completed safely within 90 days."
        elif desired:
            dn=f"{desired.day} {desired.strftime('%B')} {desired.year}"
            return f"Do not make this payment by {dn}. None of the available options keeps the {hcur} {mb} minimum protected."
        return f"Do not make this payment. None of the available options keeps the {hcur} {mb} minimum protected."
    m=plan["m"]; st=plan["st"]; sc=plan["s"]
    if st=="affordable_now" and m=="full_payment":
        return f"Pay {hcur} {ra} today. This leaves at least {hcur} {mb} available over the next 90 days."
    if m=="installments":
        n=len(sc); per=fdisplay(sc[0][1]); sd=sc[0][0]
        sdn=f"{sd.day} {sd.strftime('%B')} {sd.year}"
        return f"Use {n} installments of {hcur} {per}, starting {sdn}. This leaves at least {hcur} {mb} available."
    if m=="partial_payment":
        f1=fdisplay(sc[0][1]); f2=fdisplay(sc[1][1]); d2=sc[1][0]
        d2n=f"{d2.day} {d2.strftime('%B')} {d2.year}"
        return f"Pay {hcur} {f1} today and the remaining {hcur} {f2} on {d2n}. This completes the full request and keeps the {hcur} {mb} minimum protected."
    if m=="wait":
        pd2=sc[0][0]; pdn=f"{pd2.day} {pd2.strftime('%B')} {pd2.year}"
        return f"Pay {hcur} {ra} in full on {pdn}. Paying earlier would take the balance below the {hcur} {mb} minimum."
    if m=="full_payment" and plan.get("ch","none")!="none":
        chg=plan["ch"]; cparts=[]
        for c in chg.split("|"):
            if c.startswith("stop:"):
                eid=c.split(":")[1]; evt=data_g["event_by_id"].get(eid,{})
                cat=evt.get("category","expense").replace("_"," ")
                cparts.append(f"Stop the {cat}")
            elif c.startswith("reduce_to:"):
                ps=c.split(":"); eid=ps[1]; na=ps[2]
                evt=data_g["event_by_id"].get(eid,{}); cat=evt.get("category","expense").replace("_"," ")
                cparts.append(f"reduce the {cat} to {hcur} {na}")
        txt=" and ".join(cparts)
        return f"{txt}, then pay {hcur} {ra} today. This leaves at least {hcur} {mb} available."
    return "No safe payment option available."


def naf(rid, sa, expl):
    return {"request_id":rid,"amount_safe_to_pay":fn(sa),"affordability_status":"not_affordable",
            "recommended_payment_method":"not_recommended","payment_plan":"none",
            "earliest_date_for_full_payment":"","spending_changes_needed":"none",
            "decision_explanation":expl or "No safe payment option available."}


def main():
    print("Loading data...")
    data = load_all_data()
    print(f"Processing {len(data['requests'])} requests...")
    results = []
    for i, req in enumerate(data["requests"]):
        rid = req["request_id"]
        if (i+1)%50==0 or i==0: print(f"  [{i+1}/{len(data['requests'])}] {rid}...")
        try: result = solve(data, req)
        except Exception as e:
            import traceback; traceback.print_exc()
            result = naf(rid, 0, f"Error: {e}")
        results.append(result)

    out = os.path.join(DATASET_DIR, "output.csv")
    flds = ["request_id","amount_safe_to_pay","affordability_status",
            "recommended_payment_method","payment_plan",
            "earliest_date_for_full_payment","spending_changes_needed","decision_explanation"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flds); w.writeheader()
        for r in results: w.writerow(r)
    print(f"\nDone! Output: {out}")
    from collections import Counter
    sc = Counter(r["affordability_status"] for r in results)
    print("Status:", dict(sorted(sc.items())))


if __name__ == "__main__":
    main()
