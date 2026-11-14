"""Machine & Maintenance Management — Bharathi Oil Mill"""

import streamlit as st
import psycopg2.extras
from datetime import date, timedelta
import pandas as pd
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db

st.set_page_config(page_title="Machines – Bharathi Oil Mill", layout="wide")
st.markdown("## ⚙️ Machine & Maintenance Management")
st.markdown("---")

STATUS_COLORS = {
    "active": "#27ae60",
    "maintenance": "#e67e22",
    "breakdown": "#e74c3c",
    "inactive": "#95a5a6",
}
STATUS_ICONS = {
    "active": "✅", "maintenance": "🔧", "breakdown": "🔴", "inactive": "⚫"
}
TYPE_ICONS = {
    "grain_milling": "🌾", "spice_grinding": "🌶", "dhal_splitting": "🫘",
    "oil_extraction": "🫒", "oil_cake_grinding": "🟤", "wet_grinding": "💧",
}

tab_fleet, tab_add, tab_maint, tab_history = st.tabs(
    ["🏭 Machine Fleet", "➕ Add Machine", "🔧 Log Maintenance", "📋 Maintenance History"])


# ─── TAB 1: FLEET VIEW ────────────────────────────────────────────────────────
with tab_fleet:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT m.*,
                   COALESCE(SUM(mm.cost), 0) as total_maint_cost,
                   MAX(mm.maintenance_date) as last_maint
            FROM machines m
            LEFT JOIN machine_maintenance mm ON mm.machine_id = m.id
            GROUP BY m.id ORDER BY m.machine_type, m.machine_name
        """)
        machines = cur.fetchall()

    # Summary
    total = len(machines)
    active = sum(1 for m in machines if m["status"] == "active")
    in_maint = sum(1 for m in machines if m["status"] == "maintenance")
    broken = sum(1 for m in machines if m["status"] == "breakdown")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Machines", total)
    c2.metric("✅ Active", active)
    c3.metric("🔧 In Maintenance", in_maint)
    c4.metric("🔴 Breakdown", broken)

    st.markdown("---")

    # Group by type
    machine_by_type = {}
    for m in machines:
        machine_by_type.setdefault(m["machine_type"], []).append(m)

    for mtype, mlist in machine_by_type.items():
        icon = TYPE_ICONS.get(mtype, "⚙️")
        st.markdown(f"#### {icon} {mtype.replace('_', ' ').title()}")
        for m in mlist:
            status_col = STATUS_COLORS.get(m["status"], "#888")
            status_icon = STATUS_ICONS.get(m["status"], "⚙️")
            days_to_service = None
            overdue = False
            if m["next_service_date"]:
                days_to_service = (m["next_service_date"] - date.today()).days
                overdue = days_to_service < 0

            with st.container():
                col_name, col_status, col_maint, col_action = st.columns([3, 1.5, 2, 1.5])
                col_name.markdown(f"**{m['machine_name']}**  \n"
                                  f"<small>S/N: {m.get('serial_number') or '—'}</small>",
                                  unsafe_allow_html=True)
                col_status.markdown(
                    f'<span style="color:{status_col};font-weight:600">{status_icon} {m["status"].upper()}</span>',
                    unsafe_allow_html=True)
                if days_to_service is not None:
                    svc_text = f"⚠️ **OVERDUE {abs(days_to_service)}d**" if overdue else f"Service in {days_to_service}d"
                    col_maint.markdown(svc_text)
                else:
                    col_maint.write("—")
                new_status = col_action.selectbox("", list(STATUS_COLORS.keys()),
                                                  index=list(STATUS_COLORS.keys()).index(m["status"]),
                                                  key=f"sts_{m['id']}")
                if new_status != m["status"]:
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("UPDATE machines SET status=%s WHERE id=%s",
                                    (new_status, m["id"]))
                    st.rerun()


# ─── TAB 2: ADD MACHINE ───────────────────────────────────────────────────────
with tab_add:
    with st.form("add_machine"):
        st.markdown("#### ➕ Add New Machine")
        col1, col2 = st.columns(2)
        with col1:
            m_name = st.text_input("Machine Name *", placeholder="Oil Rotary #7 - Groundnut")
            m_type = st.selectbox("Machine Type", list(TYPE_ICONS.keys()),
                                  format_func=lambda x: TYPE_ICONS.get(x, "⚙️") + " " + x.replace("_", " ").title())
            m_serial = st.text_input("Serial Number")
        with col2:
            m_purchase = st.date_input("Purchase Date", value=None)
            m_next_svc = st.date_input("Next Service Date", value=None)
            m_status = st.selectbox("Status", list(STATUS_COLORS.keys()))
        m_notes = st.text_area("Notes", height=60)
        if st.form_submit_button("💾 Add Machine", type="primary"):
            if m_name:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO machines (machine_name, machine_type, serial_number,
                            purchase_date, next_service_date, status, notes)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (m_name, m_type, m_serial or None,
                          m_purchase, m_next_svc, m_status, m_notes))
                st.success(f"✅ Machine '{m_name}' added!")
                st.rerun()
            else:
                st.error("Machine name is required.")


# ─── TAB 3: LOG MAINTENANCE ───────────────────────────────────────────────────
with tab_maint:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM machines ORDER BY machine_name")
        all_machines = cur.fetchall()

    with st.form("log_maint"):
        st.markdown("#### 🔧 Log Maintenance Entry")
        sel_machine = st.selectbox("Machine", all_machines,
                                   format_func=lambda x: f"{TYPE_ICONS.get(x['machine_type'],'⚙️')} {x['machine_name']}")
        col1, col2 = st.columns(2)
        with col1:
            maint_date = st.date_input("Maintenance Date", value=date.today())
            maint_type = st.selectbox("Type", ["Routine Service", "Repair", "Part Replacement",
                                               "Lubrication", "Cleaning", "Emergency", "Other"])
            cost = st.number_input("Cost (₹)", min_value=0.0, value=0.0)
        with col2:
            technician = st.text_input("Technician / Vendor")
            next_svc = st.date_input("Next Service Date", value=date.today() + timedelta(days=90))
            new_status = st.selectbox("Machine Status After", list(STATUS_COLORS.keys()))
        description = st.text_area("Description / Work Done *", height=80)

        if st.form_submit_button("💾 Log Maintenance", type="primary"):
            if description:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO machine_maintenance
                            (machine_id, maintenance_date, maintenance_type, description,
                             cost, technician, next_service_date)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (sel_machine["id"], maint_date, maint_type, description,
                          cost, technician or None, next_svc))
                    cur.execute("""
                        UPDATE machines SET status=%s, last_service_date=%s,
                            next_service_date=%s WHERE id=%s
                    """, (new_status, maint_date, next_svc, sel_machine["id"]))
                st.success(f"✅ Maintenance logged for {sel_machine['machine_name']}")
                st.rerun()
            else:
                st.error("Description is required.")


# ─── TAB 4: MAINTENANCE HISTORY ───────────────────────────────────────────────
with tab_history:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT mm.*, m.machine_name, m.machine_type
            FROM machine_maintenance mm
            JOIN machines m ON m.id = mm.machine_id
            ORDER BY mm.maintenance_date DESC, mm.created_at DESC
            LIMIT 200
        """)
        maint_history = cur.fetchall()

    # Total costs
    if maint_history:
        total_cost = sum(r["cost"] for r in maint_history)
        st.metric("Total Maintenance Cost (All Time)", f"₹{total_cost:,.2f}")

        df_hist = pd.DataFrame(maint_history)
        df_hist["maintenance_date"] = pd.to_datetime(df_hist["maintenance_date"]).dt.strftime("%d-%m-%Y")
        df_hist["next_service_date"] = pd.to_datetime(df_hist["next_service_date"]).dt.strftime("%d-%m-%Y").fillna("—")
        st.dataframe(
            df_hist[["maintenance_date", "machine_name", "maintenance_type",
                     "description", "cost", "technician", "next_service_date"]].rename(
                columns={"maintenance_date": "Date", "machine_name": "Machine",
                         "maintenance_type": "Type", "description": "Work Done",
                         "cost": "Cost (₹)", "technician": "Technician",
                         "next_service_date": "Next Service"}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No maintenance records yet.")
