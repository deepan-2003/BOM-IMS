"""Labour Management — Bharathi Oil Mill"""

import streamlit as st
import psycopg2.extras
from datetime import date, timedelta
import pandas as pd
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db

st.set_page_config(page_title="Labour – Bharathi Oil Mill", layout="wide")
st.markdown("## 👷 Labour Management")
st.markdown("---")

tab_attend, tab_roster, tab_report = st.tabs(
    ["📅 Attendance & Wages", "👥 Worker Roster", "📊 Reports"])


# ─── TAB 1: ATTENDANCE ───────────────────────────────────────────────────────
with tab_attend:
    st.markdown("### 📅 Mark Attendance")
    
    work_date = st.date_input("Work Date", value=date.today())
    
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM labourers WHERE is_active=TRUE ORDER BY name")
        labourers = cur.fetchall()

    if not labourers:
        st.warning("No labourers registered. Add workers in the Roster tab.")
    else:
        # Check for existing attendance on selected date
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT la.*, l.name, l.daily_wage
                FROM labour_attendance la
                JOIN labourers l ON l.id = la.labourer_id
                WHERE la.work_date = %s
            """, (work_date,))
            existing_attend = {r["labourer_id"]: r for r in cur.fetchall()}

        st.markdown(f"**Workers for {work_date.strftime('%d %B %Y')}:**")
        
        attendance_data = []
        for lab in labourers:
            exist = existing_attend.get(lab["id"], {})
            with st.expander(f"👷 {lab['name']}  {'✅' if exist.get('present') else '—'}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    present = st.checkbox("Present", value=bool(exist.get("present", True)),
                                         key=f"p_{lab['id']}_{work_date}")
                    days = st.number_input("Days worked", min_value=0.0, max_value=1.0,
                                          value=float(exist.get("days_worked", 1.0)),
                                          step=0.5, key=f"d_{lab['id']}_{work_date}")
                with col2:
                    default_wage = float(lab["daily_wage"]) * days
                    wage = st.number_input("Wage Paid (₹)", min_value=0.0,
                                          value=float(exist.get("wage_paid", default_wage)),
                                          key=f"w_{lab['id']}_{work_date}")
                    advance = st.number_input("Advance (₹)", min_value=0.0,
                                             value=float(exist.get("advance", 0.0)),
                                             key=f"a_{lab['id']}_{work_date}")
                with col3:
                    pay_m = st.radio("Payment", ["cash", "upi"],
                                    index=0 if exist.get("payment_method", "cash") == "cash" else 1,
                                    key=f"pm_{lab['id']}_{work_date}")
                    notes = st.text_input("Notes", value=exist.get("notes", "") or "",
                                         key=f"n_{lab['id']}_{work_date}")
                attendance_data.append({
                    "labourer_id": lab["id"],
                    "present": present,
                    "days_worked": days,
                    "wage_paid": wage,
                    "advance": advance,
                    "payment_method": pay_m,
                    "notes": notes,
                    "existing_id": exist.get("id"),
                })

        if st.button("💾 Save Attendance", type="primary"):
            with get_db() as conn:
                cur = conn.cursor()
                for rec in attendance_data:
                    if rec["existing_id"]:
                        cur.execute("""
                            UPDATE labour_attendance SET present=%s, days_worked=%s,
                            wage_paid=%s, advance=%s, payment_method=%s, notes=%s
                            WHERE id=%s
                        """, (rec["present"], rec["days_worked"], rec["wage_paid"],
                              rec["advance"], rec["payment_method"], rec["notes"],
                              rec["existing_id"]))
                    else:
                        cur.execute("""
                            INSERT INTO labour_attendance
                                (labourer_id, work_date, present, days_worked,
                                 wage_paid, advance, payment_method, notes)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (rec["labourer_id"], work_date, rec["present"],
                              rec["days_worked"], rec["wage_paid"], rec["advance"],
                              rec["payment_method"], rec["notes"]))
            st.success("✅ Attendance saved!")
            st.rerun()

    # Daily summary
    st.markdown("---")
    st.markdown("### 📋 Today's Summary")
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT l.name, la.present, la.days_worked, la.wage_paid, la.advance,
                   la.payment_method, la.notes
            FROM labour_attendance la
            JOIN labourers l ON l.id = la.labourer_id
            WHERE la.work_date = %s
            ORDER BY l.name
        """, (work_date,))
        today_summary = cur.fetchall()

    if today_summary:
        df_sum = pd.DataFrame(today_summary)
        total_wage = df_sum["wage_paid"].sum()
        total_advance = df_sum["advance"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Workers Present", int(df_sum["present"].sum()))
        c2.metric("Total Wages Paid", f"₹{total_wage:.2f}")
        c3.metric("Total Advance", f"₹{total_advance:.2f}")
        st.dataframe(df_sum, use_container_width=True, hide_index=True)


# ─── TAB 2: ROSTER ────────────────────────────────────────────────────────────
with tab_roster:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM labourers ORDER BY is_active DESC, name")
        all_labourers = cur.fetchall()

    action = st.radio("Action", ["View Roster", "Add Labourer", "Edit Labourer", "Delete Labourer"], horizontal=True)

    if action == "View Roster":
        if all_labourers:
            df_lab = pd.DataFrame(all_labourers)
            df_lab["status"] = df_lab["is_active"].map({True: "✅ Active", False: "❌ Inactive"})
            st.dataframe(
                df_lab[["name", "phone", "daily_wage", "status"]].rename(
                    columns={"name": "Name", "phone": "Phone",
                             "daily_wage": "Daily Wage (₹)", "status": "Status"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No labourers registered yet.")

    elif action == "Add Labourer":
        with st.form("add_lab"):
            st.markdown("#### ➕ Add New Labourer")
            col1, col2 = st.columns(2)
            with col1:
                l_name = st.text_input("Name *")
                l_phone = st.text_input("Phone")
            with col2:
                l_wage = st.number_input("Daily Wage (₹)", min_value=0.0, value=400.0)
            if st.form_submit_button("💾 Add Labourer", type="primary"):
                if l_name:
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO labourers (name, phone, daily_wage) VALUES (%s,%s,%s)",
                            (l_name, l_phone or None, l_wage)
                        )
                    st.success(f"✅ {l_name} added!")
                    st.rerun()
                else:
                    st.error("Name required.")

    elif action == "Edit Labourer":
        sel_lab = st.selectbox("Select Labourer", all_labourers,
                               format_func=lambda x: f"{x['name']} ({'Active' if x['is_active'] else 'Inactive'})")
        if sel_lab:
            with st.form("edit_lab"):
                col1, col2 = st.columns(2)
                with col1:
                    e_name = st.text_input("Name", value=sel_lab["name"])
                    e_phone = st.text_input("Phone", value=sel_lab["phone"] or "")
                with col2:
                    e_wage = st.number_input("Daily Wage (₹)", value=float(sel_lab["daily_wage"]))
                    e_active = st.checkbox("Active", value=bool(sel_lab["is_active"]))
                if st.form_submit_button("💾 Update", type="primary"):
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE labourers SET name=%s, phone=%s, daily_wage=%s, is_active=%s WHERE id=%s
                        """, (e_name, e_phone or None, e_wage, e_active, sel_lab["id"]))
                    st.success("✅ Updated!")
                    st.rerun()

    elif action == "Delete Labourer":
        st.warning("Deleting a labourer will deactivate the worker. Past attendance and wage records will be preserved for reports.")
        deletable = [lab for lab in all_labourers if lab["is_active"]]
        if not deletable:
            st.info("There are no active labourers to delete.")
        else:
            sel_delete = st.selectbox(
                "Select Labourer to Delete", deletable,
                format_func=lambda x: f"{x['name']} ({x.get('phone') or 'No phone'})"
            )
            confirm_delete = st.checkbox(
                f"I confirm that {sel_delete['name']} should be removed from the active roster.",
                key=f"confirm_delete_lab_{sel_delete['id']}"
            )
            if st.button("🗑️ Delete Labourer", type="primary", disabled=not confirm_delete):
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE labourers SET is_active=FALSE WHERE id=%s", (sel_delete["id"],))
                st.success(f"{sel_delete['name']} was removed from the active roster. Historical records are retained.")
                st.rerun()


# ─── TAB 3: REPORTS ───────────────────────────────────────────────────────────
with tab_report:
    st.markdown("### 📊 Labour Reports")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        from_date = st.date_input("From", value=date.today().replace(day=1))
    with col_f2:
        to_date = st.date_input("To", value=date.today())

    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT l.name, 
                   COUNT(la.id) FILTER (WHERE la.present) as days_present,
                   SUM(la.days_worked) as total_days,
                   SUM(la.wage_paid) as total_wages,
                   SUM(la.advance) as total_advance
            FROM labourers l
            LEFT JOIN labour_attendance la ON la.labourer_id = l.id
                AND la.work_date BETWEEN %s AND %s
            WHERE l.is_active = TRUE
            GROUP BY l.id, l.name
            ORDER BY l.name
        """, (from_date, to_date))
        report_data = cur.fetchall()

    if report_data:
        df_rep = pd.DataFrame(report_data)
        total_wages = df_rep["total_wages"].sum()
        total_adv = df_rep["total_advance"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Period: {from_date} to {to_date}", "")
        c2.metric("Total Wages", f"₹{total_wages:.2f}")
        c3.metric("Total Advances", f"₹{total_adv:.2f}")

        df_rep.columns = ["Name", "Days Present", "Total Days", "Total Wages (₹)", "Total Advance (₹)"]
        df_rep["Total Wages (₹)"] = df_rep["Total Wages (₹)"].apply(lambda x: f"₹{x:.2f}" if x else "₹0.00")
        df_rep["Total Advance (₹)"] = df_rep["Total Advance (₹)"].apply(lambda x: f"₹{x:.2f}" if x else "₹0.00")
        st.dataframe(df_rep, use_container_width=True, hide_index=True)
    
    # Daily wage expense log
    st.markdown("#### 📅 Daily Wage Log")
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT la.work_date, l.name, la.days_worked, la.wage_paid,
                   la.advance, la.payment_method, la.notes
            FROM labour_attendance la
            JOIN labourers l ON l.id = la.labourer_id
            WHERE la.work_date BETWEEN %s AND %s
            ORDER BY la.work_date DESC, l.name
        """, (from_date, to_date))
        daily_log = cur.fetchall()

    if daily_log:
        df_daily = pd.DataFrame(daily_log)
        df_daily["work_date"] = pd.to_datetime(df_daily["work_date"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df_daily, use_container_width=True, hide_index=True)
