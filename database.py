"""
Database initialization and connection management for Bharathi Oil Mill
Supports both Supabase (PostgreSQL) and local PostgreSQL
"""

import psycopg2
import psycopg2.extras
import streamlit as st
from contextlib import contextmanager
import os


def get_connection():
    """Get database connection from Streamlit secrets or environment variables."""
    db_url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url)
    else:
        conn = psycopg2.connect(
            host=st.secrets.get("DB_HOST", "localhost"),
            port=st.secrets.get("DB_PORT", 5432),
            database=st.secrets.get("DB_NAME", "bharathi_oil_mill"),
            user=st.secrets.get("DB_USER", "postgres"),
            password=st.secrets.get("DB_PASSWORD", "password"),
        )
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Initialize all database tables."""
    with get_db() as conn:
        cur = conn.cursor()

        # ── Services / Mill Services ──────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id SERIAL PRIMARY KEY,
                category VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                rate_per_kg DECIMAL(10,2) NOT NULL,
                unit VARCHAR(20) DEFAULT 'kg',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Customers ─────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                phone VARCHAR(15),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Bills (POS) ───────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id SERIAL PRIMARY KEY,
                bill_number VARCHAR(20) UNIQUE NOT NULL,
                customer_id INTEGER REFERENCES customers(id),
                customer_name VARCHAR(100),
                customer_phone VARCHAR(15),
                subtotal DECIMAL(10,2) DEFAULT 0,
                discount DECIMAL(10,2) DEFAULT 0,
                total DECIMAL(10,2) DEFAULT 0,
                payment_method VARCHAR(20),
                payment_status VARCHAR(20) DEFAULT 'paid',
                reminder_date DATE,
                notes TEXT,
                bill_type VARCHAR(30) DEFAULT 'service',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Bill Items ────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                id SERIAL PRIMARY KEY,
                bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
                service_id INTEGER REFERENCES services(id),
                service_name VARCHAR(100),
                quantity_kg DECIMAL(10,3),
                rate_per_kg DECIMAL(10,2),
                amount DECIMAL(10,2),
                notes TEXT
            );
        """)

        # ── Oil Processing (oil cake buy-back) ────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS oil_processing (
                id SERIAL PRIMARY KEY,
                bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
                seed_type VARCHAR(50),
                input_kg DECIMAL(10,3),
                processing_rate DECIMAL(10,2),
                processing_fee DECIMAL(10,2),
                oil_cake_kg DECIMAL(10,3),
                oil_cake_rate DECIMAL(10,2),
                oil_cake_value DECIMAL(10,2),
                net_amount DECIMAL(10,2),
                direction VARCHAR(10)
            );
        """)

        # ── Inventory ─────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                item_name VARCHAR(100) NOT NULL,
                category VARCHAR(50),
                quantity DECIMAL(10,3) DEFAULT 0,
                unit VARCHAR(20) DEFAULT 'kg',
                rate_per_unit DECIMAL(10,2) DEFAULT 0,
                reorder_level DECIMAL(10,3) DEFAULT 0,
                notes TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Inventory Transactions ────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES inventory(id),
                transaction_type VARCHAR(20),
                quantity DECIMAL(10,3),
                rate DECIMAL(10,2),
                total_value DECIMAL(10,2),
                reference_bill VARCHAR(20),
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Labourers ─────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS labourers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(15),
                daily_wage DECIMAL(10,2) DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Labour Attendance ─────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS labour_attendance (
                id SERIAL PRIMARY KEY,
                labourer_id INTEGER REFERENCES labourers(id),
                work_date DATE NOT NULL,
                present BOOLEAN DEFAULT TRUE,
                days_worked DECIMAL(4,2) DEFAULT 1.0,
                wage_paid DECIMAL(10,2) DEFAULT 0,
                advance DECIMAL(10,2) DEFAULT 0,
                payment_method VARCHAR(20) DEFAULT 'cash',
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Machines ──────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(100) NOT NULL,
                machine_type VARCHAR(50),
                serial_number VARCHAR(50),
                purchase_date DATE,
                last_service_date DATE,
                next_service_date DATE,
                status VARCHAR(20) DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Machine Maintenance ───────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_maintenance (
                id SERIAL PRIMARY KEY,
                machine_id INTEGER REFERENCES machines(id),
                maintenance_date DATE NOT NULL,
                maintenance_type VARCHAR(50),
                description TEXT,
                cost DECIMAL(10,2) DEFAULT 0,
                technician VARCHAR(100),
                next_service_date DATE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Expenses ──────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                expense_date DATE NOT NULL,
                category VARCHAR(50),
                description TEXT,
                amount DECIMAL(10,2),
                payment_method VARCHAR(20) DEFAULT 'cash',
                reference VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Seed default services ─────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM services")
        count = cur.fetchone()[0]
        if count == 0:
            default_services = [
                # Grain milling
                ('grain_milling', 'Wheat Milling', 2.50, 'kg'),
                ('grain_milling', 'Rice Milling', 2.00, 'kg'),
                ('grain_milling', 'Kambu (Pearl Millet) Milling', 2.50, 'kg'),
                ('grain_milling', 'Kezhvaragu (Ragi) Milling', 2.50, 'kg'),
                ('grain_milling', 'Corn Milling', 2.00, 'kg'),
                # Spice grinding
                ('spice_grinding', 'Chilli Powder Grinding', 5.00, 'kg'),
                ('spice_grinding', 'Masala Powder Grinding (Mix)', 5.00, 'kg'),
                ('spice_grinding', 'Coriander Powder Grinding', 4.50, 'kg'),
                # Dhal splitting
                ('dhal_splitting', 'Ulunthu (Urad) Splitting', 3.00, 'kg'),
                ('dhal_splitting', 'Toor Dhal Splitting', 3.00, 'kg'),
                # Oil extraction
                ('oil_extraction', 'Groundnut Oil Extraction', 8.00, 'kg'),
                ('oil_extraction', 'Sesame Oil Extraction', 10.00, 'kg'),
                ('oil_extraction', 'Coconut Oil Extraction', 7.00, 'kg'),
                ('oil_extraction', 'Ilupai (Mahua) Oil Extraction', 8.00, 'kg'),
                ('oil_extraction', 'Neem Oil Extraction', 8.00, 'kg'),
                ('oil_extraction', 'Castor Oil Extraction', 9.00, 'kg'),
                # Oil cake grinding
                ('oil_cake_grinding', 'Oil Cake Grinding', 3.00, 'kg'),
                # Wet grinding
                ('wet_grinding', 'Idiyappam Rice Grinding', 4.00, 'kg'),
                ('wet_grinding', 'Idli/Dosa Batter Grinding', 3.50, 'kg'),
            ]
            for svc in default_services:
                cur.execute(
                    "INSERT INTO services (category, name, rate_per_kg, unit) VALUES (%s, %s, %s, %s)",
                    svc
                )

        # ── Seed default inventory items ──────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM inventory")
        count = cur.fetchone()[0]
        if count == 0:
            default_inventory = [
                ('Groundnut Oil Cake', 'oil_cake', 0, 'kg', 12.00),
                ('Sesame Oil Cake', 'oil_cake', 0, 'kg', 10.00),
                ('Coconut Oil Cake', 'oil_cake', 0, 'kg', 8.00),
                ('Ilupai Oil Cake', 'oil_cake', 0, 'kg', 6.00),
                ('Neem Oil Cake', 'oil_cake', 0, 'kg', 5.00),
                ('Groundnut Oil (Retail)', 'oil_product', 0, 'litre', 180.00),
                ('Sesame Oil (Retail)', 'oil_product', 0, 'litre', 220.00),
                ('Coconut Oil (Retail)', 'oil_product', 0, 'litre', 160.00),
                ('Packing Covers', 'supplies', 100, 'pcs', 2.00),
            ]
            for item in default_inventory:
                cur.execute(
                    "INSERT INTO inventory (item_name, category, quantity, unit, rate_per_unit) VALUES (%s,%s,%s,%s,%s)",
                    item
                )

        # ── Seed default machines ─────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM machines")
        count = cur.fetchone()[0]
        if count == 0:
            default_machines = [
                ('Flour Mill #1', 'grain_milling', 'active'),
                ('Flour Mill #2', 'grain_milling', 'active'),
                ('Spice Grinder #1', 'spice_grinding', 'active'),
                ('Dhal Splitter #1', 'dhal_splitting', 'active'),
                ('Oil Rotary #1 - Groundnut', 'oil_extraction', 'active'),
                ('Oil Rotary #2 - Sesame', 'oil_extraction', 'active'),
                ('Oil Rotary #3 - Coconut', 'oil_extraction', 'active'),
                ('Oil Rotary #4 - Ilupai', 'oil_extraction', 'active'),
                ('Oil Rotary #5 - Multi', 'oil_extraction', 'active'),
                ('Oil Rotary #6 - Multi', 'oil_extraction', 'active'),
                ('Oil Cake Grinder #1', 'oil_cake_grinding', 'active'),
                ('Wet Grinder #1 - Idiyappam', 'wet_grinding', 'active'),
            ]
            for m in default_machines:
                cur.execute(
                    "INSERT INTO machines (machine_name, machine_type, status) VALUES (%s,%s,%s)",
                    m
                )

        conn.commit()
        print("✅ Database initialized successfully.")


def generate_bill_number():
    """Generate sequential bill number like BOM-20241114-0001"""
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM bills WHERE bill_number LIKE %s",
            (f"BOM-{today}-%",)
        )
        count = cur.fetchone()[0]
    return f"BOM-{today}-{count+1:04d}"
