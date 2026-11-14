"""
Point of Sale — Bharathi Oil Mill
Handles: service billing, oil seed processing with oil-cake buy-back,
         customer info, payment, QR, pending bills.
"""

import streamlit as st
import psycopg2.extras
from datetime import date, timedelta
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_db, generate_bill_number
from utils.bill_printer import generate_bill_html
from utils.qr_utils import generate_bill_qr

st.set_page_config(page_title="POS – Bharathi Oil Mill", layout="wide")

# ── Styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.pos-card {background:#fff; border-radius:12px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.08);}
.item-row {display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid #f0f0f0;}
.total-box {background:linear-gradient(135deg,#c0392b,#e74c3c); color:#fff; border-radius:10px; padding:16px; text-align:center;}
.total-amount {font-size:2.2rem; font-weight:800;}
.badge-paid {background:#27ae60; color:#fff; padding:2px 10px; border-radius:12px; font-size:12px;}
.badge-pending {background:#e67e22; color:#fff; padding:2px 10px; border-radius:12px; font-size:12px;}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🏪 Point of Sale")
st.markdown("---")

# ── Load services ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_services():
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM services WHERE is_active=TRUE ORDER BY category, name")
        return cur.fetchall()

services = load_services()
svc_by_cat = {}
for s in services:
    svc_by_cat.setdefault(s["category"], []).append(s)

CAT_LABELS = {
    "grain_milling": "🌾 Grain Milling",
    "spice_grinding": "🌶 Spice Grinding",
    "dhal_splitting": "🫘 Dhal Splitting",
    "oil_extraction": "🫒 Oil Extraction",
    "oil_cake_grinding": "🟤 Oil Cake Grinding",
    "wet_grinding": "💧 Wet Grinding",
}

# ── Session state ─────────────────────────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []          # [{service_id, name, qty, rate, amount}]
if "oil_proc" not in st.session_state:
    st.session_state.oil_proc = []      # oil-seed processing rows

tab_new, tab_pending, tab_scan = st.tabs(["🧾 New Bill", "⏳ Pending Bills", "📷 Scan QR"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: NEW BILL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_new:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # ── Service selector ──────────────────────────────────────────────────
        st.markdown("### ➕ Add Services")
        sel_cat = st.selectbox("Category", list(svc_by_cat.keys()),
                               format_func=lambda x: CAT_LABELS.get(x, x))
        cat_services = svc_by_cat.get(sel_cat, [])
        sel_svc = st.selectbox("Service", cat_services,
                               format_func=lambda s: f"{s['name']}  (₹{s['rate_per_kg']}/kg)")

        col_q, col_r, col_add = st.columns([2, 2, 1])
        with col_q:
            qty = st.number_input("Qty (kg)", min_value=0.001, value=1.0, step=0.5, format="%.3f", key="qty_input")
        with col_r:
            rate = st.number_input("Rate ₹/kg", min_value=0.0,
                                   value=float(sel_svc["rate_per_kg"]), step=0.5, key="rate_input")
        with col_add:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add", use_container_width=True, type="primary"):
                st.session_state.cart.append({
                    "service_id": sel_svc["id"],
                    "service_name": sel_svc["name"],
                    "quantity_kg": qty,
                    "rate_per_kg": rate,
                    "amount": round(qty * rate, 2),
                    "notes": "",
                })
                st.rerun()

        # ── Oil Seed Processing ───────────────────────────────────────────────
        with st.expander("🫒 Oil Seed Processing (with Oil Cake Buy-back)", expanded=False):
            oil_seeds = [s for s in services if s["category"] == "oil_extraction"]
            oil_svc_sel = st.selectbox("Oil Seed Type", oil_seeds,
                                       format_func=lambda s: s["name"], key="oil_svc_sel")

            # Load oil cake inventory rate
            def get_oilcake_rate(seed_name):
                seed_map = {
                    "Groundnut": "Groundnut Oil Cake",
                    "Sesame": "Sesame Oil Cake",
                    "Coconut": "Coconut Oil Cake",
                    "Ilupai": "Ilupai Oil Cake",
                    "Neem": "Neem Oil Cake",
                }
                for k, v in seed_map.items():
                    if k.lower() in seed_name.lower():
                        with get_db() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT rate_per_unit FROM inventory WHERE item_name=%s", (v,))
                            row = cur.fetchone()
                            return float(row[0]) if row else 10.0
                return 10.0

            o_col1, o_col2 = st.columns(2)
            with o_col1:
                o_input_kg = st.number_input("Input Seed (kg)", min_value=0.1, value=5.0, step=0.5, key="o_inp")
                o_proc_rate = st.number_input("Processing Rate ₹/kg", min_value=0.0,
                                              value=float(oil_svc_sel["rate_per_kg"]), key="o_prate")
            with o_col2:
                o_cake_kg = st.number_input("Oil Cake Returned (kg)", min_value=0.0, value=round(o_input_kg * 0.4, 3),
                                            step=0.1, key="o_cake")
                o_cake_rate = st.number_input("Oil Cake Rate ₹/kg (buy-back)",
                                              min_value=0.0,
                                              value=get_oilcake_rate(oil_svc_sel["name"]),
                                              key="o_crate")

            proc_fee = round(o_input_kg * o_proc_rate, 2)
            cake_val = round(o_cake_kg * o_cake_rate, 2)
            net = round(proc_fee - cake_val, 2)
            direction = "Customer pays" if net > 0 else "Mill pays customer"
            st.info(f"**Processing fee:** ₹{proc_fee:.2f}  |  **Oil cake value:** ₹{cake_val:.2f}  |  **Net (_{direction}_):** ₹{abs(net):.2f}")

            if st.button("➕ Add Oil Processing", key="add_oil_proc"):
                st.session_state.oil_proc.append({
                    "seed_type": oil_svc_sel["name"],
                    "input_kg": o_input_kg,
                    "processing_rate": o_proc_rate,
                    "processing_fee": proc_fee,
                    "oil_cake_kg": o_cake_kg,
                    "oil_cake_rate": o_cake_rate,
                    "oil_cake_value": cake_val,
                    "net_amount": net,
                    "direction": "collect" if net > 0 else "pay",
                })
                st.rerun()

        # ── Cart ──────────────────────────────────────────────────────────────
        st.markdown("### 🛒 Cart")
        if not st.session_state.cart and not st.session_state.oil_proc:
            st.info("No items added yet.")
        else:
            for i, item in enumerate(st.session_state.cart):
                c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 0.8])
                c1.write(f"**{item['service_name']}**")
                c2.write(f"{item['quantity_kg']:.3f} kg")
                c3.write(f"₹{item['amount']:.2f}")
                if c4.button("🗑", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

            for i, op in enumerate(st.session_state.oil_proc):
                c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 0.8])
                c1.write(f"🫒 **{op['seed_type']}** _(oil proc)_")
                c2.write(f"{op['input_kg']:.3f} kg")
                net_disp = f"₹{abs(op['net_amount']):.2f} {'←' if op['net_amount']>0 else '→'}"
                c3.write(net_disp)
                if c4.button("🗑", key=f"del_op_{i}"):
                    st.session_state.oil_proc.pop(i)
                    st.rerun()

    # ── Right panel: summary + customer + payment ──────────────────────────────
    with col_right:
        subtotal = sum(i["amount"] for i in st.session_state.cart)
        oil_net = sum(op["net_amount"] for op in st.session_state.oil_proc)
        grand_total = round(subtotal + oil_net, 2)

        st.markdown(f"""
        <div class="total-box">
            <div style="font-size:.85rem;opacity:.85">TOTAL AMOUNT</div>
            <div class="total-amount">₹{grand_total:.2f}</div>
            <div style="font-size:.8rem;opacity:.7">Services: ₹{subtotal:.2f} | Oil proc net: ₹{oil_net:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 👤 Customer Info _(optional)_")
        cust_name = st.text_input("Customer Name", placeholder="Leave blank for walk-in")
        cust_phone = st.text_input("Phone Number", placeholder="+91 XXXXX XXXXX")
        notes = st.text_area("Notes", placeholder="Any special instructions...", height=60)

        st.markdown("### 💳 Payment")
        payment_method = st.radio("Method", ["Cash", "UPI", "Skip / Pending"],
                                  horizontal=True)
        
        reminder_date = None
        if payment_method == "Skip / Pending":
            st.warning("⏳ This bill will be marked as **Pending**.")
            if not cust_name and not cust_phone:
                st.error("Please add customer name or phone for pending bills!")
            reminder_date = st.date_input("Reminder Date", value=date.today() + timedelta(days=7))

        discount = st.number_input("Discount (₹)", min_value=0.0, value=0.0, step=1.0)
        final_total = max(0, grand_total - discount)
        if discount > 0:
            st.markdown(f"**Final Total after discount: ₹{final_total:.2f}**")

        col_save, col_clear = st.columns(2)
        with col_save:
            save_btn = st.button("💾 Save Bill", type="primary", use_container_width=True,
                                 disabled=(not st.session_state.cart and not st.session_state.oil_proc))
        with col_clear:
            if st.button("🧹 Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.session_state.oil_proc = []
                st.rerun()

        if save_btn:
            if payment_method == "Skip / Pending" and not cust_name and not cust_phone:
                st.error("Add customer name/phone for pending bills.")
            else:
                bill_no = generate_bill_number()
                pay_method = payment_method.lower() if payment_method != "Skip / Pending" else "pending"
                pay_status = "pending" if payment_method == "Skip / Pending" else "paid"

                with get_db() as conn:
                    cur = conn.cursor()

                    # Optionally upsert customer
                    cust_id = None
                    if cust_name or cust_phone:
                        cur.execute(
                            "INSERT INTO customers (name, phone) VALUES (%s,%s) RETURNING id",
                            (cust_name or None, cust_phone or None)
                        )
                        cust_id = cur.fetchone()[0]

                    # Insert bill
                    cur.execute("""
                        INSERT INTO bills (bill_number, customer_id, customer_name, customer_phone,
                            subtotal, discount, total, payment_method, payment_status,
                            reminder_date, notes)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                    """, (bill_no, cust_id, cust_name or None, cust_phone or None,
                          grand_total, discount, final_total,
                          pay_method, pay_status, reminder_date, notes or None))
                    bill_id = cur.fetchone()[0]

                    # Insert bill items
                    for item in st.session_state.cart:
                        cur.execute("""
                            INSERT INTO bill_items (bill_id, service_id, service_name,
                                quantity_kg, rate_per_kg, amount)
                            VALUES (%s,%s,%s,%s,%s,%s)
                        """, (bill_id, item["service_id"], item["service_name"],
                              item["quantity_kg"], item["rate_per_kg"], item["amount"]))

                    # Insert oil processing rows + update inventory
                    for op in st.session_state.oil_proc:
                        cur.execute("""
                            INSERT INTO oil_processing (bill_id, seed_type, input_kg,
                                processing_rate, processing_fee, oil_cake_kg, oil_cake_rate,
                                oil_cake_value, net_amount, direction)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (bill_id, op["seed_type"], op["input_kg"],
                              op["processing_rate"], op["processing_fee"],
                              op["oil_cake_kg"], op["oil_cake_rate"],
                              op["oil_cake_value"], op["net_amount"], op["direction"]))

                        # Update oil cake inventory
                        seed_cake_map = {
                            "groundnut": "Groundnut Oil Cake",
                            "sesame": "Sesame Oil Cake",
                            "coconut": "Coconut Oil Cake",
                            "ilupai": "Ilupai Oil Cake",
                            "neem": "Neem Oil Cake",
                        }
                        for k, v in seed_cake_map.items():
                            if k in op["seed_type"].lower():
                                cur.execute("""
                                    UPDATE inventory SET quantity = quantity + %s, updated_at=NOW()
                                    WHERE item_name = %s
                                """, (op["oil_cake_kg"], v))
                                cur.execute("""
                                    INSERT INTO inventory_transactions
                                        (inventory_id, transaction_type, quantity, rate, total_value, reference_bill)
                                    SELECT id, 'in', %s, %s, %s, %s FROM inventory WHERE item_name=%s
                                """, (op["oil_cake_kg"], op["oil_cake_rate"],
                                      op["oil_cake_value"], bill_no, v))
                                break

                # Fetch the saved bill for printing
                with get_db() as conn:
                    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur.execute("SELECT * FROM bills WHERE bill_number=%s", (bill_no,))
                    saved_bill = dict(cur.fetchone())
                    cur.execute("SELECT * FROM bill_items WHERE bill_id=%s", (bill_id,))
                    saved_items = [dict(r) for r in cur.fetchall()]
                    cur.execute("SELECT * FROM oil_processing WHERE bill_id=%s", (bill_id,))
                    saved_ops = [dict(r) for r in cur.fetchall()]

                st.success(f"✅ Bill **{bill_no}** saved!")
                st.session_state.cart = []
                st.session_state.oil_proc = []

                # Show QR + print button
                qr_b64 = generate_bill_qr({**saved_bill, "items": saved_items})
                col_qr, col_btn = st.columns([1, 2])
                with col_qr:
                    st.image(f"data:image/png;base64,{qr_b64}", width=130, caption="Scan to verify")
                with col_btn:
                    bill_html = generate_bill_html(saved_bill, saved_items, saved_ops)
                    st.download_button("🖨 Download / Print Bill",
                                       data=bill_html,
                                       file_name=f"{bill_no}.html",
                                       mime="text/html",
                                       use_container_width=True)
                st.cache_data.clear()
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: PENDING BILLS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_pending:
    st.markdown("### ⏳ Pending / Unpaid Bills")
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT b.*, 
                   CASE WHEN b.reminder_date <= CURRENT_DATE THEN true ELSE false END as overdue
            FROM bills b
            WHERE b.payment_status='pending'
            ORDER BY b.reminder_date ASC NULLS LAST, b.created_at DESC
        """)
        pending_bills = cur.fetchall()

    if not pending_bills:
        st.success("🎉 No pending bills!")
    else:
        for bill in pending_bills:
            overdue = bill["overdue"]
            color = "#ffeaea" if overdue else "#fffbea"
            icon = "🔴" if overdue else "🟡"
            with st.container():
                st.markdown(f"""
                <div style="background:{color};border-radius:8px;padding:12px;margin-bottom:8px;border-left:4px solid {'#e74c3c' if overdue else '#f39c12'}">
                {icon} <strong>{bill['bill_number']}</strong> &nbsp;|&nbsp;
                👤 {bill['customer_name'] or 'Walk-in'} &nbsp;|&nbsp;
                📞 {bill['customer_phone'] or '—'} &nbsp;|&nbsp;
                💰 ₹{bill['total']:.2f} &nbsp;|&nbsp;
                📅 Due: {bill['reminder_date'] or 'Not set'}
                {'&nbsp; <span style="color:#e74c3c;font-weight:700">OVERDUE!</span>' if overdue else ''}
                </div>
                """, unsafe_allow_html=True)

                col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
                with col_m1:
                    new_method = st.selectbox("Mark as paid via",
                                              ["cash", "upi"],
                                              key=f"pm_{bill['id']}")
                with col_m2:
                    st.write("")
                with col_m3:
                    if st.button("✅ Mark Paid", key=f"pay_{bill['id']}"):
                        with get_db() as conn:
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE bills SET payment_status='paid',
                                payment_method=%s WHERE id=%s
                            """, (new_method, bill["id"]))
                        st.success(f"Bill {bill['bill_number']} marked as paid!")
                        st.cache_data.clear()
                        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: SCAN QR (decode)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_scan:
    st.markdown("### 📷 Scan / Decode QR Code")
    st.info("Paste the bill number to retrieve details, or upload a QR code image.")

    search_bill = st.text_input("Enter Bill Number", placeholder="BOM-20240101-0001")
    if search_bill:
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM bills WHERE bill_number=%s", (search_bill,))
            b = cur.fetchone()
            if b:
                cur.execute("SELECT * FROM bill_items WHERE bill_id=%s", (b["id"],))
                b_items = cur.fetchall()
                cur.execute("SELECT * FROM oil_processing WHERE bill_id=%s", (b["id"],))
                b_ops = cur.fetchall()

                st.success(f"✅ Bill found: **{b['bill_number']}**")
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"**Customer:** {b['customer_name'] or 'Walk-in'}")
                    st.write(f"**Phone:** {b['customer_phone'] or '—'}")
                    st.write(f"**Total:** ₹{b['total']:.2f}")
                    st.write(f"**Status:** {b['payment_status']}")
                    st.write(f"**Payment:** {b['payment_method']}")
                    if b_items:
                        st.markdown("**Items:**")
                        for item in b_items:
                            st.write(f"• {item['service_name']} – {item['quantity_kg']} kg – ₹{item['amount']}")
                with col_b:
                    qr_b64 = generate_bill_qr({**dict(b), "items": [dict(i) for i in b_items]})
                    st.image(f"data:image/png;base64,{qr_b64}", width=150)

                bill_html = generate_bill_html(dict(b), [dict(i) for i in b_items],
                                               [dict(o) for o in b_ops])
                st.download_button("🖨 Download Bill", data=bill_html,
                                   file_name=f"{b['bill_number']}.html",
                                   mime="text/html")
            else:
                st.error("Bill not found.")
