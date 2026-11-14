"""Inventory Management — Bharathi Oil Mill"""

import streamlit as st
import psycopg2.extras
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db
import pandas as pd

st.set_page_config(page_title="Inventory – Bharathi Oil Mill", layout="wide")
st.markdown("## 📦 Inventory Management")
st.markdown("---")

CAT_ICONS = {
    "oil_cake": "🟤", "oil_product": "🫙", "supplies": "📦",
    "grain": "🌾", "spice": "🌶", "other": "📋",
}

tab_view, tab_add, tab_txn, tab_bulk_sale = st.tabs(
    ["📊 Stock View", "➕ Add / Edit Item", "📋 Transactions", "💰 Bulk Oil Cake Sale"])


# ─── TAB 1: STOCK VIEW ────────────────────────────────────────────────────────
with tab_view:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM inventory ORDER BY category, item_name")
        items = cur.fetchall()

    if not items:
        st.info("No inventory items found.")
    else:
        df = pd.DataFrame(items)
        df["value"] = df["quantity"] * df["rate_per_unit"]
        df["status"] = df.apply(
            lambda r: "🔴 Low" if r["quantity"] <= r["reorder_level"] and r["reorder_level"] > 0
                      else "✅ OK", axis=1)
        df["icon"] = df["category"].map(CAT_ICONS).fillna("📋")
        df["display"] = df["icon"] + " " + df["item_name"]

        # Summary cards
        total_val = df["value"].sum()
        low_stock = (df["quantity"] <= df["reorder_level"]).sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Inventory Value", f"₹{total_val:,.2f}")
        c2.metric("Total Items", len(df))
        c3.metric("Low Stock Alerts", int(low_stock), delta_color="inverse")

        st.markdown("---")
        
        for cat, group in df.groupby("category"):
            icon = CAT_ICONS.get(cat, "📋")
            st.markdown(f"#### {icon} {cat.replace('_', ' ').title()}")
            display_df = group[["item_name", "quantity", "unit", "rate_per_unit", "value", "status", "reorder_level"]].copy()
            display_df.columns = ["Item", "Qty", "Unit", "Rate/Unit (₹)", "Value (₹)", "Status", "Reorder Level"]
            display_df["Qty"] = display_df["Qty"].apply(lambda x: f"{x:.3f}")
            display_df["Rate/Unit (₹)"] = display_df["Rate/Unit (₹)"].apply(lambda x: f"₹{x:.2f}")
            display_df["Value (₹)"] = display_df["Value (₹)"].apply(lambda x: f"₹{x:.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)


# ─── TAB 2: ADD / EDIT ITEM ───────────────────────────────────────────────────
with tab_add:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM inventory ORDER BY item_name")
        inv_items = cur.fetchall()

    action = st.radio("Action", ["Add New Item", "Edit Existing", "Adjust Stock"], horizontal=True)

    if action == "Add New Item":
        with st.form("add_inv"):
            st.markdown("#### ➕ Add New Inventory Item")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Item Name *")
                cat = st.selectbox("Category", list(CAT_ICONS.keys()),
                                   format_func=lambda x: x.replace("_", " ").title())
                qty = st.number_input("Opening Qty", min_value=0.0, value=0.0)
            with col2:
                unit = st.selectbox("Unit", ["kg", "litre", "pcs", "bag", "ton"])
                rate = st.number_input("Rate per Unit (₹)", min_value=0.0, value=0.0)
                reorder = st.number_input("Reorder Level", min_value=0.0, value=0.0)
            notes = st.text_area("Notes", height=60)
            if st.form_submit_button("💾 Add Item", type="primary"):
                if name:
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO inventory (item_name, category, quantity, unit, rate_per_unit, reorder_level, notes)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (name, cat, qty, unit, rate, reorder, notes))
                    st.success(f"✅ '{name}' added!")
                    st.rerun()
                else:
                    st.error("Item name is required.")

    elif action == "Edit Existing":
        sel_item = st.selectbox("Select Item", inv_items,
                                format_func=lambda x: x["item_name"])
        if sel_item:
            with st.form("edit_inv"):
                col1, col2 = st.columns(2)
                with col1:
                    e_rate = st.number_input("New Rate/Unit (₹)", value=float(sel_item["rate_per_unit"]))
                    e_reorder = st.number_input("Reorder Level", value=float(sel_item["reorder_level"]))
                with col2:
                    e_notes = st.text_area("Notes", value=sel_item["notes"] or "", height=80)
                if st.form_submit_button("💾 Update", type="primary"):
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE inventory SET rate_per_unit=%s, reorder_level=%s,
                            notes=%s, updated_at=NOW() WHERE id=%s
                        """, (e_rate, e_reorder, e_notes, sel_item["id"]))
                    st.success("✅ Updated!")
                    st.rerun()

    elif action == "Adjust Stock":
        sel_item = st.selectbox("Select Item", inv_items,
                                format_func=lambda x: f"{x['item_name']} (Current: {x['quantity']} {x['unit']})")
        if sel_item:
            with st.form("adj_stock"):
                col1, col2 = st.columns(2)
                with col1:
                    adj_type = st.radio("Type", ["Stock In", "Stock Out", "Correction"])
                    adj_qty = st.number_input("Quantity", min_value=0.001, value=1.0)
                with col2:
                    adj_rate = st.number_input("Rate (₹)", min_value=0.0, value=float(sel_item["rate_per_unit"]))
                    adj_ref = st.text_input("Reference / Notes")
                if st.form_submit_button("💾 Adjust", type="primary"):
                    with get_db() as conn:
                        cur = conn.cursor()
                        if adj_type == "Stock In":
                            cur.execute("UPDATE inventory SET quantity=quantity+%s, updated_at=NOW() WHERE id=%s",
                                        (adj_qty, sel_item["id"]))
                            txn_type = "in"
                        elif adj_type == "Stock Out":
                            cur.execute("UPDATE inventory SET quantity=GREATEST(0,quantity-%s), updated_at=NOW() WHERE id=%s",
                                        (adj_qty, sel_item["id"]))
                            txn_type = "out"
                        else:
                            cur.execute("UPDATE inventory SET quantity=%s, updated_at=NOW() WHERE id=%s",
                                        (adj_qty, sel_item["id"]))
                            txn_type = "correction"
                        cur.execute("""
                            INSERT INTO inventory_transactions
                                (inventory_id, transaction_type, quantity, rate, total_value, notes)
                            VALUES (%s,%s,%s,%s,%s,%s)
                        """, (sel_item["id"], txn_type, adj_qty, adj_rate,
                              adj_qty * adj_rate, adj_ref))
                    st.success("✅ Stock adjusted!")
                    st.rerun()


# ─── TAB 3: TRANSACTIONS ──────────────────────────────────────────────────────
with tab_txn:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT it.*, i.item_name, i.unit
            FROM inventory_transactions it
            JOIN inventory i ON i.id = it.inventory_id
            ORDER BY it.created_at DESC LIMIT 100
        """)
        txns = cur.fetchall()

    if txns:
        df_txn = pd.DataFrame(txns)
        df_txn["created_at"] = pd.to_datetime(df_txn["created_at"]).dt.strftime("%d-%m-%Y %H:%M")
        st.dataframe(
            df_txn[["created_at", "item_name", "transaction_type", "quantity", "unit", "rate", "total_value", "reference_bill", "notes"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No transactions yet.")


# ─── TAB 4: BULK OIL CAKE SALE ────────────────────────────────────────────────
with tab_bulk_sale:
    st.markdown("### 💰 Sell Oil Cake in Bulk")
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM inventory WHERE category='oil_cake' AND quantity>0 ORDER BY item_name")
        cake_items = cur.fetchall()

    if not cake_items:
        st.info("No oil cake stock available.")
    else:
        with st.form("bulk_cake_sale"):
            sel_cake = st.selectbox("Oil Cake Type", cake_items,
                                    format_func=lambda x: f"{x['item_name']} (Stock: {x['quantity']:.2f} kg @ ₹{x['rate_per_unit']}/kg)")
            col1, col2 = st.columns(2)
            with col1:
                sale_qty = st.number_input("Sale Qty (kg)", min_value=0.1,
                                           max_value=float(sel_cake["quantity"]),
                                           value=min(10.0, float(sel_cake["quantity"])))
                sale_rate = st.number_input("Sale Rate ₹/kg", min_value=0.0,
                                            value=float(sel_cake["rate_per_unit"]))
            with col2:
                buyer_name = st.text_input("Buyer Name")
                buyer_phone = st.text_input("Buyer Phone")
            pay_m = st.radio("Payment", ["Cash", "UPI"], horizontal=True)

            sale_amount = round(sale_qty * sale_rate, 2)
            st.info(f"**Sale Amount: ₹{sale_amount:.2f}**")

            if st.form_submit_button("💾 Record Sale", type="primary"):
                from database import generate_bill_number
                bill_no = generate_bill_number()
                with get_db() as conn:
                    cur = conn.cursor()
                    # Deduct inventory
                    cur.execute("UPDATE inventory SET quantity=quantity-%s, updated_at=NOW() WHERE id=%s",
                                (sale_qty, sel_cake["id"]))
                    cur.execute("""
                        INSERT INTO inventory_transactions
                            (inventory_id, transaction_type, quantity, rate, total_value, reference_bill, notes)
                        VALUES (%s, 'out', %s, %s, %s, %s, %s)
                    """, (sel_cake["id"], sale_qty, sale_rate, sale_amount,
                          bill_no, f"Bulk sale to {buyer_name or 'unknown'}"))

                    # Create a bill record
                    cur.execute("""
                        INSERT INTO bills (bill_number, customer_name, customer_phone,
                            subtotal, total, payment_method, payment_status, bill_type)
                        VALUES (%s,%s,%s,%s,%s,%s,'paid','oil_cake_sale') RETURNING id
                    """, (bill_no, buyer_name or None, buyer_phone or None,
                          sale_amount, sale_amount, pay_m.lower()))
                    bill_id = cur.fetchone()[0]
                    cur.execute("""
                        INSERT INTO bill_items (bill_id, service_name, quantity_kg, rate_per_kg, amount)
                        VALUES (%s,%s,%s,%s,%s)
                    """, (bill_id, sel_cake["item_name"], sale_qty, sale_rate, sale_amount))

                st.success(f"✅ Sale recorded! Bill: {bill_no} | Amount: ₹{sale_amount:.2f}")
                st.rerun()
