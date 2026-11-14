"""Reports & Analytics — Bharathi Oil Mill"""

import streamlit as st
import psycopg2.extras
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import date, timedelta
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db

st.set_page_config(page_title="Reports – Bharathi Oil Mill", layout="wide")
st.markdown("## 📊 Reports & Analytics")
st.markdown("---")

# Date filter
col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
with col_f1:
    from_date = st.date_input("From", value=date.today().replace(day=1))
with col_f2:
    to_date = st.date_input("To", value=date.today())
with col_f3:
    st.markdown("<br>", unsafe_allow_html=True)
    quick = st.selectbox("Quick", ["Custom", "Today", "This Week", "This Month", "Last Month"])
    if quick == "Today":
        from_date = to_date = date.today()
    elif quick == "This Week":
        from_date = date.today() - timedelta(days=date.today().weekday())
        to_date = date.today()
    elif quick == "This Month":
        from_date = date.today().replace(day=1)
        to_date = date.today()
    elif quick == "Last Month":
        first_this = date.today().replace(day=1)
        to_date = first_this - timedelta(days=1)
        from_date = to_date.replace(day=1)



def build_professional_excel(sheets):
    """Create a polished multi-sheet Excel workbook with filters, totals and formatting."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            safe = frame.copy() if frame is not None else pd.DataFrame()
            safe.to_excel(writer, sheet_name=sheet_name[:31], index=False, startrow=3)
            ws = writer.book[sheet_name[:31]]
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(safe.columns)))
            title = ws.cell(1, 1, f"BHARATHI OIL MILL  |  {sheet_name.upper()}")
            title.font = Font(name="Aptos Display", size=16, bold=True, color="FFFFFF")
            title.fill = PatternFill("solid", fgColor="17324D")
            title.alignment = Alignment(vertical="center")
            ws.row_dimensions[1].height = 30
            ws.cell(2, 1, f"Report period: {from_date:%d-%m-%Y} to {to_date:%d-%m-%Y}").font = Font(
                italic=True, color="64748B", size=9)
            for cell in ws[4]:
                if cell.column <= len(safe.columns):
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="B33A3A")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.freeze_panes = "A5"
            if len(safe.columns):
                ws.auto_filter.ref = f"A4:{get_column_letter(len(safe.columns))}{max(4, len(safe)+4)}"
                for col_idx, col in enumerate(safe.columns, 1):
                    values = [str(col)] + [str(v) for v in safe[col].dropna().head(250)]
                    width = min(max(max((len(v) for v in values), default=10) + 3, 13), 38)
                    ws.column_dimensions[get_column_letter(col_idx)].width = width
            for row in ws.iter_rows(min_row=5):
                for cell in row:
                    cell.alignment = Alignment(vertical="center")
                    if cell.row % 2 == 0:
                        cell.fill = PatternFill("solid", fgColor="F1F5F9")
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '#,##0.00;[Red]-#,##0.00'
    output.seek(0)
    return output.getvalue()


# ─── DOWNLOAD CENTRE ─────────────────────────────────────────────────────────
st.markdown("### 📥 Professional Excel Export")
st.caption("Export the selected date range as a formatted workbook with separate sheets for bills, item-level transactions, expenses, stock movements and daily totals.")
with get_db() as conn:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT bill_number AS "Bill Number", created_at AS "Date", customer_name AS "Customer",
               customer_phone AS "Phone", subtotal AS "Subtotal", discount AS "Discount",
               total AS "Total", payment_method AS "Payment Method",
               payment_status AS "Payment Status", bill_type AS "Bill Type"
        FROM bills WHERE DATE(created_at) BETWEEN %s AND %s ORDER BY created_at
    """, (from_date, to_date))
    export_bills = pd.DataFrame(cur.fetchall())
    cur.execute("""
        SELECT b.bill_number AS "Bill Number", b.created_at AS "Date", b.customer_name AS "Customer",
               bi.service_name AS "Item / Service", bi.quantity_kg AS "Quantity (kg)",
               bi.rate_per_kg AS "Rate", bi.amount AS "Amount"
        FROM bill_items bi JOIN bills b ON b.id=bi.bill_id
        WHERE DATE(b.created_at) BETWEEN %s AND %s ORDER BY b.created_at
    """, (from_date, to_date))
    export_items = pd.DataFrame(cur.fetchall())
    cur.execute("""
        SELECT expense_date AS "Date", category AS "Category", description AS "Description",
               amount AS "Amount", payment_method AS "Payment Method", reference AS "Reference"
        FROM expenses WHERE expense_date BETWEEN %s AND %s ORDER BY expense_date
    """, (from_date, to_date))
    export_expenses = pd.DataFrame(cur.fetchall())
    cur.execute("""
        SELECT it.created_at AS "Date", i.item_name AS "Item",
               it.transaction_type AS "Movement", it.quantity AS "Quantity",
               i.unit AS "Unit", it.rate AS "Rate", it.total_value AS "Value",
               it.reference_bill AS "Reference Bill", it.notes AS "Notes"
        FROM inventory_transactions it LEFT JOIN inventory i ON i.id=it.inventory_id
        WHERE DATE(it.created_at) BETWEEN %s AND %s ORDER BY it.created_at
    """, (from_date, to_date))
    export_stock = pd.DataFrame(cur.fetchall())
    cur.execute("""
        SELECT DATE(created_at) AS "Date", COUNT(*) AS "Bills",
               SUM(CASE WHEN payment_status='paid' THEN total ELSE 0 END) AS "Collected",
               SUM(CASE WHEN payment_status='pending' THEN total ELSE 0 END) AS "Pending",
               SUM(total) AS "Gross Total"
        FROM bills WHERE DATE(created_at) BETWEEN %s AND %s
        GROUP BY DATE(created_at) ORDER BY DATE(created_at)
    """, (from_date, to_date))
    export_daily = pd.DataFrame(cur.fetchall())

excel_data = build_professional_excel({
    "Bills": export_bills, "Transactions": export_items,
    "Expenses": export_expenses, "Stock Movements": export_stock,
    "Daily Summary": export_daily
})
st.download_button("⬇️ Download Professional Excel Report",
                   data=excel_data,
                   file_name=f"Bharathi_Oil_Mill_Report_{from_date:%Y%m%d}_{to_date:%Y%m%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   type="primary")
st.markdown("---")

tab_summary, tab_bills, tab_service, tab_expenses = st.tabs(
    ["📈 Summary", "🧾 All Bills", "🔍 Service Analytics", "💸 Expenses"])


# ─── TAB 1: SUMMARY ──────────────────────────────────────────────────────────
with tab_summary:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Revenue summary
        cur.execute("""
            SELECT 
                COUNT(*) as total_bills,
                SUM(CASE WHEN payment_status='paid' THEN total ELSE 0 END) as collected,
                SUM(CASE WHEN payment_status='pending' THEN total ELSE 0 END) as pending,
                SUM(total) as gross_total
            FROM bills WHERE DATE(created_at) BETWEEN %s AND %s
        """, (from_date, to_date))
        rev = cur.fetchone()

        # Labour cost
        cur.execute("""
            SELECT COALESCE(SUM(wage_paid + advance), 0) as total_labour
            FROM labour_attendance WHERE work_date BETWEEN %s AND %s
        """, (from_date, to_date))
        labour = cur.fetchone()

        # Maintenance cost
        cur.execute("""
            SELECT COALESCE(SUM(cost), 0) as total_maint
            FROM machine_maintenance WHERE maintenance_date BETWEEN %s AND %s
        """, (from_date, to_date))
        maint = cur.fetchone()

        # Expenses
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_exp
            FROM expenses WHERE expense_date BETWEEN %s AND %s
        """, (from_date, to_date))
        exp = cur.fetchone()

    collected = float(rev["collected"] or 0)
    pending = float(rev["pending"] or 0)
    total_labour = float(labour["total_labour"] or 0)
    total_maint = float(maint["total_maint"] or 0)
    total_exp = float(exp["total_exp"] or 0)
    gross = float(rev["gross_total"] or 0)
    net_profit = collected - total_labour - total_maint - total_exp

    st.markdown(f"#### Period: {from_date} → {to_date}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Revenue Collected", f"₹{collected:,.2f}")
    c2.metric("⏳ Pending", f"₹{pending:,.2f}")
    c3.metric("📃 Total Bills", int(rev["total_bills"] or 0))
    c4.metric("📈 Gross Revenue", f"₹{gross:,.2f}")

    st.markdown("---")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("👷 Labour Cost", f"₹{total_labour:,.2f}")
    c6.metric("⚙️ Maintenance Cost", f"₹{total_maint:,.2f}")
    c7.metric("💸 Other Expenses", f"₹{total_exp:,.2f}")
    c8.metric("🤑 Net Profit (est.)", f"₹{net_profit:,.2f}",
              delta=f"{'▲' if net_profit > 0 else '▼'} from collected")

    # Daily revenue chart
    st.markdown("---")
    st.markdown("#### 📅 Daily Revenue")
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT DATE(created_at) as day, SUM(total) as revenue, COUNT(*) as bills
            FROM bills WHERE DATE(created_at) BETWEEN %s AND %s
            AND payment_status='paid'
            GROUP BY DATE(created_at) ORDER BY day
        """, (from_date, to_date))
        daily = cur.fetchall()
    if daily:
        df_daily = pd.DataFrame(daily)
        df_daily["day"] = pd.to_datetime(df_daily["day"]).dt.strftime("%d %b")
        st.bar_chart(df_daily.set_index("day")["revenue"])


# ─── TAB 2: ALL BILLS ────────────────────────────────────────────────────────
with tab_bills:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT b.bill_number, b.customer_name, b.customer_phone,
                   b.total, b.payment_method, b.payment_status,
                   b.reminder_date, b.bill_type,
                   DATE(b.created_at) as bill_date
            FROM bills b
            WHERE DATE(b.created_at) BETWEEN %s AND %s
            ORDER BY b.created_at DESC
        """, (from_date, to_date))
        bills = cur.fetchall()

    if bills:
        df_bills = pd.DataFrame(bills)
        df_bills["bill_date"] = pd.to_datetime(df_bills["bill_date"]).dt.strftime("%d-%m-%Y")
        df_bills["payment_status"] = df_bills["payment_status"].apply(
            lambda x: "✅ Paid" if x == "paid" else "⏳ Pending")
        df_bills["total"] = df_bills["total"].apply(lambda x: f"₹{x:.2f}")
        df_bills = df_bills.rename(columns={
            "bill_number": "Bill #", "customer_name": "Customer",
            "customer_phone": "Phone", "total": "Total",
            "payment_method": "Method", "payment_status": "Status",
            "reminder_date": "Reminder", "bill_type": "Type",
            "bill_date": "Date"
        })
        st.dataframe(df_bills, use_container_width=True, hide_index=True)
    else:
        st.info("No bills in this period.")


# ─── TAB 3: SERVICE ANALYTICS ────────────────────────────────────────────────
with tab_service:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT bi.service_name,
                   COUNT(*) as times,
                   SUM(bi.quantity_kg) as total_kg,
                   SUM(bi.amount) as total_revenue
            FROM bill_items bi
            JOIN bills b ON b.id = bi.bill_id
            WHERE DATE(b.created_at) BETWEEN %s AND %s
            GROUP BY bi.service_name
            ORDER BY total_revenue DESC
        """, (from_date, to_date))
        svc_data = cur.fetchall()

    if svc_data:
        df_svc = pd.DataFrame(svc_data)
        df_svc.columns = ["Service", "Times", "Total kg", "Revenue (₹)"]
        df_svc["Revenue (₹)"] = df_svc["Revenue (₹)"].apply(lambda x: f"₹{x:.2f}")
        df_svc["Total kg"] = df_svc["Total kg"].apply(lambda x: f"{x:.2f} kg")
        st.dataframe(df_svc, use_container_width=True, hide_index=True)
    else:
        st.info("No service data in this period.")

    # Oil cake summary
    st.markdown("#### 🟤 Oil Cake Transactions")
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT op.seed_type, SUM(op.oil_cake_kg) as total_cake_kg,
                   SUM(op.oil_cake_value) as total_cake_value
            FROM oil_processing op
            JOIN bills b ON b.id = op.bill_id
            WHERE DATE(b.created_at) BETWEEN %s AND %s
            GROUP BY op.seed_type ORDER BY total_cake_kg DESC
        """, (from_date, to_date))
        cake_data = cur.fetchall()
    if cake_data:
        df_cake = pd.DataFrame(cake_data)
        df_cake.columns = ["Seed Type", "Oil Cake Collected (kg)", "Value (₹)"]
        df_cake["Value (₹)"] = df_cake["Value (₹)"].apply(lambda x: f"₹{x:.2f}")
        st.dataframe(df_cake, use_container_width=True, hide_index=True)


# ─── TAB 4: EXPENSES ─────────────────────────────────────────────────────────
with tab_expenses:
    col_e1, col_e2 = st.columns([2, 1])
    with col_e1:
        st.markdown("#### 💸 Expense Log")
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT * FROM expenses
                WHERE expense_date BETWEEN %s AND %s
                ORDER BY expense_date DESC
            """, (from_date, to_date))
            expenses = cur.fetchall()
        if expenses:
            df_exp = pd.DataFrame(expenses)
            df_exp["expense_date"] = pd.to_datetime(df_exp["expense_date"]).dt.strftime("%d-%m-%Y")
            df_exp["amount"] = df_exp["amount"].apply(lambda x: f"₹{x:.2f}")
            st.dataframe(
                df_exp[["expense_date", "category", "description", "amount", "payment_method"]],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No expenses in this period.")

    with col_e2:
        st.markdown("#### ➕ Add Expense")
        with st.form("add_exp"):
            exp_date = st.date_input("Date", value=date.today())
            exp_cat = st.selectbox("Category", [
                "Electricity", "Fuel", "Repairs", "Supplies", "Transport",
                "Rent", "Misc", "Labour", "Maintenance"
            ])
            exp_desc = st.text_input("Description")
            exp_amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0)
            exp_pay = st.radio("Payment", ["cash", "upi"], horizontal=True)
            if st.form_submit_button("💾 Add", type="primary"):
                if exp_amt > 0:
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO expenses (expense_date, category, description, amount, payment_method)
                            VALUES (%s,%s,%s,%s,%s)
                        """, (exp_date, exp_cat, exp_desc, exp_amt, exp_pay))
                    st.success("✅ Expense recorded!")
                    st.rerun()
