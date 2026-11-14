"""
Bharathi Oil Mill — Home Dashboard
Run with: streamlit run Home.py
"""

import streamlit as st
import psycopg2.extras
from datetime import date, timedelta
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

st.set_page_config(
    page_title="Bharathi Oil Mills",
    page_icon="assets/bom.png",
    layout="wide"
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
.css-1d391kg, [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%) !important;
}
[data-testid="stSidebar"] .stMarkdown, 
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p { color: #e0e0e0 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    border-left: 4px solid #c0392b;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] { 
    font-size: 0.8rem; color: #666; font-weight: 600; 
}
[data-testid="metric-container"] [data-testid="stMetricValue"] { 
    font-size: 1.5rem; font-weight: 800; color: #1a1a2e; 
}

/* Page header */
.page-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #c0392b 100%);
    color: white;
    padding: 24px 28px;
    border-radius: 16px;
    margin-bottom: 24px;
}
.mill-logo { font-size: 2.5rem; }
.mill-title { font-size: 1.8rem; font-weight: 800; margin: 0; }
.mill-sub { font-size: 0.9rem; opacity: 0.8; margin-top: 2px; }

/* Alert cards */
.alert-card {
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.alert-red { background:#ffeaea; border-left:4px solid #e74c3c; }
.alert-orange { background:#fff4e5; border-left:4px solid #e67e22; }
.alert-green { background:#eafff0; border-left:4px solid #27ae60; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 6])

with col1:
    st.image("assets/bom_logo.jpeg", width=85)

with col2:
    st.markdown("""
    <p class="mill-title">Bharathi Oil Mills</p>
    <p class="mill-sub">
        Traditional Cold-Press & Milling Services · Management System
    </p>
    """, unsafe_allow_html=True)

# ── DB Init ───────────────────────────────────────────────────────────────────
try:
    from database import init_db, get_db
    init_db()
except Exception as e:
    st.error(f"⚠️ Database connection error: {e}")
    st.markdown("""
    **Setup required:** Create a `.streamlit/secrets.toml` file:
    ```toml
    DATABASE_URL = "postgresql://user:password@host:5432/bharathi_oil_mill"
    ```
    Or set individual fields:
    ```toml
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "bharathi_oil_mill"
    DB_USER = "postgres"
    DB_PASSWORD = "your_password"
    ```
    """)
    st.stop()

# ── Today's KPIs ──────────────────────────────────────────────────────────────
today = date.today()
month_start = today.replace(day=1)

try:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Today revenue
        cur.execute("""
            SELECT COALESCE(SUM(total),0) as today_rev,
                   COUNT(*) as today_bills
            FROM bills WHERE DATE(created_at)=%s AND payment_status='paid'
        """, (today,))
        today_data = cur.fetchone()

        # Pending bills
        cur.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(total),0) as amt
            FROM bills WHERE payment_status='pending'
        """)
        pending_data = cur.fetchone()

        # Overdue
        cur.execute("""
            SELECT COUNT(*) as overdue FROM bills
            WHERE payment_status='pending' AND reminder_date <= %s
        """, (today,))
        overdue_data = cur.fetchone()

        # Month revenue
        cur.execute("""
            SELECT COALESCE(SUM(total),0) as month_rev
            FROM bills WHERE DATE(created_at) >= %s AND payment_status='paid'
        """, (month_start,))
        month_data = cur.fetchone()

        # Active machines
        cur.execute("""
            SELECT status, COUNT(*) as cnt FROM machines GROUP BY status
        """)
        machine_status = {r["status"]: r["cnt"] for r in cur.fetchall()}

        # Low stock
        cur.execute("""
            SELECT COUNT(*) as low FROM inventory
            WHERE quantity <= reorder_level AND reorder_level > 0
        """)
        low_stock = cur.fetchone()

        # Upcoming service
        cur.execute("""
            SELECT machine_name, next_service_date,
                   (next_service_date - CURRENT_DATE) as days_left
            FROM machines WHERE next_service_date IS NOT NULL
            AND next_service_date <= CURRENT_DATE + INTERVAL '14 days'
            ORDER BY next_service_date ASC LIMIT 5
        """)
        upcoming_service = cur.fetchall()

        # Recent bills
        cur.execute("""
            SELECT bill_number, customer_name, total, payment_status,
                   payment_method, DATE(created_at) as bill_date
            FROM bills ORDER BY created_at DESC LIMIT 8
        """)
        recent_bills = cur.fetchall()

except Exception as e:
    st.error(f"Error fetching dashboard data: {e}")
    st.stop()

# ── KPI Metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Today's Revenue", f"₹{float(today_data['today_rev']):,.2f}",
            f"{today_data['today_bills']} bills")
col2.metric("📅 This Month", f"₹{float(month_data['month_rev']):,.2f}")
col3.metric("⏳ Pending Bills", int(pending_data["cnt"]),
            f"₹{float(pending_data['amt']):,.2f} due")
col4.metric("🔴 Overdue", int(overdue_data["overdue"]),
            delta_color="inverse")
col5.metric("✅ Active Machines",
            machine_status.get("active", 0),
            f"🔧 {machine_status.get('maintenance', 0)} in maint.")

st.markdown("---")

col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    # ── Recent Bills ─────────────────────────────────────────────────────────
    st.markdown("### 🧾 Recent Bills")
    if recent_bills:
        for bill in recent_bills:
            status_icon = "✅" if bill["payment_status"] == "paid" else "⏳"
            status_color = "#27ae60" if bill["payment_status"] == "paid" else "#e67e22"
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;
                        padding:10px 14px; background:#f8f9fa; border-radius:8px; margin-bottom:6px;">
              <div>
                <strong>{bill['bill_number']}</strong>
                <span style="margin-left:10px;color:#666;font-size:.85rem">
                  👤 {bill['customer_name'] or 'Walk-in'}
                </span>
              </div>
              <div style="text-align:right">
                <strong>₹{float(bill['total']):.2f}</strong>
                <span style="margin-left:8px;color:{status_color};font-size:.8rem">
                  {status_icon} {bill['payment_status'].upper()}
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No bills yet today.")

with col_right:
    # ── Alerts ───────────────────────────────────────────────────────────────
    st.markdown("### 🔔 Alerts")
    
    alerts_shown = 0
    
    if int(overdue_data["overdue"]) > 0:
        st.markdown(f"""
        <div class="alert-card alert-red">
          🔴 <div><strong>{overdue_data['overdue']} overdue bill(s)</strong><br>
          <small>Collect payments immediately</small></div>
        </div>""", unsafe_allow_html=True)
        alerts_shown += 1

    if int(pending_data["cnt"]) > 0:
        st.markdown(f"""
        <div class="alert-card alert-orange">
          ⏳ <div><strong>{pending_data['cnt']} pending bill(s)</strong><br>
          <small>₹{float(pending_data['amt']):,.2f} to collect</small></div>
        </div>""", unsafe_allow_html=True)
        alerts_shown += 1

    if int(low_stock["low"]) > 0:
        st.markdown(f"""
        <div class="alert-card alert-orange">
          📦 <div><strong>{low_stock['low']} item(s) low in stock</strong><br>
          <small>Check inventory</small></div>
        </div>""", unsafe_allow_html=True)
        alerts_shown += 1

    for svc in upcoming_service:
        days = int(svc["days_left"].days) if hasattr(svc["days_left"], "days") else int(svc["days_left"])
        cls = "alert-red" if days <= 0 else "alert-orange"
        label = "OVERDUE" if days <= 0 else f"in {days}d"
        st.markdown(f"""
        <div class="alert-card {cls}">
          ⚙️ <div><strong>{svc['machine_name']}</strong><br>
          <small>Service {label} · {svc['next_service_date']}</small></div>
        </div>""", unsafe_allow_html=True)
        alerts_shown += 1

    if alerts_shown == 0:
        st.markdown("""
        <div class="alert-card alert-green">
          ✅ <div><strong>All good!</strong><br>
          <small>No urgent alerts</small></div>
        </div>""", unsafe_allow_html=True)

    # ── Quick Nav ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🚀 Quick Actions")
    st.page_link("pages/01_POS.py", label="🧾 New Bill / POS", use_container_width=True)
    st.page_link("pages/02_Inventory.py", label="📦 Inventory", use_container_width=True)
    st.page_link("pages/03_Labour.py", label="👷 Labour", use_container_width=True)
    st.page_link("pages/04_Machines.py", label="⚙️ Machines", use_container_width=True)
    st.page_link("pages/05_Services.py", label="🛠 Services & Rates", use_container_width=True)
    st.page_link("pages/06_Reports.py", label="📊 Reports", use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#aaa;font-size:.8rem'>"
    f"Bharathi Oil Mill Management System · {today.strftime('%d %B %Y')} · "
    f"Built with Streamlit + PostgreSQL</div>",
    unsafe_allow_html=True
)
