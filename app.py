import streamlit as st
import pandas as pd
import json
import re
from io import StringIO

# ── Configuration ───────────────────────────────────────────────────────────────
METRICS = [
    "Annual revenues for vendor",
    "Year-on-year revenue growth",
    "Net-new logo revenues",
    "Percentage of vendor revenues from SaaS",
    "Average deal size",
    "Average time to close",
    "Renewal rate",
    "Net revenue expansion",
    "Registered deals",
    "Win/loss ratio for registered deals",
    "Partner Generated Opportunities as a % of Pipeline",
    "Frequency of business",
    "MDF utilization rate",
    "Quality of sales organization",
    "Customer satisfaction",
    "Vendor certification(s)",
    "Sales support calls received",
    "Tech support calls received",
    "Communication with vendor",
    "Total revenues (if available)",
    "Dedication vs. competitive products",
    "Dedication vs. other vendors",
    "Geographical market coverage",
    "Vertical market coverage",
    "Quality of management",
    "Known litigation (No=5, Yes = 1)",
    "Export control and protection of intellectual property",
    "Financial strength"
]

MAX_SCORE = 5 * len(METRICS)  # 140

# ── Helpers ─────────────────────────────────────────────────────────────────────
def get_score(perf, crit_dict):
    if not crit_dict:
        return 0
    perf_str = str(perf).strip().lower().replace("$", "").replace(",", "").replace("%", "")
    try:
        perf_num = float(perf_str)
    except ValueError:
        perf_num = None

    for s in range(5, 0, -1):
        crit = crit_dict.get(f"Score {s}", "").strip().lower().replace("$", "").replace(",", "").replace("%", "")
        if not crit: continue
        if '>' in crit:
            try:
                thresh = float(re.search(r'\d+\.?\d*', crit).group())
                if perf_num is not None and perf_num > thresh: return s
            except: pass
        elif '<' in crit:
            try:
                thresh = float(re.search(r'\d+\.?\d*', crit).group())
                if perf_num is not None and perf_num < thresh: return s
            except: pass
        elif '-' in crit:
            try:
                low, high = map(float, re.findall(r'\d+\.?\d*', crit))
                if perf_num is not None and low <= perf_num <= high: return s
            except: pass
        else:
            if perf_str in crit or crit in perf_str: return s
    return 0

def color_score(val):
    try:
        v = int(val)
        if v >= 4: return "background-color: #d4edda; color: #155724;"
        if v == 3: return "background-color: #fff3cd; color: #856404;"
        if v <= 2: return "background-color: #f8d7da; color: #721c24;"
    except: pass
    return ""

# ── Session State Init ──────────────────────────────────────────────────────────
if 'criteria' not in st.session_state:
    st.session_state.criteria = {m: {f"Score {s}": "" for s in range(1,6)} for m in METRICS}
if 'partners' not in st.session_state:
    st.session_state.partners = pd.DataFrame(columns=["Partner Name"] + METRICS + ["Total Score", "Percentage"])

# ── App ─────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Partner Scorecard", layout="wide")
st.title("Partner Scorecard App")

# Hardcoded login – CHANGE THESE FOR EACH CLIENT INSTANCE!
VALID_USERNAME = "clientuser"   # ← Customize per client
VALID_PASSWORD = "securepass2026"  # ← Customize per client

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

st.success("Logged in!")

tab1, tab2, tab3 = st.tabs(["1. Define Scoring Rules", "2. Score a Partner", "3. View All My Partners"])

# Tab 1: Define Criteria
with tab1:
    st.header("Define Scoring Criteria (1–5) – Used for All Your Partners")
    with st.form("criteria_form"):
        for metric in METRICS:
            st.subheader(metric)
            cols = st.columns(5)
            for i, s in enumerate(range(1,6)):
                with cols[i]:
                    key = f"crit_{metric}_{s}"
                    st.session_state.criteria[metric][f"Score {s}"] = st.text_input(
                        f"Score {s}", value=st.session_state.criteria[metric][f"Score {s}"], key=key
                    )
        if st.form_submit_button("Save Criteria"):
            st.success("Criteria saved!")

    # Backup / Restore Criteria
    st.subheader("Backup / Restore Criteria")
    crit_json = json.dumps(st.session_state.criteria, indent=2)
    st.download_button("Download Criteria JSON", crit_json, "criteria_backup.json", "application/json")

    uploaded_crit = st.file_uploader("Upload Criteria JSON to Restore", type="json")
    if uploaded_crit:
        try:
            st.session_state.criteria = json.load(uploaded_crit)
            st.success("Criteria restored!")
        except:
            st.error("Invalid JSON file.")

# Tab 2: Score Partner
with tab2:
    st.header("Add / Score a Partner")
    if not any(any(v) for v in st.session_state.criteria.values()):
        st.warning("Define and save criteria first in Tab 1.")
    else:
        partner_name = st.text_input("Partner Name").strip()
        if partner_name:
            with st.form("partner_form"):
                performances = {}
                for metric in METRICS:
                    performances[metric] = st.text_input(metric, key=f"perf_{metric}_{partner_name}")
                if st.form_submit_button("Submit & Score"):
                    scores = {m: get_score(performances[m], st.session_state.criteria[m]) for m in METRICS}
                    total = sum(scores.values())
                    perc = round(total / MAX_SCORE * 100, 1)

                    new_row = {"Partner Name": partner_name, **scores, "Total Score": total, "Percentage": perc}
                    st.session_state.partners = pd.concat([st.session_state.partners, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"Partner '{partner_name}' scored and added!")
                    st.balloons()

# Tab 3: Overview
with tab3:
    st.header("All Your Partners – Color-Coded Scores")
    if st.session_state.partners.empty:
        st.info("No partners added yet.")
    else:
        styled = st.session_state.partners.style.applymap(color_score, subset=METRICS + ["Total Score"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # CSV Export
        csv_buffer = StringIO()
        st.session_state.partners.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download All Partners CSV",
            csv_buffer.getvalue(),
            "my_partners_scorecard.csv",
            "text/csv"
        )

        # CSV Restore
        uploaded_csv = st.file_uploader("Upload CSV to Restore / Merge Partners", type="csv")
        if uploaded_csv:
            try:
                uploaded_df = pd.read_csv(uploaded_csv)
                st.session_state.partners = pd.concat([st.session_state.partners, uploaded_df]).drop_duplicates(subset=["Partner Name"], keep="last")
                st.success("Partners restored/merged!")
            except:
                st.error("Invalid CSV file.")
