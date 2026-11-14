"""Services & Rate Management — Bharathi Oil Mill"""

import streamlit as st
import psycopg2.extras
import pandas as pd
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db

st.set_page_config(page_title="Services – Bharathi Oil Mill", layout="wide")
st.markdown("## ⚙️ Services & Rate Management")
st.markdown("---")

CAT_LABELS = {
    "grain_milling": "🌾 Grain Milling",
    "spice_grinding": "🌶 Spice Grinding",
    "dhal_splitting": "🫘 Dhal Splitting",
    "oil_extraction": "🫒 Oil Extraction",
    "oil_cake_grinding": "🟤 Oil Cake Grinding",
    "wet_grinding": "💧 Wet Grinding",
}

with get_db() as conn:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM services ORDER BY category, name")
    services = cur.fetchall()

tab_view, tab_add, tab_edit = st.tabs(["📋 All Services", "➕ Add Service", "✏️ Edit Rates"])

with tab_view:
    if services:
        df = pd.DataFrame(services)
        df["category_label"] = df["category"].map(CAT_LABELS).fillna(df["category"])
        df["status"] = df["is_active"].map({True: "✅ Active", False: "❌ Inactive"})
        for cat, group in df.groupby("category"):
            st.markdown(f"#### {CAT_LABELS.get(cat, cat)}")
            disp = group[["name", "rate_per_kg", "unit", "status"]].copy()
            disp.columns = ["Service Name", "Rate per kg (₹)", "Unit", "Status"]
            disp["Rate per kg (₹)"] = disp["Rate per kg (₹)"].apply(lambda x: f"₹{x:.2f}")
            st.dataframe(disp, use_container_width=True, hide_index=True)

with tab_add:
    with st.form("add_svc"):
        st.markdown("#### ➕ Add New Service")
        col1, col2 = st.columns(2)
        with col1:
            s_name = st.text_input("Service Name *")
            s_cat = st.selectbox("Category", list(CAT_LABELS.keys()),
                                 format_func=lambda x: CAT_LABELS.get(x, x))
        with col2:
            s_rate = st.number_input("Rate per kg (₹) *", min_value=0.0, value=5.0)
            s_unit = st.selectbox("Unit", ["kg", "litre", "pcs"])
        if st.form_submit_button("💾 Add Service", type="primary"):
            if s_name:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO services (category, name, rate_per_kg, unit) VALUES (%s,%s,%s,%s)",
                        (s_cat, s_name, s_rate, s_unit)
                    )
                st.success(f"✅ Service '{s_name}' added!")
                st.rerun()

with tab_edit:
    sel_svc = st.selectbox("Select Service to Edit", services,
                           format_func=lambda x: f"{CAT_LABELS.get(x['category'],x['category'])} → {x['name']}")
    if sel_svc:
        with st.form("edit_svc"):
            col1, col2 = st.columns(2)
            with col1:
                new_rate = st.number_input("New Rate (₹/kg)", value=float(sel_svc["rate_per_kg"]))
            with col2:
                new_active = st.checkbox("Active", value=bool(sel_svc["is_active"]))
            if st.form_submit_button("💾 Update", type="primary"):
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE services SET rate_per_kg=%s, is_active=%s, updated_at=NOW() WHERE id=%s",
                        (new_rate, new_active, sel_svc["id"])
                    )
                st.success("✅ Updated!")
                st.cache_data.clear()
                st.rerun()
