"""
Buy or Wait? — AI-Powered Financial Decision Agent
Interactive Streamlit Web App
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import sys
from datetime import timedelta
from collections import defaultdict

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "code"))
from main import (load_all_data, solve, parse_date, parse_float, get_event_hc,
                  detect_recurring, process_messages, build_cashflows, run_forecast)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Buy or Wait? — Financial Decision Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F8BF9, #9B59B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .status-affordable_now { color: #2ECC71; font-weight: 700; }
    .status-affordable_with_plan { color: #F39C12; font-weight: 700; }
    .status-affordable_later { color: #3498DB; font-weight: 700; }
    .status-not_affordable { color: #E74C3C; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ── Load Data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return load_all_data()

@st.cache_data
def get_all_results(_data):
    """Process all requests and return results."""
    results = []
    for req in _data["requests"]:
        try:
            result = solve(_data, req)
        except Exception as e:
            result = {"request_id": req["request_id"], "affordability_status": "error",
                      "recommended_payment_method": "error", "amount_safe_to_pay": "0",
                      "payment_plan": "none", "earliest_date_for_full_payment": "",
                      "spending_changes_needed": "none", "decision_explanation": str(e)}
        results.append(result)
    return results

data = load_data()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">💰 Buy or Wait?</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Financial Decision Agent — Analyzes your finances and recommends the safest way to pay</p>', unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Controls")

    # Build request options
    requests_list = data["requests"]
    request_options = {}
    for r in requests_list:
        rid = r["request_id"]
        uid = r["user_id"]
        amt = r.get("requested_amount", "?")
        rtype = r.get("request_type", "?")
        prof = data["profile_by_user"].get(uid, {})
        cur = prof.get("home_currency", "")
        request_options[f"{rid} — {rtype} ({cur} {amt})"] = rid

    selected_label = st.selectbox("📋 Select a Request", list(request_options.keys()))
    selected_rid = request_options[selected_label]

    st.markdown("---")
    st.markdown("### 📊 Dataset Stats")
    st.metric("Total Requests", len(requests_list))
    st.metric("Unique Users", len(data["profile_by_user"]))
    st.metric("Financial Events", len(data["events"]))
    st.metric("Messages", len(data["messages"]))

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    This agent evaluates financial requests using:
    - 📈 90-day cash flow forecasting
    - 🔄 Recurring expense detection
    - 🔍 Binary search safe amount calculation
    - 💳 Multi-method payment evaluation
    """)

# ── Get selected request data ────────────────────────────────────────────────
req = next(r for r in requests_list if r["request_id"] == selected_rid)
uid = req["user_id"]
prof = data["profile_by_user"].get(uid, {})
rdate = parse_date(req.get("request_date", ""))
ramt = parse_float(req.get("requested_amount", "0")) or 0
hcur = prof.get("home_currency", "USD")
balance = parse_float(prof.get("current_available_balance", "0")) or 0
minbal = parse_float(prof.get("minimum_balance_to_keep", "0")) or 0

# Run solver for this request
result = solve(data, req)

# ── Main Content Tabs ────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Decision", "👤 Profile", "📈 Forecast", "📊 Overview"])

# ── Tab 1: Decision ──────────────────────────────────────────────────────────
with tab1:
    st.markdown(f"### Request: `{selected_rid}`")

    # Request details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Type:** `{req.get('request_type', 'N/A')}`")
        st.markdown(f"**Date:** `{req.get('request_date', 'N/A')}`")
    with col2:
        st.markdown(f"**Amount:** `{hcur} {ramt:,.2f}`")
        st.markdown(f"**Deadline:** `{req.get('desired_completion_date', 'N/A')}`")
    with col3:
        st.markdown(f"**Partial OK:** `{req.get('allows_partial_payment', 'N/A')}`")
        st.markdown(f"**User:** `{uid}`")

    st.markdown("---")

    # Request text
    if req.get("request_text"):
        st.info(f"💬 *\"{req['request_text']}\"*")

    st.markdown("---")

    # Result metrics
    status = result["affordability_status"]
    method = result["recommended_payment_method"]

    status_colors = {
        "affordable_now": "🟢", "affordable_with_plan": "🟡",
        "affordable_later": "🔵", "not_affordable": "🔴"
    }
    method_icons = {
        "full_payment": "💳", "installments": "📅", "partial_payment": "✂️",
        "wait": "⏳", "not_recommended": "🚫"
    }

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Safe to Pay", f"{hcur} {result['amount_safe_to_pay']}")
    c2.metric("📊 Status", f"{status_colors.get(status, '⚪')} {status.replace('_', ' ').title()}")
    c3.metric("💳 Method", f"{method_icons.get(method, '❓')} {method.replace('_', ' ').title()}")
    c4.metric("📅 Earliest Full", result.get("earliest_date_for_full_payment", "N/A") or "—")

    st.markdown("---")

    # Payment plan
    col_plan, col_changes = st.columns(2)
    with col_plan:
        st.markdown("#### 📋 Payment Plan")
        plan_str = result.get("payment_plan", "none")
        if plan_str and plan_str != "none":
            plan_data = []
            for entry in plan_str.split("|"):
                parts = entry.split(":")
                if len(parts) == 2:
                    plan_data.append({"Date": parts[0], "Amount": f"{hcur} {parts[1]}"})
            if plan_data:
                st.dataframe(pd.DataFrame(plan_data), use_container_width=True, hide_index=True)
        else:
            st.markdown("*No payment plan recommended*")

    with col_changes:
        st.markdown("#### 🔧 Spending Changes")
        changes = result.get("spending_changes_needed", "none")
        if changes and changes != "none":
            for c in changes.split("|"):
                if c.startswith("stop:"):
                    eid = c.split(":")[1]
                    evt = data["event_by_id"].get(eid, {})
                    st.markdown(f"🛑 **Stop** `{evt.get('category', eid)}` — {evt.get('description', '')}")
                elif c.startswith("reduce_to:"):
                    ps = c.split(":")
                    eid, amt = ps[1], ps[2]
                    evt = data["event_by_id"].get(eid, {})
                    st.markdown(f"📉 **Reduce** `{evt.get('category', eid)}` to {hcur} {amt}")
        else:
            st.markdown("✅ *No spending changes needed*")

    st.markdown("---")
    # Explanation
    st.markdown("#### 💡 Explanation")
    st.success(result.get("decision_explanation", "N/A"))


# ── Tab 2: Profile ───────────────────────────────────────────────────────────
with tab2:
    st.markdown(f"### 👤 Financial Profile — `{uid}`")

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Balance", f"{hcur} {balance:,.2f}")
    c2.metric("🛡️ Minimum Balance", f"{hcur} {minbal:,.2f}")
    c3.metric("💵 Available Above Min", f"{hcur} {max(0, balance - minbal):,.2f}")

    st.markdown("---")

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### 🎯 Priorities")
        prios = prof.get("financial_priorities", "")
        if prios:
            for i, p in enumerate(prios.split("|"), 1):
                st.markdown(f"{i}. `{p.strip()}`")

        st.markdown("#### 🛡️ Protected Categories")
        protected = prof.get("expense_categories_to_protect", "")
        if protected:
            for p in protected.split("|"):
                st.markdown(f"- 🔒 `{p.strip()}`")

    with col_right:
        st.markdown("#### 💳 Payment Methods")
        methods = prof.get("payment_methods_user_will_consider", "")
        if methods:
            for m in methods.split("|"):
                st.markdown(f"- ✅ `{m.strip()}`")
        max_inst = prof.get("max_installment_months", "")
        if max_inst:
            st.markdown(f"- 📅 Max installment months: **{max_inst}**")

        st.markdown("#### ✂️ Willing to Adjust")
        w_reduce = prof.get("expense_categories_user_is_willing_to_reduce", "")
        w_stop = prof.get("expense_categories_user_is_willing_to_stop", "")
        if w_reduce:
            for w in w_reduce.split("|"):
                if w.strip(): st.markdown(f"- 📉 Reduce: `{w.strip()}`")
        if w_stop:
            for w in w_stop.split("|"):
                if w.strip(): st.markdown(f"- 🛑 Stop: `{w.strip()}`")

    # Recent events table
    st.markdown("---")
    st.markdown("#### 📜 Recent Financial Events")
    user_events = data["events_by_user"].get(uid, [])
    if user_events and rdate:
        recent = [e for e in user_events
                  if parse_date(e.get("event_date", "")) and
                  abs((parse_date(e["event_date"]) - rdate).days) <= 60]
        recent.sort(key=lambda x: x.get("event_date", ""), reverse=True)
        if recent:
            df_events = pd.DataFrame([{
                "Date": e.get("event_date", ""),
                "Category": e.get("category", ""),
                "Direction": "⬆️ Credit" if e.get("direction") == "credit" else ("⬇️ Debit" if e.get("direction") == "debit" else e.get("direction", "")),
                "Amount": f"{e.get('currency', hcur)} {e.get('amount', 'N/A')}",
                "Status": e.get("status", ""),
                "Description": e.get("description", "")[:40],
            } for e in recent[:20]])
            st.dataframe(df_events, use_container_width=True, hide_index=True)


# ── Tab 3: Forecast ──────────────────────────────────────────────────────────
with tab3:
    st.markdown(f"### 📈 90-Day Balance Forecast — `{uid}`")

    if rdate:
        events = data["events_by_user"].get(uid, [])
        adj = process_messages(data, uid, selected_rid)
        recurring, sal_day, sal_amt = detect_recurring(events, hcur, data, rdate)
        base_flows = build_cashflows(data, uid, hcur, rdate, adj, recurring, sal_day)

        # Build daily balance series
        end_date = rdate + timedelta(days=90)
        dates = []
        balances_no_pay = []
        balances_with_pay = []
        cur_no = balance
        cur_with = balance - min(ramt, balance)  # after payment

        flows_with_pay = dict(base_flows)
        flows_with_pay[rdate] = flows_with_pay.get(rdate, 0) - ramt

        d = rdate
        while d <= end_date:
            dates.append(d)
            cur_no += base_flows.get(d, 0)
            cur_with += flows_with_pay.get(d, 0)
            balances_no_pay.append(cur_no)
            balances_with_pay.append(cur_with)
            d += timedelta(days=1)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=balances_no_pay, mode='lines',
                                  name='Without Payment', line=dict(color='#4F8BF9', width=2)))
        fig.add_trace(go.Scatter(x=dates, y=balances_with_pay, mode='lines',
                                  name=f'After Paying {hcur} {ramt:,.0f}',
                                  line=dict(color='#E74C3C', width=2, dash='dash')))
        fig.add_hline(y=minbal, line_dash="dot", line_color="#F39C12",
                      annotation_text=f"Minimum Balance ({hcur} {minbal:,.0f})")
        fig.update_layout(
            title="Projected Balance Over 90 Days",
            xaxis_title="Date", yaxis_title=f"Balance ({hcur})",
            template="plotly_dark", height=450,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Recurring expenses breakdown
        st.markdown("---")
        st.markdown("#### 🔄 Detected Monthly Recurring Patterns")
        if recurring:
            rec_data = []
            for r in recurring:
                rec_data.append({
                    "Category": r["category"],
                    "Direction": "Income" if r["direction"] == "credit" else "Expense",
                    "Monthly Amount": f"{hcur} {r['amount']:,.2f}",
                    "Flexibility": r.get("flexibility", "fixed"),
                })
            rec_data.sort(key=lambda x: x["Direction"])
            st.dataframe(pd.DataFrame(rec_data), use_container_width=True, hide_index=True)

            # Pie chart of expenses
            expenses = [r for r in recurring if r["direction"] == "debit"]
            if expenses:
                fig_pie = px.pie(
                    values=[r["amount"] for r in expenses],
                    names=[r["category"] for r in expenses],
                    title="Monthly Expense Breakdown",
                    template="plotly_dark"
                )
                fig_pie.update_layout(height=350)
                st.plotly_chart(fig_pie, use_container_width=True)


# ── Tab 4: Overview ──────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📊 Full Dataset Overview")

    with st.spinner("Processing all 250 requests..."):
        all_results = get_all_results(data)

    df_results = pd.DataFrame(all_results)

    # Status distribution
    c1, c2 = st.columns(2)
    with c1:
        status_counts = df_results["affordability_status"].value_counts()
        colors = {"affordable_now": "#2ECC71", "affordable_with_plan": "#F39C12",
                  "affordable_later": "#3498DB", "not_affordable": "#E74C3C"}
        fig_status = px.pie(values=status_counts.values, names=status_counts.index,
                           title="Affordability Status Distribution",
                           color=status_counts.index,
                           color_discrete_map=colors, template="plotly_dark")
        fig_status.update_layout(height=350)
        st.plotly_chart(fig_status, use_container_width=True)

    with c2:
        method_counts = df_results["recommended_payment_method"].value_counts()
        fig_method = px.bar(x=method_counts.index, y=method_counts.values,
                           title="Recommended Payment Methods",
                           labels={"x": "Method", "y": "Count"},
                           template="plotly_dark", color=method_counts.index)
        fig_method.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_method, use_container_width=True)

    # Results table
    st.markdown("---")
    st.markdown("#### 📋 All Results")
    st.dataframe(df_results[["request_id", "amount_safe_to_pay", "affordability_status",
                              "recommended_payment_method", "earliest_date_for_full_payment",
                              "spending_changes_needed"]],
                 use_container_width=True, hide_index=True, height=400)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#666; padding:10px'>"
    "Built with ❤️ by Nishita Singh | "
    "<a href='https://github.com/nishita339/buy-or-wait-financial-agent' target='_blank'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True
)
